#!/usr/bin/env python3
"""Join module and NaozhoWakePerf elapsed-realtime samples. Python 3.9+."""
import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
from statistics import median
import subprocess

# Stages emitted by both 1.1 and later versions. Keep the public list and old report fields.
STAGES = ("DARK_OBSERVED_AT", "PREWARM_START_AT", "PREWARM_READY_AT", "WAKE_CANDIDATE_AT",
          "FULL_WAKE_AT", "RETURN_PENDING_AT", "RETURN_DELIVERED_AT", "COMMIT_DELIVERED_AT",
          "ACTIVITY_START_AT", "ACTIVITY_READY_AT", "CLOCK_FOCUSED_AT", "LOCKED_CONFIRMED_AT",
          "CLOCK_FOCUSED")
REQUIRED = set(STAGES[3:])
DETAIL = ("GUARD1_READY_AT", "RETURN_SEND_AT", "GUARD2_READY_AT", "COMMIT_SEND_AT",
          "COMMIT_RECEIVED_AT", "ACTIVITY_REQUEST_AT")
ALL_STAGES = set(STAGES) | set(DETAIL) | {"GUARD2_REFRESH_AT"}
REQUEST_STAGES = set(STAGES[6:12]) | set(DETAIL) | {"GUARD2_REFRESH_AT"}
ROW = re.compile(r"([0-9]+) ([A-Z_0-9]+) (.*)")
FIELD = re.compile(r"\b(boot|dark|at|pid|request|epoch|entry|retained_clock)=([\w./-]+)")
METRICS = {
    "on_to_first_clock_draw_ms": ("WAKE_CANDIDATE_AT", "ACTIVITY_READY_AT"),
    "on_to_focus_ms": ("WAKE_CANDIDATE_AT", "CLOCK_FOCUSED_AT"),
    "full_to_draw_ms": ("FULL_WAKE_AT", "ACTIVITY_READY_AT"),
    "on_to_locked_ms": ("WAKE_CANDIDATE_AT", "LOCKED_CONFIRMED_AT"),
    "candidate_to_root_confirmed_ms": ("WAKE_CANDIDATE_AT", "CLOCK_FOCUSED"),
    "full_to_ready_and_locked_ms": ("FULL_WAKE_AT", "LOCKED_CONFIRMED_AT"),
    "pending_to_return_proof_ms": ("RETURN_PENDING_AT", "RETURN_DELIVERED_AT"),
    "return_proof_to_activity_ms": ("RETURN_DELIVERED_AT", "ACTIVITY_START_AT"),
    "on_to_activity_ms": ("WAKE_CANDIDATE_AT", "ACTIVITY_START_AT"),
    "on_to_full_ms": ("WAKE_CANDIDATE_AT", "FULL_WAKE_AT"),
    "full_to_pending_ms": ("FULL_WAKE_AT", "RETURN_PENDING_AT"),
    "pending_to_guard1_ready_ms": ("RETURN_PENDING_AT", "GUARD1_READY_AT"),
    "guard1_ready_to_return_send_ms": ("GUARD1_READY_AT", "RETURN_SEND_AT"),
    "return_send_to_proof_ms": ("RETURN_SEND_AT", "RETURN_DELIVERED_AT"),
    "return_proof_to_commit_send_ms": ("RETURN_DELIVERED_AT", "COMMIT_SEND_AT"),
    "return_send_to_guard2_ready_ms": ("RETURN_SEND_AT", "GUARD2_READY_AT"),
    "guard2_refresh_to_commit_send_ms": ("GUARD2_REFRESH_AT", "COMMIT_SEND_AT"),
    "guard2_ready_to_commit_send_ms": ("GUARD2_READY_AT", "COMMIT_SEND_AT"),
    "commit_send_to_receiver_ms": ("COMMIT_SEND_AT", "COMMIT_RECEIVED_AT"),
    "receiver_to_activity_request_ms": ("COMMIT_RECEIVED_AT", "ACTIVITY_REQUEST_AT"),
    "activity_request_to_start_ms": ("ACTIVITY_REQUEST_AT", "ACTIVITY_START_AT"),
    "activity_to_first_draw_ms": ("ACTIVITY_START_AT", "ACTIVITY_READY_AT"),
    "activity_to_focus_ms": ("ACTIVITY_START_AT", "CLOCK_FOCUSED_AT"),
    "locked_to_root_confirmation_ms": ("LOCKED_CONFIRMED_AT", "CLOCK_FOCUSED"),
    "prewarm_ms": ("PREWARM_START_AT", "PREWARM_READY_AT"),
}


@dataclass(frozen=True)
class Event:
    at: int
    pid: str
    request: str
    epoch: str
    entry: str
    retained: str


