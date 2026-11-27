#!/usr/bin/env python3
"""DSH acceptance for daily power return. Snapshot/assessment never synthesize input or send a broadcast."""
import argparse
import hashlib
import json
import re
import shlex
import secrets
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
WINDOW_CHECK="CLASSPATH="+MOD+"/power.jar /system/bin/app_process64 /system/bin com.naozho.power.DailyWindowCheck"
NAME = "naozho-power-daily-1.0.4.zip"
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
    focus=one(r"^\s*mCurrentFocus=Window\{[^ {}]+ u0 ([^{}\n]+)\}\s*$",d.shell("dumpsys","window","displays"),"focus")
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


PRESETS=(400,500,600,700,800,1000)
VETO_ROW=(r"type=(?:[A-Z_]{1,48}|unknown) owner=[a-zA-Z0-9_.]{1,160}"
          r"(?: (?:visible|onscreen|surface|focus|focusable|touchable|obscured|edge)=(?:true|false|unknown)){8}"
          r" class=(?:unknown|inactive|secure|app|wallpaper|decor|panel_or_ime|protected|dialog|unclassified)")

COUNTS=("visible_window_count","decorative_window_count","interactive_window_count","blocking_window_count","unknown_window_count","omitted_rows")
COUNT_FIELDS="".join(" "+key+r"=(-1|\d+)" for key in COUNTS)
ROW_SUFFIX=(r" class_reason=[a-z_]{1,48} parser_source=[a-z_]{1,32} field_missing=[a-z_+]{1,120}"
            r" focusable_parse_status=[a-z_]{1,32} touchable_parse_status=[a-z_]{1,32}"
            r" geometry_valid=(?:true|false) touch_region=[a-z_]{1,24}"
            r"(?: collector_command=dumpsys_window_-a_visible collector_source=wms_visible window_block_index=\d+"
            r" flags_line_found=(?:true|false) flags_parse_status=[a-z_]{1,32} flags_source=[a-z_]{1,32}"
            r" flags_value_count=\d+(?: flags_line_number=-?\d+ attrs_brace_depth=-?\d+ attrs_parse_status=(?:balanced|unclosed|missing|duplicate))? parser_error=[a-z_]{1,48})? actual_blocker=(?:true|false)")

SNAPSHOT_META=(r"snapshot_command=dumpsys_window_-a_visible snapshot_first_line=(?:unavailable|empty|window_header|redacted_prefix|Dump_time_?:_?\d{4}-\d\d-\d\d_\d\d:\d\d:\d\d\.\d{3})"
               r" header_found=(?:true|false) header_line_number=\d+ footer_found=(?:true|false) footer_line_number=\d+"
               r" snapshot_parse_status=[a-z_]{1,48} window_block_count=\d+")

def snapshot_header(text):
    head,has,meta=text.partition(" snapshot_command=")
    if not has: return head,{}
    meta="snapshot_command="+meta
    require(re.fullmatch(SNAPSHOT_META,meta),"unrecognized snapshot diagnostic")
    fields=dict(field.split("=",1) for field in meta.split())
    for key in ("header_line_number","footer_line_number","window_block_count"): fields[key]=int(fields[key])
    for key in ("header_found","footer_found"): fields[key]=fields[key]=="true"
    if fields["snapshot_first_line"].startswith("Dump_time"):
        fields["snapshot_first_line"]=fields["snapshot_first_line"].replace("_"," ")
    return head,fields

def window_rows(rows,extended):
    require(len(rows)<=(24 if extended else 9) and all(re.fullmatch(VETO_ROW+(ROW_SUFFIX if extended else ""),r) for r in rows),"window metadata format unknown")
    return [dict(item.split("=",1) for item in r.split()) for r in rows]

