"""Summarize locally exported JSONL. No device, network or dependencies."""
import argparse
import collections
import json
import sys
from pathlib import Path


def summarize(rows):
    groups = {}
    for r in rows:
        session = groups.setdefault(r["session"], {})
        i = int(r["session_row"])
        if i in session and session[i] != r:
            raise ValueError("Conflicting rows for one session/sequence")
        session[i] = r
    reports = []
    for sid, entries in groups.items():
        indices = sorted(entries)
        events = [entries[i] for i in indices]
        kinds = collections.Counter(r["event_classification"] for r in events)
        first, last = events[0], events[-1]
        full = [r["wake_epoch_id"] for r in events if r["event_classification"] == "FULL_WAKE"]
        reports.append({
            "session": sid, "boots": sorted({str(r["boot_id"]) for r in events}),
            "pids": sorted({r["observer_pid"] for r in events}),
            "first_wall": first["wall_clock"], "last_wall": last["wall_clock"],
            "observed_duration_s": (last["elapsedRealtimeNanos"] - first["elapsedRealtimeNanos"]) / 1e9,
            "ending_session_age_ms": last["session_age_ms"],
            "start_battery_pct": first["battery_pct"], "end_battery_pct": last["battery_pct"],
            "process_cpu_delta_ms": last["process_cpu_ms"] - first["process_cpu_ms"],
            "event_counts": dict(kinds), "full_wake_ids": full,
            "epoch_collisions": len(full) - len(set(full)),
            "unobserved_log_rows": indices[-1] - len(indices),
            "session_start_seen": kinds["SESSION_START"] == 1, "session_end_seen": kinds["SESSION_END"] == 1,
            "previous_unclean_sessions": last["previous_unclean_sessions"],
            "cpu_wakeup_count": None,
        })
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", type=Path, nargs="+")
    args = parser.parse_args()
    rows = []
    size = 0
    for path in args.logs:
        size += path.stat().st_size
        # Older Windows PowerShell may export UTF-16. Prefer cmd.exe raw redirection.
        with path.open("r", encoding="utf-8-sig") as data:
            rows.extend(json.loads(line) for line in data if line.strip())
    if not rows:
        parser.error("No event rows in input")
    result = {"exported_bytes": size, "sessions": summarize(rows)}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, OSError) as error:
        sys.exit("Invalid or incomplete input: " + str(error))
