#!/usr/bin/env python3
"""DSH acceptance for daily power return. Snapshot/assessment never synthesize input or send a broadcast."""
import argparse
import hashlib
import json
import re
import shlex
from decimal import Decimal
import subprocess
import sys
from pathlib import Path

import argparse

import hashlib

import json

import os

import shutil

import tempfile

import re

import shlex

import subprocess

import sys

import threading

import time

import xml.etree.ElementTree as ET

from pathlib import Path

PKG = "com.naozho.clock"

RX = PKG + "/.mode.ConfirmedPowerReceiver"

ACTION = PKG + ".action.CONFIRMED_POWER_DOUBLE"

ADMIN = PKG + "/.display.ClockDeviceAdmin"

PERM = "android.permission.STATUS_BAR_SERVICE"

FREEME = "com.droiclaw.launcher3/com.freeme.launcher.FreemeLauncher"

CANDIDATE = "8bcf50a524f58b6c8180d699f47a18fd096d94b7b12d737d1a60710d189597d4"

CERT = "801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578"

APP_UID = "10191"

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def one(regex, raw, label):
    match = re.findall(regex, raw, re.M)
    require(len(match) == 1, label + " missing or ambiguous")
    return match[0]

def receiver_ok(raw):
    require(re.search(r"^1 receivers found:", raw, re.M), "expected exactly one receiver")
    for field in ["name=" + PKG + ".mode.ConfirmedPowerReceiver", "packageName=" + PKG,
                  "enabled=true exported=true", "permission=" + PERM]:
        require(re.search(r"(?m)^\s*" + re.escape(field) + r"(?:\s|$)", raw),
                "installed receiver field unconfirmed: " + field)

