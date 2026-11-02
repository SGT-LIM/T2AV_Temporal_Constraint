#!/usr/bin/env python3
# VENDORED from /projectnb/ivc-ml/youngsun/T2AV_data/real_av_pilot/build_items.py (md5 30f6fdb8032b4c36fcbed5095385fcd6, mtime 2026-11-01 21:58, copied 2026-11-02).
# Verbatim except this header, the paths import below, and the ANN line (annotations stay in T2AV_data). Kept in sync by
# tests/test_vendored.py. Includes --anchor-mode eligible (11/01).
"""Window-based item builder for HD-EPIC (A/V/AVB/TC-Relation/TC-Count) and CountixAV (TC-Count). v7 (2026-09-15).

Design principle: NO hand-written verb vocabulary. Events are whatever the HD-EPIC annotators wrote; "same action" is
defined by the dataset's own (verb_class, noun_class) from main_action_classes. Every remaining rule is a number or a
structural condition and is listed in RULES below so it can be reported and varied.

Each item = one real clip + one prompt + per-axis GT vector. PASS item asserts every axis and the real video satisfies
all; each FAIL variant breaks exactly one axis and leaves the others PASS.

  python build_items.py hdepic    --participants P01 P02 --out items_hdepic_medium.json
  python build_items.py countixav --split val --out items_countixav_val.json
"""
import argparse, json, random, ast
from t2av_eval import paths as _P
from pathlib import Path
import numpy as np, pandas as pd

ANN = _P.DATA / "real_av_pilot" / "annotations"     # vendored: was Path(__file__).resolve().parent / "annotations"
random.seed(42)

RULES = dict(
    window_s=25.0,            # clip length
    pre_pad_s=5.0,            # clip starts this long before the first anchor
    min_event_s=0.7,          # narration duration lower bound for silent events (= 25th percentile of all HD-EPIC narrations, 0.73 s)
    max_silent=3,             # silent events per window, spread evenly in time
    merge_gap_s=1.0,          # consecutive narrations of the same (verb_class, noun_class) closer than this = one occurrence
    sound_tol_s=0.15,         # tolerance when matching a sound segment to an action segment
    max_sound_s=5.0,          # sound segments longer than this are background (excluded from pairing)
    swap_min_gap_s=1.0,       # TC-Relation FAIL swaps adjacent occurrences at least this far apart
    shift_candidates_s=[2.0, 2.5, 3.0, 1.5],   # AVB FAIL audio offset magnitude: first candidate with no coincidental realignment
    shift_collision_tol_s=1.0,                  # a shifted anchor sound landing within this of any same-class action = coincidental match
)

# Anchors: the only place a vocabulary appears, and it is the sound-class pairing (which HD-EPIC does not provide).
# verb_class id (HD_EPIC_verb_classes.csv) -> HD-EPIC-Sounds class it must co-occur with.
ANCHOR_VC = {4: 'open / close',    # close
             7: 'cut / chop',      # cut (cut/slice/chop/dice ...)
             21: 'beep',           # press
             8: 'water'}           # turn-off (only when noun class is tap; sound = water stops)
TAP_NC = 0

# 11/01 (user): the fixed 4-class table above is no longer the rule for new builds. --anchor-mode eligible pairs ANY non-ambient
# HD-EPIC-Sounds class with ANY narration action under the same clean-pair rule (find_anchors), except the collision classes below,
# in whichever participant it appears; the >= 20 dB loudness rule is applied afterwards on the clip audio
# (gepa_stage2/make_mute_anchor.db_reimpl), as for mute_anchor. --anchor-mode table (default) reproduces the 10/08 and 10/28 item files.
ANCHOR_MODE = 'table'
AMBIENT_CLASSES = {'background', 'sizzling / boiling', 'kettle / mixer / appliance', 'hoover / fan'}
EXCLUDED_CLASSES = {'metal-only collision', 'plastic-only collision', 'metal / plastic collision'}   # first 11/01 exclusion (superseded below)
# 11/01 (user, final): every collision class is excluded; the eligible anchor classes are the non-collision classes with enough
# pairs passing >= 20 dB in both groups (docs/event_inventory_1101.md): open / close, cut / chop, stir / mix / whisk. water and beep
# drop (their intended pairs, turn-off tap and press, never pass the loudness rule). stir / mix / whisk is for A and AVB only: no
# count_off claim may target a stir event (a continuous stirring action has no agreed count); TCR may keep it.
ELIGIBLE_CLASSES = {'open / close', 'cut / chop', 'stir / mix / whisk'}
NO_COUNT_CLASSES = {'stir / mix / whisk'}
def sound_text(cls):
    """sound described by its HD-EPIC-Sounds class label, no paraphrase"""
    return f"a '{cls}' sound" if cls != 'water' else "the 'water' sound stopping"
