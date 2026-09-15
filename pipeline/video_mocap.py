"""Phone video -> motion file, with no mocap suit, no service and no fee.

    python3 pipeline/video_mocap.py IN.mp4 motions/video/squat.json \
        [--start 1.5] [--end 6.0] [--auto-rep] [--fps 30] [--smooth 1.5] \
        [--mirror] [--source "own capture, iPhone 15, side view"]

Runs Google MediaPipe Pose (Apache-2.0, on-device, CPU) over the clip and
writes the per-frame world directions of every driver bone that
pipeline/build_exercise.py already retargets — the same override table the
Mixamo lane feeds into transfer_pose — so a clip you shoot of yourself doing
a lunge becomes a motion source exactly like a Mixamo FBX, except that you
own it and can redistribute the result.

What comes out is *directions*, not joint angles: thigh = hip->knee, shin =
knee->ankle, foot = ankle->toe, upper arm = shoulder->elbow, forearm =
elbow->wrist, hand = wrist->index, spine = hip centre->shoulder centre, neck
= shoulder centre->ear centre. The pelvis carries a full basis (left,
forward, up) so a push-up or bridge takes the legs with it. Hip height above
the lowest foot point gives the vertical root travel (world landmarks are
hip-centred, so the video cannot say how far the hips moved; a squat's drop
is recovered from the feet instead). Horizontal travel is zero: exercises
are rendered in place.

Roll references ("twists") are the body's own forward carried through the
pelvis/torso rotation and projected perpendicular to each segment — the same
rule aim_bone's twist_ref applies to the MakeHuman rest pose — because a
monocular pose model has no axial rotation to give. That is enough to keep
the shortest-arc flips out of a squat, a lunge or a curl; it is not enough
for a wrist pronation cue, and it says so in the output metadata.

Conventions match the renderer: metres, Z up, the figure faces -Y, its left
side at +X. The clip's facing is measured from the hips and yawed into that
frame automatically, so a side-view video and a front-view video produce the
same motion file.

Requirements (local only — this never runs in CI):
    uv venv --python 3.12 .venv && uv pip install mediapipe==0.10.21 opencv-python-headless numpy
MediaPipe 1.0.x crashes on macOS (Metal delegate, "Service is unavailable");
0.10.21 with the CPU delegate is the version that works, on Apple silicon.
The pose model (pose_landmarker_heavy.task, ~30 MB) downloads once into
~/.cache/opengym3d/.
"""
import argparse
import json
import math
import os
import sys
import urllib.request

import numpy as np

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task")
MODEL_PATH = os.path.expanduser("~/.cache/opengym3d/pose_landmarker_heavy.task")

# MediaPipe BlazePose landmark indices
NOSE, EAR_L, EAR_R = 0, 7, 8
SHO_L, SHO_R, ELB_L, ELB_R, WRI_L, WRI_R = 11, 12, 13, 14, 15, 16
IDX_L, IDX_R = 19, 20
HIP_L, HIP_R, KNEE_L, KNEE_R, ANK_L, ANK_R = 23, 24, 25, 26, 27, 28
HEEL_L, HEEL_R, TOE_L, TOE_R = 29, 30, 31, 32
FLOOR_POINTS = (ANK_L, ANK_R, HEEL_L, HEEL_R, TOE_L, TOE_R)

# driver bone -> (from landmark(s), to landmark(s)); centres are averaged
SEGMENTS = {
    "spine": ((HIP_L, HIP_R), (SHO_L, SHO_R)),
    "chest": ((HIP_L, HIP_R), (SHO_L, SHO_R)),
    "neck": ((SHO_L, SHO_R), (EAR_L, EAR_R)),
    "head": ((SHO_L, SHO_R), (EAR_L, EAR_R)),
    "thigh.L": (HIP_L, KNEE_L), "shin.L": (KNEE_L, ANK_L), "foot.L": (ANK_L, TOE_L),
    "thigh.R": (HIP_R, KNEE_R), "shin.R": (KNEE_R, ANK_R), "foot.R": (ANK_R, TOE_R),
    "upper_arm.L": (SHO_L, ELB_L), "forearm.L": (ELB_L, WRI_L), "hand.L": (WRI_L, IDX_L),
    "upper_arm.R": (SHO_R, ELB_R), "forearm.R": (ELB_R, WRI_R), "hand.R": (WRI_R, IDX_R),
}
TORSO_FRAME = {"upper_arm.L", "forearm.L", "hand.L", "upper_arm.R", "forearm.R",
               "hand.R", "neck", "head", "chest"}
HAND_MIN_M = 0.06          # wrist->index shorter than this = no readable hand


def ensure_model():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        print(f"downloading pose model -> {MODEL_PATH}")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


