# render_all_mediapipe_overlay.py
import json, cv2, argparse
from pathlib import Path

HAND_CONNECTIONS = [
    ("wrist","thumb_cmc"), ("thumb_cmc","thumb_mcp"), ("thumb_mcp","thumb_ip"), ("thumb_ip","thumb_tip"),
    ("wrist","index_mcp"), ("index_mcp","index_pip"), ("index_pip","index_dip"), ("index_dip","index_tip"),
    ("wrist","middle_mcp"), ("middle_mcp","middle_pip"), ("middle_pip","middle_dip"), ("middle_dip","middle_tip"),
    ("wrist","ring_mcp"), ("ring_mcp","ring_pip"), ("ring_pip","ring_dip"), ("ring_dip","ring_tip"),
    ("wrist","pinky_mcp"), ("pinky_mcp","pinky_pip"), ("pinky_pip","pinky_dip"), ("pinky_dip","pinky_tip"),
]

POSE_CONNECTIONS = [
    ("left_shoulder","right_shoulder"),
    ("left_shoulder","left_elbow"), ("left_elbow","left_wrist"),
    ("right_shoulder","right_elbow"), ("right_elbow","right_wrist"),
    ("left_shoulder","left_hip"), ("right_shoulder","right_hip"),
    ("left_hip","right_hip"),
    ("left_hip","left_knee"), ("left_knee","left_ankle"),
    ("right_hip","right_knee"), ("right_knee","right_ankle"),
]

def pt(lm, w, h):
    return int(lm["x"] * w), int(lm["y"] * h)

def draw_landmarks(img, landmarks, connections, prefix="", draw_names=True, radius=3):
    h, w = img.shape[:2]

    for a, b in connections:
        if a in landmarks and b in landmarks:
            cv2.line(img, pt(landmarks[a], w, h), pt(landmarks[b], w, h), (0, 255, 0), 2)

    for name, lm in landmarks.items():
        x, y = pt(lm, w, h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(img, (x, y), radius, (0, 0, 255), -1)
            if draw_names:
                cv2.putText(img, f"{prefix}{name}", (x + 4, y - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 255, 255), 1, cv2.LINE_AA)

def render_one(video_path, json_path, out_path, draw_names=True, draw_face=True):
    data = json.load(open(json_path))
    samples = data["sampled_frames"]

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    frame_idx = 0
    sample_i = 0

    while True:
        ok, img = cap.read()
        if not ok:
            break

        t = frame_idx / fps

        while sample_i + 1 < len(samples) and abs(samples[sample_i + 1]["t"] - t) < abs(samples[sample_i]["t"] - t):
            sample_i += 1

        fr = samples[sample_i]

        if fr.get("pose_landmarks"):
            draw_landmarks(img, fr["pose_landmarks"], POSE_CONNECTIONS, "pose:", draw_names, radius=4)

        if fr.get("left_hand_landmarks"):
            draw_landmarks(img, fr["left_hand_landmarks"], HAND_CONNECTIONS, "L:", draw_names, radius=3)

        if fr.get("right_hand_landmarks"):
            draw_landmarks(img, fr["right_hand_landmarks"], HAND_CONNECTIONS, "R:", draw_names, radius=3)

        if draw_face and fr.get("mouth_lip_landmarks"):
            draw_landmarks(img, fr["mouth_lip_landmarks"], [], "face:", draw_names=False, radius=2)

        cv2.putText(img, f"t={t:.2f}s | sample={fr['sample_index']} @ {fr['t']:.2f}s",
                    (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2, cv2.LINE_AA)

        writer.write(img)
        frame_idx += 1

    cap.release()
    writer.release()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-root", required=True)
    ap.add_argument("--video-root", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--no-names", action="store_true")
    args = ap.parse_args()

    json_root = Path(args.json_root)
    video_root = Path(args.video_root)
    out_root = Path(args.out_root)

    json_files = sorted(json_root.rglob("*_raw.json"))

    print(f"[INFO] found {len(json_files)} json files")

    for jp in json_files:
        stem = jp.stem              # xxx_raw
        mp4_name = stem + ".mp4"

        candidates = list(video_root.rglob(mp4_name))
        if not candidates:
            print(f"[WARN] video not found for {jp}")
            continue

        vp = candidates[0]

        rel = jp.relative_to(json_root)
        out_path = out_root / rel.with_suffix(".mp4")

        print(f"[RENDER] {vp} -> {out_path}")
        render_one(
            video_path=vp,
            json_path=jp,
            out_path=out_path,
            draw_names=not args.no_names,
            draw_face=True,
        )

    print("[DONE]")

if __name__ == "__main__":
    main()