# A-FAIL claim: the most frequent HD-EPIC-Sounds class (dataset-wide) that does not occur in the window (set at load time)
SOUND_CLASS_FREQ = []
NOUN_CLASS_NAME = {}   # noun class id -> HD-EPIC class key, filled at load time


def third_person(verb):
    """annotated verb (imperative) -> 3rd person: 'pick up' -> 'picks up', 'turn on' -> 'turns on', 'wash' -> 'washes'"""
    parts = verb.split()
    v = parts[0]
    if v.endswith(('s', 'sh', 'ch', 'x', 'z')): v += 'es'
    elif v.endswith('y') and v[-2] not in 'aeiou': v = v[:-1] + 'ies'
    else: v += 's'
    return ' '.join([v] + parts[1:])


def load_hdepic(participants):
    s = pd.read_csv(ANN / 'HD_EPIC_Sounds.csv'); n = pd.read_pickle(ANN / 'HD_EPIC_Narrations.pkl')
    s['st'] = pd.to_timedelta(s.start_timestamp).dt.total_seconds(); s['en'] = pd.to_timedelta(s.stop_timestamp).dt.total_seconds()
    s = s[(s.en - s.st) < RULES['max_sound_s']].reset_index(drop=True)
    global SOUND_CLASS_FREQ, NOUN_CLASS_NAME
    SOUND_CLASS_FREQ = list(s['class'].value_counts().index)   # all participants, most frequent first
    NOUN_CLASS_NAME = pd.read_csv(ANN / 'HD_EPIC_noun_classes.csv').set_index('id')['key'].str.replace(':', ' ').to_dict()
    n = n[n.participant_id.isin(participants)].copy()
    ok = n.main_actions.apply(len).gt(0) & n.main_action_classes.apply(lambda x: len(x) > 0 and len(x[0]) == 2)
    n = n[ok].copy()
    n['verb'] = n.main_actions.apply(lambda x: x[0][0]); n['noun'] = n.main_actions.apply(lambda x: x[0][1])
    n['vc'] = n.main_action_classes.apply(lambda x: int(x[0][0])); n['nc'] = n.main_action_classes.apply(lambda x: int(x[0][1]))
    n['hand'] = n.hands.apply(lambda h: (lambda hh: hh[0] if len(hh) == 1 else None)([x for x in list(h) if x in ('left hand', 'right hand')]))
    n['hand'] = n['hand'].astype(object).where(n['hand'].notna(), None)
    n['dur'] = n.end_timestamp - n.start_timestamp
    return s, n


def find_anchors_eligible(s, n):
    """--anchor-mode eligible: the find_anchors clean-pair rule for every verb class and every non-ambient, non-excluded sound class."""
    out = []
    s = s[s['class'].isin(ELIGIBLE_CLASSES) & ~s['class'].str.contains('collision')]
    for vid, g in n.groupby('video_id'):
        sg = s[s.video_id == vid]; st, en, cl = sg.st.values, sg.en.values, sg['class'].values
        nst, nen = g.start_timestamp.values, g.end_timestamp.values
        tol = RULES['sound_tol_s']
        for r in g.itertuples():
            idx = np.where((st < r.end_timestamp + tol) & (en > r.start_timestamp - tol))[0]
            for tgt in sorted(set(cl[idx])):
                hit = [i for i in idx if cl[i] == tgt]
                if len(hit) != 1: continue
                i = hit[0]
                if ((nst < en[i]) & (nen > st[i])).sum() != 1: continue
                if st[i] > r.end_timestamp + tol: continue
                out.append(dict(video_id=vid, nid=r.unique_narration_id, verb=r.verb, noun=r.noun, vc=r.vc, nc=r.nc, hand=r.hand,
                                a_st=float(r.start_timestamp), a_en=float(r.end_timestamp), s_st=float(st[i]), s_en=float(en[i]), sound=tgt))
    return pd.DataFrame(out).sort_values(['video_id', 'a_st']).reset_index(drop=True)


