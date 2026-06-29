#!/usr/bin/env python3
"""
Build temporal benchmark JSONL specs from one editable config file.

Changes vs the previous version:
- Standalone `count` is removed and folded into the new `order_count` relation.
- `order_count` is supported natively (single / block / interleave patterns), with a
  polymorphic per-position `count` (int = uniform, list[int] = per-position).
- Each event_set may override which relations are generated via `event_set["relations"]`
  (useful when a set is not physically synchronizable, e.g. a both-hands action paired
  with a one-hand gesture -> declare order / order_count only).

Example:
  python build_specs_from_config.py \
    --config jun15_config.json \
    --out-jsonl jun15_spec.jsonl \
    --out-json jun15_spec.json
"""

import argparse
import itertools
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union

Count = Union[int, List[int]]


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(rows: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# order_count count handling
# --------------------------------------------------------------------------- #
def normalize_counts(sequence: List[str], count: Count) -> List[int]:
    n = len(sequence)
    if isinstance(count, bool):
        raise ValueError("count must be int or list[int], not bool")
    if isinstance(count, int):
        if count < 1:
            raise ValueError(f"uniform count must be >= 1, got {count}")
        return [count] * n
    if isinstance(count, (list, tuple)):
        counts = list(count)
        if len(counts) != n:
            raise ValueError(f"per-position count length {len(counts)} != sequence length {n}")
        if not all(isinstance(c, int) and not isinstance(c, bool) and c >= 1 for c in counts):
            raise ValueError(f"per-position counts must be ints >= 1, got {counts}")
        return counts
    raise ValueError(f"count must be int or list[int], got {type(count).__name__}")


def order_count_total_occurrences(value: Dict[str, Any]) -> Dict[str, int]:
    """TC-Count gold helper: per-event total occurrences across the realized timeline."""
    seq = value["sequence"]
    counts = normalize_counts(seq, value["count"])
    out: Dict[str, int] = {}
    for eid, k in zip(seq, counts):
        out[eid] = out.get(eid, 0) + k
    return out


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #
def validate_config(cfg: Dict[str, Any]) -> None:
    subject_ids = {s["id"] for s in cfg.get("subjects", [])}
    if not subject_ids:
        raise ValueError("Config must define at least one subject in `subjects`.")

    event_ids = set()
    for ev in cfg.get("events", []):
        if "id" not in ev:
            raise ValueError(f"Event missing id: {ev}")
        if ev["id"] in event_ids:
            raise ValueError(f"Duplicate event id: {ev['id']}")
        event_ids.add(ev["id"])

        actor = ev.get("actor")
        if actor and actor not in subject_ids:
            raise ValueError(f"Event {ev['id']} uses unknown actor {actor}")

        if ev.get("modality") not in {"speech", "silent_action", "sounding_action"}:
            raise ValueError(
                f"Event {ev['id']} has unsupported modality {ev.get('modality')}. "
                "Use speech, silent_action, or sounding_action."
            )

    if not event_ids:
        raise ValueError("Config must define at least one event in `events`.")

    for es in cfg.get("event_sets", []):
        for eid in es["events"]:
            if eid not in event_ids:
                raise ValueError(f"Event set {es.get('name')} references unknown event id {eid}")


def selected_events(cfg: Dict[str, Any], event_ids: List[str]) -> List[Dict[str, Any]]:
    events_by_id = {ev["id"]: ev for ev in cfg["events"]}
    return [events_by_id[eid] for eid in event_ids]


def make_content_view(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = {}
    for ev in events:
        counts[ev["modality"]] = counts.get(ev["modality"], 0) + 1
    content = {}
    for ev in events:
        key = ev["modality"] if counts[ev["modality"]] == 1 else ev["id"]
        content[key] = {k: v for k, v in ev.items() if k not in {"id", "modality"}}
    return content


def base_item(cfg: Dict[str, Any], event_set: Dict[str, Any]) -> Dict[str, Any]:
    evs = selected_events(cfg, event_set["events"])
    defaults = cfg.get("defaults", {})
    return {
        "modality_combination": event_set["name"],
        "subjects": cfg["subjects"],
        "events": evs,
        "content": make_content_view(evs),
        "scene_hint": event_set.get("scene_hint", defaults.get("scene_hint", "plain indoor room")),
        "camera_hint": event_set.get("camera_hint", defaults.get("camera_hint", "static medium shot")),
    }


# --------------------------------------------------------------------------- #
# relative relations
# --------------------------------------------------------------------------- #
def make_relative_items(cfg: Dict[str, Any], event_set: Dict[str, Any], relation: str) -> List[Dict[str, Any]]:
    event_ids = event_set["events"]
    defaults = cfg.get("defaults", {})
    items = []

    if relation == "synchronization":
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_rel_sync"
        item["temporal_constraint"] = {
            "relation_type": "synchronization",
            "timing_type": "relative",
            "value": {"events": event_ids},
        }
        items.append(item)

    elif relation == "sync_count":
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_rel_sync_count"
        item["temporal_constraint"] = {
            "relation_type": "sync_count",
            "timing_type": "relative",
            "value": {"events": event_ids, "count": defaults.get("sync_count", 2)},
        }
        items.append(item)

    elif relation == "order":
        for perm in itertools.permutations(event_ids):
            item = base_item(cfg, event_set)
            item["item_id"] = f"{slugify(event_set['name'])}_rel_order_" + "_then_".join(slugify(x) for x in perm)
            item["temporal_constraint"] = {
                "relation_type": "order",
                "timing_type": "relative",
                "value": {"sequence": list(perm)},
            }
            items.append(item)

    elif relation == "order_count":
        items.extend(make_order_count_items(cfg, event_set))

    else:
        raise ValueError(f"Unsupported relative relation: {relation}")

    return items


def _order_count_patterns(event_set: Dict[str, Any], defaults: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Explicit per-set patterns win; otherwise build from defaults.order_count knobs."""
    if event_set.get("order_count_patterns"):
        return event_set["order_count_patterns"]

    knobs = defaults.get("order_count", {})
    single_counts = knobs.get("single_counts", [2, 3])
    block_count = knobs.get("block_count", 2)
    interleave_cycles = knobs.get("interleave_cycles", 2)
    enable = set(knobs.get("enable", ["single", "block", "interleave"]))
    ev = event_set["events"]

    pats: List[Dict[str, Any]] = []
    if "single" in enable:
        for eid in ev:
            for n in single_counts:
                pats.append({"kind": "single", "events": [eid], "count": n})
    if "block" in enable and len(ev) >= 2:
        pats.append({"kind": "block", "events": list(ev), "count": block_count})
    if "interleave" in enable and len(ev) >= 2:
        pats.append({"kind": "interleave", "events": list(ev) * interleave_cycles, "count": 1})
    return pats


def make_order_count_items(cfg: Dict[str, Any], event_set: Dict[str, Any]) -> List[Dict[str, Any]]:
    defaults = cfg.get("defaults", {})
    items = []
    for p in _order_count_patterns(event_set, defaults):
        sequence = list(p["events"])
        count: Count = p.get("count", 1)
        normalize_counts(sequence, count)  # validate early
        cnt_tag = "c" + (str(count) if isinstance(count, int) else "-".join(map(str, count)))
        tag = f"{p['kind']}_" + "_".join(slugify(e) for e in p["events"]) + f"_{cnt_tag}"
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_rel_order_count_{tag}"
        item["temporal_constraint"] = {
            "relation_type": "order_count",
            "timing_type": "relative",
            "value": {"sequence": sequence, "count": count},
        }
        items.append(item)
    return items


# --------------------------------------------------------------------------- #
# absolute relations
# --------------------------------------------------------------------------- #
def make_absolute_items(cfg: Dict[str, Any], event_set: Dict[str, Any], relation: str) -> List[Dict[str, Any]]:
    event_ids = event_set["events"]
    defaults = cfg.get("defaults", {})
    items = []

    if relation == "synchronization":
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_abs_sync"
        item["temporal_constraint"] = {
            "relation_type": "synchronization",
            "timing_type": "absolute",
            "value": {"schedule": [{"time_sec": defaults.get("sync_time_sec", 2.0), "events": event_ids}]},
        }
        items.append(item)

    elif relation == "sync_count":
        times = event_set.get("sync_count_times_sec", defaults.get("sync_count_times_sec", [1.5, 3.5]))
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_abs_sync_count"
        item["temporal_constraint"] = {
            "relation_type": "sync_count",
            "timing_type": "absolute",
            "value": {"schedule": [{"time_sec": t, "events": event_ids} for t in times]},
        }
        items.append(item)

    elif relation == "order":
        times_by_len = defaults.get("order_times_sec_by_length", {})
        times = event_set.get("order_times_sec", times_by_len.get(str(len(event_ids))))
        if times is None:
            raise ValueError(
                f"No absolute order timestamps for event set length {len(event_ids)}. "
                "Set defaults.order_times_sec_by_length or event_set.order_times_sec."
            )
        if len(times) != len(event_ids):
            raise ValueError(
                f"Order timestamp count mismatch for {event_set['name']}: "
                f"{len(times)} timestamps for {len(event_ids)} events."
            )
        for perm in itertools.permutations(event_ids):
            item = base_item(cfg, event_set)
            item["item_id"] = f"{slugify(event_set['name'])}_abs_order_" + "_then_".join(slugify(x) for x in perm)
            item["temporal_constraint"] = {
                "relation_type": "order",
                "timing_type": "absolute",
                "value": {"schedule": [{"time_sec": t, "events": [eid]} for t, eid in zip(times, perm)]},
            }
            items.append(item)

    else:
        raise ValueError(f"Unsupported absolute relation: {relation}")

    return items


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def _relations_for(event_set: Dict[str, Any], relation_plan: Dict[str, Any], timing: str) -> List[str]:
    """Per-event_set override wins; otherwise the global plan."""
    override = event_set.get("relations")
    if override and timing in override:
        return override[timing]
    return relation_plan.get(timing, [])


def build_specs(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    validate_config(cfg)
    relation_plan = cfg.get("relations_to_generate", {})

    rows = []
    for event_set in cfg.get("event_sets", []):
        for relation in _relations_for(event_set, relation_plan, "relative"):
            rows.extend(make_relative_items(cfg, event_set, relation))
        for relation in _relations_for(event_set, relation_plan, "absolute"):
            rows.extend(make_absolute_items(cfg, event_set, relation))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out-jsonl", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=None)
    args = parser.parse_args()

    cfg = read_json(args.config)
    rows = build_specs(cfg)
    write_jsonl(rows, args.out_jsonl)

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {len(rows)} specs")
    print(f"Saved JSONL: {args.out_jsonl}")
    if args.out_json:
        print(f"Saved JSON:  {args.out_json}")


if __name__ == "__main__":
    main()
