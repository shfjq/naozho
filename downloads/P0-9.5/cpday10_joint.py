#!/usr/bin/env python3
"""DSH one-shot acceptance runner. Phone installation and approvals stay manual."""
import argparse
import hashlib
import json
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
BASELINE = "2df55e6aa4159ed33608c514dcd39842ad8381ad4afa586b9db4f210481c5aae"
ROLLBACK = "8ff9643921c0d76f9e8e8e2f256d98e74a04d6d6f8110f22fa527c039890f4f4"


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

    def installed(self, digest, version, code):
        require(self.shell("getprop", "ro.product.device") == "CPDAY10", "unexpected device")
        require(self.shell("getprop", "ro.build.version.sdk") == "36", "unexpected SDK")
        require(self.shell("am", "get-current-user") == "0", "unexpected user")
        owners = self.shell("dpm", "list-owners")
        require(re.search(r"User\s+0:\s+admin=" + re.escape(ADMIN) + r",DeviceOwner\b", owners), "owner changed")
        apk = one(r"^package:(/[^\s]+/base\.apk)$", self.shell("pm", "path", "--user", "0", PKG), "base APK")
        require(self.shell("sha256sum", apk).split()[0] == digest, "installed APK SHA-256 differs")
        p = self.shell("dumpsys", "package", PKG)
        require(re.search(r"(?m)^\s*versionCode=" + str(code) + r"\b", p) and
                re.search(r"(?m)^\s*versionName=" + re.escape(version) + r"\s*$", p), "installed version differs")
        uid = one(r"^package:com\.naozho\.clock uid:(\d+)$",
                  self.shell("cmd", "package", "list", "packages", "--user", "0", "-U", PKG), "app UID")
        receivers = self.shell("cmd", "package", "query-receivers", "--user", "0", "-a", ACTION, "-n", RX)
        if digest == CANDIDATE:
            receiver_ok(receivers)
        else:
            require("No receivers found" in receivers, "unexpected baseline/rollback receiver")
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


def stable(prefs):
    return {k:prefs.get(k) for k in ("managed_lock", "managed_home", "native_home")}


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before","verify","return","rollback"])
    parser.add_argument("--serial", required=True)
    parser.add_argument("--record", type=Path, default=Path("p095-local.json"))
    args = parser.parse_args()
    d = Device(args.serial)
    if args.phase == "before":
        uid = d.installed(BASELINE, "0.6.9-dev", 24)
        require(d.state() == ("NONE","Freeme"), "expected NONE + Freeme before update")
        with args.record.open("x", encoding="utf-8") as out:
            json.dump(dict(device_hash=d.local_identity(),uid=uid,configuration=stable(d.prefs())), out, indent=2)
        print("BASELINE_OK version=24 owner=user0 data_snapshot=saved")
        return
    baseline = json.loads(args.record.read_text(encoding="utf-8"))
    rollback = args.phase == "rollback"
    uid = d.installed(ROLLBACK if rollback else CANDIDATE, "0.6.9-rollback-dev" if rollback else "0.6.13-dev", 28)
    require(baseline["device_hash"] == d.local_identity(), "baseline belongs to another device or ADB endpoint")
    require(uid == baseline["uid"], "application UID changed")
    prefs = d.prefs()
    if args.phase in ("verify","rollback"):
        require(stable(prefs) == baseline["configuration"], "deployment configuration differs from baseline; inspect")
        require(d.state() == ("NONE","Freeme"), "expected NONE + Freeme")
        print("ROLLBACK_OK owner=user0 receiver=absent" if rollback else
              "APK_OK version=28 owner=user0 receiver=enabled_exported_SYSTEM_permission")
        return
    require(d.state() == ("NONE","Freeme"), "return requires NONE + Freeme")
    require(prefs.get("managed_lock") == "true" and prefs.get("managed_home", "false") == "false"
            and prefs.get("android") == "true" and int(prefs.get("mode_since","0")) > 0,
            "maintenance pause / independent mode / normal exit boundary not ready")
    # This host record prevents accidental retries even after timeout, Ctrl-C or partial delivery.
    report = Path(str(args.record) + ".attempt")
    with report.open("x", encoding="utf-8", buffering=1) as out:
        def note(message):
            print(message, flush=True)
            print(message, file=out, flush=True)
        start = d.shell("date", "+%m-%d %H:%M:%S.%3N")
        require(re.fullmatch(r"\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}", start), "device timestamp unavailable")
        note("One Return session. Wait for ready=return_once before pressing the physical key.")
        fixed = "/system/bin/sh /data/adb/modules/naozho_power_trial/trial.sh return"
        cmd = ["adb", "-s", args.serial, "shell", shlex.join(["su","-c",fixed])]
        # Stream prompts to console immediately. The module bounds its own observation window.
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace") as child:
            limit = threading.Timer(100, child.kill)
            limit.start()
            try:
                result = ""
                for line in child.stdout:
                    line = line.strip()
                    if line.startswith(("permission_probe=", "ready=", "return_receiver=", "result=")):
                        note(line)
                    if line.startswith("result="):
                        result = line
                rc = child.wait()
            finally:
                limit.cancel()
        # Read-only evidence after success OR failure; never issue a second broadcast.
        final = None
        for _ in range(8):
            try:
                final = d.state()
            except RuntimeError:
                final = ("unknown","unknown")
            if rc or final == ("LOCKED","clock"):
                break
            time.sleep(0.35)
        logs = d.shell("logcat","-b","main","-d","-T",start,"--uid="+uid,"-s","NaozhoPowerReturn:I","NaozhoMode:I")
        for line in logs.splitlines():
            if "NaozhoPowerReturn" in line or ("NaozhoMode" in line and any(term in line for term in
                    ("Lock Task after start:", "startLockTask requested", "startLockTask failed"))):
                note("device_log " + line[:600])
        stages = log_stage(logs)
        note("system=" + "/".join(final) + " app=" + json.dumps(stages,sort_keys=True))
        require(rc == 0 and result == "result=request_submitted_verify_app_focus_and_lock",
                "module stopped; keep the attempt report")
        require(final == ("LOCKED","clock") and stages["app_requested"] == 1 and stages["focus_commit"] == 1
                and stages["lock80"] == 1 and stages["expired"] == 0 and stages["guard_rejected"] == 1,
                "window, single delivery, focus or flags not confirmed; keep the attempt report")
        note("SOFTWARE_CHAIN_OK; DSH must verify the clock responds to touch.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ET.ParseError, RuntimeError, subprocess.SubprocessError) as err:
        sys.exit("STOP: " + str(err))