def veto_details(text):
    if not text: return None
    lines=text.splitlines()
    base=r"last_veto_reason=([A-Za-z0-9_]{1,100}) last_veto_at=(\d{1,15}) extra_windows=(-?\d+) down_gap_ms=(-?\d+)"
    header,meta=snapshot_header(lines[0])
    extended=re.fullmatch(base+COUNT_FIELDS,header)
    first=extended or re.fullmatch(base,lines[0])
    require(first,"veto metadata format unknown")
    detail=dict(last_veto_reason=first[1],last_veto_at=int(first[2]),extra_windows=int(first[3]),
                down_gap_ms=int(first[4]),windows=window_rows(lines[1:],bool(extended)))
    if extended: detail.update({key:int(extended[i]) for i,key in enumerate(COUNTS,5)})
    detail.update(meta)
    return detail

def check_details(text,standalone):
    if not text: return None
    lines=text.splitlines()
    head=r"decision=([a-z_]{1,80})" if standalone else r"checked_at=(\d{1,15}) delivered=(\d+)"
    header,meta=snapshot_header(lines[0])
    m=re.fullmatch(head+COUNT_FIELDS,header)
    require(m,"window checks unavailable")
    result={"windows":window_rows(lines[1:],True),**meta}
    if standalone: result["decision"]=m[1]
    else: result.update(checked_at=int(m[1]),delivered=int(m[2]))
    result.update({key:int(m[i]) for i,key in enumerate(COUNTS,2 if standalone else 3)})
    return result

def policy_return(text):
    if not text:
        return None
    m=re.fullmatch(r"window_ms=(\d+) down_gap_ms=(\d+) policy_count=2 delivered=(\d+)",text)
    require(m and int(m[1]) in PRESETS and 40<=int(m[2])<int(m[1]),"unconfirmed system policy receipt")
    return dict(window_ms=int(m[1]),down_gap_ms=int(m[2]),policy_count=2,delivered=int(m[3]))

# Use a single WMS read. Headers are deleted on the phone. The host only exports
# the two SystemUI bars, with public flag names/numbers and bounded rectangle syntax.
BAR_SLICE=r"""set -o pipefail; dumpsys window -a visible | /system/bin/sed -nE '
/^  Window #/ { s/.*/WIN/; p; d; }
/^    mOwnerUid=/ { / package=com\.android\.systemui( |$)/s/.*/SYSTEMUI/p; d; }
/^[[:blank:]]*mAttrs=\{/ {
 h
 s/.* ty=([A-Z_]+).*/TYPE \1/p
 g
 s/^.*[[:blank:]](fl|flags)[[:blank:]]*=[[:blank:]]*([^}]*).*/INLINE \2/p
 d
}
/^[[:blank:]]*(fl|flags)[[:blank:]]*=/ { s/^[[:blank:]]*(fl|flags)[[:blank:]]*=[[:blank:]]*/LINE /; p; d; }
/^[[:blank:]]*(mTouchableInsets=|touchable region=)/p
s/^  mBlurEnabled=(true|false)[[:blank:]]*$/END/p'"""
PUBLIC_FLAGS=set("ALLOW_LOCK_WHILE_SCREEN_ON DIM_BEHIND BLUR_BEHIND NOT_FOCUSABLE NOT_TOUCHABLE NOT_TOUCH_MODAL TOUCHABLE_WHEN_WAKING KEEP_SCREEN_ON LAYOUT_IN_SCREEN LAYOUT_NO_LIMITS FULLSCREEN FORCE_NOT_FULLSCREEN DITHER SECURE SCALED IGNORE_CHEEK_PRESSES LAYOUT_INSET_DECOR ALT_FOCUSABLE_IM WATCH_OUTSIDE_TOUCH SHOW_WHEN_LOCKED SHOW_WALLPAPER TURN_SCREEN_ON DISMISS_KEYGUARD SPLIT_TOUCH HARDWARE_ACCELERATED LOCAL_FOCUS_MODE LAYOUT_IN_OVERSCAN TRANSLUCENT_STATUS TRANSLUCENT_NAVIGATION SLIPPERY LAYOUT_ATTACHED_IN_DECOR DRAWS_SYSTEM_BAR_BACKGROUNDS".split())

