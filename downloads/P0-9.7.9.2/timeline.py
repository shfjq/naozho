#!/usr/bin/env python3
"""Summarize one boot's wake journal and only the clock performance tag. Python 3.9+."""
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess

STAGES = ("DARK_OBSERVED_AT", "PREWARM_START_AT", "PREWARM_READY_AT", "WAKE_CANDIDATE_AT",
          "FULL_WAKE_AT", "RETURN_PENDING_AT", "RETURN_DELIVERED_AT", "COMMIT_DELIVERED_AT",
          "ACTIVITY_START_AT", "ACTIVITY_READY_AT", "CLOCK_FOCUSED_AT", "LOCKED_CONFIRMED_AT",
          "CLOCK_FOCUSED")
REQUIRED = set(STAGES[3:])
def read_cycles(text):
    cycles = collections.defaultdict(dict)
    for line in text.splitlines():
        m = re.fullmatch(r"(\d+) ([A-Z_]+) (.*)", line.strip())
        if not m or m[2] not in STAGES:
            continue
        fields = dict(re.findall(r"\b(boot|dark|at|pid|request|epoch|reused)=([\w./-]+)", m[3]))
        if not all(fields.get(k, "").isdigit() for k in ("boot", "dark")):
            continue
        key = (int(fields["boot"]), int(fields["dark"]))
        cycles[key].setdefault(m[2], set()).add((int(fields.get("at", m[1])),fields.get("pid",""),
                                                 fields.get("request",""),fields.get("epoch","")))
    for (boot, dark), rows in sorted(cycles.items()):
        times = {k:min(v)[0] for k,v in rows.items()}
        issues = ["duplicate_" + k for k,v in rows.items() if len(v)>1]
        ids = {r[2] for values in rows.values() for r in values if r[2]}
        if len(ids) != 1:
            issues.append("request_id_missing_or_conflicting")
        missing = sorted(REQUIRED - rows.keys())
        if missing:
            issues.append("incomplete")
        ordered = ("WAKE_CANDIDATE_AT","FULL_WAKE_AT","RETURN_PENDING_AT","RETURN_DELIVERED_AT",
                   "ACTIVITY_START_AT","LOCKED_CONFIRMED_AT","CLOCK_FOCUSED")
        for earlier,later in zip(ordered,ordered[1:]):
            if earlier in times and later in times and times[earlier]>times[later]:
                issues.append("invalid_order")
        for stage in ("ACTIVITY_READY_AT","CLOCK_FOCUSED_AT"):
            if stage in times and "LOCKED_CONFIRMED_AT" in times and times[stage]>times["LOCKED_CONFIRMED_AT"]:
                issues.append("locked_before_frame_or_focus")
        warm = "unconfirmed"
        if "PREWARM_READY_AT" in rows and "WAKE_CANDIDATE_AT" in rows and "ACTIVITY_START_AT" in rows:
            ready = min(rows["PREWARM_READY_AT"])
            warm = ("ready_same_process" if ready[0] <= times["WAKE_CANDIDATE_AT"] and
                    ready[1] == min(rows["ACTIVITY_START_AT"])[1] and ready[1] else "late_or_process_changed")
        duration = lambda left,right: times[right]-times[left] if not issues else None
        yield {"boot":boot,"dark_elapsed":dark,"request_id":next(iter(ids)) if len(ids)==1 else None,
               "warm":warm,"stages_elapsed_ms":times,"missing":missing,"issues":issues,
               "on_to_first_clock_draw_ms":duration("WAKE_CANDIDATE_AT","ACTIVITY_READY_AT"),
               "on_to_focus_ms":duration("WAKE_CANDIDATE_AT","CLOCK_FOCUSED_AT"),
               "full_to_draw_ms":duration("FULL_WAKE_AT","ACTIVITY_READY_AT"),
               "on_to_locked_ms":duration("WAKE_CANDIDATE_AT","LOCKED_CONFIRMED_AT"),
               "candidate_to_root_confirmed_ms":duration("WAKE_CANDIDATE_AT","CLOCK_FOCUSED"),
               "full_to_ready_and_locked_ms":duration("FULL_WAKE_AT","LOCKED_CONFIRMED_AT"),
               "pending_to_return_proof_ms":duration("RETURN_PENDING_AT","RETURN_DELIVERED_AT"),
               "return_proof_to_activity_ms":duration("RETURN_DELIVERED_AT","ACTIVITY_START_AT"),
               "touch":"requires_user","freeme_flash":"requires_observation"}

def collect():
    # A single authorized device; commands only read the module's own logs or the one application tag.
    root = "su -c 'cd /data/adb/modules/naozho_wake && { if [ -f events.1 ]; then cat events.1; fi; cat events; }'"
    def adb(*args):
        return subprocess.check_output(["adb", *args], timeout=15).decode("utf-8",errors="strict")
    return adb("shell",root) + "\n" + adb("logcat","-d","-v","raw","-s","NaozhoWakePerf:I","*:S")

if __name__ == "__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--collect",action="store_true",help="read from the one connected approved device")
    mode.add_argument("--logs",type=Path,nargs="+",help="offline UTF-8 short logs")
    options=cli.parse_args()
    raw=collect() if options.collect else "\n".join(p.read_text(encoding="utf-8-sig") for p in options.logs)
    print(json.dumps(list(read_cycles(raw)),ensure_ascii=False,indent=2))
