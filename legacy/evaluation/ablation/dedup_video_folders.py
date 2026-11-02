#!/usr/bin/env python3
"""Move duplicate gen_id-style video folders out of main_videos/<model>/.

Canonical folder names are the hyphen-style item_ids from the prompt JSON
(e.g. help-with-thumbs_up__sync). Leftover gen_id-style folders
(e.g. help_thumb__help-with-thumbs_up_sync) hold byte-identical copies and,
because new_eval registers gen_id aliases, would be evaluated a second time.

A folder is moved ONLY if every mp4 in it has an md5-identical twin in the
canonical folder of the same item. Anything else is left in place and printed.

Usage:
    python dedup_video_folders.py --prompt-json relative_500_v5_fixed.json \
        --videos-root /projectnb/ivc-ml/youngsun/T2AV_data/videos_repo/main_videos \
        [--models LTX_2p3 MOVA] [--dry-run]
"""
import argparse, hashlib, json, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import new_eval as NE  # for build_item_meta_map (alias resolution)

GEN_ID_RE = re.compile(r"__.*_(ord|sync|cnt)(_x\d)?$")


def md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-json", type=Path, required=True)
    ap.add_argument("--videos-root", type=Path, required=True)
    ap.add_argument("--models", nargs="*", default=["LTX_2p3", "MOVA"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = json.load(open(args.prompt_json))
    item_ids = {it["item_id"] for it in items}
    meta = NE.build_item_meta_map(items)

    for model in args.models:
        root = args.videos_root / model
        dump = args.videos_root / f"{model}_dup_gen_id_folders"
        folders = [d for d in root.iterdir() if d.is_dir()]
        canon = {d.name: d for d in folders if d.name in item_ids}
        gen = [d for d in folders if d.name not in item_ids and GEN_ID_RE.search(d.name)]
        other = [d for d in folders if d.name not in item_ids and not GEN_ID_RE.search(d.name)]

        print(f"\n[{model}] canonical={len(canon)}/{len(item_ids)} gen_id={len(gen)} other={len(other)}")
        missing = sorted(item_ids - set(canon))
        if missing:
            print(f"  [WARN] {len(missing)} item_ids have no canonical folder: {missing[:5]} ...")
        for d in other:
            print(f"  [SKIP] unrecognized folder (left alone): {d.name}")

        moved = kept = 0
        for d in sorted(gen):
            m = meta.get(d.name)
            target = canon.get(m["original_item_id"]) if m else None
            if target is None:
                print(f"  [KEEP] {d.name}: no canonical twin folder")
                kept += 1
                continue
            canon_md5 = {md5(p) for p in target.glob("*.mp4")}
            mine = list(d.glob("*.mp4"))
            if not mine or any(md5(p) not in canon_md5 for p in mine):
                print(f"  [KEEP] {d.name}: mp4 content differs from {target.name}")
                kept += 1
                continue
            if args.dry_run:
                print(f"  [DRY]  would move {d.name} -> {dump.name}/")
            else:
                dump.mkdir(exist_ok=True)
                shutil.move(str(d), str(dump / d.name))
            moved += 1
        print(f"  moved={moved} kept={kept}")
        remaining = sum(1 for _ in root.rglob("*.mp4"))
        print(f"  mp4 remaining under {root.name}: {remaining}" + (" (dry-run, unchanged)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
