#!/usr/bin/env python3
"""Rebuild HD-EPIC _A (absent-sound claim) and _Vnoun (object swap) with non-kitchen sounds / objects (2026-10-25).
  python gepa_stage2/regen_variants.py panns    # PANNs scores (CPU ~5 min)
  python gepa_stage2/regen_variants.py build    # writes hdepic_medium_prompts_v2.json"""
import argparse, collections, glob, json, os, random, re, subprocess, sys
import numpy as np
import pandas as pd

E = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av/eval"
AN = "/projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/annotations"
PJ = f"{E}/hdepic_medium_prompts.json"
PJ2 = f"{E}/hdepic_medium_prompts_v2.json"
OUTD = f"{E}/regen_2026-10-25"
CKPT = "/projectnb/ivc-ml/youngsun/hf_cache/panns/Cnn14_mAP=0.431.pth"
SOUNDS = {
    "dog bark": ["Bark", "Dog", "Bow-wow", "Yip"],
    "cat meow": ["Meow", "Cat", "Caterwaul"],
    "car horn": ["Vehicle horn, car horn, honking", "Car alarm"],
    "siren": ["Siren", "Civil defense siren", "Police car (siren)", "Ambulance (siren)", "Fire engine, fire truck (siren)"],
    "train horn": ["Train horn", "Train whistle", "Train"],
    "applause": ["Applause", "Clapping"],
    "baby cry": ["Baby cry, infant cry", "Crying, sobbing"],
}
OBJECTS = ["umbrella", "basketball", "guitar", "violin", "helmet", "tennis racket", "teddy bear"]

def mp4(iid):
    f = glob.glob(f"{E}/hdepic_medium_shard*/{iid}/{iid}_v1_raw.mp4")
    return f[0] if f else None

def load_audio(path, sr=32000):
    raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def step_panns(a):
    from panns_inference import AudioTagging, labels
    os.makedirs(os.path.dirname(CKPT), exist_ok=True)
    at = AudioTagging(checkpoint_path=CKPT, device="cuda" if a.gpu else "cpu")
    idx = {}
    for k, names in SOUNDS.items():
        ii = [labels.index(n) for n in names if n in labels]
        miss = [n for n in names if n not in labels]
        if miss: print(f"[warn] {k}: AudioSet labels not found {miss}")
        idx[k] = ii
    items = json.load(open(PJ))
    wins = sorted({x["item_id"][: -len("_A")] for x in items if x["item_id"].endswith("_A")})
    rows = []
    for n, w in enumerate(wins, 1):
        f = mp4(w + "_pass") or mp4(w + "_A")
        if not f: print("[skip] no clip", w); continue
        y = load_audio(f)
        if len(y) == 0: print("[skip] no audio", w); continue
        prob, _ = at.inference(y[None, :])
        rows.append(dict(window=w, **{k: float(prob[0, ii].max()) for k, ii in idx.items()}))
        if n % 20 == 0: print(f"{n}/{len(wins)}", flush=True)
    os.makedirs(OUTD, exist_ok=True)
    pd.DataFrame(rows).to_csv(f"{OUTD}/panns_probs.csv", index=False)
    d = pd.DataFrame(rows).set_index("window")
    print(d.describe().T[["mean", "max"]].round(3))
    print("clips with prob >= .05 per class:", (d >= .05).sum().to_dict())
    print("->", f"{OUTD}/panns_probs.csv")

def video_words(vid, narr):
    return " ".join(narr.get(vid, [])).lower()

def load_narr():
    try:
        df = pd.read_pickle(f"{AN}/HD_EPIC_Narrations.pkl")
    except Exception as e:
        print("[warn] narrations not loaded:", e); return {}
    vcol = next((c for c in df.columns if c.lower() in ("video_id", "video")), None)
    tcols = [c for c in df.columns if df[c].dtype == object and c != vcol]
    if vcol is None: print("[warn] no video column in narrations"); return {}
    out = collections.defaultdict(list)
    for _, r in df.iterrows():
        out[r[vcol]].append(" ".join(str(r[c]) for c in tcols))
    return out

def claim_event(lab):
    s = f"a '{lab}' sound"
    ev = dict(id="e_sound_claim", modality="sounding_action", actor="person_A", action=s, acting_body_part="none",
              target_body_part="none", target_sound=s,
              definition=f"A '{lab}' sound is audible at some point in the clip; its source does not need to be visible.")
    return ev, {k: v for k, v in ev.items() if k != "id"}

def verb_of(eid):
    return " ".join(eid.split("_")[1:])

