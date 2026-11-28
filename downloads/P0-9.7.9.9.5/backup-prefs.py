#!/usr/bin/env python3
"""DSH-only, read-only private backup. Never uploads data. Run only after deployment approval."""
import argparse, pathlib, subprocess, re, tarfile, io, json, hashlib

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True)
    p.add_argument('--out',required=True,type=pathlib.Path)
    args=p.parse_args()
    if args.out.exists():raise SystemExit('Refusing to overwrite existing backup directory')
    def adb(*command):return subprocess.check_output(['adb','-s',args.serial,*command],stderr=subprocess.PIPE,timeout=40)
    package=adb('shell','dumpsys','package','com.naozho.clock').decode(errors='replace')
    version=re.search(r'\bversionCode=(\d+)',package)
    uid=re.search(r'\buserId=(\d+)',package)
    if not version or version[1]!='39' or not uid:raise SystemExit('Expected installed versionCode 39; stopped')
    data=adb('exec-out','su','-c','tar -C /data/user/0/com.naozho.clock -cf - shared_prefs')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as t:
        names=t.getnames()
        for item in t.getmembers():
            path=pathlib.PurePosixPath(item.name)
            if not path.parts or path.parts[0]!='shared_prefs' or '..' in path.parts or not (item.isfile() or item.isdir()):
                raise SystemExit('Unexpected archive member; stopped')
        if 'shared_prefs/clock_display.xml' not in names or 'shared_prefs/clock_weather.xml' not in names:
            raise SystemExit('Incomplete preferences backup; stopped')
    args.out.mkdir(parents=True)
    (args.out/'clock-shared-prefs.tar').write_bytes(data)
    (args.out/'backup-check.json').write_text(json.dumps({'versionCode':39,'uid':int(uid[1]),'files':len(names),
        'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},indent=2),encoding='utf-8')
    print('Private backup saved locally. Do not upload this directory to GitHub.')
if __name__=='__main__':main()
