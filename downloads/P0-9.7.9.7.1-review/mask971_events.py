#!/usr/bin/env python3
"""Audit one captured naozho_wake 1.5.0 journal cycle. Offline, no device access.

Pass events.1 via --previous if rotation occurred. --current is the literal events
file. Keep the clock's logcat separate: this reader accepts only root journal rows.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

UUID = r"[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}"
ROW = re.compile(r"(\d{1,19}) ([A-Za-z0-9_ .:/=-]{1,200})", re.ASCII)
# These stages are serialized by WakeDaemon, WakeDispatch and WakeBoard. Independent
# guard/proof observations may interleave and are not given an invented ordering here.
STAGES = ("DARK_OBSERVED_AT", "WAKE_CANDIDATE_AT", "FULL_WAKE_AT", "RETURN_PENDING_AT",
          "RETURN_SEND_AT", "RETURN_DELIVERED_AT", "COMMIT_SEND_AT", "COMMIT_DELIVERED_AT",
          "ACTIVITY_REQUEST_AT", "ROOT_ATM_ACCEPTED_AT", "CLOCK_FOCUS_LOCK_VERIFIED_AT",
          "CLOCK_FOCUSED", "HANDOFF_COMPLETE")


def audit(chunks, boot, dark):
    key = str(boot), str(dark)
    seen = defaultdict(list)
    issues = set()
    active = False
    previous_ms = None
    disposition = None
    arrival_order = []
    sustained_off = True
    for blob in chunks:
        if blob and not blob.endswith(b'\n'):
            issues.add('incomplete_journal_line')
        # WakeDaemon writes US-ASCII followed by a single LF. A CR, alternate
        # separator, empty interior row or truncated final row is not an exact capture.
        lines = blob.split(b'\n')
        if lines[-1] == b'':
            lines.pop()
        for raw in lines:
            match = ROW.fullmatch(raw.decode('ascii', errors='replace'))
            if not match:
                issues.add('unrecognized_journal_line')
                continue
            clock, payload = int(match[1]), match[2].split()
            if not payload:
                issues.add('unrecognized_journal_line')
                continue
            stage, args = payload[0], payload[1:]
            pairs = [word.split('=', 1) for word in args if '=' in word]
            fields = dict(pairs)
            scope = (fields.get('boot'), fields.get('dark'))
            if scope == key and stage == STAGES[0]:
                active = True
            if active:
                # REFUSED may describe an unrelated worker: without scope the journal
                # cannot prove continuity. MASK_REFUSED_AT describes only the built-in
                # visual path and is expected on this firmware.
                unscoped = scope == (None, None)
                if (scope == key or unscoped) and (stage.startswith('REFUSED') or stage in
                        ('STOPPED', 'MAINTENANCE_PAUSED', 'observer_unregistered', 'observer_ready') or
                        (stage == 'power_readback' and args[:1] == ['REFUSED'])):
                    issues.add('interrupted_or_ambiguous_session')
                if stage == 'DARK_OBSERVED_AT' and scope != key:
                    issues.add('cycle_superseded')
                if stage in ('DOZE', 'DOZE_SUSPEND') and not seen['WAKE_CANDIDATE_AT']:
                    sustained_off = False
                if previous_ms is not None and clock < previous_ms:
                    issues.add('elapsed_time_reversed')
                previous_ms = clock
            if stage not in STAGES or scope != key:
                continue
            if len(fields) != len(pairs):
                issues.add('ambiguous_field')
            seen[stage].append((clock, fields))
            arrival_order.append(STAGES.index(stage))
            if stage == 'HANDOFF_COMPLETE':
                disposition = fields.get('mask')
                active = False
    for stage in STAGES:
        if len(seen[stage]) != 1:
            issues.add(('missing:' if not seen[stage] else 'duplicate:') + stage)
    order = [seen[s][0][0] for s in STAGES if seen[s]]
    if order != sorted(order) or arrival_order != sorted(arrival_order):
        issues.add('out_of_order')
    edges = {}
    for stage in STAGES[:3]:
        for written, fields in seen[stage]:
            at = fields.get('at', '')
            if not re.fullmatch('[0-9]{1,19}', at) or not (dark <= int(at) <= written):
                issues.add('invalid_observation_time:' + stage)
            else:
                edges[stage] = int(at)
    off, on, full = [edges.get(s) for s in STAGES[:3]]
    if off is not None and off != dark:
        # Re-entry from DOZE can have a new OFF observation within the older dark
        # interval. It cannot certify five continuous seconds of this OFF event.
        issues.add('ambiguous_off_edge')
    if ((off is not None and on is not None and on < off)
            or (on is not None and full is not None and full < on)):
        issues.add('observation_order')
    for _, row in seen['FULL_WAKE_AT']:
        if not re.fullmatch(UUID + '/' + str(dark) + r'/[1-9][0-9]*', row.get('epoch', '')):
            issues.add('invalid_wake_epoch')
    requests = {row.get('request', '') for stage in STAGES[4:] for _, row in seen[stage]}
    if len(requests) != 1 or not all(re.fullmatch(UUID, request) for request in requests):
        issues.add('request_mismatch_or_missing')
    senders = {row.get('uid') for stage in ('RETURN_DELIVERED_AT', 'COMMIT_DELIVERED_AT') for _, row in seen[stage]}
    if len(senders) != 1 or not senders <= {'0', '2000'}:
        issues.add('unconfirmed_sender_uid')
    if seen['HANDOFF_COMPLETE'] and disposition != 'not_submitted':
        issues.add('unexpected_wake_1_5_mask_disposition')
    return {'boot_count': boot, 'dark_elapsed_ms': dark, 'root_journal_chain_consistent': not issues,
            'issues': sorted(issues), 'observed_count': {s: len(seen[s]) for s in STAGES},
            'off_to_on_edge_ms': on-off if off is not None and on is not None and on >= off else None,
            'off_edge_span_over_5s_without_logged_aod': bool(not issues and sustained_off and on-off > 5000),
            'wake_module_mask_disposition': disposition,
            'independent_watcher_survival': 'not_evidenced_by_wake_journal',
            'mask_visibility_and_input': 'requires_independent_observation',
            'five_second_visible_timeout': 'requires_mask_visibility_evidence',
            'actual_clock_touch_and_browser_task': 'requires_independent_observation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--boot', type=int, required=True)
    parser.add_argument('--dark', type=int, required=True)
    args = parser.parse_args()
    if args.boot < 0 or args.dark < 0:
        parser.error('boot and dark must be nonnegative')
    paths = [path for path in (args.previous, args.current) if path]
    try:
        if len(paths) == 2 and paths[0].samefile(paths[1]):
            parser.error('previous and current must be separate captures')
        # The writer rotates after 32768 bytes before the next (<=222 byte) append.
        chunks = []
        for path in paths:
            with path.open('rb') as stream:
                blob = stream.read(33001)
            if len(blob) > 33000:
                parser.error('expected a single bounded raw wake journal per path')
            chunks.append(blob)
    except OSError as exc:
        parser.error(str(exc))
    result = audit(chunks, args.boot, args.dark)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['root_journal_chain_consistent'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
