"""Anatomical QA: does the figure perform the exercise the spec names?

    python3 pipeline/anatomy_qa.py census site/assets/*.glb     # measure
    python3 pipeline/anatomy_qa.py check  site/assets/deadlift.glb

The joint gate (qa_glb.py) proves the skeleton is sound. It cannot tell a
deadlift from a squat, a lateral raise from a front raise, or a curl whose
shoulder flies up from one that stays put — every one of those has intact
bones and legal hinges. This module measures the movement itself from the
same sampled joint positions and grades it against the pattern the spec
declares:

    "movement": {"pattern": "hinge"}          # deadlift, RDL, good morning
    "movement": {"pattern": "squat"}          # air/back/overhead/sumo squat
    "movement": {"pattern": "curl"}           # bicep, hammer

Every rule is a named metric with a bound. The bounds were set from a
census of the 24 live, human-reviewed GLBs (2026-09-15, `census` below)
plus anatomical margin — never eyeballed. A spec may loosen or tighten a
bound for its own reasons:

    "movement": {"pattern": "hinge", "qa": {"knee_min_deg": [70, 180]}}

Metrics (all from world joint positions, glTF Y-up, metres/degrees):

    hip_drop_m        pelvis vertical travel over the rep
    knee_min_deg      tightest knee (180 = straight)
    elbow_min_deg / elbow_max_deg
    torso_lean_max_deg  pelvis->neck line from vertical, worst frame
    hip_flex_max_deg  torso-to-thigh angle (0 = standing tall)
    arm_elev_max_deg  upper arm from hanging (0 down, 90 horizontal, 180 up)
    arm_lateral_frac  at peak elevation: |sideways| / (|sideways|+|forward|)
    wrist_over_head_m max wrist height above the head joint
    wrist_over_shoulder_m min wrist height above the shoulder (press bottom)
    hands_forward_m   max forward distance of the hand midpoint from the hips
    foot_split_m      max fore/aft separation of the feet
    foot_spread_m     max side-to-side separation of the feet
    head_rise_m       head vertical travel (crunch / situp)
    hip_low           pelvis stays within 0.45 m of the floor (floor work)
    root_rise_m       pelvis vertical travel (calf raise, jumps)
    thigh_lift_max_deg  thigh from hanging (high knees)
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_glb  # noqa: E402

UP = (0.0, 1.0, 0.0)


def _n(v):
    l = math.sqrt(sum(c * c for c in v)) or 1e-9
    return tuple(c / l for c in v)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _mid(a, b):
    return tuple((x + y) / 2 for x, y in zip(a, b))


def _ang(u, v):
    return qa_glb.angle_between(u, v)


def _hinge(f, prox, mid, dist):
    """Interior joint angle, 180 = straight."""
    return 180.0 - _ang(_sub(f[mid], f[prox]), _sub(f[dist], f[mid]))


# ------------------------------------------------------------------ metrics

def body_axes(f):
    """(lateral, forward) unit vectors of the pelvis in this frame.
    lateral points to the figure's left; forward = lateral x up, so it is
    the facing direction whichever way the figure was exported."""
    lateral = _n(_sub(f["upperleg01.L"], f["upperleg01.R"]))
    forward = _n(_cross(lateral, UP))
    return lateral, forward


def metrics(frames, times, names):
    """Every metric the rules can bound, plus the frame it peaked in."""
    need = ["root", "neck01", "head", "upperarm01.L", "upperarm01.R",
            "lowerarm01.L", "lowerarm01.R", "wrist.L", "wrist.R",
            "upperleg01.L", "upperleg01.R", "upperleg02.L", "upperleg02.R",
            "lowerleg01.L", "lowerleg01.R", "lowerleg02.L", "lowerleg02.R",
            "foot.L", "foot.R"]
    missing = [b for b in need if b not in names]
    if missing:
        raise ValueError(f"bones missing: {missing}")

    floor = min(min(f["foot.L"][1], f["foot.R"][1], f["wrist.L"][1],
                    f["wrist.R"][1], f["head"][1], f["root"][1]) for f in frames)
    m = {}

    def peak(name, series, fn=max):
        v = fn(series)
        m[name] = (round(v, 3), round(times[series.index(v)], 3))

    root_y = [f["root"][1] - floor for f in frames]
    peak("hip_drop_m", [max(root_y) - y for y in root_y])
    peak("root_rise_m", [y - min(root_y) for y in root_y])
    peak("hip_height_min_m", root_y, min)
    peak("hip_height_max_m", root_y, max)

    knees = [min(_hinge(f, "upperleg02.L", "lowerleg01.L", "lowerleg02.L"),
                 _hinge(f, "upperleg02.R", "lowerleg01.R", "lowerleg02.R"))
             for f in frames]
    peak("knee_min_deg", knees, min)
    peak("knee_max_deg", [max(_hinge(f, "upperleg02.L", "lowerleg01.L", "lowerleg02.L"),
                              _hinge(f, "upperleg02.R", "lowerleg01.R", "lowerleg02.R"))
                          for f in frames])
    elbows = [(_hinge(f, "upperarm02.L", "lowerarm01.L", "lowerarm02.L"),
               _hinge(f, "upperarm02.R", "lowerarm01.R", "lowerarm02.R"))
              for f in frames]
    peak("elbow_min_deg", [min(e) for e in elbows], min)
    peak("elbow_max_deg", [max(e) for e in elbows])

    torso = [_sub(f["neck01"], f["root"]) for f in frames]
    lean = [_ang(t, UP) for t in torso]
    peak("torso_lean_max_deg", lean)
    peak("torso_lean_min_deg", lean, min)
    thighs = [_mid(_sub(f["lowerleg01.L"], f["upperleg01.L"]),
                   _sub(f["lowerleg01.R"], f["upperleg01.R"])) for f in frames]
    # hip flexion: 0 when the torso continues the thigh line upward
    peak("hip_flex_max_deg", [180.0 - _ang(t, th) for t, th in zip(torso, thighs)])

    elev, lat_frac = [], []
    for f in frames:
        lateral, forward = body_axes(f)
        best = (-1.0, 0.0)
        for s, sign in (("L", 1.0), ("R", -1.0)):
            ua = _sub(f["lowerarm01." + s], f["upperarm01." + s])
            e = _ang(ua, (0.0, -1.0, 0.0))
            side = abs(_dot(ua, lateral))
            fwd = abs(_dot(ua, forward))
            frac = side / (side + fwd + 1e-9)
            if e > best[0]:
                best = (e, frac)
        elev.append(best[0])
        lat_frac.append(best[1])
    peak("arm_elev_max_deg", elev)
    peak("arm_elev_min_deg", elev, min)
    m["arm_lateral_frac"] = (round(lat_frac[elev.index(max(elev))], 3),
                             m["arm_elev_max_deg"][1])

    peak("wrist_over_head_m", [max(f["wrist.L"][1], f["wrist.R"][1]) - f["head"][1]
                               for f in frames])
    peak("wrist_over_shoulder_m",
         [min(f["wrist.L"][1] - f["upperarm01.L"][1],
              f["wrist.R"][1] - f["upperarm01.R"][1]) for f in frames], min)
    wr = [max(f["wrist.L"][1], f["wrist.R"][1]) - floor for f in frames]
    peak("wrist_rise_m", wr)
    peak("wrist_travel_m", [w - min(wr) for w in wr])
    peak("wrist_over_shoulder_max_m",
         [max(f["wrist.L"][1] - f["upperarm01.L"][1],
              f["wrist.R"][1] - f["upperarm01.R"][1]) for f in frames])
    hf = []
    for f in frames:
        _, forward = body_axes(f)
        hf.append(_dot(_sub(_mid(f["wrist.L"], f["wrist.R"]), f["root"]), forward))
    peak("hands_forward_m", hf)
    peak("hands_forward_min_m", hf, min)

    split, spread = [], []
    for f in frames:
        lateral, forward = body_axes(f)
        d = _sub(f["foot.L"], f["foot.R"])
        split.append(abs(_dot(d, forward)))
        spread.append(abs(_dot(d, lateral)))
    peak("foot_split_m", split)
    peak("foot_spread_m", spread)
    peak("foot_spread_min_m", spread, min)

    head_y = [f["head"][1] - floor for f in frames]
    peak("head_rise_m", [y - min(head_y) for y in head_y])
    peak("head_height_max_m", head_y)
    m["hip_low"] = (max(root_y) <= 0.45, 0.0)

    peak("thigh_lift_max_deg",
         [max(_ang(_sub(f["lowerleg01.L"], f["upperleg01.L"]), (0, -1, 0)),
              _ang(_sub(f["lowerleg01.R"], f["upperleg01.R"]), (0, -1, 0)))
          for f in frames])
    return m


# ------------------------------------------------------------------ rules
# pattern -> {metric: [lo, hi]} (None = unbounded). Set from the 2026-09-15
# census of the live GLBs; see NOTES.md for the numbers behind each bound.

PATTERNS = {
    # standing, hips travel down and up between the feet
    "squat": {"knee_min_deg": [None, 100], "hip_drop_m": [0.25, None],
              "torso_lean_max_deg": [None, 60], "foot_split_m": [None, 0.35]},
    # hips travel back, torso folds, knees stay soft — NOT a squat
    "hinge": {"torso_lean_max_deg": [40, None], "hip_flex_max_deg": [60, None],
              "knee_min_deg": [80, None]},
    # hinge with the implement swung to chest height
    "swing": {"torso_lean_max_deg": [40, None], "knee_min_deg": [80, None],
              "arm_elev_max_deg": [70, None]},
    # one foot forward, both knees bend, torso upright
    "lunge": {"foot_split_m": [0.4, None], "knee_min_deg": [None, 115],
              "hip_drop_m": [0.15, None], "torso_lean_max_deg": [None, 40]},
    # hands from the shoulders to overhead, legs quiet
    "press_vertical": {"wrist_over_head_m": [0.1, None],
                       "wrist_over_shoulder_m": [None, 0.2],
                       "elbow_min_deg": [None, 110], "elbow_max_deg": [140, None],
                       "torso_lean_max_deg": [None, 25], "hip_drop_m": [None, 0.15]},
    # elbow flexes fully, upper arm stays down, body still
    "curl": {"elbow_min_deg": [None, 70], "elbow_max_deg": [130, None],
             "arm_elev_max_deg": [None, 60], "torso_lean_max_deg": [None, 20],
             "hip_drop_m": [None, 0.1]},
    # straight arms to shoulder height in the frontal plane
    "raise_lateral": {"arm_elev_max_deg": [65, 115], "arm_lateral_frac": [0.65, None],
                      "elbow_min_deg": [120, None], "torso_lean_max_deg": [None, 20],
                      "hip_drop_m": [None, 0.1]},
    # straight arms to shoulder height in the sagittal plane
    "raise_front": {"arm_elev_max_deg": [65, 115], "arm_lateral_frac": [None, 0.35],
                    "elbow_min_deg": [120, None], "torso_lean_max_deg": [None, 20],
                    "hip_drop_m": [None, 0.1]},
    # torso held folded, elbows drive the hands to the ribs
    "row": {"torso_lean_min_deg": [20, None], "torso_lean_max_deg": [30, None],
            "elbow_min_deg": [None, 100], "elbow_max_deg": [140, None],
            "knee_min_deg": [100, None], "wrist_travel_m": [0.15, None]},
    # arms overhead, only the elbow moves
    "tricep_overhead": {"wrist_over_head_m": [0.05, None], "elbow_min_deg": [None, 90],
                        "elbow_max_deg": [140, None], "arm_elev_max_deg": [140, None],
                        "torso_lean_max_deg": [None, 25]},
    # straight legs, heels lift the whole body a few centimetres
    "calf_raise": {"root_rise_m": [0.04, 0.15], "knee_min_deg": [150, None],
                   "torso_lean_max_deg": [None, 20]},
    # knees held near 90, nothing travels
    "wall_sit": {"knee_min_deg": [60, 110], "knee_max_deg": [None, 125],
                 "hip_drop_m": [None, 0.08], "torso_lean_max_deg": [None, 25]},
    # body a straight line held off the floor on hands/forearms and toes
    "plank": {"hip_low": True, "hip_drop_m": [None, 0.08],
              "torso_lean_max_deg": [55, 100], "head_rise_m": [None, 0.08]},
    # prone, elbows lower and raise the body
    "push_up": {"hip_height_max_m": [None, 0.6], "hip_drop_m": [0.08, None],
                "elbow_min_deg": [None, 100], "elbow_max_deg": [150, None],
                "torso_lean_max_deg": [55, 110]},
    # prone, chest and limbs lift off the floor
    "prone_lift": {"hip_height_max_m": [None, 0.4], "head_rise_m": [0.05, None]},
    # supine, head and shoulders curl up
    "supine_curl": {"hip_height_max_m": [None, 0.35], "head_rise_m": [0.08, None]},
    # supine, hips drive up while the shoulders stay down
    "bridge": {"root_rise_m": [0.12, None], "head_rise_m": [None, 0.12],
               "hip_height_max_m": [None, 0.6]},
    # walk / jog / run: alternating stride, upright
    "locomotion": {"foot_split_m": [0.4, None], "hip_drop_m": [None, 0.35],
                   "torso_lean_max_deg": [None, 45]},
    # in place, thighs come to horizontal
    "high_knees": {"thigh_lift_max_deg": [70, None], "torso_lean_max_deg": [None, 30]},
    "jumping_jack": {"foot_spread_m": [0.6, None], "foot_spread_min_m": [None, 0.35],
                     "arm_elev_max_deg": [150, None], "arm_elev_min_deg": [None, 40]},
    "crawl": {"hip_low": True, "foot_split_m": [0.3, None]},
    # snatch / clean and jerk / high pull: pull from a dip, bar travels far
    "olympic": {"hip_drop_m": [0.2, None], "knee_min_deg": [None, 100],
                "wrist_travel_m": [0.6, None]},
    # burpee / jump push-up: the whole body leaves the floor or the plank
    "plyometric": {"root_rise_m": [0.3, None]},
    "seated_hold": {"hip_low": True, "hip_drop_m": [None, 0.05]},
}

# Patterns with no live GLB behind their bounds yet — anatomy + margin only,
# to be refined by `census` on the first capture that renders.
PROVISIONAL = {"hinge", "press_vertical", "raise_lateral", "row", "tricep_overhead",
               "calf_raise", "wall_sit", "prone_lift", "bridge", "high_knees"}


def rules_for(spec):
    mv = spec.get("movement") or {}
    pat = mv.get("pattern")
    if pat not in PATTERNS:
        raise KeyError(f"unknown movement pattern {pat!r} (known: {sorted(PATTERNS)})")
    rules = dict(PATTERNS[pat])
    rules.update(mv.get("qa", {}))
    return pat, rules


def evaluate(frames, times, names, spec):
    """[{rule, ok, detail, value, t}] for every bound the pattern sets."""
    pat, rules = rules_for(spec)
    m = metrics(frames, times, names)
    out = []
    for metric, bound in rules.items():
        if metric not in m:
            out.append({"rule": f"{pat}:{metric}", "ok": False,
                        "detail": f"no such metric {metric}", "value": None})
            continue
        value, t = m[metric]
        if isinstance(bound, bool):
            ok = value == bound
            detail = f"{metric} = {value} (want {bound})"
        else:
            lo, hi = bound
            ok = (lo is None or value >= lo) and (hi is None or value <= hi)
            detail = (f"{metric} = {value} (want "
                      f"{'' if lo is None else lo}..{'' if hi is None else hi})")
        out.append({"rule": f"{pat}:{metric}", "ok": ok, "detail": detail,
                    "value": value, "t": t})
    return out


# ------------------------------------------------------------------ CLI

def census(glbs):
    rows = []
    for g in glbs:
        _, names, times, frames, _ = qa_glb.sample_clip(g)
        m = metrics(frames, times, names)
        rows.append((Path(g).stem, m))
    keys = list(rows[0][1])
    print("exercise".ljust(20) + "".join(k[:14].rjust(15) for k in keys))
    for gid, m in rows:
        print(gid[:20].ljust(20) + "".join(
            (f"{m[k][0]:.2f}" if not isinstance(m[k][0], bool) else str(m[k][0])).rjust(15)
            for k in keys))
    return rows


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, *glbs = argv
    repo = Path(__file__).resolve().parent.parent
    if cmd == "census":
        census(glbs)
        return 0
    if cmd == "check":
        bad = 0
        for g in glbs:
            spec_path = repo / "exercises" / f"{Path(g).stem}.json"
            spec = json.loads(spec_path.read_text())
            _, names, times, frames, _ = qa_glb.sample_clip(g)
            res = evaluate(frames, times, names, spec)
            fails = [r for r in res if not r["ok"]]
            bad += bool(fails)
            print(f"{Path(g).stem:24s} {spec['movement']['pattern']:12s} "
                  f"{'PASS' if not fails else 'FAIL'}")
            for r in fails:
                print(f"    {r['rule']:34s} {r['detail']}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