def find_anchors(s, n):
    """Action-sound pairs: anchor verb class; exactly one segment of the paired sound class overlaps the action (+- tol);
    that sound segment overlaps no other narration; the sound starts before the action ends."""
    out = []
    for vid, g in n.groupby('video_id'):
        sg = s[s.video_id == vid]; st, en, cl = sg.st.values, sg.en.values, sg['class'].values
        nst, nen = g.start_timestamp.values, g.end_timestamp.values
        tol = RULES['sound_tol_s']
        for r in g.itertuples():
            if r.vc not in ANCHOR_VC: continue
            if r.vc == 8 and r.nc != TAP_NC: continue
            tgt = ANCHOR_VC[r.vc]
            idx = np.where((st < r.end_timestamp + tol) & (en > r.start_timestamp - tol))[0]
            hit = [i for i in idx if cl[i] == tgt]
            if len(hit) != 1: continue
            i = hit[0]
            if ((nst < en[i]) & (nen > st[i])).sum() != 1: continue
            if st[i] > r.end_timestamp + tol: continue
            out.append(dict(video_id=vid, nid=r.unique_narration_id, verb=r.verb, noun=r.noun, vc=r.vc, nc=r.nc, hand=r.hand,
                            a_st=float(r.start_timestamp), a_en=float(r.end_timestamp), s_st=float(st[i]), s_en=float(en[i]), sound=tgt))
    return pd.DataFrame(out).sort_values(['video_id', 'a_st']).reset_index(drop=True)


def occurrences(win_n, vc, nc, lo):
    """start times (relative to lo) of occurrences of (vc, nc) in the window; consecutive narrations closer than
    merge_gap_s are one occurrence (annotators split long actions)."""
    same = win_n[(win_n.vc == vc) & (win_n.nc == nc)].sort_values('start_timestamp')
    occ, last_end = [], -1e9
    for r in same.itertuples():
        if r.start_timestamp - last_end >= RULES['merge_gap_s']: occ.append(round(r.start_timestamp - lo, 2))
        last_end = max(last_end, r.end_timestamp)
    hands = set(same.hand); hand = hands.pop() if len(hands) == 1 and None not in hands else None
    verb = same.verb.mode().iloc[0] if len(same) else None                      # most frequent annotated verb in the group
    nouns = set(same.noun)
    noun = nouns.pop() if len(nouns) == 1 else NOUN_CLASS_NAME.get(nc, same.noun.iloc[0])   # class name when objects differ
    return occ, hand, verb, noun