def module_bar_fields(d):
    output=d.shell("su","-c",WINDOW_CHECK+" --bar-fields")
    if re.fullmatch(r"error=[a-z_]{1,80}",output): raise RuntimeError(output)
    result=[]
    for line in output.splitlines():
        match=re.fullmatch(r"bar=(NAVIGATION_BAR|STATUS_BAR) source=([a-z_]+) status=([a-z_]+) flags=([A-Za-z0-9_,-]+) region=([a-z_]+)",line)
        require(match,"unexpected bar diagnostic")
        flags=match[4].split(",") if match[3]=="parsed" else []
        require(all(t.removeprefix("FLAG_") in PUBLIC_FLAGS or re.fullmatch(r"-?[0-9]{1,10}|0[xX][0-9a-fA-F]{1,8}|(?=.*[0-9])[0-9a-fA-F]{1,8}",t) for t in flags),"unknown field in sanitized output")
        result.append(dict(type=match[1],flags_source=match[2],flags_parse_status=match[3],public_flags=flags,touch_region=match[5]))
    require(sorted(row["type"] for row in result)==["NAVIGATION_BAR","STATUS_BAR"],"bar coverage incomplete")
    return {"scope":"two_systemui_bars","collector_source":"wms_visible","bars":result}

def bar_sample(d):
    require(d.shell("getprop","ro.product.device")=="CPDAY10" and d.shell("am","get-current-user")=="0","wrong device/user")
    text=d.shell("/system/bin/sh","-c",BAR_SLICE)
    require(len(text)<131072 and text.splitlines().count("END")==1,"incomplete WMS fields")
    result=[]; trusted=False; active=None
    for line in text.splitlines():
        if line=="END": break
        if line=="WIN": trusted=False; active=None
        elif line=="SYSTEMUI": trusted=True
        elif line.startswith("TYPE "):
            active=None
            if trusted and line[5:] in ("STATUS_BAR","NAVIGATION_BAR"):
                active={"type":line[5:],"public_flags":[],"insets":[],"regions":[]}
                result.append(active)
        elif active is not None:
            line=line.strip()
            if line.startswith(("LINE ","INLINE ")) or line in ("LINE","INLINE"):
                source,_,value=line.partition(" ")
                value=re.split(r"\s+(?:pfl|sysui|vsysui|apr|bhv|fitTypes|fitSides)=",value,1)[0].rstrip("}").strip()
                # Keep separators and known flags; an unexpected string never leaves memory.
                parts=re.split(r"([\s|,]+)",value)
                safe="".join(t if not t or re.fullmatch(r"[\s|,]+|0[xX][0-9a-fA-F]{1,8}|-?\d{1,10}",t)
                             or re.fullmatch(r"(?=.*\d)[0-9a-fA-F]{1,8}",t)
                             or t.removeprefix("FLAG_") in PUBLIC_FLAGS else "<unrecognized>" for t in parts)
                active["public_flags"].append([source,safe[:512]])
            elif line.startswith("mTouchableInsets="):
                active["insets"].append(line if re.fullmatch(r"mTouchableInsets=[0-3] mGivenInsetsPending=(?:true|false)",line) else "unrecognized")
            elif line.startswith("touchable region="):
                region=line.split("=",1)[1]
                active["regions"].append(region if len(region)<512 and re.fullmatch(r"SkRegion\([() ,0-9-]*\)",region) else "unrecognized")
    require(sorted(row["type"] for row in result)==["NAVIGATION_BAR","STATUS_BAR"],"expected exactly one SystemUI bar of each type")
    return {"scope":"two_systemui_bars","bars":result}

