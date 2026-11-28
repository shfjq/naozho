#!/usr/bin/env python3
"""Join module and NaozhoWakePerf elapsed-realtime samples. Python 3.9+."""
import argparse
from collections import defaultdict
import csv
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
PREVIEW = {"PREVIEW_ARMED_AT", "PREVIEW_SUBMITTED_AT", "PREVIEW_ON_OBSERVED_AT", "PREVIEW_CLEARED_AT"}
FRAME = {"CLOCK_FRAME_COMMITTED_AT", "CLOCK_PREVIEW_HANDOFF_AT"}
ALL_STAGES = set(STAGES) | set(DETAIL) | {"GUARD2_REFRESH_AT"} | PREVIEW | FRAME
REQUEST_STAGES = set(STAGES[6:12]) | set(DETAIL) | {"GUARD2_REFRESH_AT"} | FRAME
ROW = re.compile(r"([0-9]+) ([A-Z_0-9]+) (.*)")
FIELD = re.compile(r"\b(boot|dark|at|pid|request|epoch|entry|retained_clock|via|focus_seed|wm_focus|wm_visible|phase|reason|call_start)=([\w./-]+)")
METRICS = {
    "on_to_first_clock_draw_ms": ("WAKE_CANDIDATE_AT", "ACTIVITY_READY_AT"),
    "on_to_clock_frame_commit_ms": ("WAKE_CANDIDATE_AT", "CLOCK_FRAME_COMMITTED_AT"),
    "draw_to_clock_frame_commit_ms": ("ACTIVITY_READY_AT", "CLOCK_FRAME_COMMITTED_AT"),
    "frame_commit_to_handoff_ms": ("CLOCK_FRAME_COMMITTED_AT", "CLOCK_PREVIEW_HANDOFF_AT"),
    "on_to_focus_ms": ("WAKE_CANDIDATE_AT", "CLOCK_FOCUSED_AT"),
    "full_to_draw_ms": ("FULL_WAKE_AT", "ACTIVITY_READY_AT"),
    "on_to_locked_ms": ("WAKE_CANDIDATE_AT", "LOCKED_CONFIRMED_AT"),
    "candidate_to_root_confirmed_ms": ("WAKE_CANDIDATE_AT", "CLOCK_FOCUSED"),
    "full_to_ready_and_locked_ms": ("FULL_WAKE_AT", "LOCKED_CONFIRMED_AT"),
    "pending_to_return_proof_ms": ("RETURN_PENDING_AT", "RETURN_DELIVERED_AT"),
    "return_proof_to_activity_ms": ("RETURN_DELIVERED_AT", "ACTIVITY_START_AT"),
    "full_to_return_proof_ms": ("FULL_WAKE_AT", "RETURN_DELIVERED_AT"),
    "guard2_ready_to_commit_receiver_ms": ("GUARD2_READY_AT", "COMMIT_RECEIVED_AT"),
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
    via: str
    focus_seed: str
    wm_focus: str
    wm_visible: str
    phase: str
    reason: str
    call_start: str


def report(boot, dark, rows):
    times = {stage: min(e.at for e in events) for stage, events in rows.items()}
    issues = ["duplicate_" + stage for stage, events in rows.items() if len(events) > 1 and stage not in PREVIEW]
    preview_issues = ["duplicate_" + stage for stage in sorted(PREVIEW & rows.keys()) if len(rows[stage]) > 1]
    ids = {e.request for stage, events in rows.items() if stage not in PREVIEW for e in events if e.request}
    if len(ids) != 1 or any(not e.request for k in REQUEST_STAGES & rows.keys() for e in rows[k]):
        issues.append("request_id_missing_or_conflicting")
    if "CLOCK_PREVIEW_HANDOFF_AT" in rows and "CLOCK_FRAME_COMMITTED_AT" not in rows:
        issues.append("missing_committed_frame_at_handoff")
    missing = sorted(REQUIRED - rows.keys())
    if missing:
        issues.append("incomplete")
    # ARM/AMS can report COMMIT delivery after Android already drew the Activity. Focus can
    # arrive before or after draw. Check only protocol ordering, never physical scan-out.
    edges = set(METRICS.values()) | {
        ("CLOCK_FOCUSED_AT", "CLOCK_PREVIEW_HANDOFF_AT"), ("LOCKED_CONFIRMED_AT", "CLOCK_PREVIEW_HANDOFF_AT"),
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

    on = times.get("WAKE_CANDIDATE_AT")
    submitted, cleared = times.get("PREVIEW_SUBMITTED_AT"), times.get("PREVIEW_CLEARED_AT")
    if cleared is not None and (submitted is None or cleared < submitted):
        preview_issues.append("clear_without_prior_submission")

    def preview_field(stage, field):
        samples = rows.get(stage, ())
        return getattr(next(iter(samples)), field) if len(samples) == 1 else None

    phase = preview_field("PREVIEW_SUBMITTED_AT", "phase")
    call_start = preview_field("PREVIEW_SUBMITTED_AT", "call_start")
    call_ms = None
    if call_start:
        if call_start.isascii() and call_start.isdigit() and dark <= int(call_start) <= submitted:
            call_ms = submitted - int(call_start)
        else:
            preview_issues.append("invalid_widget_service_call_time")
    clear_reason = preview_field("PREVIEW_CLEARED_AT", "reason")
    handoff = times.get("CLOCK_PREVIEW_HANDOFF_AT")
    if clear_reason == "handoff" and (handoff is None or cleared < handoff):
        preview_issues.append("handoff_clear_without_prior_handoff")
    if submitted is not None and submitted < dark:
        preview_issues.append("submission_before_dark_epoch")
    # OFF publication may precede the root ON callback by hours. These are software times.
    handoff_to_clear = None
    if clear_reason == "handoff" and not (issues or preview_issues):
        handoff_to_clear = cleared - handoff
    result["preview"] = {
        "widget_service_call_ms": call_ms,
        "submission_recorded": submitted is not None,
        "submission_phase": phase if phase in {"off", "on"} else "unreported",
        "dark_to_submission_ms": submitted - dark if submitted is not None and not preview_issues else None,
        "clear_reason": clear_reason or "unreported",
        "handoff_to_clear_ms": handoff_to_clear,
        "submission_minus_on_callback_ms": submitted - on if submitted is not None and on is not None and not preview_issues else None,
        "clear_minus_submission_ms": cleared - submitted if cleared is not None and not preview_issues else None,
        "issues": preview_issues,
    }
    if rows.get("FULL_WAKE_AT") and len(rows["FULL_WAKE_AT"]) == 1:
        result["power_evidence_source"] = next(iter(rows["FULL_WAKE_AT"])).via or "unreported"
    result["window_evidence"] = {}
    for stage in ("GUARD1_READY_AT", "GUARD2_READY_AT", "GUARD2_REFRESH_AT"):
        if len(rows.get(stage, ())) == 1:
            sample = next(iter(rows[stage]))
            result["window_evidence"][stage] = {"focus": sample.wm_focus or "unreported",
                                                "visible": sample.wm_visible or "unreported"}
            if stage == "GUARD1_READY_AT":
                result["window_evidence"][stage]["focus_seed"] = sample.focus_seed or "unreported"
    return result


POWER_ROW = re.compile(
    r"[0-9]+ PMS_SAMPLE boot=([0-9]+) dark=([0-9]+) slot=([0-9]+) "
    r"due=([0-9]+) start=([0-9]+) end=([0-9]+) decision_at=([0-9]+) "
    r"via=([a-z_]+) result=([a-zA-Z0-9_]+)"
)


def read_cycles(text):
    power_samples = defaultdict(set)
    cycles = defaultdict(lambda: defaultdict(set))
    for line in text.splitlines():
        line = line.strip()
        sample = POWER_ROW.fullmatch(line)
        if sample:
            boot, dark, slot, due, start, end, decision = map(int, sample.groups()[:7])
            power_samples[boot, dark].add((slot, due, start, end, decision, sample[8], sample[9]))
            continue
        row = ROW.fullmatch(line)
        if not row or row[2] not in ALL_STAGES:
            continue
        fields = dict(FIELD.findall(row[3]))
        if not all(re.fullmatch(r"[0-9]+", fields.get(k, "")) for k in ("boot", "dark")):
            continue
        when = fields.get("at", row[1])
        if not when.isascii() or not when.isdigit():
            continue
        event = Event(int(when), fields.get("pid", ""), fields.get("request", ""),
                      fields.get("epoch", ""), fields.get("entry", ""), fields.get("retained_clock", ""),
                      fields.get("via", ""), fields.get("focus_seed", ""),
                      fields.get("wm_focus", ""), fields.get("wm_visible", ""),
                      fields.get("phase", ""), fields.get("reason", ""), fields.get("call_start", ""))
        cycles[int(fields["boot"]), int(fields["dark"])][row[2]].add(event)
    for boot, dark in sorted(cycles.keys() | power_samples.keys()):
        cycle = report(boot, dark, cycles[boot, dark])
        cycle["power_samples"] = []
        for slot, due, start, end, decision, source, classification in sorted(power_samples[boot, dark]):
            ordered = due <= start <= end <= decision
            cycle["power_samples"].append({
                "slot": slot, "due": due, "started": start, "finished": end, "decided": decision,
                "scheduler_delay_ms": start - due if ordered else None,
                "service_read_ms": end - start if ordered else None,
                "callback_delay_ms": decision - end if ordered else None,
                "source": source, "classification": classification,
            })
        yield cycle


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


# The operator enters offsets measured in one local physical recording from the first lit frame.
# Keys come from the generated sheet. Blank cells mean that the evidence is unavailable.
LEGACY_SHEET = ("boot", "dark_elapsed", "first_clock_ms", "first_clock_surface",
                "freeme_seen", "clock_touch", "first_touch_response_ms")
GAP_FIELDS = ("handoff_gap_seen", "gap_start_ms", "gap_end_ms")
SHEET_FIELDS = LEGACY_SHEET + GAP_FIELDS


def write_sheet(path, cycles):
    with path.open("x", newline="", encoding="utf-8-sig") as dest:
        writer = csv.DictWriter(dest, fieldnames=SHEET_FIELDS)
        writer.writeheader()
        for cycle in cycles:
            writer.writerow({k: cycle[k] for k in ("boot", "dark_elapsed")})


def add_observations(path, cycles):
    lookup = {(c["boot"], c["dark_elapsed"]): c for c in cycles}
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as src:
        reader = csv.DictReader(src)
        if reader.fieldnames not in (list(LEGACY_SHEET), list(SHEET_FIELDS)):
            raise ValueError("unexpected field sheet columns")
        for line, row in enumerate(reader, 2):
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("unexpected number of fields")
                key = (int(row["boot"]), int(row["dark_elapsed"]))
                if key not in lookup or key in seen:
                    raise ValueError("unmatched or repeated boot/dark pair")
                seen.add(key)
                if not any(row.get(k, "").strip() for k in SHEET_FIELDS[2:]):
                    continue
                first = row["first_clock_surface"].strip() or "unknown"
                freeme = row["freeme_seen"].strip() or "unknown"
                touch = row["clock_touch"].strip() or "untested"
                if (first not in {"launcher_widget", "clock_activity", "unknown"} or
                        freeme not in {"yes", "no", "unknown"} or touch not in {"responded", "failed", "untested"}):
                    raise ValueError("invalid observation category")
                first_ms, touch_ms = [int(row[name]) if row[name].strip() else None for name in
                                      ("first_clock_ms", "first_touch_response_ms")]
                if any(v < 0 for v in (first_ms, touch_ms) if v is not None):
                    raise ValueError("physical offsets must be nonnegative")
                if touch_ms is not None and (touch != "responded" or (first_ms is not None and touch_ms < first_ms)):
                    raise ValueError("inconsistent physical touch response")
                gap = row.get("handoff_gap_seen", "").strip() or "unknown"
                start, end = [int(row[k]) if row.get(k, "").strip() else None for k in GAP_FIELDS[1:]]
                if gap not in {"yes", "no", "unknown"}:
                    raise ValueError("invalid handoff gap observation")
                if (start is None) != (end is None):
                    raise ValueError("record both gap boundaries or leave both blank")
                if start is not None and (gap != "yes" or start < 0 or start >= end or
                                          (first_ms is not None and start < first_ms)):
                    raise ValueError("inconsistent observed handoff gap")
                lookup[key]["physical_observation"] = {
                    "handoff_gap_seen": gap, "gap_start_ms": start, "gap_end_ms": end,
                    "gap_duration_ms": end - start if start is not None else None,
                    "first_clock_ms": first_ms, "first_clock_surface": first, "freeme_seen": freeme,
                    "clock_touch": touch, "first_touch_response_ms": touch_ms,
                    "clock_visible_under_1s": first_ms < 1000 if first_ms is not None else None,
                    # A later human tap does not establish when the Activity could first accept a tap.
                    "responsive_by_2s_witnessed": True if touch_ms is not None and touch_ms <= 2000 else None,
                }
            except (TypeError, ValueError) as error:
                raise ValueError(f"field sheet line {line}: {error}") from error


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
    cli.add_argument("--save-logs", type=Path, help="save one new local UTF-8 input file during collection")
    field_work = cli.add_mutually_exclusive_group()
    field_work.add_argument("--write-field-sheet", type=Path, help="create a new CSV for local operator observations")
    field_work.add_argument("--field-sheet", type=Path, help="join observed physical screen and touch results by boot/dark")
    options = cli.parse_args()
    if options.save_logs and not options.collect:
        cli.error("--save-logs requires --collect")
    raw = collect() if options.collect else "\n".join(p.read_text(encoding="utf-8-sig") for p in options.logs)
    cycles = [row for row in read_cycles(raw) if options.boot is None or row["boot"] == options.boot]
    try:
        if options.save_logs:
            with options.save_logs.open("x", encoding="utf-8") as snapshot:
                snapshot.write(raw)
        if options.write_field_sheet:
            write_sheet(options.write_field_sheet, cycles)
        if options.field_sheet:
            add_observations(options.field_sheet, cycles)
    except (ValueError, OSError) as error:
        cli.error(str(error))
    result = {"cycles": cycles, "groups": list(summaries(cycles))} if options.summary else cycles
    print(json.dumps(result, ensure_ascii=False, indent=2))