def build_windows(s, n, anchors):
    W, pad = RULES['window_s'], RULES['pre_pad_s']
    items = []
    for vid, g in anchors.groupby('video_id'):
        nn = n[n.video_id == vid]; sg = s[s.video_id == vid]
        vid_nc = set(nn.nc)
        last_hi = -1e9
        for p in g.itertuples():
            lo = max(0.0, p.a_st - pad)
            if lo < last_hi: continue
            hi = lo + W; last_hi = hi
            win_n = nn[(nn.start_timestamp >= lo) & (nn.end_timestamp <= hi)]
            win_anchors = g[(g.a_st >= lo) & (g.a_en <= hi)]
            win_sounds = set(sg[(sg.st >= lo) & (sg.en <= hi)]['class'])
            # silent candidates: any narration not of an anchor class, long enough, not overlapping an anchor action
            cand = win_n[(~win_n.vc.isin(ANCHOR_VC if ANCHOR_MODE == 'table' else set(win_anchors.vc))) & (win_n.dur >= RULES['min_event_s'])]
            cand = cand[~cand.apply(lambda r: any((r.start_timestamp < a.a_en) and (r.end_timestamp > a.a_st) for a in win_anchors.itertuples()), axis=1)] if len(cand) else cand
            # one candidate per (vc, nc): keep the earliest
            cand = cand.sort_values('start_timestamp').drop_duplicates(['vc', 'nc'])
            if len(cand) < 2: continue
            pick = cand.iloc[np.unique(np.linspace(0, len(cand) - 1, min(RULES['max_silent'], len(cand))).astype(int))]
            events = []
            for a in win_anchors.drop_duplicates(['vc', 'nc']).itertuples():
                occ, hand, verb, noun = occurrences(win_n, a.vc, a.nc, lo)
                k_snd = int(((sg.st >= lo) & (sg.en <= hi) & (sg['class'] == a.sound)).sum())
                events.append(dict(kind='sounding', verb=verb, noun=noun, vc=int(a.vc), nc=int(a.nc), hand=hand, sound=a.sound,
                                   count=len(occ), occurrences=occ, sound_segments_in_window=k_snd, t=[round(a.a_st - lo, 2), round(a.a_en - lo, 2)],
                                   sound_t=[round(a.s_st - lo, 2), round(a.s_en - lo, 2)]))
            for r in pick.itertuples():
                occ, hand, verb, noun = occurrences(win_n, r.vc, r.nc, lo)
                events.append(dict(kind='silent', verb=verb, noun=noun, vc=int(r.vc), nc=int(r.nc), hand=hand,
                                   count=len(occ), occurrences=occ, t=[round(r.start_timestamp - lo, 2), round(r.end_timestamp - lo, 2)]))
            events.sort(key=lambda e: e['t'][0])
            seq = sorted([(t, i) for i, e in enumerate(events) for t in e['occurrences']])
            shifts = choose_shifts(events, win_n, sg, lo, hi)
            items.extend(make_variants(vid, lo, hi, events, seq, win_sounds, vid_nc, set(win_n.nc), nn, shifts))
    return items


def choose_shifts(events, win_n, sg, lo, hi):
    """For each direction pick the first candidate magnitude such that no shifted anchor-class sound lands within
    shift_collision_tol_s of ANY same-class action in the window. Returns {'AVBlate': +s or None, 'AVBearly': -s or None}."""
    tol = RULES['shift_collision_tol_s']; out = {}
    snd_act = []
    for e in events:
        if e['kind'] != 'sounding': continue
        snd = sg[(sg.st >= lo) & (sg.en <= hi) & (sg['class'] == e['sound'])].st.values
        acts = win_n[win_n.vc == e['vc']][['start_timestamp', 'end_timestamp']].values
        snd_act.append((snd, acts))
    for tag, sign in (('AVBlate', 1), ('AVBearly', -1)):
        chosen = None
        for mag in RULES['shift_candidates_s']:
            sh = sign * mag; ok = True
            for snd, acts in snd_act:
                for st in snd:
                    t = st + sh
                    if any((a0 - tol <= t <= a1 + tol) for a0, a1 in acts): ok = False; break
                if not ok: break
            if ok: chosen = sh; break
        out[tag] = chosen
    return out


def ev_text(e, hand=None):
    h = f" with the {hand}" if hand else ""
    return f"{third_person(e['verb'])} the {e['noun']}{h}"


def prompt_from(events, seq, extra=None):
    order = [i for _, i in seq] + ([extra] if extra is not None else [])
    seen, parts = {}, []
    for i in order:
        e = events[i]
        txt = ev_text(e, e.get('hand')) + (' again' if seen.get(i) else '')
        if e['kind'] == 'sounding': txt += f", with {sound_text(e['sound'])}"
        seen[i] = seen.get(i, 0) + 1; parts.append(txt)
    body = "A person " + parts[0]
    for p in parts[1:]: body += f", then {p}"
    return body + ". These listed actions happen in this order and exactly this many times in the clip."