def sample_pair(d):
    require(d.shell("am","get-current-user")=="0" and d.shell("getprop","ro.product.device")=="CPDAY10","wrong target")
    token=secrets.token_hex(8)
    boot=int(d.shell("settings","get","global","boot_count"))
    until=int(Decimal(d.shell("cat","/proc/uptime").split()[0])*1000)+30000
    require("version=1.0.4" in d.shell("su","-c","cat "+MOD+"/module.prop").splitlines(),"expected module 1.0.4")
    cmd=("umask 077; test -s "+MOD+"/armed && test ! -f "+MOD+"/disable && echo "+
         shlex.quote(f"{token} {boot} {until}")+" > "+MOD+"/sample-request.tmp && mv -f "+MOD+"/sample-request.tmp "+MOD+"/sample-request")
    d.shell("su","-c",cmd)
    print("30s measurement ticket",token,". Press the physical power key twice. No input is synthesized.")

def timing(d,a):
    require(d.shell("getprop","ro.product.device")=="CPDAY10" and d.shell("am","get-current-user")=="0","wrong device/user")
    key=["settings","--user","0"]
    if a.command=="recover-timing":
        backup=json.loads(a.backup.read_text(encoding="utf-8"))
        require(backup["device"]==d.local_identity() and re.fullmatch(r"null|[0-9]{1,9}",backup["original"])
                and backup["target"] in PRESETS,"invalid recovery record")
        require(d.shell("su","-c","if [ -f "+MOD+"/module.prop ]; then echo present; else echo absent; fi")=="absent",
                "use timing-restore while module is installed")
        current=d.shell(*key,"get","secure","multi_press_timeout")
        require(current in (backup["original"],str(backup["target"])),"external setting change, inspect manually")
        if current!=backup["original"]:
            args=["delete","secure","multi_press_timeout"] if backup["original"]=="null" else ["put","secure","multi_press_timeout",backup["original"]]
            d.shell("su","-c",shlex.join([*key,*args]))
        require(d.shell(*key,"get","secure","multi_press_timeout")==backup["original"],"restore readback failed")
        print("Original user-0 setting verified. A normal reboot may be needed for the system policy cache.")
        return
    require("version=1.0.4" in d.shell("su","-c","cat "+MOD+"/module.prop").splitlines(),"expected module 1.0.4")
    command="/system/bin/sh "+MOD+"/timing.sh"
    status=d.shell("su","-c",command+" status")
    match=re.fullmatch(r"setting=(null|[0-9]{1,9}) lease=(?:none|(null|[0-9]{1,9})/([0-9]+))",status)
    require(match,"timing status unavailable")
    print(status)
    if a.command=="timing-prepare":
        require(match[3] is None or int(match[3])==a.ms,"restore before changing preset")
        old=match[2] or match[1]
        with a.backup.open("x",encoding="utf-8") as f:
            json.dump(dict(device=d.local_identity(),original=old,target=a.ms),f)
        print(d.shell("su","-c",command+" prepare "+str(a.ms)))
    elif a.command=="timing-restore":
        print(d.shell("su","-c",command+" restore"))