def find_signer(explicit):
    if explicit:
        tool = Path(explicit)
    else:
        found = shutil.which("apksigner")
        if found:
            return found
        roots = [os.environ.get(key) for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT")]
        if os.environ.get("LOCALAPPDATA"):
            roots.append(str(Path(os.environ["LOCALAPPDATA"]) / "Android/Sdk"))
        for root in filter(None, roots):
            for tool in sorted((Path(root) / "build-tools").glob("*/apksigner*"), reverse=True):
                if tool.name in ("apksigner", "apksigner.bat") and tool.is_file():
                    return str(tool)
        raise RuntimeError("Android SDK Build Tools apksigner unavailable; specify --apksigner")
    require(tool.is_file(), "apksigner not found")
    return str(tool.resolve())

def signed_candidate(apk, signer):
    require(hashlib.sha256(apk.read_bytes()).hexdigest() == CANDIDATE, "pulled APK SHA-256 differs")
    run = subprocess.run([signer, "verify", "--verbose", "--print-certs", str(apk)],
                         capture_output=True, text=True, errors="replace", timeout=60)
    require(run.returncode == 0 and "Verified using v2 scheme (APK Signature Scheme v2): true" in run.stdout
            and re.findall(r"(?m)^Signer #\d+ certificate SHA-256 digest: (\w+)\s*$",run.stdout) == [CERT],
            "installed APK signature / expected signer not verified")

class Device:
    def __init__(self, serial):
        self.serial = serial

    def shell(self, *args, timeout=20):
        result = subprocess.run(["adb", "-s", self.serial, "shell", shlex.join(args)],
                                capture_output=True, timeout=timeout, encoding="utf-8", errors="replace")
        # Never persist the full dumps, unrelated windows, SharedPreferences or adb identifiers.
        require(result.returncode == 0, "ADB command failed: " + args[0])
        return result.stdout.strip()

    def local_identity(self):
        # Wireless ADB ports can change after the module-manager reboot. Keep only a local
        # digest of the shell-user Android ID; never log the identifier or include it in a kit.
        value = self.shell("settings", "--user", "0", "get", "secure", "android_id")
        if not re.fullmatch(r"[0-9a-fA-F]{8,16}", value):
            value = "adb-endpoint:" + self.serial
        return hashlib.sha256(("p095:" + value).encode()).hexdigest()

    def installed(self, signer):
        require(self.shell("getprop", "ro.product.device") == "CPDAY10", "unexpected device")
        require(self.shell("getprop", "ro.build.version.sdk") == "36", "unexpected SDK")
        require(self.shell("am", "get-current-user") == "0", "unexpected user")
        owners = self.shell("dpm", "list-owners")
        require(re.search(r"User\s+0:\s+admin=" + re.escape(ADMIN) + r",DeviceOwner\b", owners), "owner changed")
        apk = one(r"^package:(/[^\s]+/base\.apk)$", self.shell("pm", "path", "--user", "0", PKG), "base APK")
        with tempfile.TemporaryDirectory() as temp:
            local = Path(temp) / "base.apk"
            pull = subprocess.run(["adb", "-s", self.serial, "pull", apk, str(local)], capture_output=True, timeout=90)
            require(pull.returncode == 0, "could not read installed APK")
            signed_candidate(local, signer)
        p = self.shell("dumpsys", "package", PKG)
        require(re.search(r"(?m)^\s*versionCode=28\b", p) and
                re.search(r"(?m)^\s*versionName=0\.6\.13-dev\s*$", p), "installed version differs")
        uid = one(r"^package:com\.naozho\.clock uid:(\d+)$",
                  self.shell("cmd", "package", "list", "packages", "--user", "0", "-U", PKG), "app UID")
        receivers = self.shell("cmd", "package", "query-receivers", "--user", "0", "-a", ACTION, "-n", RX)
        receiver_ok(receivers)
        require(uid == APP_UID, "app UID differs from CPDAY10 baseline")
        return uid

    def prefs(self):
        # run-as is the debuggable APK's own identity. Only selected XML entries leave the phone.
        fields = "^( *<(boolean|string|long) name=\"(managed_lock|managed_home|native_home|android|mode_since)\")"
        rows = self.shell("run-as", PKG, "grep", "-E", fields, "shared_prefs/desktop_mode.xml")
        return {e.attrib["name"]: e.get("value", e.text or "") for e in ET.fromstring("<prefs>"+rows+"</prefs>")}

    def state(self):
        services = self.shell("dumpsys", "activity", "activities")
        lock = one(r"^\s*mLockTaskModeState=(?:LOCK_TASK_MODE_)?(LOCKED|NONE|PINNED)\s*$", services, "lock state")
        windows = self.shell("dumpsys", "window", "displays")
        if "mCurrentFocus=" not in windows:
            windows = self.shell("dumpsys", "window", "windows")
        component = one(r"^\s*mCurrentFocus=Window\{[^\s{}]+ u0 ([^\s{}]+)\}\s*$", windows, "focus")
        clock = {"."+base for base in ["MainActivity", "mode.PowerClockEntry"]}
        clock |= {PKG + name for name in clock}
        focus = "Freeme" if component == FREEME else "other"
        if component.startswith(PKG + "/") and component.split("/", 1)[1] in clock:
            focus = "clock"
        return lock, focus

def log_stage(lines):
    # Only output stage counters. No full device log escapes to a report.
    stages = {key:sum(message in line for line in lines.splitlines()) for key, message in {
        "app_requested":"Confirmed double delivered; awaiting foreground and lock readback",
        "focus_commit":"Double committed on foreground focus",
        "guard_rejected":"Double rejected at receiver; no activity requested",
        "expired":"Double expired or became ineligible before focus",
    }.items()}
    stages["lock80"] = sum("Lock Task after start: state=LOCKED independent=true flags=80 (" in line
                           and "allowlist=[com.naozho.clock]" in line for line in lines.splitlines())
    return stages

MOD = "/data/adb/modules/naozho_power_daily"
NAME = "naozho-power-daily-1.0.0.zip"
CLOCK = {PKG+"/.MainActivity",PKG+"/"+PKG+".MainActivity",PKG+"/.mode.PowerClockEntry",PKG+"/"+PKG+".mode.PowerClockEntry"}

def optional(d, *args):
    try:
        return d.shell(*args)
    except (RuntimeError, subprocess.SubprocessError):
        return ""

def local_package():
    home = Path(__file__).resolve().parent
    path = home/NAME
    expected = one(r"^([0-9a-f]{64})  "+re.escape(NAME)+r"$", (home/"CONTENTS-SHA256.txt").read_text(), "module in manifest")
    require(hashlib.sha256(path.read_bytes()).hexdigest()==expected, "local module digest differs")
    return path, expected

def stage(d):
    path, digest = local_package()
    dest = "/sdcard/Download/"+NAME
    if d.shell("sh","-c","if [ -e "+dest+" ]; then echo exists; fi") != "exists":
        subprocess.run(["adb","-s",d.serial,"push",str(path),dest],check=True,timeout=90)
    require(d.shell("sha256sum",dest).split()[0]==digest,"staged module differs; inspect existing file")
    print("Staged for manual review in Downloads:", NAME)

def get_policy(dump):
    # DPM emits per-admin and resolved values. Require agreement inside user 0.
    flags=[]
    user=None
    local=False
    for line in dump.splitlines():
        if line.strip()=="Local Policies:":
            local=True
            user=None
        elif re.fullmatch(r"\s*User \d+:\s*",line):
            user=line.strip()
        elif line.strip() in ("Global Policies:","Device-wide Policies:"):
            local=False
        elif local and user=="User 0:":
            for packages, features in re.findall(r"LockTaskPolicy\s*\{mPackages=\s*([^;]+);\s*mFlags=\s*(\d+)\s*\}",line):
                flags.append(int(features) if packages.strip()==PKG else -1)
    return flags[0] if flags and len(set(flags))==1 else None

def battery_values(raw):
    def field(name):
        match=re.search(r"(?m)^\s*"+name+r":\s*(-?\d+)\s*$",raw)
        return int(match[1]) if match else None
    connected=re.findall(r"(?m)^\s*(?:AC|USB|Wireless|Dock) powered:\s*(true|false)\s*$",raw)
    charge=field("Charge counter")
    return dict(level=field("level"), temperature_tenths_c=field("temperature"), charge_uah=charge if charge and charge>0 else None,
                plugged=any(s=="true" for s in connected) if connected else None)

def numeric(s):
    return int(s) if s.isdecimal() else None

def app_markers(lines):
    seen=[]
    for line in lines.splitlines():
        m=re.match(r"^\s*(\d+\.\d+)\s",line)
        if not m:
            continue
        for label, count in log_stage(line).items():
            if count:
                seen.append([int(Decimal(m[1])*1000000),label])
    return seen


def inspect_page(d):
    focus=one(r"^\s*mCurrentFocus=Window\{[^ {}]+ u0 ([^ {}\n]+)\}\s*$",d.shell("dumpsys","window","displays"),"focus")
    require(re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+/[A-Za-z.][A-Za-z0-9_.$]*",focus),"no ordinary activity")
    pkg, cls=focus.split("/")
    rows=d.shell("cmd","package","list","packages","-3","--user","0",pkg)
    require("package:"+pkg in rows.splitlines(),"expected third-party package")
    raw=d.shell("pm","path","--user","0",pkg)
    require(len(raw.splitlines())==1,"split build needs separate review")
    base=one(r"^package:(/[^\s]+/base\.apk)$",raw,"base APK")
    digest=d.shell("sha256sum",base).split()[0]
    require(re.fullmatch(r"[0-9a-f]{64}",digest),"no APK digest")
    print("For Codex review only:",pkg+"/"+(pkg+cls if cls.startswith(".") else cls),digest)


def snapshot(d):
    require(d.shell("getprop","ro.product.device")=="CPDAY10" and d.shell("am","get-current-user")=="0","wrong target")
    acts=d.shell("dumpsys","activity","activities")
    lock=one(r"^\s*mLockTaskModeState=(?:LOCK_TASK_MODE_)?(NONE|PINNED|LOCKED)\s*$",acts,"lock")
    lst=re.search(r"(?m)^\s*mLockTaskPackages \(userId:packages\)= *\n((?:[ \t]*u\d+:\[[^\n]*\]\s*\n?)*)",acts)
    allow=bool(lst and re.search(r"(?m)^\s*u0:\[com\.naozho\.clock\]\s*$",lst[1]))
    focus=one(r"^\s*mCurrentFocus=Window\{[^ {}]+ u0 ([^ {}\n]+)\}\s*$",d.shell("dumpsys","window","displays"),"focus")
    proc_names=d.shell("sh","-c",r"ps -A -o PID,ARGS | /system/bin/sed -nE '1p; s/^[[:space:]]*([0-9]+)[[:space:]]+naozho\.power\.daily[[:space:]]*$/\1/p'")
    lines=proc_names.splitlines()
    require(lines and re.fullmatch(r"\s*PID\s+(?:ARGS|COMMAND|CMDLINE)\s*",lines[0]),"process table unavailable")
    pids=lines[1:]
    require(all(v.isdecimal() for v in pids),"ambiguous listener identity")
    pid=int(pids[0]) if len(pids)==1 and pids[0].isdigit() else None
    def root(cmd):
        return optional(d,"su","-c",cmd)
    root_ok=root("id -u")=="0"
    require(root_ok,"root readback unavailable")
    status=root("cat "+MOD+"/status")
    match=re.fullmatch(r"state=([A-Za-z0-9_]+) probes=(\d+) attempts=(\d+) delivered=(\d+) skipped=(\d+)",status)
    report=dict(outcome=match[1],probes=int(match[2]),attempts=int(match[3]),delivered=int(match[4]),vetoes=int(match[5])) if match else None
    counters={}
    if pid is not None:
        stat=root(f"cat /proc/{pid}/stat").rpartition(") ")[2].split()
        require(len(stat)>=20,"listener process changed during snapshot")
        counters.update(cpu_ticks=int(stat[11])+int(stat[12]), start_ticks=int(stat[19]))
        proc=root(f"cat /proc/{pid}/status")
        for label,key in [("VmRSS","rss_kib"),("Threads","threads")]:
            m=re.search(r"(?m)^"+label+r":\s*(\d+)",proc)
            counters[key]=int(m[1]) if m else None
        counters["fd_count"]=numeric(root(f"ls -1 /proc/{pid}/fd | wc -l").strip())
    size=root("wc -c "+MOD+"/daily.log "+MOD+"/daily.log.1 2>/dev/null; true")
    log_bytes=sum(int(n) for n in re.findall(r"(?m)^\s*(\d+) /data/adb/modules/naozho_power_daily/daily\.log(?:\.1)?\s*$",size))
    markers=app_markers(d.shell("logcat","-d","-t","250","-b","main","-v","epoch","-v","usec","--uid=10191",
                                "-s","NaozhoPowerReturn:I","NaozhoMode:I"))
    epoch_us=int(Decimal(d.shell("date","+%s.%6N"))*1000000)
    return dict(markers=markers,epoch_us=epoch_us,device=d.local_identity(),boot=int(d.shell("settings","get","global","boot_count")),
                uptime_s=float(d.shell("cat","/proc/uptime").split()[0]), clock_hz=numeric(optional(d,"getconf","CLK_TCK")),
                owner=bool(re.search(r"User\s+0:\s+admin="+re.escape(ADMIN)+r",DeviceOwner\b",d.shell("dpm","list-owners"))),
                enforcing=d.shell("getenforce")=="Enforcing", lock=lock, allow_clock_only=allow,
                flags=get_policy(d.shell("dumpsys","device_policy")),
                focus="clock" if focus in CLOCK else "Freeme" if focus==FREEME else "other",
                listener_count=len(pids),pid=pid, resource=counters,report=report,log_bytes=log_bytes,
                armed=root("if [ -f "+MOD+"/armed ]; then echo yes; fi")=="yes",
                sys_wakeup_count=numeric(root("timeout 2 cat /sys/power/wakeup_count")),
                battery=battery_values(d.shell("dumpsys","battery")))

def assess(a,b,expected,touch):
    require(a["device"]==b["device"] and a["boot"]==b["boot"] and b["uptime_s"]>a["uptime_s"],"different device/boot or snapshot order")
    require(a["owner"] and b["owner"] and a["enforcing"] and b["enforcing"],"Owner or Enforcing missing")
    require(a["armed"] and b["armed"] and a["listener_count"]==b["listener_count"]==1 and a["pid"]==b["pid"]
            and a["resource"]["start_ticks"]==b["resource"]["start_ticks"],"listener restart or incomplete readback")
    require(a["report"] and b["report"],"missing listener evidence")
    delta=tuple(b["report"][s]-a["report"][s] for s in ("attempts","delivered"))
    if expected=="return":
        require(a["lock"]=="NONE" and a["focus"]!="clock" and b["lock"]=="LOCKED" and b["focus"]=="clock"
                and b["flags"]==80 and b["allow_clock_only"] and delta==(1,1),"single return/focus/flags/allowlist unconfirmed")
        labels=[label for stamp,label in b["markers"] if a["epoch_us"] < stamp <= b["epoch_us"]]
        require(all(labels.count(k)==1 for k in ("app_requested","focus_commit","lock80"))
                and "expired" not in labels and labels.count("guard_rejected")==b["report"]["probes"]-a["report"]["probes"], "fresh app request/focus/lock receipt missing or ambiguous")
        require(touch,"DSH must verify actual touch on the clock")
    else:
        require(delta==(0,0) and b["lock"]==a["lock"] and b["focus"]==a["focus"],"unexpected dispatch or mode change")
    print("PASS",expected,"actual touch recorded" if touch else "")

def consumption(a,b):
    require(a["device"]==b["device"] and a["boot"]==b["boot"],"measure each interval within one boot")
    seconds=b["uptime_s"]-a["uptime_s"]
    require(seconds>0,"snapshot order")
    def delta(x,y): return None if x is None or y is None else y-x
    out={"hours":round(seconds/3600,3),"system_wakeups_delta":delta(a["sys_wakeup_count"],b["sys_wakeup_count"]),
         "log_bytes_at_end":b["log_bytes"],"worker_at_end":b["resource"],"battery_start":a["battery"],"battery_end":b["battery"]}
    if a["battery"]["plugged"] is False and b["battery"]["plugged"] is False:
        for key in ("level","charge_uah"):
            x=delta(a["battery"][key],b["battery"][key])
            if x is not None: out[key+"_used_per_hour"]=round(-x*3600/seconds,3)
    if a["resource"] and a["resource"].get("start_ticks")==b["resource"].get("start_ticks") and a["pid"]==b["pid"]:
        ticks=delta(a["resource"]["cpu_ticks"],b["resource"]["cpu_ticks"])
        out["cpu_ticks_delta"]=ticks
        if a["clock_hz"] and a["clock_hz"]==b["clock_hz"]: out["mean_cpu_percent_one_core"]=100*ticks/a["clock_hz"]/seconds
    print(json.dumps(out,indent=2))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("preflight","stage","snapshot","profile","inspect-page"):
        c=sub.add_parser(name); c.add_argument("--serial",required=True)
        if name in ("preflight","stage","profile"): c.add_argument("--apksigner")
        if name=="snapshot": c.add_argument("--out",required=True,type=Path)
        if name=="profile": c.add_argument("--review",required=True,type=Path)
    for name in ("assess","consumption"):
        c=sub.add_parser(name)
        c.add_argument("before",type=Path); c.add_argument("after",type=Path)
        if name=="assess":
            c.add_argument("--expect",choices=("return","no-return"),required=True)
            c.add_argument("--touch-confirmed",action="store_true")
    a=p.parse_args()
    if a.command in ("assess","consumption"):
        before,after=[json.loads(f.read_text(encoding="utf-8")) for f in (a.before,a.after)]
        if a.command=="assess": assess(before,after,a.expect,a.touch_confirmed)
        else: consumption(before,after)
        return
    d=Device(a.serial)
    if a.command=="preflight":
        print("installed identity checked; user 0 Owner; UID",d.installed(find_signer(a.apksigner)))
    elif a.command=="stage":
        d.installed(find_signer(a.apksigner))
        stage(d)
    elif a.command=="inspect-page": inspect_page(d)
    elif a.command=="profile":
        # Only pinned, reviewed third-party components. Never transmit free-form shell code.
        d.installed(find_signer(a.apksigner))
        require(a.review.stat().st_size<=4096,"profile too large")
        pages=a.review.read_text(encoding="ascii").splitlines()
        pat=r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+/[A-Za-z][A-Za-z0-9_.$]+ [a-f0-9]{64}"
        require(len(pages)<=16 and all(re.fullmatch(pat,l) for l in pages) and len({l.split()[0] for l in pages})==len(pages),"invalid reviewed profile")
        require(d.shell("su","-c","if [ -e "+MOD+"/armed ]; then echo active; fi")!="active","disarm before updating page review")
        # Script and destination are constants. Input travels over stdin, never through a shell argument.
        cmd="umask 077; test -d "+MOD+" && cat > "+MOD+"/pages.tmp && mv -f "+MOD+"/pages.tmp "+MOD+"/pages"
        subprocess.run(["adb","-s",a.serial,"shell","-T",shlex.join(["su","-c",cmd])],
                       input=("\n".join(pages)+"\n").encode("ascii"),check=True,timeout=15)
    else:
        state=snapshot(d)
        with a.out.open("x",encoding="utf-8") as f: json.dump(state,f,indent=2)
        print(a.out, state["focus"],state["lock"],"flags",state["flags"],"workers",state["listener_count"],state["report"])
if __name__=="__main__":
    try: main()
    except (RuntimeError,OSError,ValueError,subprocess.SubprocessError) as e: sys.exit("STOP: "+str(e))