def make_variants(vid, lo, hi, events, seq, win_sounds, vid_nc, win_nc, nn, shifts):
    axes_all = ['A', 'V', 'AVB', 'TC-Relation', 'TC-Count']
    base = dict(source='hdepic', video_id=vid, clip=[round(lo, 2), round(hi, 2)], events=events, sequence=seq, axes=axes_all)
    wid = f"hdepic_{vid}_{int(lo*100):07d}"
    def gt(fail=None, broken_kind=None):
        # hierarchy: A fail -> AVB fail; V fail on a SOUNDING event -> AVB fail; any A/V/AVB fail -> TC-Rel & TC-Cnt fail
        g = {a: 'PASS' for a in axes_all}
        if fail is None: return g
        g[fail] = 'FAIL'
        if fail == 'A' or (fail == 'V' and broken_kind == 'sounding'): g['AVB'] = 'FAIL'
        if fail in ('A', 'V', 'AVB'): g['TC-Relation'] = 'FAIL'; g['TC-Count'] = 'FAIL'
        return g
    out = [{**base, 'item_id': f"{wid}_pass", 'variant': 'original', 'gt': gt(), 'prompt': prompt_from(events, seq), 'media': {'op': 'cut'}}]
    # A FAIL: claim a sound class that never occurs in the window
    absent = [c for c in SOUND_CLASS_FREQ if c not in win_sounds and c != 'background']
    if absent:
        c = absent[0]; txt = f"a '{c}' sound"
        out.append({**base, 'item_id': f"{wid}_A", 'variant': 'fail_absent_sound', 'gt': gt('A'), 'broken_event_kind': 'sounding',
                    'prompt': prompt_from(events, seq)[:-1] + f", and {txt} can be heard.", 'media': {'op': 'cut'},
                    'a_fail_claim': dict(sound=c, text=txt), 'fail_reason': f"claims {c} (most frequent class absent from window); window has {sorted(win_sounds)}"})
    out.append({**base, 'item_id': f"{wid}_mute", 'variant': 'fail_mute', 'gt': gt('A'), 'broken_event_kind': 'sounding', 'prompt': prompt_from(events, seq),
                'media': {'op': 'cut+mute'}, 'fail_reason': 'audio removed'})
    # V FAIL (hand): swap the stated hand of the first event that has one
    hand_ev = [e for e in events if e.get('hand')]
    if hand_ev:
        e = hand_ev[0]; other = 'left hand' if e['hand'] == 'right hand' else 'right hand'
        ev2 = [dict(x, hand=other) if x is e else x for x in events]
        bi = events.index(e)
        out.append({**base, 'events': ev2, 'broken_event_idx': bi, 'broken_event_kind': e['kind'],
                    'item_id': f"{wid}_Vhand", 'variant': 'fail_hand_swap', 'gt': gt('V', e['kind']), 'prompt': prompt_from(ev2, seq),
                    'media': {'op': 'cut'}, 'fail_reason': f"{e['verb']} {e['noun']}: prompt says {other}, annotation says {e['hand']}"})
    # V FAIL (object): replace the object of a silent event with an object of another noun class that this participant
    # interacts with in this video (so it exists in the kitchen) but not inside this window (so the action is absent here)
    sil = [e for e in events if e['kind'] == 'silent']
    if sil:
        e = sil[0]
        pool = nn[(~nn.nc.isin(win_nc)) & (nn.vc == e['vc'])]        # same verb class, object never touched in this window
        if len(pool) == 0: pool = nn[~nn.nc.isin(win_nc)]
        if len(pool):
            r = pool.sample(1, random_state=hash(wid) % 2**32).iloc[0]
            ev2 = [dict(x, noun=r.noun) if x is e else x for x in events]
            bi = events.index(e)
            out.append({**base, 'events': ev2, 'broken_event_idx': bi, 'broken_event_kind': e['kind'],
                        'item_id': f"{wid}_Vnoun", 'variant': 'fail_noun_swap', 'gt': gt('V', e['kind']), 'prompt': prompt_from(ev2, seq),
                        'media': {'op': 'cut'}, 'fail_reason': f"prompt says {e['verb']} {r.noun} (noun class {int(r.nc)} absent from window), video shows {e['noun']}"})
    # AVB FAIL: audio offset
    for tag, sh in shifts.items():
        if sh is None: continue   # every candidate magnitude realigns with another same-class action: no clean AVB negative for this window
        out.append({**base, 'item_id': f"{wid}_{tag}", 'variant': f'fail_audio_shift_{"late" if sh > 0 else "early"}', 'gt': gt('AVB'), 'broken_event_kind': 'sounding',
                    'prompt': prompt_from(events, seq), 'media': {'op': 'cut+audio_shift', 'shift_s': sh}, 'fail_reason': f"audio shifted {sh:+.1f}s"})
    # TC-Relation FAIL: swap two adjacent occurrences of different events at least swap_min_gap_s apart
    for j in range(len(seq) - 1):
        (t1, i1), (t2, i2) = seq[j], seq[j + 1]
        if i1 != i2 and t2 - t1 >= RULES['swap_min_gap_s']:
            seq2 = seq[:j] + [(t1, i2), (t2, i1)] + seq[j + 2:]
            out.append({**base, 'item_id': f"{wid}_TCR", 'variant': 'fail_order_swap', 'gt': gt('TC-Relation'), 'prompt': prompt_from(events, seq2),
                        'media': {'op': 'cut'}, 'sequence_claimed': seq2, 'fail_reason': f"swapped '{events[i1]['verb']} {events[i1]['noun']}' and '{events[i2]['verb']} {events[i2]['noun']}'"})
            break
    # TC-Count FAIL: claim one extra occurrence of an event (prefer one that already repeats)
    countable = [i for i, e in enumerate(events) if not (ANCHOR_MODE == 'eligible' and e.get('sound') in NO_COUNT_CLASSES)]
    if not countable:
        return out                                   # eligible mode: no countable event -> no count_off item for this window
    idx = next((i for i in countable if events[i]['count'] >= 2), countable[0])
    out.append({**base, 'item_id': f"{wid}_TCC", 'variant': 'fail_count_off', 'gt': gt('TC-Count'), 'prompt': prompt_from(events, seq, extra=idx),
                'media': {'op': 'cut'}, 'count_override': {str(idx): events[idx]['count'] + 1},
                'fail_reason': f"{events[idx]['verb']} {events[idx]['noun']}: prompt claims {events[idx]['count'] + 1}, annotation {events[idx]['count']}"})
    return out


