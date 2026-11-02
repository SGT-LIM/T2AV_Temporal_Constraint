#!/usr/bin/env python
"""
caption_accuracy.py

캡션(V축 도구 증거)이 프롬프트 이벤트를 실제로 정확히 기술하는지 평가.

  (1) 이벤트 유무: 캡션이 이벤트를 언급했는가  vs  사람 GT(V축 PASS, 어노테이터 다수결)
      - 규칙 매칭(동의어 사전)과 Gemini 텍스트 전용 매칭을 둘 다 돌리고 일치율도 보고
      - 비디오는 Gemini에 절대 주지 않음 (judge 정확도가 아니라 캡션 정확도를 재는 것)
  (2) 타임스탬프(timestamped 캡션만): 캡션이 말한 시간 구간  vs  Whisper(speech)/FLAM(sounding) 검출 시점
      - 도구 출력도 GT가 아니므로 "accuracy"가 아니라 "audio tool과의 agreement"로 보고
      - silent action은 오디오 참조가 없어 범위 밖

사용 예:
  cd evaluation/ablation
  python caption_accuracy.py --no-gemini            # 규칙 매칭만, 무료, 조인 확인용
  python caption_accuracy.py                        # 규칙 + Gemini
  python caption_accuracy.py --conditions omni_fps8_ts_v3 qwen3vl_fps8_v3 --models LTX_2p3

출력: --out 폴더에 per_event.csv, summary_presence.csv, summary_timing.csv
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

csv.field_size_limit(sys.maxsize)

ROOT = "/projectnb/ivc-ml/youngsun"
DEF_CAPTIONS = f"{ROOT}/T2AV_Temporal_Constraint/evaluation/ablation/captions"
DEF_SUBSET = f"{ROOT}/T2AV_data/eval_subsets/min3"
DEF_ANN = f"{ROOT}/T2AV_data/ann_analysis/per_annotation.csv"
DEF_AUDIO_CACHE = f"{ROOT}/T2AV_data/audio_evidence_cache"
DEF_OUT = f"{ROOT}/T2AV_Temporal_Constraint/eval_results/caption_accuracy"
DEF_GEMINI_CACHE = f"{DEF_OUT}/gemini_cache"

# ----------------------------------------------------------------------------
# 이벤트 라벨 → primitive
# ----------------------------------------------------------------------------
PRIMS = ["slapping_the_thigh", "clapping_hands", "snapping_fingers",
         "thumbs_up", "raise_open_palm", "peace_sign", "crossed_arms"]
KIND_OF = {"slapping_the_thigh": "sounding", "clapping_hands": "sounding", "snapping_fingers": "sounding",
           "thumbs_up": "silent", "raise_open_palm": "silent", "peace_sign": "silent", "crossed_arms": "silent"}


def label_side(label: str):
    """'(right hand)' -> right, '(left hand on left thigh)' -> left, '(with both hands)'/'(both arms)' -> both, else ''"""
    m = re.search(r"\(([^)]*)\)", label)
    if not m:
        return ""
    t = m.group(1).lower()
    if "both" in t:
        return "both"
    if "left" in t and "right" not in t:
        return "left"
    if "right" in t and "left" not in t:
        return "right"
    return ""


def parse_label(label: str):
    """'Speech: say "help"' -> ('speech', 'help'); 'Silent action: thumbs_up (right hand)' -> ('silent', 'thumbs_up')"""
    m = re.search(r'say\s+"([^"]+)"', label) or re.search(r'"([^"]+)"', label)
    if m and (label.lower().startswith("speech") or "say" in label.lower()):
        return "speech", m.group(1).strip().lower()
    for p in PRIMS:
        if p in label:
            return KIND_OF[p], p
    return "unknown", label


# 규칙 사전. 캡션은 자유 문장이라 recall이 새는 게 정상 — Gemini와의 일치율로 보정 정도를 확인한다.
RULES = {
    "thumbs_up": [r"thumbs?[\s-]?up"],
    "raise_open_palm": [r"open\s+palm", r"palm[s]?\s+(facing|toward|out|forward|to the camera)",
                        r"raise[sd]?\s+(his|her|their|an?|the|one|both)?\s*(right|left)?\s*(open\s+)?(hand|palm)",
                        r"hand\s+raised", r"holds?\s+up\s+(his|her|their|an?|the)?\s*(right|left)?\s*(open\s+)?(hand|palm)",
                        r"stop\s+gesture", r"wav(e|es|ing)\b"],
    "peace_sign": [r"peace\s+sign", r"\bv[\s-]?sign", r"two\s+fingers", r"victory\s+sign"],
    "crossed_arms": [r"cross(es|ed|ing)?\s+(his|her|their)?\s*arms", r"arms\s+(are\s+)?(crossed|folded)",
                     r"fold(s|ed|ing)?\s+(his|her|their)?\s*arms"],
    "slapping_the_thigh": [r"slap", r"smack", r"(pat|hit|strike|tap)(s|ted|ting|ping)?\s+(his|her|their)?\s*(right|left)?\s*(thigh|leg|lap)",
                           r"hand\s+(on|against)\s+(his|her|their)?\s*(right|left)?\s*thigh"],
    "clapping_hands": [r"clap", r"applau"],
    "snapping_fingers": [r"snap", r"click(s|ed|ing)?\s+(his|her|their)?\s*fingers"],
}
SPEECH_WORD_ALIASES = {"okay": ["okay", "ok"], "hello": ["hello", "hi"], "yes": ["yes", "yeah"],
                       "help": ["help"], "stop": ["stop"]}


SPEECH_ANY = re.compile(r"\b(speak|speaks|speaking|spoke|talk|talks|talking|say|says|said|saying|utter|utters|shout|shouts|exclaim|exclaims|"
                        r"mouth(s|ing)?\s+(moves|moving|opens|open|words?)|lips?\s+(move|moves|moving)|mouthing|verbal|words?\b|greet|greets|announces?)\b", re.I)


def rule_match_word(prim, caption_text):
    """speech: 그 단어까지 언급했는가 (A축 참고용)"""
    text = caption_text
    words = SPEECH_WORD_ALIASES.get(prim, [prim])
    for w in words:
        m = re.search(r'(say|says|said|saying|utter|utters|shout|shouts|mouth|mouths|exclaim|exclaims|word)\W{0,20}["\']?\b' + re.escape(w) + r'\b', text, re.I)
        if m:
            return True
    for w in words:
        if re.search(r'["“]\s*' + re.escape(w) + r'[.!?,]*\s*["”]', text, re.I):
            return True
    return False


def rule_match(kind, prim, caption_text):
    """returns (matched: bool, snippet: str). speech는 말하는 모습 언급이면 매칭(V축 기준)"""
    text = caption_text
    if kind == "speech":
        m = SPEECH_ANY.search(text)
        if m:
            return True, text[max(0, m.start() - 30): m.end() + 30]
        return rule_match_word(prim, text), ""
    if False:
        words = SPEECH_WORD_ALIASES.get(prim, [prim])
        # 발화 문맥을 우선: says/saying/word/mouths "X" 근처. 없으면 단순 단어 매칭(false positive 감수)
        for w in words:
            m = re.search(r'(say|says|said|saying|utter|utters|shout|shouts|mouth|mouths|exclaim|exclaims|word)\W{0,20}["\']?\b' + re.escape(w) + r'\b', text, re.I)
            if m:
                return True, text[max(0, m.start() - 30): m.end() + 30]
        for w in words:
            m = re.search(r'["“]\s*' + re.escape(w) + r'[.!?,]*\s*["”]', text, re.I)
            if m:
                return True, text[max(0, m.start() - 30): m.end() + 30]
        return False, ""
    for pat in RULES.get(prim, []):
        m = re.search(pat, text, re.I)
        if m:
            return True, text[max(0, m.start() - 30): m.end() + 30]
    return False, ""


# ----------------------------------------------------------------------------
# timestamped 캡션 파싱
# ----------------------------------------------------------------------------
TS_LINE = re.compile(r"^\s*\[?\s*(\d+(?:\.\d+)?)\s*s?\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*s?\s*\]?\s*(?:\([^)]*\))?\s*[:\-]?\s*(.*)$")


def parse_ts_caption(caption_text):
    """[(start, end, text), ...]; 타임스탬프 줄이 하나도 없으면 []"""
    segs = []
    for line in caption_text.splitlines():
        m = TS_LINE.match(line)
        if m and m.group(3).strip():
            segs.append((float(m.group(1)), float(m.group(2)), m.group(3).strip()))
    return segs


def rule_time_range(segs, kind, prim):
    for s, e, t in segs:
        ok, _ = rule_match(kind, prim, t)
        if ok:
            return s, e
    return None


# ----------------------------------------------------------------------------
# 오디오 증거 캐시 (Whisper + FLAM 텍스트 섹션) 파싱
# ----------------------------------------------------------------------------
def load_audio_index(cache_dir):
    """'<MODEL>/<item_folder>/<file>.mp4' -> section text (여러 캐시 엔트리가 있으면 가장 긴 섹션 = 가장 정보 많은 것)"""
    idx = {}
    for f in glob.glob(os.path.join(cache_dir, "*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        v = d.get("video")
        if not v or d.get("error"):
            continue
        b = "/".join(v.replace("\\", "/").split("/")[-3:])  # <MODEL>/<item_folder>/<file>.mp4 (모델 간 폴더·파일명이 같아 모델까지 포함)
        s = d.get("section", "")
        if b not in idx or len(s) > len(idx[b]):
            idx[b] = s
    if idx:
        print("[audio cache] sample key:", next(iter(idx)))
    return idx


def whisper_word_times(section, word):
    """'words: Help.@1.07-1.63' 줄에서 word 매칭 → ([(s,e)], fallback)
    fallback=True: 해당 단어는 못 찾았지만 Whisper가 잡은 발화 세그먼트(어떤 말이든)를 대신 사용"""
    out = []
    aliases = SPEECH_WORD_ALIASES.get(word, [word])
    wh = section.split("OpenFLAM frame-wise")[0]
    for w, s, e in re.findall(r"(\S+?)@(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", wh):
        wl = re.sub(r"[^a-z]", "", w.lower())
        if wl in aliases:
            out.append((float(s), float(e)))
    segs = [(float(s), float(e)) for s, e, _ in re.findall(r"\[\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]\s*\(no_speech_prob=([\d.]+)", wh)]
    if not out:
        for (s, e), (_, _, txt) in zip(segs, re.findall(r"\[\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\]\s*\([^)]*\)\s*(.*)", wh)):
            if any(re.search(r"\b" + a + r"\b", txt, re.I) for a in aliases):
                out.append((s, e))
    if out:
        return out, False
    return segs, bool(segs)


FLAM_KEY = {"slapping_the_thigh": ["slap"], "clapping_hands": ["clap"], "snapping_fingers": ["snap"]}


def flam_peak_times(section, prim):
    """해당 primitive 쿼리들의 threshold 이상 검출 peak 시각. 없으면 top frame peak 1개 (fallback 표시)."""
    i = section.find("OpenFLAM frame-wise")
    if i < 0:
        return [], False
    flam = section[i:]
    blocks = re.split(r"\n\s*Query:", flam)[1:]
    peaks, fallback = [], []
    for b in blocks:
        head = b.split("\n", 1)[0].lower()
        if not any(k in head for k in FLAM_KEY.get(prim, [])):
            continue
        peaks += [float(x) for x in re.findall(r"peak@(\d+(?:\.\d+)?)s", b)]
        tf = re.search(r"top frame peaks:\s*(\d+(?:\.\d+)?)s", b)
        if tf:
            fallback.append(float(tf.group(1)))
    if peaks:
        return sorted(set(peaks)), False
    return (fallback[:1], True) if fallback else ([], False)


def interval_dist(rng, t):
    s, e = rng
    if s <= t <= e:
        return 0.0
    return min(abs(t - s), abs(t - e))


# ----------------------------------------------------------------------------
# Gemini 텍스트 전용 매칭
# ----------------------------------------------------------------------------
SYSTEM = """You are checking whether a video caption mentions specific events. You only see the caption text, never the video.
For each event decide if the caption clearly describes that event happening (mentioned=true). A vague or unrelated gesture does not count.
For speech events: mentioned=true if the caption indicates the person is speaking at all (speaks, talks, says something, mouth or lips moving, utters a word). The exact word is NOT required for mentioned. Set word_mentioned=true only if the caption also gives that specific word (or an obvious variant such as "ok" for "okay"). For non-speech events word_mentioned is always false.
If the caption has time ranges, report the start and end seconds of the sentence that describes the event; otherwise use null.
For a mentioned hand/arm action also report which side the caption says performs it: "left", "right", "both", or "unspecified" if the caption does not say. Use "none" when the event is not mentioned or is speech. Report the side exactly as written in the caption, do not infer or mirror it.
Quote the exact caption words as evidence (empty string if not mentioned)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "mentioned": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "start_s": {"type": ["number", "null"]},
                    "end_s": {"type": ["number", "null"]},
                    "side": {"type": "string", "enum": ["left", "right", "both", "unspecified", "none"]},
                    "word_mentioned": {"type": "boolean"},
                },
                "required": ["event_id", "mentioned", "evidence", "start_s", "end_s", "side", "word_mentioned"],
            },
        }
    },
    "required": ["events"],
}