def detect(video, start, end, mirror):
    """Run the pose landmarker over [start, end] seconds. Returns (fps,
    list of (t_seconds, 33x3 world landmarks in metres or None))."""
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    cap = cv2.VideoCapture(video)
    assert cap.isOpened(), f"cannot open {video}"
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    opts = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=ensure_model(),
            delegate=mp_python.BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.VIDEO, num_poses=1,
        min_pose_detection_confidence=0.5, min_tracking_confidence=0.5)
    landmarker = vision.PoseLandmarker.create_from_options(opts)
    frames = []
    i = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        t = i / fps
        i += 1
        if t < start:
            continue
        if end is not None and t > end:
            break
        if mirror:
            bgr = cv2.flip(bgr, 1)
        img = mp.Image(image_format=mp.ImageFormat.SRGB,
                       data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        res = landmarker.detect_for_video(img, int(round(t * 1000)))
        if res.pose_world_landmarks:
            lm = res.pose_world_landmarks[0]
            pts = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float64)
            vis = np.array([p.visibility for p in lm])
            frames.append((t, pts, vis))
        else:
            frames.append((t, None, None))
    print(f"{video}: {n} frames @ {fps:.2f} fps, "
          f"{sum(1 for f in frames if f[1] is not None)}/{len(frames)} detected "
          f"in [{start}, {end if end is not None else 'end'}] s")
    return fps, frames


def to_blender(pts):
    """MediaPipe world (x right, y down, z toward the camera is negative)
    -> Z-up world where a person facing the camera faces -Y."""
    out = np.empty_like(pts)
    out[:, 0] = pts[:, 0]
    out[:, 1] = pts[:, 2]
    out[:, 2] = -pts[:, 1]
    return out


def fill_gaps(frames):
    """Linear interpolation across undetected frames; leading/trailing gaps
    are dropped. Returns (times, positions[n,33,3])."""
    good = [k for k, f in enumerate(frames) if f[1] is not None]
    assert len(good) >= 4, "fewer than 4 detected frames — is there a person in shot?"
    frames = frames[good[0]:good[-1] + 1]
    times = np.array([f[0] for f in frames])
    pos = np.zeros((len(frames), 33, 3))
    have = np.array([f[1] is not None for f in frames])
    for k, f in enumerate(frames):
        if f[1] is not None:
            pos[k] = to_blender(f[1])
    idx = np.arange(len(frames))
    for j in range(33):
        for c in range(3):
            pos[~have, j, c] = np.interp(idx[~have], idx[have], pos[have, j, c])
    missing = int((~have).sum())
    if missing:
        print(f"interpolated {missing} undetected frames")
    return times, pos


def smooth(pos, sigma):
    if sigma <= 0:
        return pos
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([np.repeat(pos[:1], r, 0), pos, np.repeat(pos[-1:], r, 0)])
    out = np.empty_like(pos)
    for j in range(pos.shape[1]):
        for c in range(3):
            out[:, j, c] = np.convolve(pad[:, j, c], k, mode="valid")
    return out


def yaw_to_face_minus_y(pos):
    """Rotate every frame about Z so the subject's mean hip line puts their
    left side at +X (the renderer's convention)."""
    left = pos[:, HIP_L] - pos[:, HIP_R]
    mean = left[:, :2].mean(axis=0)
    ang = math.atan2(mean[1], mean[0])          # angle of "left" from +X
    c, s = math.cos(-ang), math.sin(-ang)
    rot = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    print(f"facing: hips yawed by {math.degrees(-ang):.1f} deg")
    return pos @ rot.T


def resample(times, pos, fps):
    t0, t1 = times[0], times[-1]
    n = max(2, int(round((t1 - t0) * fps)) + 1)
    new_t = t0 + np.arange(n) / fps
    out = np.zeros((n, 33, 3))
    for j in range(33):
        for c in range(3):
            out[:, j, c] = np.interp(new_t, times, pos[:, j, c])
    return new_t, out


def hip_height(pos):
    hip = (pos[:, HIP_L] + pos[:, HIP_R]) / 2
    floor = pos[:, list(FLOOR_POINTS), 2].min(axis=1)
    return hip[:, 2] - floor


def auto_rep(h):
    """First full standing -> bottom -> standing cycle of the hip height."""
    lo, hi = h.min(), h.max()
    rng = hi - lo
    assert rng > 0.05, f"hip height only moves {rng*100:.1f} cm — no rep to find"
    high = lo + 0.85 * rng
    # the deepest frame is the rep; walk out from it to the last standing
    # frame before and the first standing frame after, so the seconds of
    # talking/setup before the descent never end up in the loop
    j = int(np.argmin(h))
    i0 = next((i for i in range(j, -1, -1) if h[i] >= high), None)
    assert i0 is not None, "no standing frame before the bottom"
    k = next((i for i in range(j, len(h)) if h[i] >= high), None)
    assert k is not None, "never stands back up after the bottom"
    # widen to the local maxima so the loop closes on the tallest frames
    while i0 > 0 and h[i0 - 1] >= h[i0]:
        i0 -= 1
    while k + 1 < len(h) and h[k + 1] >= h[k]:
        k += 1
    print(f"auto-rep: frames {i0}-{k} (bottom at {j}, "
          f"hip height {h[i0]*100:.0f} -> {h[j]*100:.0f} -> {h[k]*100:.0f} cm)")
    return i0, k


def unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def centre(pos, ids):
    return pos[list(ids)].mean(axis=0) if isinstance(ids, tuple) else pos[ids]


def basis(pos_f):
    """Pelvis (left, forward, up) from the hips and shoulders."""
    left = unit(pos_f[HIP_L] - pos_f[HIP_R])
    up = unit(centre(pos_f, (SHO_L, SHO_R)) - centre(pos_f, (HIP_L, HIP_R)))
    fwd = unit(np.cross(left, up))
    up = unit(np.cross(fwd, left))
    return left, fwd, up


def torso_basis(pos_f):
    left = unit(pos_f[SHO_L] - pos_f[SHO_R])
    up = unit(centre(pos_f, (EAR_L, EAR_R)) - centre(pos_f, (HIP_L, HIP_R)))
    fwd = unit(np.cross(left, up))
    up = unit(np.cross(fwd, left))
    return left, fwd, up


def perp(v, d):
    """Component of v perpendicular to unit d."""
    return v - d * np.dot(v, d)


def twist_for(seg_dir, frame_fwd, frame_up, frame_left):
    """twist_ref's rule, carried by the body frame: forward unless the
    segment lies along it, then up, then left."""
    for ref in (frame_fwd, frame_up, frame_left):
        side = perp(ref, seg_dir)
        if np.linalg.norm(side) > 0.3:
            return unit(side)
    return unit(frame_fwd)


def hinge_twist(seg_dir, other_dir, sign, fallback):
    """Roll reference for a hinged limb segment, read off the joint itself:
    the front of a thigh is opposite to where the shin folds (knees bend
    backward), the front of an upper arm is where the forearm folds (elbows
    bend forward); for the distal segment the front is away from the
    proximal one. Continuous: blends into the body-forward reference as the
    joint straightens, because a straight joint has no bend plane. The
    first spike (2026-09-15) flipped legs 178 deg mid-squat when the
    body-forward rule switched from 'forward' to 'up' as the thigh came
    horizontal; the bend plane never switches."""
    side = perp(other_dir, seg_dir)
    n = np.linalg.norm(side)                    # sin(bend angle)
    if n < 1e-6:
        return fallback
    w = min(1.0, max(0.0, (n - 0.17) / 0.34))   # 0 at <10 deg, 1 past 30 deg
    ref = unit(w * sign * side / n + (1.0 - w) * fallback)
    return ref if np.linalg.norm(ref) > 1e-6 else fallback


def limb_twists(dirs, fwd_legs, fwd_arms, up, left, tl, tu):
    out = {}
    for s in ("L", "R"):
        thigh, shin = np.array(dirs[f"thigh.{s}"]), np.array(dirs[f"shin.{s}"])
        ua, fa = np.array(dirs[f"upper_arm.{s}"]), np.array(dirs[f"forearm.{s}"])
        hand = np.array(dirs[f"hand.{s}"])
        foot = np.array(dirs[f"foot.{s}"])
        out[f"thigh.{s}"] = hinge_twist(thigh, shin, -1.0, twist_for(thigh, fwd_legs, up, left))
        out[f"shin.{s}"] = hinge_twist(shin, thigh, +1.0, twist_for(shin, fwd_legs, up, left))
        # a foot's roll reference is its dorsum (twist_ref picks 'up' for a
        # bone that points forward): where the shin rises from the ankle
        out[f"foot.{s}"] = hinge_twist(foot, shin, -1.0, twist_for(foot, up, fwd_legs, left))
        out[f"upper_arm.{s}"] = hinge_twist(ua, fa, +1.0, twist_for(ua, fwd_arms, tu, tl))
        out[f"forearm.{s}"] = hinge_twist(fa, ua, +1.0, twist_for(fa, fwd_arms, tu, tl))
        # the hand follows the forearm's roll: a monocular estimate has no
        # pronation, and wrist->index is the noisiest segment in the set
        out[f"hand.{s}"] = unit(perp(out[f"forearm.{s}"], hand)) \
            if np.linalg.norm(perp(out[f"forearm.{s}"], hand)) > 1e-6 \
            else twist_for(hand, fwd_arms, tu, tl)
    return out


FOOT_BACKWARD_DOT = -0.3   # toes more than ~107 deg from body-forward = swap


