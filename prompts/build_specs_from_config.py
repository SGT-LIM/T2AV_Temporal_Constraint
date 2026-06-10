#!/usr/bin/env python3
"""
Build temporal benchmark JSONL specs from one editable config file.

Main idea:
- Edit only the config JSON when adding people/events/action definitions.
- This script generates JSONL benchmark items using a stable relation_type + timing_type schema.
- The prompt-generation MD should be generic and should read event definitions from each item.

Example:
  python build_temporal_specs_from_config.py \
    --config temporal_benchmark_config.current.json \
    --out-jsonl comb_temporal_selected_specs_relation_timing.generated.jsonl \
    --out-json comb_temporal_selected_specs_relation_timing.generated.json
"""

import argparse
import itertools
import json
import re
from pathlib import Path
from typing import Any, Dict, List


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
    """
    Compatibility view for current prompt-generation code/guideline.

    If there is only one event of each modality, creates:
      content.speech, content.silent_action, content.sounding_action

    If there are multiple events of the same modality, creates:
      content.<event_id>

    The canonical representation is the top-level `events` list.
    """
    counts = {}
    for ev in events:
        counts[ev["modality"]] = counts.get(ev["modality"], 0) + 1

    content = {}
    for ev in events:
        key = ev["modality"] if counts[ev["modality"]] == 1 else ev["id"]
        # Keep all action-specific fields except id/modality; id/modality remain in events.
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
            "value": {
                "events": event_ids,
                "count": defaults.get("sync_count", 2),
            },
        }
        items.append(item)

    elif relation == "count":
        # Optional: generate independent count items for each event in the set.
        # Current benchmark does not use this by default, but config can request it.
        for eid in event_ids:
            item = base_item(cfg, event_set)
            item["item_id"] = f"{slugify(event_set['name'])}_rel_count_{slugify(eid)}"
            item["temporal_constraint"] = {
                "relation_type": "count",
                "timing_type": "relative",
                "value": {
                    "target": eid,
                    "count": defaults.get("count", 2),
                },
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

    else:
        raise ValueError(f"Unsupported relative relation: {relation}")

    return items


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
            "value": {
                "schedule": [
                    {
                        "time_sec": defaults.get("sync_time_sec", 2.0),
                        "events": event_ids,
                    }
                ]
            },
        }
        items.append(item)

    elif relation == "sync_count":
        times = event_set.get("sync_count_times_sec", defaults.get("sync_count_times_sec", [1.5, 3.5]))
        item = base_item(cfg, event_set)
        item["item_id"] = f"{slugify(event_set['name'])}_abs_sync_count"
        item["temporal_constraint"] = {
            "relation_type": "sync_count",
            "timing_type": "absolute",
            "value": {
                "schedule": [{"time_sec": t, "events": event_ids} for t in times]
            },
        }
        items.append(item)

    elif relation == "count":
        # Optional independent absolute count for each event.
        times = event_set.get("count_times_sec", defaults.get("count_times_sec", [1.0, 2.0, 3.0]))
        for eid in event_ids:
            item = base_item(cfg, event_set)
            item["item_id"] = f"{slugify(event_set['name'])}_abs_count_{slugify(eid)}"
            item["temporal_constraint"] = {
                "relation_type": "count",
                "timing_type": "absolute",
                "value": {
                    "schedule": [{"time_sec": t, "events": [eid]} for t in times]
                },
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
                "value": {
                    "schedule": [
                        {"time_sec": t, "events": [eid]}
                        for t, eid in zip(times, perm)
                    ]
                },
            }
            items.append(item)

    else:
        raise ValueError(f"Unsupported absolute relation: {relation}")

    return items


def build_specs(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    validate_config(cfg)

    relation_plan = cfg.get("relations_to_generate", {})
    relative_relations = relation_plan.get("relative", [])
    absolute_relations = relation_plan.get("absolute", [])

    rows = []
    for event_set in cfg.get("event_sets", []):
        for relation in relative_relations:
            rows.extend(make_relative_items(cfg, event_set, relation))
        for relation in absolute_relations:
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