_client = None


def gemini_client():
    global _client
    if _client is None:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            sys.exit("GEMINI_API_KEY / GOOGLE_API_KEY 환경변수가 없습니다 (new_eval.py 돌리던 셸과 같은 변수 사용)")
        _client = genai.Client(api_key=key)
    return _client


def gemini_match(model_name, caption_text, events, cache_dir):
    """events: [{event_id, description}] → {event_id: {mentioned, evidence, start_s, end_s}}"""
    os.makedirs(cache_dir, exist_ok=True)
    key = hashlib.md5(json.dumps([model_name, caption_text, events, SYSTEM, SCHEMA], sort_keys=True).encode()).hexdigest()  # 지시문·스키마 바뀌면 재호출
    cf = os.path.join(cache_dir, key + ".json")
    if os.path.exists(cf):
        return json.load(open(cf))
    from google.genai import types
    user = "CAPTION:\n" + caption_text.strip() + "\n\nEVENTS:\n" + "\n".join(
        f"- event_id={e['event_id']}: {e['description']}" for e in events)
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_json_schema=SCHEMA,
                                      system_instruction=SYSTEM, temperature=0.0, seed=42)
    last = None
    for attempt, wait in enumerate([0, 30, 60, 120]):
        if wait:
            time.sleep(wait)
        try:
            r = gemini_client().models.generate_content(model=model_name, contents=user, config=cfg)
            out = {e["event_id"]: e for e in json.loads(r.text)["events"]}
            json.dump(out, open(cf, "w"))
            return out
        except Exception as ex:  # 429/503/500 재시도
            last = ex
    print(f"[WARN] gemini failed after retries: {last}", file=sys.stderr)
    return None


