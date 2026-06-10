import ast
import re
import cv2
import pandas as pd
import mediapipe as mp
from pathlib import Path

CSV_PATH = "/home/coder/T2V_Gen/results/gemini/with_tools/focused_raw/results.csv"
VIDEO_PATH = "/home/coder/T2V_Gen/LTX-2/outputs/refined_prompt_ver2/Si_So_rel_ord_SoSi/Si_So_rel_ord_SoSi_v1_raw.mp4"
VIDEO_RELPATH = "Si_So_rel_ord_SoSi/Si_So_rel_ord_SoSi_v1_raw.mp4"

OUTDIR = Path("/home/coder/T2V_Gen/LTX-2/outputs/refined_prompt_ver2/Si_So_rel_ord_SoSi/focused_mediapipe_overlay")
OUTDIR.mkdir(parents=True, exist_ok=True)

def extract_list(text, key):
    m = re.search(rf"{re.escape(key)}: (\[.*?\])", text)
    if not m:
        return []
    return ast.literal_eval(m.group(1))

df = pd.read_csv(CSV_PATH)
row = df[df["video_relpath"] == VIDEO_RELPATH].iloc[0]
summary = row["mediapipe_summary"]

selected_pose = set(extract_list(summary, "Selected pose landmarks"))
selected_left = set(extract_list(summary, "Selected left-hand landmarks"))
selected_right = set(extract_list(summary, "Selected right-hand landmarks"))

print("Selected pose:", selected_pose)
print("Selected left hand:", selected_left)
print("Selected right hand:", selected_right)

mp_holistic = mp.solutions.holistic

pose_names = {i: lm.name.lower() for i, lm in enumerate(mp_holistic.PoseLandmark)}

hand_names = {
    0: "wrist",
    1: "thumb_cmc",
    2: "thumb_mcp",
    3: "thumb_ip",
    4: "thumb_tip",
    5: "index_mcp",
    6: "index_pip",
    7: "index_dip",
    8: "index_tip",
    9: "middle_mcp",
    10: "middle_pip",
    11: "middle_dip",
    12: "middle_tip",
    13: "ring_mcp",
    14: "ring_pip",
    15: "ring_dip",
    16: "ring_tip",
    17: "pinky_mcp",
    18: "pinky_pip",
    19: "pinky_dip",
    20: "pinky_tip",
}

def draw_filtered(img, landmarks, names, selected, prefix, color):
    if landmarks is None:
        return
    h, w = img.shape[:2]
    for idx, lm in enumerate(landmarks.landmark):
        name = names.get(idx)
        if name not in selected:
            continue
        x, y = int(lm.x * w), int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(img, (x, y), 5, color, -1)
            cv2.putText(
                img,
                f"{prefix}{name}",
                (x + 5, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                color,
                1,
                cv2.LINE_AA,
            )

cap = cv2.VideoCapture(VIDEO_PATH)
src_fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

sample_fps = 8.0
max_frames = 40
step = max(1, round(src_fps / sample_fps))

out_video = str(OUTDIR / "Si_So_rel_ord_SoSi_v1_focused_filtered_keypoints.mp4")
writer = cv2.VideoWriter(
    out_video,
    cv2.VideoWriter_fourcc(*"mp4v"),
    sample_fps,
    (w, h),
)

with mp_holistic.Holistic(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    refine_face_landmarks=False,
    enable_segmentation=False,
) as holistic:
    frame_idx = 0
    sample_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret or sample_idx >= max_frames:
            break

        if frame_idx % step != 0:
            frame_idx += 1
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = holistic.process(rgb)
        vis = frame.copy()

        draw_filtered(vis, res.pose_landmarks, pose_names, selected_pose, "pose:", (0, 255, 255))
        draw_filtered(vis, res.left_hand_landmarks, hand_names, selected_left, "L:", (255, 0, 0))
        draw_filtered(vis, res.right_hand_landmarks, hand_names, selected_right, "R:", (0, 0, 255))

        t = frame_idx / src_fps
        cv2.putText(
            vis,
            f"focused_raw filtered only | sample={sample_idx} frame={frame_idx} t={t:.2f}s",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imwrite(str(OUTDIR / f"focused_{sample_idx:03d}_t{t:.2f}.jpg"), vis)
        writer.write(vis)

        sample_idx += 1
        frame_idx += 1

cap.release()
writer.release()

print("Saved frames:", OUTDIR)
print("Saved video:", out_video)
