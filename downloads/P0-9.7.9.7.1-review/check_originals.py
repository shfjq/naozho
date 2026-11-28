"""Identify a saved pair of mask 1.0.0 artifacts on the host. No device access."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


ANDROID = "{http://schemas.android.com/apk/res/android}"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def module_identity(path):
    with ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != len({entry.filename for entry in members}):
            raise ValueError("module ZIP contains duplicate names")
        if archive.getinfo("module.prop").file_size > 16 * 1024:
            raise ValueError("unexpected module.prop size")
        text = archive.read("module.prop").decode("utf-8")
        props = {}
        for line in text.splitlines():
            key, separator, value = line.partition("=")
            if separator and key in ("id", "version", "versionCode"):
                if key in props:
                    raise ValueError("ambiguous module.prop")
                props[key] = value
        if (props.get("id"), props.get("version")) != ("naozho_mask", "1.0.0"):
            raise ValueError("expected the original naozho_mask 1.0.0 module")
        if not re.fullmatch(r"[0-9]+", props.get("versionCode", "")):
            raise ValueError("missing or invalid module versionCode")
        if sum(entry.file_size for entry in members) > 256 * 1024 * 1024:
            raise ValueError("unexpected uncompressed module size")
        if archive.testzip() is not None:
            raise ValueError("module ZIP failed CRC verification")
    return props


def apk_identity(text):
    root = ElementTree.fromstring(text)
    if (root.get("package"), root.get(ANDROID + "versionName")) != ("com.naozho.mask", "1.0.0"):
        raise ValueError("expected the original com.naozho.mask 1.0.0 APK")
    if not re.fullmatch(r"[0-9]+", root.get(ANDROID + "versionCode", "")):
        raise ValueError("missing APK versionCode")
    return {k: root.get(ANDROID + k) for k in ("versionName", "versionCode")}


def sdk(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ValueError(f"{Path(args[0]).name} failed (exit {result.returncode})")
    return result.stdout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apk", type=Path, required=True)
    p.add_argument("--module", type=Path, required=True)
    p.add_argument("--apksigner", default="apksigner")
    p.add_argument("--apkanalyzer", default="apkanalyzer")
    args = p.parse_args()
    props = module_identity(args.module)
    sig = sdk([args.apksigner, "verify", "--print-certs", str(args.apk)])
    certs = re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([a-fA-F0-9]{64})\s*$", sig, re.M)
    if not certs:
        raise ValueError("missing signed APK certificate digest")
    apk = apk_identity(sdk([args.apkanalyzer, "manifest", "print", str(args.apk)]))
    print(json.dumps({"apk": dict(apk, package="com.naozho.mask", signer_sha256=certs,
                                bytes=args.apk.stat().st_size, sha256=digest(args.apk)),
                      "module": dict(props, bytes=args.module.stat().st_size, sha256=digest(args.module))},
                     indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, BadZipFile, ElementTree.ParseError, subprocess.TimeoutExpired) as error:
        sys.exit(str(error))