# ----------------------------------------------------------------------------
# 사람 GT (V축, 다수결)
# ----------------------------------------------------------------------------
def load_gt(ann_csv, models, items_by_model):
    """{(model, item_id, prim_key): {"v_pass": bool, "n": int, "n_pass": int, "kind", "prim", "label", "event_id"}}"""
    rows = list(csv.DictReader(open(ann_csv, newline="")))
    # (model,item,user) → 최신 file만 (어노테이터가 같은 비디오를 중복 저장한 경우)
    latest = {}
    for r in rows:
        k = (r["model"], r["item_id"], r["user"])
        if k not in latest or r["file"] > latest[k]:
            latest[k] = r["file"]
    votes = defaultdict(list)
    meta = {}
    side_fail = {}
    mouth_moved = {}
    absent_votes = {}
    flagged = []
    for r in rows:
        if r["model"] not in models or r["item_id"] not in items_by_model.get(r["model"], set()):
            continue
        if latest[(r["model"], r["item_id"], r["user"])] != r["file"]:
            continue
        kind, prim = parse_label(r["event_label"])
        # 같은 primitive가 아이템에 두 번 나오는 경우(예: clap x2는 count이므로 1이벤트) 대비 event_id도 키에 포함
        pk = f"{kind}:{prim}:{r['event_id']}"
        votes[(r["model"], r["item_id"], pk)].append(r["v"].strip().upper() == "PASS")
        rat = r.get("v_rationale", "") or ""
        if r["v"].strip().upper() != "PASS":
            if kind != "speech" and re.search(r"wrong (hand|side|arm)|other (hand|side|arm)|opposite (hand|side|arm)|instead of (the )?(left|right)|mirror|switched|swapped|(left|right) (hand|arm|side) (instead|rather)", rat, re.I):
                side_fail[(r["model"], r["item_id"], pk)] = side_fail.get((r["model"], r["item_id"], pk), 0) + 1
                flagged.append((kind, r["event_label"][:35], rat[:90]))
            if kind == "speech" and re.search(r"(mouth|lip)\w* (motion|movement)s? (does ?n.t|doesn't|did ?n.t|do not|not) match|different word|wrong word|says? (something|another)", rat, re.I):
                mouth_moved[(r["model"], r["item_id"], pk)] = 1
            if re.search(r"did ?n.t occur|did not occur|does not occur|never (done|happen|occur|perform)|not (performed|done|present|shown)|no (mouth|lip) (motion|movement)|no speech|no (visible )?(thumbs|clap|slap|snap|peace|palm|gesture|action)|(action|gesture|event) (is )?(missing|absent)|nothing happens", rat, re.I) \
               and not re.search(r"not visible|misform|extra finger|deform|unclear|hard to (see|tell)", rat, re.I):
                absent_votes[(r["model"], r["item_id"], pk)] = absent_votes.get((r["model"], r["item_id"], pk), 0) + 1
        meta[(r["model"], r["item_id"], pk)] = dict(kind=kind, prim=prim, label=r["event_label"], event_id=r["event_id"])
    import random; random.seed(0)
    print(f"[GT] absent-reason events: {len(absent_votes)}")
    print(f"[GT] wrong-hand flagged rows: {len(flagged)} (silent {sum(f[0]=='silent' for f in flagged)}, sounding {sum(f[0]=='sounding' for f in flagged)}); speech mouth-moved events: {len(mouth_moved)}")
    for f in random.sample(flagged, min(8, len(flagged))): print("   [flag]", f[0], "|", f[1], "|", f[2])
    gt = {}
    for k, vs in votes.items():
        v_pass = sum(vs) * 2 > len(vs)
        # presence-relaxed: PASS이거나, FAIL인데 어노테이터 사유가 손 방향 문제인 경우(동작 자체는 있었음)
        ls = label_side(meta[k]["label"])
        if v_pass:
            video_side = ls
        elif side_fail.get(k, 0) > 0 and ls in ("left", "right"):
            video_side = "right" if ls == "left" else "left"
        else:
            video_side = ""
        v_present = v_pass or side_fail.get(k, 0) > 0 or k in mouth_moved
        v_absent = (not v_present) and absent_votes.get(k, 0) > 0
        gt[k] = dict(v_pass=v_pass, v_present=v_present, v_absent=v_absent, video_side=video_side, n=len(vs), n_pass=sum(vs), **meta[k])
    return gt


