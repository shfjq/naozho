#!/usr/bin/env python3
"""DSH one-shot acceptance runner. Phone installation and approvals stay manual."""
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
ROUND = "P0-9.6"
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


def verify_receipts(markers):
    # Validate one ordered pair of independently proven receipts in this module invocation.
    # Failed/partial history samples remain in the report and never satisfy these steps.
    stream = "\n".join(markers)
    probe = one(r"^dispatch_attempt stage=probe trace=(\S+)$", stream, "probe attempt")
    formal = one(r"^dispatch_attempt stage=return trace=(\S+)$", stream, "formal attempt")
    require(probe != formal, "probe and formal request reused an identifier")
    uid = one(r"^permission_probe=DELIVERED uid=(\d+) user=0 permission=android\.permission\.STATUS_BAR_SERVICE$",
              stream, "permission probe delivery")
    require(one(r"^return_receiver=DELIVERED uid=(\d+) user=0$", stream, "formal delivery") == uid,
            "probe and formal senders differ")
    ordered = []
    for stage, trace, terminal in (("probe", probe, "permission_probe="), ("return", formal, "return_receiver=")):
        dispatch = markers.index(f"dispatch_attempt stage={stage} trace={trace}")
        checks = [i for i,line in enumerate(markers) if line.startswith(f"history_check stage={stage} trace={trace} ")
                  and f" sender_uid={uid} " in line and line.endswith(" check=verified")]
        require(len(checks) == 1, "missing or ambiguous verified history for " + stage)
        ordered.extend([dispatch, checks[0], next(i for i,line in enumerate(markers) if line.startswith(terminal))])
        if stage == "probe":
            require(markers.count("ready=return_once") == 1, "missing or ambiguous ready marker")
            ordered.append(markers.index("ready=return_once"))
    require(ordered == sorted(ordered), "module markers out of order")


def check_current(d, signer):
    uid = d.installed(signer)
    require(d.state() == ("NONE", "Freeme"), "expected NONE + Freeme")
    prefs = d.prefs()
    require(prefs.get("managed_lock") == "true" and prefs.get("managed_home", "false") == "false"
            and prefs.get("native_home") == FREEME and prefs.get("android") == "true"
            and int(prefs.get("mode_since", "0")) > 0,
            "expected enabled independent clock in Android mode with a normal exit boundary")
    require(d.shell("getenforce") == "Enforcing", "SELinux state differs")
    power = d.shell("dumpsys", "power")
    require(re.search(r"(?m)^ *mWakefulness=Awake *$", power), "expected awake device")
    boot = d.shell("settings", "get", "global", "boot_count")
    require(boot.isdecimal(), "boot count unavailable")
    return dict(round=ROUND, device_hash=d.local_identity(), uid=uid, configuration=stable(prefs),
                boot_count=int(boot), sha256=CANDIDATE, signer_sha256=CERT, versionCode=28)


def baseline_phase(phase, path, current):
    if phase == "resume":
        require(not Path(str(path)+".attempt").exists(), "prior attempt exists; preserve this record")
        with path.open("x", encoding="utf-8") as out:
            json.dump(current, out, indent=2)
        return
    saved = json.loads(path.read_text(encoding="utf-8"))
    for key in ("round","device_hash","uid","configuration","sha256","signer_sha256","versionCode"):
        require(saved.get(key) == current[key], "baseline mismatch: " + key)
    # KernelSU Manager may request an approved reboot. All live state and identity were re-read.
    print("baseline_boot=%s current_boot=%s" % (saved.get("boot_count"), current["boot_count"]))


def previous_record(path, current):
    # P0-9.5 kept the same local identity algorithm. Read these two files only.
    old_data = path.read_bytes()
    old = json.loads(old_data.decode("utf-8-sig"))
    for field in ("device_hash", "uid", "configuration"):
        require(old.get(field) == current[field], "previous P0-9.5 baseline differs: " + field)
    attempt = Path(str(path) + ".attempt").read_bytes()
    require(b"result=delivery_history_unconfirmed" in attempt.splitlines(),
            "previous failed attempt not identified")
    return {"baseline_sha256": hashlib.sha256(old_data).hexdigest(),
            "attempt_sha256": hashlib.sha256(attempt).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["resume", "verify", "return"])
    parser.add_argument("--serial", required=True)
    parser.add_argument("--apksigner", help="Android SDK Build Tools apksigner or apksigner.bat")
    parser.add_argument("--record", type=Path, default=Path("p096-local.json"))
    parser.add_argument("--previous-record", type=Path,
                        help="resume only: link the original P0-9.5 baseline and failed .attempt, read-only")
    args = parser.parse_args()
    require(not args.previous_record or args.phase == "resume", "--previous-record is for resume only")
    d = Device(args.serial)
    current = check_current(d, find_signer(args.apksigner))
    if args.previous_record:
        current["previous"] = previous_record(args.previous_record, current)
    baseline_phase(args.phase, args.record, current)
    if args.phase != "return":
        print("CURRENT_APK_OK receiver=verified owner=user0 uid=" + current["uid"]
              + " boot=" + str(current["boot_count"]) + " sha256=" + CANDIDATE + " signer=" + CERT)
        return
    uid = current["uid"]
    props = d.shell("su","-c","cat /data/adb/modules/naozho_power_trial/module.prop")
    require(one(r"^version=(.+)$",props,"module version") == "0.2.1"
            and one(r"^versionCode=(.+)$",props,"module code") == "3"
            and one(r"^id=(.+)$",props,"module id") == "naozho_power_trial", "expected approved trial 0.2.1/3")
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
        markers = []
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding="utf-8", errors="replace") as child:
            limit = threading.Timer(100, child.kill)
            limit.start()
            try:
                result = ""
                for line in child.stdout:
                    line = line.strip()
                    if line.startswith(("dispatch_attempt ", "history_check ", "permission_probe=", "ready=", "return_receiver=", "result=")):
                        note(line)
                        markers.append(line)
                    if line.startswith("result="):
                        result = line
                rc = child.wait()
            finally:
                limit.cancel()
        attempts = sum(line.startswith("dispatch_attempt stage=return ") for line in markers)
        note("module_reported_return_attempts=" + str(attempts))
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
        verify_receipts(markers)
        require(final == ("LOCKED","clock") and stages["app_requested"] == 1 and stages["focus_commit"] == 1
                and stages["lock80"] == 1 and stages["expired"] == 0 and stages["guard_rejected"] == 1,
                "window, single delivery, focus or flags not confirmed; keep the attempt report")
        note("SOFTWARE_CHAIN_OK; DSH must verify the clock responds to touch.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ET.ParseError, RuntimeError, subprocess.SubprocessError) as err:
        sys.exit("STOP: " + str(err))