def step_build(a):
    rng = random.Random(a.seed)
    items = json.load(open(PJ)); d = {x["item_id"]: x for x in items}
    probs = pd.read_csv(f"{OUTD}/panns_probs.csv").set_index("window")
    narr = load_narr()
    used_s, used_o = collections.Counter(), collections.Counter()
    rep, skipped = [], collections.Counter()
    new = {}
    for iid in sorted(i for i in d if i.endswith("_A")):
        w = iid[:-2]; p = d.get(w + "_pass")
        if p is None or w not in probs.index: skipped["A_no_pass_or_probs"] += 1; continue
        cand = [k for k in SOUNDS if probs.loc[w, k] < a.max_prob]
        if not cand: skipped["A_all_classes_present"] += 1; continue
        rng.shuffle(cand); lab = min(cand, key=lambda k: used_s[k]); used_s[lab] += 1
        x = json.loads(json.dumps(d[iid]))
        ev, ct = claim_event(lab)
        x["events"] = [e for e in x["events"] if e["id"] != "e_sound_claim"] + [ev]
        x["content"]["e_sound_claim"] = ct
        x["generated_prompt"] = p["generated_prompt"].rstrip()[:-1] + f", and a '{lab}' sound can be heard."
        x["a_fail_claim_v2"] = lab
        new[iid] = x
        rep.append(dict(item=iid, variant="A", new=lab, prob=round(float(probs.loc[w, lab]), 4), prompt=x["generated_prompt"]))
    for iid in sorted(i for i in d if i.endswith("_Vnoun")):
        w = iid[:-6]; p = d.get(w + "_pass"); old = d[iid]
        if p is None: skipped["V_no_pass"] += 1; continue
        pe = {e["id"]: e for e in p["events"]}; oe = {e["id"]: e for e in old["events"]}
        eid = next((k for k in pe if k in oe and pe[k].get("action") != oe[k].get("action")), None)
        if eid is None:
            eid = next((e["id"] for e in p["events"] if e.get("modality") == "silent_action"), None)
        if eid is None: skipped["V_no_silent_event"] += 1; continue
        e0 = pe[eid]; verb = verb_of(eid); act = e0["action"]
        if not act.startswith(verb + " "): skipped["V_action_not_verb_noun"] += 1; continue
        noun = act[len(verb) + 1:]
        m = re.match(r"The person (.+?) the " + re.escape(noun) + r"\b", e0.get("definition", ""))
        if not m: skipped["V_definition_pattern"] += 1; continue
        v3 = m.group(1); phrase = f"{v3} the {noun}"
        others = [e for e in p["events"] if e["id"] != eid and phrase in e.get("definition", "")]
        if others: skipped["V_phrase_shared_with_other_event"] += 1; continue
        if p["generated_prompt"].count(phrase) == 0: skipped["V_phrase_not_in_prompt"] += 1; continue
        vid = w.split("_")[1]; vw = video_words(vid, narr)
        cand = [o for o in OBJECTS if not re.search(r"\b" + re.escape(o.split()[-1]) + r"\b", vw)]
        if not cand: skipped["V_all_objects_in_narration"] += 1; continue
        rng.shuffle(cand); obj = min(cand, key=lambda o: used_o[o]); used_o[obj] += 1
        x = json.loads(json.dumps(p))
        x.update(item_id=iid, canonical_item_id=old["canonical_item_id"], variant=old["variant"])
        newphrase = f"{v3} the {obj}"
        for e in x["events"]:
            if e["id"] == eid:
                e["action"] = f"{verb} {obj}"; e["definition"] = e["definition"].replace(phrase, newphrase)
                x["content"][eid] = {**x["content"][eid], "action": e["action"], "definition": e["definition"]}
        x["generated_prompt"] = p["generated_prompt"].replace(phrase, newphrase)
        x["v_fail_object_v2"] = dict(event=eid, original=noun, claimed=obj)
        for k in old:
            if k not in x: x[k] = old[k]
        new[iid] = x
        rep.append(dict(item=iid, variant="Vnoun", new=f"{noun} -> {obj}", prob="", prompt=x["generated_prompt"]))
    out = [new.get(x["item_id"], x) for x in items]
    dropped = [i for i in d if (i.endswith("_A") or i.endswith("_Vnoun")) and i not in new]
    if a.drop_skipped:
        out = [x for x in out if x["item_id"] not in dropped]
    json.dump(out, open(PJ2, "w"), indent=1)
    os.makedirs(OUTD, exist_ok=True)
    pd.DataFrame(rep).to_csv(f"{OUTD}/regen_report.csv", index=False)
    with open(f"{OUTD}/dropped_items.txt", "w") as f: f.write("\n".join(dropped))
    print(f"_A rebuilt {sum(r['variant']=='A' for r in rep)} | class use {dict(used_s)}")
    print(f"_Vnoun rebuilt {sum(r['variant']=='Vnoun' for r in rep)} | object use {dict(used_o)}")
    print(f"not rebuilt {len(dropped)} ({'dropped from v2' if a.drop_skipped else 'old version kept in v2'}): {dict(skipped)}")
    ck = os.path.join(OUTD, "listen_A"); os.makedirs(ck, exist_ok=True)
    rr = pd.DataFrame([r for r in rep if r["variant"] == "A"])
    k = 0
    for lab, g in rr.groupby("new"):
        for _, r in g.sample(min(2, len(g)), random_state=0).iterrows():
            k += 1; src = mp4(r["item"][:-2] + "_pass")
            if src: subprocess.run(["cp", src, f"{ck}/{k:02d}_{lab.replace(' ', '-')}_{r['item'][7:-2]}.mp4"])
    print("\nexamples:")
    for v in ("A", "Vnoun"):
        for r in [r for r in rep if r["variant"] == v][:4]: print(f"  [{v}] {r['new']}: {r['prompt'][-170:]}")
    print(f"\n-> {PJ2}\n-> {OUTD}/regen_report.csv | {OUTD}/dropped_items.txt | listening clips {ck} ({k})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("step", choices=["panns", "build"])
    ap.add_argument("--max-prob", type=float, default=0.05); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--gpu", action="store_true"); ap.add_argument("--drop-skipped", action="store_true")
    a = ap.parse_args()
    step_panns(a) if a.step == "panns" else step_build(a)
