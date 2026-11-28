#!/usr/bin/env python3
"""Offline release verification and explicit, serial-bound CPDAY10 operations (Python 3.9+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, BadZipFile

PKG = "com.naozho.clock"
ADMIN = PKG + "/.display.ClockDeviceAdmin"
CERT = "801bc9dd5ea1144377f8e4520e1bb8bf6950e9e8d22733bba0465076df1c9578"
MOD = "/data/adb/modules/naozho_wake"
KSUD = "/data/adb/ksud"
KNOWN = {
    ("0.6.18-dev", 33, "8706abf247a1241cac309a6aa711b5e2fb5adaa070ccad3e426f2e354516e2e7"): "1.3.1",
    ("0.6.18-dev", 34, "6331cd3c6745fa836649fac7fc7e75b1b9bfb42790b561d620934e01d705e0e8"): "1.3.1",
    ("0.6.19-dev", 34, "c1e4add5207b1f2475558322ee4d05aa9d283835d5a90eac5819cffb1e8ea365"): "1.4.0",
}
PAIRS = {
    "1.3.1": ("naozho-0.6.18-dev-vc35.apk", "naozho-wake-1.3.1-vc35-rollback.zip", "5"),
    "1.4.0": ("naozho-0.6.19-dev-vc35.apk", "naozho-wake-1.4.0-vc35-rollback.zip", "6"),
    "1.5.0": ("naozho-0.6.20-dev-wake.apk", "naozho-wake-1.5.0.zip", "7"),
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, label, timeout=60):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    need(result.returncode == 0, f"{label} failed (exit {result.returncode}); keep this stage for review")
    return result.stdout.decode("utf-8", "replace").strip()


def one(pattern, text, field):
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    need(len(matches) == 1, "missing or ambiguous " + field)
    return matches[0]


def signer(explicit=None):
    found = explicit or shutil.which("apksigner")
    if not found:
        for root in (os.getenv("ANDROID_HOME"), os.getenv("ANDROID_SDK_ROOT"),
                     str(Path(os.getenv("LOCALAPPDATA", "")) / "Android/Sdk")):
            if root:
                files = sorted((Path(root) / "build-tools").glob("*/apksigner*"), reverse=True)
                tools = [p for p in files if p.name in ("apksigner.bat", "apksigner") and p.is_file()]
                if tools:
                    found = str(tools[0])
                    break
    need(found and Path(found).is_file(), "Android SDK Build Tools apksigner missing; use --apksigner")
    return found


def signed(path, tool):
    output = run([tool, "verify", "--verbose", "--print-certs", str(path)], "apksigner")
    need(re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([a-f0-9]{64})\s*$", output, re.M) == [CERT]
         and "Verified using v2 scheme (APK Signature Scheme v2): true" in output, "APK signer or v2 verification failed")
    return CERT


def checksums(root):
    rows = (root / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    entries = {}
    for row in rows:
        digest, name = one(r"^([0-9a-f]{64}) [ *]([A-Za-z0-9][A-Za-z0-9_.-]*)$", row, "SHA256SUMS row")
        need(name not in entries, "duplicate manifest row")
        entries[name] = digest
    return entries


def pair(root, entries, version, tool):
    a, m, code = PAIRS[version]
    for name in (a, m):
        need(entries.get(name) == sha(root / name), "digest mismatch: " + name)
    signed(root / a, tool)
    with ZipFile(root / m) as z:
        need(z.testzip() is None and len(z.namelist()) == len(set(z.namelist())), "invalid module ZIP")
        props = dict(row.split("=", 1) for row in z.read("module.prop").decode().splitlines() if "=" in row)
        need((props["id"], props["version"], props["versionCode"]) == ("naozho_wake", version, code), "incorrect module version")
        need(z.read("clock.sha256").decode().strip() == entries[a], "APK and module pin do not match")
    return root / a, root / m


def lock_policy(dump):
    local, user0 = False, False
    policies = set()
    for line in dump.splitlines():
        section = line.strip()
        if section in ("Local Policies:", "Global Policies:", "Device-wide Policies:"):
            local, user0 = section == "Local Policies:", False
        elif re.fullmatch(r"User [0-9]+:", section):
            user0 = section == "User 0:"
        elif local and user0:
            for packages, flags in re.findall(r"LockTaskPolicy\s*\{mPackages=\s*([^;]+);\s*mFlags=\s*(\d+)\s*\}", line):
                policies.add((int(flags), packages.strip() in (PKG, "[" + PKG + "]")))
    if len(policies) == 1:
        flags, clock_only = policies.pop()
        return {"flags":flags, "clock_only":clock_only}
    return {"flags":None, "clock_only":None}


def focus_summary(dump):
    windows = re.findall(r"(?m)^ *mCurrentFocus=Window\{[^\s{}]+ u0 ([^\s{}]+)\} *$", dump)
    apps = re.findall(r"(?m)^ *mFocusedApp=ActivityRecord\{[^\s{}]+ u0 ([^\s{}]+) t(\d+)[^{}]*\} *$", dump)
    if len(windows) != 1 or len(apps) != 1:
        return {"foreground":"unknown","task":None}
    def canonical(value):
        pkg, sep, cls = value.partition("/")
        if not sep or not re.fullmatch(r"[a-zA-Z0-9_.$]+", pkg) or not re.fullmatch(r"[a-zA-Z0-9_.$]+", cls):
            return None
        return pkg, pkg + cls if cls.startswith(".") else cls
    window, activity = canonical(windows[0]), canonical(apps[0][0])
    clock_entries = {(PKG, PKG + ".MainActivity"), (PKG, PKG + ".mode.PowerClockEntry")}
    if window is None or activity is None:
        state = "unknown"
    elif window in clock_entries and activity in clock_entries:
        state = "clock"
    elif window != activity:
        state = "unstable"
    else:
        state = "other"
    return {"foreground": state, "task": int(apps[0][1]) if state in ("clock", "other") else None}



class Device:
    def __init__(self, serial):
        need(serial and not serial.startswith("-"), "select one already-authorized endpoint with --serial")
        self.args = ["adb", "-s", serial]

    def shell(self, *args):
        return run(self.args + ["shell", shlex.join(args)], args[0], 45)

    def root(self, script):
        return self.shell("su", "-c", script)

    def identity(self):
        need(self.shell("getprop", "ro.product.device") == "CPDAY10", "device differs from CPDAY10")
        need(self.shell("getprop", "ro.build.version.sdk") == "36" and
             self.shell("getprop", "ro.product.cpu.abi") == "arm64-v8a", "API or ABI differs")
        need(self.shell("am", "get-current-user") == "0" and self.shell("getenforce") == "Enforcing", "user or SELinux differs")
        need(self.root("id -u") == "0", "existing authorized KernelSU root unavailable")
        return self.root(KSUD + " --version")

    def snapshot(self, tool):
        ksu = self.identity()
        device_id = self.shell("settings", "--user", "0", "get", "secure", "android_id")
        need(re.fullmatch(r"[0-9a-fA-F]{8,16}", device_id), "cannot bind this local baseline to one handset")
        binding = hashlib.sha256(("wake97-user0/" + device_id.lower()).encode("ascii")).hexdigest()
        owner = bool(re.search(r"User\s+0:\s+admin=" + re.escape(ADMIN) + r",\s*DeviceOwner\b", self.shell("dpm", "list-owners")))
        uid = int(one(r"^package:com\.naozho\.clock uid:(\d+)$",
                      self.shell("cmd", "package", "list", "packages", "--user", "0", "-U", PKG), "clock UID"))
        package = self.shell("dumpsys", "package", PKG)
        name = one(r"^\s*versionName=(\S+)\s*$", package, "version name")
        code = int(one(r"^\s*versionCode=(\d+)\b.*$", package, "version code"))
        locations = self.shell("pm", "path", "--user", "0", PKG)
        base = one(r"^package:(/[^\s]+/base\.apk)$", locations, "base APK")
        need(len(locations.splitlines()) == 1, "split clock differs from this release")
        with tempfile.TemporaryDirectory() as temp:
            apk = Path(temp) / "installed.apk"
            run(self.args + ["pull", base, str(apk)], "read installed base APK", 120)
            cert, digest = signed(apk, tool), sha(apk)
        lock = one(r"^\s*mLockTaskModeState=(?:LOCK_TASK_MODE_)?(LOCKED|PINNED|NONE)\s*$",
                   self.shell("dumpsys", "activity", "activities"), "lock state")
        policy = lock_policy(self.shell("dumpsys", "device_policy"))
        focus = focus_summary(self.shell("dumpsys", "window", "displays"))
        power = self.shell("dumpsys", "power")
        wake = re.findall(r"(?m)^  mWakefulness=(\w+)\s*$", power)
        boot = self.shell("settings", "get", "global", "boot_count")
        props = self.root(f"[ ! -f {MOD}/module.prop ] || cat {MOD}/module.prop")
        prop = dict(r.split("=", 1) for r in props.splitlines() if "=" in r)
        pin = self.root(f"[ ! -f {MOD}/clock.sha256 ] || cat {MOD}/clock.sha256")
        processes = self.root("pidof naozho_wake || :").split()
        need(all(p.isdigit() for p in processes), "observer process enumeration failed")
        states = self.root(f'for n in armed STOP disable remove; do if [ -e {MOD}/"$n" ]; then echo "$n"; fi; done; '
                           f'if [ -d /data/adb/modules_update/naozho_wake ]; then echo pending; fi; '
                           'if [ -e /data/adb/modules/naozho_power_daily/armed ]; then echo daily_armed; fi')
        return dict(device="CPDAY10", api=36, abi="arm64-v8a", current_user=0, selinux="Enforcing",
                    fingerprint=self.shell("getprop", "ro.build.fingerprint"), device_binding=binding, ksu=ksu, owner=owner, uid=uid,
                    boot_count=int(boot) if boot.isdecimal() else None, wakefulness=wake[0] if len(wake) == 1 else None, **policy, **focus,
                    name=name, code=code, certificate=cert, apk_sha256=digest, lock=lock, observer_count=len(processes),
                    module_id=prop.get("id"), module_version=prop.get("version"),
                    module_code=prop.get("versionCode"), module_pin=pin, markers=sorted(states.splitlines()))

    def install(self, apk, module, module_hash):
        # Stage and hash the ZIP in a root-only directory before ksud consumes it.
        public = self.shell("mktemp", "/data/local/tmp/naozho-wake.XXXXXXXX")
        need(re.fullmatch(r"/data/local/tmp/naozho-wake\.[A-Za-z0-9]{8}", public), "unexpected staging path")
        try:
            run(self.args + ["push", str(module), public], "stage reviewed ZIP", 120)
            result = run(self.args + ["install", "-r", str(apk)], "replace signed clock APK", 120)
            need(result.splitlines() and result.splitlines()[-1].strip() == "Success", "Package Manager did not confirm installation")
            self.root('set -eu; umask 077; d=$(mktemp -d /data/adb/naozho-wake.XXXXXXXX); '
                      'trap \'rm -f "$d/module.zip"; rmdir "$d"\' EXIT; '
                      f'cp {public} "$d/module.zip"; sum=$(sha256sum "$d/module.zip"); '
                      f'[ "${{sum%% *}}" = {module_hash} ]; {KSUD} module install "$d/module.zip"')
        finally:
            self.shell("rm", "-f", public)


def original(s):
    version = KNOWN.get((s["name"], s["code"], s["apk_sha256"]))
    need(version and s["module_id"] == "naozho_wake" and s["module_version"] == version and
         s["module_code"] == PAIRS[version][2] and s["module_pin"] == s["apk_sha256"] and
         s["owner"] and s["certificate"] == CERT, "no verified original pair for this snapshot")
    return version


def unchanged_device(before, now):
    for key in ("device", "api", "abi", "device_binding", "fingerprint", "uid", "owner", "certificate"):
        need(before[key] == now[key], "before/current differ: " + key)
    need(now["owner"] and re.search(r"\bv?3\.3\.1\b", now["ksu"]), "unexpected Owner or KernelSU version")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", nargs="?", default="verify", choices=["verify", "status", "install", "start", "stop", "uninstall", "rollback"])
    p.add_argument("--serial"); p.add_argument("--apksigner")
    p.add_argument("--files", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--save", type=Path, help="new local status JSON; refuses to overwrite")
    p.add_argument("--before", type=Path); p.add_argument("--apply", action="store_true", help="perform the named device write after approval")
    a = p.parse_args(argv)
    if a.action == "verify":
        entries, tool = checksums(a.files), signer(a.apksigner)
        for version in PAIRS: pair(a.files, entries, version, tool)
        print("Offline verified candidate and two complete rollback pairs.")
        return
    if a.action != "status" and not a.apply:
        raise ValueError("device writes require explicit --apply; no device command issued")
    dev = Device(a.serial)
    if a.action in ("stop", "uninstall"):
        dev.identity()
        prop = dev.root(f"[ ! -f {MOD}/module.prop ] || cat {MOD}/module.prop")
        if not prop and a.action == "stop":
            print("Wake module absent."); return
        need("id=naozho_wake" in prop.splitlines(), "module identity missing")
        dev.root(f"/system/bin/sh {MOD}/stop.sh")
        need(dev.root(f"if [ -e {MOD}/armed ]; then echo armed; else echo off; fi") == "off", "module is still armed")
        if a.action == "uninstall":
            dev.root(KSUD + " module uninstall naozho_wake")
            print("Only naozho_wake marked for removal. Reboot manually when approved.")
            need(dev.root(f"[ -f {MOD}/remove ] && echo marked") == "marked", "KernelSU removal mark unconfirmed")
        else:
            print("Wake module disarmed. Read status to confirm observer_count reaches zero and check the actual screen.")
        return
    tool = signer(a.apksigner)
    now = dev.snapshot(tool)
    print(json.dumps(now, indent=2, ensure_ascii=False))
    if a.action == "status":
        if a.save:
            with a.save.open("x", encoding="utf-8") as f: json.dump(now, f, indent=2)
        return
    need(a.before, "--before requires the existing pre-install status file")
    before = json.loads(a.before.read_text(encoding="utf-8-sig")); old = original(before)
    unchanged_device(before, now)
    entries = checksums(a.files)
    candidate = pair(a.files, entries, "1.5.0", tool)
    rollback = pair(a.files, entries, old, tool)
    if a.action == "start":
        need(now["apk_sha256"] == entries[candidate[0].name] and now["module_version"] == "1.5.0" and
             now["module_code"] == "7" and now["module_id"] == "naozho_wake" and now["module_pin"] == now["apk_sha256"] and
             not set(now["markers"]).intersection({"remove","disable","pending","daily_armed"}), "candidate not ready")
        if "armed" in now["markers"]:
            print("Already armed; check observer_count and observer_ready, no toggle performed."); return
        need(now["lock"] == "NONE" and now["observer_count"] == 0, "exit normally and wait for the old observer to stop")
        dev.root(KSUD + " module action naozho_wake")
        print("Start requested; confirm exactly one observer_ready from this generation.")
        return
    need(now["lock"] == "NONE" and now["observer_count"] == 0 and
         not set(now["markers"]).intersection({"armed", "daily_armed","remove","disable"}), "stop observer and exit the clock normally first")
    if a.action == "install":
        need("pending" not in now["markers"] and original(now) == old and now["apk_sha256"] == before["apk_sha256"],
             "baseline changed or an update is pending")
        choice = candidate
    else:
        need(now["apk_sha256"] in {before["apk_sha256"], entries[candidate[0].name], entries[rollback[0].name]},
             "unrecognized installed clock; stop for review")
        choice = rollback
    dev.install(*choice, entries[choice[1].name])
    updated = dev.snapshot(tool)
    unchanged_device(before, updated)
    need(updated["apk_sha256"] == entries[choice[0].name], "installed APK differs from the selected pair")
    written_pin = dev.root("if [ -f /data/adb/modules_update/naozho_wake/clock.sha256 ]; then "
                           f"cat /data/adb/modules_update/naozho_wake/clock.sha256; else cat {MOD}/clock.sha256; fi")
    need(written_pin == updated["apk_sha256"], "module installation was not confirmed; leave wake disarmed")
    print("Replacement APK and written module pin verified. Reboot manually when approved, then read status and confirm active versions.")


if __name__ == "__main__":
    try: main()
    except (ValueError, OSError, KeyError, subprocess.TimeoutExpired, BadZipFile) as error:
        sys.exit(str(error))