def build_frames(pos, fps):
    h = hip_height(pos)
    h0 = h[0]
    out = []
    last_foot = {}
    held = 0
    for f in range(len(pos)):
        p = pos[f]
        left, fwd, up = basis(p)
        tl, tf, tu = torso_basis(p)
        dirs, twists = {}, {}
        for name, (a, b) in SEGMENTS.items():
            d = unit(centre(p, b) - centre(p, a))
            if name.startswith("hand") and \
                    np.linalg.norm(centre(p, b) - centre(p, a)) < HAND_MIN_M:
                # index finger folded onto the wrist (fist, occlusion):
                # no direction to read, keep the hand along the forearm
                d = unit(centre(p, SEGMENTS[name.replace("hand", "forearm")][1]) -
                         centre(p, SEGMENTS[name.replace("hand", "forearm")][0]))
            if name.startswith("foot"):
                # toes cannot point behind the body: when the pose model
                # swaps heel and toe on an occluded rear foot (the lunge
                # capture, frames 68-75) hold the last believable direction
                if np.dot(d, fwd) < FOOT_BACKWARD_DOT and name in last_foot:
                    d = last_foot[name]
                    held += 1
                else:
                    last_foot[name] = d
            dirs[name] = [round(float(c), 5) for c in d]
            if name.startswith("foot"):
                tw = twist_for(d, up, fwd, left)      # feet roll about up
            elif name in TORSO_FRAME:
                tw = twist_for(d, tf, tu, tl)
            else:
                tw = twist_for(d, fwd, up, left)
            twists[name] = [round(float(c), 5) for c in tw]
        for name, tw in limb_twists({k: np.array(v) for k, v in dirs.items()},
                                    fwd, tf, up, left, tl, tu).items():
            twists[name] = [round(float(c), 5) for c in tw]
        out.append({
            "hip_height": round(float(h[f]), 5),
            "root": [0.0, 0.0, round(float(h[f] - h0), 5)],
            "pelvis": {"left": [round(float(c), 5) for c in left],
                       "forward": [round(float(c), 5) for c in fwd],
                       "up": [round(float(c), 5) for c in up]},
            "dirs": dirs,
            "twists": twists,
        })
    if held:
        print(f"held {held} foot direction(s) that pointed behind the body")
    return out, h


def knee_angle(pos_f, side):
    hip, knee, ank = (HIP_L, KNEE_L, ANK_L) if side == "L" else (HIP_R, KNEE_R, ANK_R)
    a = unit(pos_f[hip] - pos_f[knee])
    b = unit(pos_f[ank] - pos_f[knee])
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b))))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--start", type=float, default=0.0, help="seconds")
    ap.add_argument("--end", type=float, default=None, help="seconds")
    ap.add_argument("--auto-rep", action="store_true",
                    help="trim to the first standing->bottom->standing cycle")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--smooth", type=float, default=1.5,
                    help="gaussian sigma in frames (0 = raw)")
    ap.add_argument("--mirror", action="store_true",
                    help="flip the video horizontally first (selfie footage)")
    ap.add_argument("--source", default="own capture",
                    help="who shot it / how — written into the file")
    ap.add_argument("--license", default="CC0-1.0",
                    help="licence of the motion (your own footage = your call)")
    args = ap.parse_args()

    fps_in, raw = detect(args.video, args.start, args.end, args.mirror)
    times, pos = fill_gaps(raw)
    pos = smooth(pos, args.smooth)
    pos = yaw_to_face_minus_y(pos)
    times, pos = resample(times, pos, args.fps)
    if args.auto_rep:
        i0, k = auto_rep(hip_height(pos))
        pos = pos[i0:k + 1]
    frames, h = build_frames(pos, args.fps)

    bottom = int(np.argmin(h))
    print(f"{len(frames)} frames @ {args.fps:g} fps ({len(frames)/args.fps:.2f} s); "
          f"hip height {h.max()*100:.0f}->{h.min()*100:.0f} cm; "
          f"knee at bottom L={knee_angle(pos[bottom], 'L'):.0f} "
          f"R={knee_angle(pos[bottom], 'R'):.0f} deg; "
          f"loop gap {np.linalg.norm(pos[0]-pos[-1], axis=1).mean()*100:.1f} cm")

    doc = {
        "format": "opengym3d-motion/1",
        "source": args.source,
        "license": args.license,
        "tool": "pipeline/video_mocap.py (MediaPipe Pose, on-device)",
        "video": os.path.basename(args.video),
        "range_s": [args.start, args.end],
        "fps": args.fps,
        "axial_rotation": "none — twists are body-forward carried, not measured",
        "frames": frames,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    print(f"wrote {args.out} ({os.path.getsize(args.out)//1024} KB)")


if __name__ == "__main__":
    sys.exit(main())