def snapshot(d):
    require(d.shell("getprop","ro.product.device")=="CPDAY10" and d.shell("am","get-current-user")=="0","wrong target")
    acts=d.shell("dumpsys","activity","activities")
    lock=one(r"^\s*mLockTaskModeState=(?:LOCK_TASK_MODE_)?(NONE|PINNED|LOCKED)\s*$",acts,"lock")
    lst=re.search(r"(?m)^\s*mLockTaskPackages \(userId:packages\)= *\n((?:[ \t]*u\d+:\[[^\n]*\]\s*\n?)*)",acts)
    allow=bool(lst and re.search(r"(?m)^\s*u0:\[com\.naozho\.clock\]\s*$",lst[1]))
    display=d.shell("dumpsys","window","displays")
    focuses=re.findall(r"(?m)^\s*mCurrentFocus=(.+?)\s*$",display)
    require(len(focuses)==1,"ambiguous focus")
    if focuses[0]=="null": focus=None
    else:
        match=re.fullmatch(r"Window\{[^ {}]+ u0 ([^{}\n]+)\}",focuses[0])
        require(match,"unexpected focus identity")
        focus=match[1]
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
    sample=root("cat "+MOD+"/sample-result")
    safe_sample=(sample if re.fullmatch(r"[a-f0-9]{16} (?:invalid_(?:sequence|or_expired)|gap_ms=\d+ hold1_ms=\d+ hold2_ms=\d+ suspend_suspected=(?:true|false))",sample) else None)
    return dict(last_window_check=check_details(root("cat "+MOD+"/last-window-check"),False),sample=safe_sample,veto=veto_details(root("cat "+MOD+"/last-veto")),policy_return=policy_return(root("cat "+MOD+"/last-return")),
                markers=markers,epoch_us=epoch_us,device=d.local_identity(),boot=int(d.shell("settings","get","global","boot_count")),
                uptime_s=float(d.shell("cat","/proc/uptime").split()[0]), clock_hz=numeric(optional(d,"getconf","CLK_TCK")),
                owner=bool(re.search(r"User\s+0:\s+admin="+re.escape(ADMIN)+r",DeviceOwner\b",d.shell("dpm","list-owners"))),
                enforcing=d.shell("getenforce")=="Enforcing", lock=lock, allow_clock_only=allow,
                flags=get_policy(d.shell("dumpsys","device_policy")),
                focus="clock" if focus in CLOCK else "Freeme" if focus==FREEME else "none" if focus is None else "other",
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
        receipt=b.get("policy_return")
        require(receipt and receipt["delivered"]==b["report"]["delivered"] and receipt["policy_count"]==2,"missing matching Android POWER policy receipt")
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
    for name in ("preflight","stage","snapshot","profile","inspect-page","sample-pair","check-windows","window-fields","legacy-window-fields"):
        c=sub.add_parser(name); c.add_argument("--serial",required=True)
        if name in ("preflight","stage","profile"): c.add_argument("--apksigner")
        if name in ("snapshot","check-windows","window-fields","legacy-window-fields"): c.add_argument("--out",required=True,type=Path)
        if name=="profile": c.add_argument("--review",required=True,type=Path)
    for name in ("timing-status","timing-prepare","timing-restore","recover-timing"):
        c=sub.add_parser(name); c.add_argument("--serial",required=True)
        if name in ("timing-prepare","recover-timing"): c.add_argument("--backup",type=Path,required=True)
        if name=="timing-prepare": c.add_argument("--ms",type=int,choices=PRESETS,default=600)
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
    if a.command.startswith("timing-") or a.command=="recover-timing": timing(d,a)
    elif a.command=="preflight":
        print("installed identity checked; user 0 Owner; UID",d.installed(find_signer(a.apksigner)))
    elif a.command=="stage":
        d.installed(find_signer(a.apksigner))
        stage(d)
    elif a.command in ("check-windows","window-fields","legacy-window-fields"):
        require(not a.out.exists(),"choose a new local JSON filename")
        if a.command=="check-windows":
            require("version=1.0.4" in d.shell("su","-c","cat "+MOD+"/module.prop").splitlines(),"requires installed 1.0.4")
            result=check_details(d.shell("su","-c",WINDOW_CHECK),True)
            require(result,"classifier did not return a result")
        elif a.command=="legacy-window-fields":
            result=bar_sample(d)
        else:
            require("version=1.0.4" in d.shell("su","-c","cat "+MOD+"/module.prop").splitlines(),"requires 1.0.4; for older captures use legacy-window-fields")
            result=module_bar_fields(d)
        with a.out.open("x",encoding="utf-8") as f: json.dump(result,f,indent=2)
        print(a.out,result.get("decision","bar fields collected"))
    elif a.command=="sample-pair": sample_pair(d)
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