# ---------------- CountixAV ----------------
def countixav_items(split):
    d = pd.read_csv(ANN / f'CountixAV_{split}.csv')
    if 'class' not in d: d['class'] = 'repetitive action'
    items = []
    for _, r in d.iterrows():
        if r.repetition_end - r.repetition_start > 10 or not (2 <= r['count'] <= 12): continue
        cid = f"{r.video_id}_{int(r.kinetics_start):06d}_{int(r.kinetics_end):06d}"
        lo, hi = round(r.repetition_start - r.kinetics_start, 2), round(r.repetition_end - r.kinetics_start, 2)
        n = int(r['count']); act = r['class']
        base = dict(source='countixav', video_id=cid, clip=[lo, hi], events=[dict(kind='repetitive', action=act, count=n)], axes=['TC-Count'])
        iid = f"countixav_{cid}_{int(lo*100):05d}"
        items.append({**base, 'item_id': f"{iid}_pass", 'variant': 'original', 'gt': {'TC-Count': 'PASS'},
                      'prompt': f"A person doing {act}, repeated exactly {n} times.", 'media': {'op': 'cut'}})
        wrong = n + random.choice([k for k in (-3, -2, 2, 3) if 2 <= n + k <= 20])
        items.append({**base, 'item_id': f"{iid}_TCC", 'variant': 'fail_count_off', 'gt': {'TC-Count': 'FAIL'},
                      'prompt': f"A person doing {act}, repeated exactly {wrong} times.", 'media': {'op': 'cut'}, 'fail_reason': f"prompt count {wrong}, true count {n}"})
    return items


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset', choices=['hdepic', 'countixav'])
    ap.add_argument('--participants', nargs='+', default=['P01', 'P02'])
    ap.add_argument('--split', default='val')
    ap.add_argument('--anchor-mode', choices=['table', 'eligible'], default='table')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.dataset == 'hdepic':
        ANCHOR_MODE = a.anchor_mode
        s, n = load_hdepic(a.participants); anc = find_anchors(s, n) if ANCHOR_MODE == 'table' else find_anchors_eligible(s, n)
        print(f"anchors: {len(anc)} {anc.verb.value_counts().to_dict()}")
        items = build_windows(s, n, anc)
    else:
        items = countixav_items(a.split)
    json.dump(items, open(a.out, 'w'), indent=1)
    df = pd.DataFrame(items)
    print(f"{len(items)} items, {df.video_id.nunique()} videos -> {a.out}")
    print(df.variant.value_counts().to_string())