def report(boot, dark, rows):
    times = {stage: min(e.at for e in events) for stage, events in rows.items()}
    issues = ["duplicate_" + stage for stage, events in rows.items() if len(events) > 1]
    ids = {e.request for events in rows.values() for e in events if e.request}
    if len(ids) != 1 or any(not e.request for k in REQUEST_STAGES & rows.keys() for e in rows[k]):
        issues.append("request_id_missing_or_conflicting")
    missing = sorted(REQUIRED - rows.keys())
    if missing:
        issues.append("incomplete")
    # ARM/AMS can report COMMIT delivery after Android already drew the Activity. Focus can
    # arrive before or after draw. Check only protocol ordering, never physical scan-out.
    edges = set(METRICS.values()) | {
        ("ACTIVITY_READY_AT", "LOCKED_CONFIRMED_AT"), ("CLOCK_FOCUSED_AT", "LOCKED_CONFIRMED_AT"),
        ("RETURN_DELIVERED_AT", "GUARD2_REFRESH_AT"), ("GUARD2_READY_AT", "GUARD2_REFRESH_AT"),
        ("COMMIT_SEND_AT", "COMMIT_DELIVERED_AT"), ("COMMIT_DELIVERED_AT", "CLOCK_FOCUSED"),
    }
    for first, last in sorted(edges):
        if first in times and last in times and times[first] > times[last]:
            issues.append("invalid_order_" + first + "_" + last)

    ready, activity = (next(iter(rows[stage])) if len(rows.get(stage, ())) == 1 else None
                       for stage in ("PREWARM_READY_AT", "ACTIVITY_START_AT"))
    warm = "unconfirmed"
    if ready and activity and "WAKE_CANDIDATE_AT" in times:
        if ready.at > times["WAKE_CANDIDATE_AT"]:
            warm = "late"
        elif ready.pid and activity.pid:
            warm = "ready_same_process" if ready.pid == activity.pid else "process_changed"
    entry = activity.entry if activity and activity.entry in {"on_create", "on_new_intent"} else "unreported"

    retained = activity.retained if activity and activity.retained in {"true", "false"} else "unreported"
    if retained == "true" and entry != "on_new_intent":
        issues.append("inconsistent_retained_lifecycle")
    epochs = {e.epoch for events in rows.values() for e in events if e.epoch}
    if len(epochs) > 1:
        issues.append("conflicting_epoch")
    result = {
        "boot": boot, "dark_elapsed": dark, "epoch": next(iter(epochs)) if len(epochs) == 1 else None,
        "request_id": next(iter(ids)) if len(ids) == 1 else None,
        "warm": warm, "activity_entry": entry, "retained_clock": retained, "stages_elapsed_ms": times, "missing": missing,
        "detail_missing": sorted(set(DETAIL) - rows.keys()), "issues": issues,
        "touch": "requires_user", "freeme_flash": "requires_observation",
    }
    for key, (first, last) in METRICS.items():
        result[key] = times[last] - times[first] if not issues and first in times and last in times else None
    result["proof_remaining_after_guard2_ms"] = None
    if not issues and "GUARD2_READY_AT" in times:
        result["proof_remaining_after_guard2_ms"] = max(0, times["RETURN_DELIVERED_AT"] - times["GUARD2_READY_AT"])
    return result


def read_cycles(text):
    cycles = defaultdict(lambda: defaultdict(set))
    for line in text.splitlines():
        row = ROW.fullmatch(line.strip())
        if not row or row[2] not in ALL_STAGES:
            continue
        fields = dict(FIELD.findall(row[3]))
        if not all(re.fullmatch(r"[0-9]+", fields.get(k, "")) for k in ("boot", "dark")):
            continue
        when = fields.get("at", row[1])
        if not when.isascii() or not when.isdigit():
            continue
        event = Event(int(when), fields.get("pid", ""), fields.get("request", ""),
                      fields.get("epoch", ""), fields.get("entry", ""), fields.get("retained_clock", ""))
        cycles[int(fields["boot"]), int(fields["dark"])][row[2]].add(event)
    for (boot, dark), rows in sorted(cycles.items()):
        yield report(boot, dark, rows)


def summaries(cycles):
    # Show only comparable observations in a band; incomplete samples remain visible in counts.
    groups = defaultdict(list)
    for cycle in cycles:
        groups[cycle["boot"], cycle["warm"], cycle["activity_entry"], cycle["retained_clock"]].append(cycle)
    for (boot, warm, entry, retained), samples in sorted(groups.items()):
        valid = [row for row in samples if not row["issues"]]
        metrics = {}
        for name in (*METRICS, "proof_remaining_after_guard2_ms"):
            values = [row[name] for row in valid if row[name] is not None]
            if values:
                metrics[name] = {"n": len(values), "min": min(values), "median": median(values), "max": max(values)}
        yield {"boot": boot, "warm": warm, "activity_entry": entry, "retained_clock": retained, "observed_groups": len(samples),
               "complete": len(valid), "incomplete_or_conflicting": len(samples)-len(valid),
               "elapsed_ms": metrics}


def collect():
    # A single authorized device; read only the module's own logs and the app performance tag.
    root = "su -c 'cd /data/adb/modules/naozho_wake && { if [ -f events.1 ]; then cat events.1; fi; cat events; }'"

    def adb(*args):
        return subprocess.check_output(["adb", *args], timeout=15).decode("utf-8", errors="strict")

    return adb("shell", root) + "\n" + adb("logcat", "-d", "-v", "raw", "-s", "NaozhoWakePerf:I", "*:S")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--collect", action="store_true", help="read the one connected approved device")
    mode.add_argument("--logs", type=Path, nargs="+", help="offline UTF-8 short logs")
    cli.add_argument("--summary", action="store_true", help="include same-boot/warm/lifecycle distributions")
    cli.add_argument("--boot", type=int, help="include only this boot_count")
    options = cli.parse_args()
    raw = collect() if options.collect else "\n".join(p.read_text(encoding="utf-8-sig") for p in options.logs)
    cycles = [row for row in read_cycles(raw) if options.boot is None or row["boot"] == options.boot]
    result = {"cycles": cycles, "groups": list(summaries(cycles))} if options.summary else cycles
    print(json.dumps(result, ensure_ascii=False, indent=2))