# ----------------------------------------------------------------------------
def summarize_presence(rows, pred_col, gt_col="gt_v_pass"):
    agg = defaultdict(lambda: Counter())
    for r in rows:
        if r[pred_col] == "":
            continue
        for grp in [(r["condition"], r["model"], "all"), (r["condition"], r["model"], r["kind"])]:
            y, p = r[gt_col] == "True", r[pred_col] == "True"
            agg[grp]["TP" if y and p else "FP" if p else "FN" if y else "TN"] += 1
    out = []
    for (cond, model, kind), c in sorted(agg.items()):
        tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
        n = tp + fp + fn + tn
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        acc = (tp + tn) / n if n else float("nan")
        out.append(dict(condition=cond, model=model, kind=kind, matcher=pred_col, n=n,
                        gt_pos=tp + fn, accuracy=round(acc, 3), precision=round(prec, 3), recall=round(rec, 3),
                        TP=tp, FP=fp, FN=fn, TN=tn))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captions-dir", default=DEF_CAPTIONS)
    ap.add_argument("--subset-dir", default=DEF_SUBSET)
    ap.add_argument("--ann", default=DEF_ANN)
    ap.add_argument("--audio-cache", default=DEF_AUDIO_CACHE)
    ap.add_argument("--out", default=DEF_OUT)
    ap.add_argument("--gemini-cache", default=DEF_GEMINI_CACHE)
    ap.add_argument("--models", nargs="+", default=["LTX_2p3", "MOVA"])
    ap.add_argument("--conditions", nargs="*", default=None, help="captions/<cond>_<MODEL>.json 의 <cond>. 생략 시 자동 탐색")
    ap.add_argument("--gemini-model", default="gemini-3.7-flash")
    ap.add_argument("--no-gemini", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="디버그용: 조건·모델당 아이템 수 제한")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    items_by_model = {m: set(os.listdir(os.path.join(args.subset_dir, m))) for m in args.models}
    gt = load_gt(args.ann, set(args.models), items_by_model)
    print(f"[GT] events with human V labels: {len(gt)}  "
          f"(annotators/event: {Counter(v['n'] for v in gt.values())})")

    conds = args.conditions
    if not conds:
        conds = sorted({re.sub(r"_(LTX_2p3|MOVA)\.json$", "", os.path.basename(f))
                        for f in glob.glob(os.path.join(args.captions_dir, "*.json"))
                        if re.search(r"_(LTX_2p3|MOVA)\.json$", f)})
    print("[conditions]", conds)

    audio_idx = load_audio_index(args.audio_cache)
    print(f"[audio cache] videos indexed: {len(audio_idx)}")

    rows = []
    for cond in conds:
        for model in args.models:
            cf = os.path.join(args.captions_dir, f"{cond}_{model}.json")
            if not os.path.exists(cf):
                print(f"[skip] {cf} 없음")
                continue
            caps = json.load(open(cf))
            by_item = {}
            for rel, d in caps.items():
                by_item[rel.split("/")[0]] = (rel, d["caption"] if isinstance(d, dict) else str(d))
            items = sorted(i for i in items_by_model[model] if i in by_item)
            missing = len(items_by_model[model]) - len(items)
            if args.limit:
                items = items[:args.limit]
            print(f"[{cond} / {model}] items with caption: {len(items)} (min3 missing: {missing})")
            n_gem_fail = 0
            for item in items:
                rel, text = by_item[item]
                segs = parse_ts_caption(text)
                is_ts = len(segs) >= 2
                evs = [(k, v) for k, v in gt.items() if k[0] == model and k[1] == item]
                if not evs:
                    continue
                ev_list = [{"event_id": pk, "description": v["label"]} for (_, _, pk), v in evs]
                gem = None
                if not args.no_gemini:
                    gem = gemini_match(args.gemini_model, text, ev_list, args.gemini_cache)
                    if gem is None:
                        n_gem_fail += 1
                section = audio_idx.get(model + "/" + "/".join(rel.split("/")[-2:]), "")
                for (_, _, pk), v in evs:
                    kind, prim = v["kind"], v["prim"]
                    r_ok, r_snip = rule_match(kind, prim, text)
                    r_rng = rule_time_range(segs, kind, prim) if (is_ts and r_ok) else None
                    g = gem.get(pk) if gem else None
                    g_ok = "" if g is None else str(bool(g["mentioned"]))
                    g_rng = None
                    if g and g["mentioned"] and g.get("start_s") is not None and g.get("end_s") is not None:
                        g_rng = (float(g["start_s"]), float(g["end_s"]))
                    # 도구 시각
                    tool_times, tool_fb = [], False
                    if kind == "speech" and section:
                        wt, tool_fb = whisper_word_times(section, prim)
                        tool_times = [(s + e) / 2 for s, e in wt]
                    elif kind == "sounding" and section:
                        tool_times, tool_fb = flam_peak_times(section, prim)
                    def dt(rng):
                        if not rng or not tool_times:
                            return ""
                        return round(min(interval_dist(rng, t) for t in tool_times), 3)
                    rows.append(dict(
                        condition=cond, model=model, item_id=item, video=rel, event_key=pk, event_id=v["event_id"],
                        kind=kind, prim=prim, label=v["label"], gt_v_pass=str(v["v_pass"]), gt_v_present=str(v["v_present"]), gt_v_absent=str(v["v_absent"]), gt_video_side=v["video_side"], gt_n=v["n"], gt_n_pass=v["n_pass"],
                        rule_mentioned=str(r_ok), rule_snippet=r_snip,
                        rule_word=str(rule_match_word(prim, text)) if kind == "speech" else "",
                        gemini_word=("" if g is None else str(bool(g.get("word_mentioned", False)))) if kind == "speech" else "",
                        gemini_mentioned=g_ok, gemini_evidence=(g or {}).get("evidence", ""),
                        label_side=label_side(v["label"]), gemini_side=(g or {}).get("side", ""),
                        caption_is_ts=str(is_ts),
                        rule_start=r_rng[0] if r_rng else "", rule_end=r_rng[1] if r_rng else "",
                        gemini_start=g_rng[0] if g_rng else "", gemini_end=g_rng[1] if g_rng else "",
                        tool_times=";".join(f"{t:.2f}" for t in tool_times), tool_fallback=str(tool_fb),
                        dt_rule=dt(r_rng), dt_gemini=dt(g_rng),
                    ))
            if n_gem_fail:
                print(f"    [WARN] gemini failures: {n_gem_fail}")

    # ---- per-event
    pe = os.path.join(args.out, "per_event.csv")
    with open(pe, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\n[write] {pe}  rows={len(rows)}")

    # ---- presence summary
    summ = summarize_presence(rows, "rule_mentioned")
    if not args.no_gemini:
        summ += summarize_presence(rows, "gemini_mentioned")
    sp = os.path.join(args.out, "summary_presence.csv")
    with open(sp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
    print(f"[write] {sp}")
    print("\n=== caption mentions event  vs  human V PASS  (kind=all) ===")
    print(f"{'condition':30s} {'model':8s} {'matcher':17s} {'n':>4s} {'pos':>4s} {'acc':>6s} {'P':>6s} {'R':>6s}")
    for s in summ:
        if s["kind"] == "all":
            print(f"{s['condition']:30s} {s['model']:8s} {s['matcher']:17s} {s['n']:4d} {s['gt_pos']:4d} "
                  f"{s['accuracy']:6.3f} {s['precision']:6.3f} {s['recall']:6.3f}")
    print("\n=== same, by event kind (gemini) ===")
    for s in summ:
        if s["kind"] != "all" and s["matcher"] == "gemini_mentioned":
            print(f"{s['condition']:30s} {s['model']:8s} {s['kind']:9s} n={s['n']:3d} acc={s['accuracy']:.3f} P={s['precision']:.3f} R={s['recall']:.3f}")
    if not args.no_gemini:
        print("\n=== silent, presence-relaxed GT (V PASS or FAIL due to wrong hand/side) vs strict ===")
        relaxed = summarize_presence(rows, "gemini_mentioned", "gt_v_present")
        strict = {(s["condition"], s["model"]): s for s in summ if s["kind"] == "silent" and s["matcher"] == "gemini_mentioned"}
        for s in relaxed:
            if s["kind"] != "silent":
                continue
            st = strict[(s["condition"], s["model"])]
            print(f"{s['condition']:30s} {s['model']:8s} strict acc={st['accuracy']:.3f} P={st['precision']:.3f} R={st['recall']:.3f}  |  "
                  f"relaxed acc={s['accuracy']:.3f} P={s['precision']:.3f} R={s['recall']:.3f}  (pos {st['gt_pos']}→{s['gt_pos']})")

    # ---- KNOWN events: present (PASS or wrong-hand / mouth-moved FAIL) + absent (FAIL with an explicit "did not occur" reason). Unknown FAILs excluded.
    if not args.no_gemini:
        print("\n=== KNOWN events: caption vs video (present: mentioned & hand not contradicting; absent: not mentioned) ===")
        print(f"{'condition':30s} {'model':8s} {'kind':9s} {'n_pres':>6s} {'n_abs':>6s} {'acc':>6s} {'P':>6s} {'R':>6s} {'halluc':>7s} {'side_wr':>8s} {'side_given':>10s}")
        agg = defaultdict(Counter)
        for r in rows:
            if r["gemini_mentioned"] == "":
                continue
            present = r["gt_v_present"] == "True"; absent = r["gt_v_absent"] == "True"
            if not (present or absent):
                continue
            k = (r["condition"], r["model"], r["kind"])
            ment = r["gemini_mentioned"] == "True"; cs = r["gemini_side"]; vs = r["gt_video_side"]
            has_side = r["kind"] != "speech" and vs in ("left", "right")
            side_wrong = ment and has_side and cs in ("left", "right") and cs != vs
            if present:
                agg[k]["n_pres"] += 1
                if ment and not side_wrong: agg[k]["TP"] += 1
                else: agg[k]["FN"] += 1          # missed, or wrong hand
                agg[k]["side_wrong"] += side_wrong
                agg[k]["side_given"] += (ment and has_side and cs in ("left", "right")); agg[k]["side_elig"] += (ment and has_side)
            else:
                agg[k]["n_abs"] += 1
                if ment: agg[k]["FP"] += 1
                else: agg[k]["TN"] += 1
        for k, c in sorted(agg.items()):
            n = c["n_pres"] + c["n_abs"]; tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
            acc = (tp + tn) / n; P = tp / (tp + fp) if tp + fp else float("nan"); R = tp / (tp + fn) if tp + fn else float("nan")
            hal = fp / c["n_abs"] if c["n_abs"] else float("nan"); se = c["side_elig"]; sg = f"{c['side_given']/se:.2f}" if se else "  n/a"
            print(f"{k[0]:30s} {k[1]:8s} {k[2]:9s} {c['n_pres']:6d} {c['n_abs']:6d} {acc:6.3f} {P:6.3f} {R:6.3f} {hal:7.3f} {c['side_wrong']:8d} {sg:>10s}")
        print("   halluc = share of known-absent events the caption still mentions; R counts wrong-hand mentions as misses")

    # ---- speech: 말하는 모습 vs 단어까지
    if not args.no_gemini:
        print("\n=== speech events: caption mentions speaking (any) vs gives the word (gemini), among human V PASS ===")
        sp = defaultdict(Counter)
        for r in rows:
            if r["kind"] != "speech" or r["gt_v_pass"] != "True" or r["gemini_mentioned"] == "":
                continue
            sp[(r["condition"], r["model"])]["n"] += 1
            sp[(r["condition"], r["model"])]["any"] += r["gemini_mentioned"] == "True"
            sp[(r["condition"], r["model"])]["word"] += r["gemini_word"] == "True"
        for (cond, model), c in sorted(sp.items()):
            print(f"{cond:30s} {model:8s} n={c['n']:3d}  speaking_any={c['any']/c['n']:.2f}  word={c['word']/c['n']:.2f}")

    # ---- rule vs gemini agreement
    if not args.no_gemini:
        print("\n=== rule vs gemini agreement ===")
        agr = defaultdict(Counter)
        for r in rows:
            if r["gemini_mentioned"] == "":
                continue
            agr[(r["condition"], r["model"])][r["rule_mentioned"] == r["gemini_mentioned"]] += 1
            agr[("ALL", r["kind"])][r["rule_mentioned"] == r["gemini_mentioned"]] += 1
        for k, c in sorted(agr.items()):
            n = c[True] + c[False]
            print(f"{k[0]:30s} {k[1]:8s} agree={c[True]/n:.3f} (n={n})")

    # ---- side summary (Gemini only; non-speech events with a side in the prompt label)
    if not args.no_gemini:
        print("\n=== caption side vs prompt side (Gemini, non-speech events with left/right in label) ===")
        print("  GT PASS & mentioned: side_specified / side_match(of specified)   |   GT FAIL & mentioned: side_specified / side_mismatch(of specified)")
        sd = defaultdict(Counter)
        for r in rows:
            if r["kind"] == "speech" or r["label_side"] in ("", "both") or r["gemini_mentioned"] != "True":
                continue
            grp = (r["condition"], r["model"], "PASS" if r["gt_v_pass"] == "True" else "FAIL")
            sd[grp]["mentioned"] += 1
            if r["gemini_side"] in ("left", "right"):
                sd[grp]["specified"] += 1
                sd[grp]["match" if r["gemini_side"] == r["label_side"] else "mismatch"] += 1
        for (cond, model, g), c in sorted(sd.items()):
            spec_rate = c["specified"] / c["mentioned"] if c["mentioned"] else float("nan")
            key = "match" if g == "PASS" else "mismatch"
            rate = c[key] / c["specified"] if c["specified"] else float("nan")
            print(f"{cond:30s} {model:8s} GT {g:4s} n={c['mentioned']:3d}  side_specified={spec_rate:.2f}  {key}={rate:.2f} (of {c['specified']})")

    # ---- timing summary (timestamped captions only)
    trows = []
    for matcher in (["dt_rule"] if args.no_gemini else ["dt_rule", "dt_gemini"]):
        grp = defaultdict(list); nfb = Counter()
        for r in rows:
            if r["caption_is_ts"] != "True" or r[matcher] == "" or r["kind"] == "silent":
                continue
            k = (r["condition"], r["model"], r["kind"], matcher)
            grp[k].append(float(r[matcher]))
            if r["tool_fallback"] == "True":
                nfb[k] += 1
        for (cond, model, kind, m), ds in sorted(grp.items()):
            ds.sort()
            med = ds[len(ds) // 2]
            trows.append(dict(condition=cond, model=model, kind=kind, matcher=m, n=len(ds), n_tool_fallback=nfb[(cond, model, kind, m)],
                              median_dt=round(med, 3),
                              frac_le_0p5=round(sum(d <= 0.5 for d in ds) / len(ds), 3),
                              frac_le_1p0=round(sum(d <= 1.0 for d in ds) / len(ds), 3)))
    if trows:
        st = os.path.join(args.out, "summary_timing.csv")
        with open(st, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(trows[0].keys())); w.writeheader(); w.writerows(trows)
        print(f"\n[write] {st}")
        print("\n=== caption time range vs audio tool time (|dt| s; timestamped captions, speech/sounding only) ===")
        for t in trows:
            print(f"{t['condition']:30s} {t['model']:8s} {t['kind']:9s} {t['matcher']:10s} n={t['n']:3d} (fallback {t['n_tool_fallback']:2d}) "
                  f"median={t['median_dt']:.2f}  <=0.5s {t['frac_le_0p5']:.2f}  <=1s {t['frac_le_1p0']:.2f}")
    else:
        print("\n[timing] timestamped 캡션 행이 없음 (조건 이름 확인: omni_fps8_ts_v3, qwen3vl_fps8_v3)")


if __name__ == "__main__":
    main()
