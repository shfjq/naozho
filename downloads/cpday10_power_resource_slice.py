"""Extract the two original resource members for the CPDAY10 P0-9 offline review.

Windows: py -3 cpday10_power_resource_slice.py "D:\\P09\\supplement\\framework-res.apk"
Python 3.8+, standard library. No Android, network or device access needed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

EXPECTED = "48a3f6912392d1d5fb066be715c3e0f888d9016011cdc9cf50b2609a2c040d02"
TARGETS = {0x010E0085: "integer/config_doublePressOnPowerBehavior",
           0x0104026B: "string/config_doublePressOnPowerTargetActivity"}
POLICIES = {1: "public", 2: "system", 4: "vendor", 8: "product", 16: "signature",
            32: "odm", 64: "oem", 128: "actor_signature", 256: "config_signature"}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def chunks(data, start, end):
    while start < end:
        if end - start < 8:
            raise ValueError("Truncated resource chunk header")
        kind, header, size = struct.unpack_from("<HHI", data, start)
        if header < 8 or header > size or size > end - start:
            raise ValueError("Invalid resource chunk bounds")
        yield kind, start, header, start + size
        start += size


def read_name(data, pos, length):
    return data[pos:pos + length].decode("utf-16-le").split("\0", 1)[0]


def inspect_table(table, targets):
    root = list(chunks(table, 0, len(table)))
    if len(root) != 1 or root[0][0] != 2 or root[0][2] < 12:
        raise ValueError("Not an Android resource table")
    _, _, header, end = root[0]
    expected_packages, = struct.unpack_from("<I", table, 8)
    packages = []
    for kind, p, h, e in chunks(table, header, end):
        if kind != 0x0200:
            continue
        if h < 268:
            raise ValueError("Truncated package name")
        package_id, = struct.unpack_from("<I", table, p + 8)
        groups = []
        for t, i, j, k in chunks(table, p + h, e):
            if t != 0x0204:
                continue
            if j < 1032:
                raise ValueError("Truncated overlayable group")
            group = {"name": read_name(table, i + 8, 512),
                     "actor": read_name(table, i + 520, 512), "policies": []}
            for sub, off, head, limit in chunks(table, i + j, k):
                if sub != 0x0205:
                    continue
                if head < 16:
                    raise ValueError("Truncated overlay policy")
                mask, count = struct.unpack_from("<II", table, off + 8)
                if count > (limit - off - head) // 4:
                    raise ValueError("Truncated resource ID list")
                hits = []
                for (resid,) in struct.iter_unpack("<I", table[off + head:off + head + count * 4]):
                    if resid in targets:
                        hits.append({"id": "0x%08x" % resid, "resource": targets[resid]})
                group["policies"].append({"flags": hex(mask), "known_flags":
                    [name for bit, name in POLICIES.items() if mask & bit],
                    "entry_count": count, "requested_entries": hits})
            groups.append(group)
        packages.append({"package_id": package_id, "name": read_name(table, p + 12, 256),
                         "overlayable_group_count": len(groups), "groups": groups})
    if len(packages) != expected_packages or not packages:
        raise ValueError("Resource package count mismatch")
    return packages


def extract(apk, dest):
    with apk.open("rb") as src:
        digest = hashlib.sha256()
        for block in iter(lambda: src.read(1 << 20), b""):
            digest.update(block)
        if digest.hexdigest() != EXPECTED:
            raise ValueError("Wrong input APK SHA-256: " + digest.hexdigest())
        src.seek(0)
        with zipfile.ZipFile(src) as z:
            members = {}
            for name in ("AndroidManifest.xml", "resources.arsc"):
                if z.namelist().count(name) != 1:
                    raise ValueError("Missing or duplicate APK member: " + name)
                members[name] = z.read(name)
    packages = inspect_table(members["resources.arsc"], TARGETS)
    if not any(p["package_id"] == 1 and p["name"] == "android" for p in packages):
        raise ValueError("Missing android framework package")
    report = {"source_apk_sha256": EXPECTED, "members": {k: sha256(v) for k, v in members.items()},
              "target_ids": {"0x%08x" % k: v for k, v in TARGETS.items()},
              "packages": packages}
    # Exclusive creation avoids overwriting the input or a previous result.
    with dest.open("xb") as output:
        try:
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in members.items():
                    z.writestr("members/" + name, data)
                z.writestr("policy.json", json.dumps(report, ensure_ascii=True, indent=2))
        except Exception:
            output.close()
            dest.unlink()
            raise
    print("Evidence file:", dest.resolve())
    print("SHA-256:", sha256(dest.read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--out", type=Path, default=Path("CPDAY10-framework-policy-evidence.zip"))
    args = parser.parse_args()
    try:
        extract(args.apk, args.out)
    except (OSError, ValueError, zipfile.BadZipFile) as err:
        sys.exit("Extraction stopped: " + str(err))


if __name__ == "__main__":
    main()
