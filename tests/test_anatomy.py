"""The anatomy gate must tell exercises apart — proven on synthetic motion.

A stick figure with the export's bone names is posed frame by frame (no
GLB needed: the gate grades joint positions) and the rules have to answer:

  a squat (hips drop, knees fold, torso near vertical)  -> squat PASS, hinge FAIL
  a hinge (hips back, torso folds, knees soft)          -> hinge PASS, squat FAIL
  a curl whose shoulder flies up                        -> curl FAIL (arm_elev)
  a lateral raise swung forward                         -> raise_lateral FAIL, raise_front PASS
  standing still                                        -> squat FAIL (no depth)
  every spec's pattern is one the module knows

    python3 -m unittest tests.test_anatomy -v
"""

import json
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import anatomy_qa  # noqa: E402

N = 31
TIMES = [i * 2.0 / (N - 1) for i in range(N)]


def figure(hip_y=0.95, knee=180.0, lean=0.0, elbow=180.0, arm_elev=0.0,
           arm_plane="lateral", split=0.0):
    """Joint positions for one frame. Figure faces +Z, left is +X.
    knee/elbow are interior angles (180 straight); lean tips the torso
    forward (+Z) by that many degrees; arm_elev lifts both upper arms from
    hanging in the given plane; split moves the left foot forward."""
    f = {}
    f["root"] = (0.0, hip_y, 0.0)
    f["upperleg01.L"] = (0.10, hip_y, 0.0)
    f["upperleg01.R"] = (-0.10, hip_y, 0.0)
    thigh, shin = 0.43, 0.43
    # knee bend folds the shin back under the thigh in the sagittal plane
    half = math.radians((180.0 - knee) / 2)
    for s, x, fwd in (("L", 0.10, split), ("R", -0.10, 0.0)):
        hip = (x, hip_y, fwd)
        kn = (x, hip_y - thigh * math.cos(half), fwd + thigh * math.sin(half))
        ft = (x, kn[1] - shin * math.cos(half), kn[2] - shin * math.sin(half))
        f[f"upperleg02.{s}"] = tuple((a + b) / 2 for a, b in zip(hip, kn))
        f[f"lowerleg01.{s}"] = kn
        f[f"lowerleg02.{s}"] = tuple((a + b) / 2 for a, b in zip(kn, ft))
        f[f"foot.{s}"] = ft
    lr = math.radians(lean)
    def up_torso(d):
        return (0.0, hip_y + d * math.cos(lr), d * math.sin(lr))
    f["spine03"] = up_torso(0.10)
    f["spine01"] = up_torso(0.40)
    f["neck01"] = up_torso(0.55)
    f["head"] = up_torso(0.68)
    er = math.radians(arm_elev)
    for s, x in (("L", 0.18), ("R", -0.18)):
        sh = (x, f["spine01"][1], f["spine01"][2])
        if arm_plane == "lateral":
            d = (math.copysign(math.sin(er), x), -math.cos(er), 0.0)
        else:
            d = (0.0, -math.cos(er), math.sin(er))
        ua = 0.30
        el = tuple(c + ua * dc for c, dc in zip(sh, d))
        # forearm folds forward (+Z) by the elbow angle
        eb = math.radians(180.0 - elbow)
        fd = (d[0], d[1] * math.cos(eb) + d[2] * math.sin(eb),
              -d[1] * math.sin(eb) + d[2] * math.cos(eb))
        wr = tuple(c + 0.27 * dc for c, dc in zip(el, fd))
        f[f"upperarm01.{s}"] = sh
        f[f"upperarm02.{s}"] = tuple((a + b) / 2 for a, b in zip(sh, el))
        f[f"lowerarm01.{s}"] = el
        f[f"lowerarm02.{s}"] = tuple((a + b) / 2 for a, b in zip(el, wr))
        f[f"wrist.{s}"] = wr
    return f


def clip(fn):
    """fn(phase 0..1..0) -> figure kwargs; a rep down and back up."""
    frames = []
    for t in TIMES:
        ph = math.sin(math.pi * t / TIMES[-1])
        frames.append(figure(**fn(ph)))
    names = {k: i for i, k in enumerate(frames[0])}
    return frames, names


def verdict(frames, names, pattern):
    res = anatomy_qa.evaluate(frames, TIMES, names, {"movement": {"pattern": pattern}})
    return all(r["ok"] for r in res), [r["detail"] for r in res if not r["ok"]]


class AnatomyGate(unittest.TestCase):
    def test_squat_is_a_squat_not_a_hinge(self):
        frames, names = clip(lambda p: {"hip_y": 0.95 - 0.45 * p, "knee": 180 - 110 * p,
                                        "lean": 25 * p})
        self.assertTrue(verdict(frames, names, "squat")[0], verdict(frames, names, "squat")[1])
        self.assertFalse(verdict(frames, names, "hinge")[0])

    def test_hinge_is_a_hinge_not_a_squat(self):
        frames, names = clip(lambda p: {"hip_y": 0.95 - 0.08 * p, "knee": 180 - 25 * p,
                                        "lean": 75 * p})
        ok, why = verdict(frames, names, "hinge")
        self.assertTrue(ok, why)
        self.assertFalse(verdict(frames, names, "squat")[0])

    def test_standing_still_has_no_depth(self):
        frames, names = clip(lambda p: {})
        self.assertFalse(verdict(frames, names, "squat")[0])

    def test_curl_shoulder_must_stay_down(self):
        clean, names = clip(lambda p: {"elbow": 180 - 140 * p, "arm_elev": 10 * p})
        self.assertTrue(verdict(clean, names, "curl")[0], verdict(clean, names, "curl")[1])
        flying, _ = clip(lambda p: {"elbow": 180 - 140 * p, "arm_elev": 80 * p,
                                    "arm_plane": "front"})
        ok, why = verdict(flying, names, "curl")
        self.assertFalse(ok)
        self.assertTrue(any("arm_elev_max_deg" in w for w in why), why)

    def test_lateral_raise_plane(self):
        side, names = clip(lambda p: {"arm_elev": 90 * p, "arm_plane": "lateral"})
        self.assertTrue(verdict(side, names, "raise_lateral")[0],
                        verdict(side, names, "raise_lateral")[1])
        self.assertFalse(verdict(side, names, "raise_front")[0])
        front, _ = clip(lambda p: {"arm_elev": 90 * p, "arm_plane": "front"})
        self.assertTrue(verdict(front, names, "raise_front")[0],
                        verdict(front, names, "raise_front")[1])
        self.assertFalse(verdict(front, names, "raise_lateral")[0])

    def test_lunge_needs_a_split_stance(self):
        lunge, names = clip(lambda p: {"hip_y": 0.95 - 0.25 * p, "knee": 180 - 85 * p,
                                       "split": 0.6})
        self.assertTrue(verdict(lunge, names, "lunge")[0], verdict(lunge, names, "lunge")[1])
        feet_together, _ = clip(lambda p: {"hip_y": 0.95 - 0.25 * p, "knee": 180 - 85 * p})
        self.assertFalse(verdict(feet_together, names, "lunge")[0])

    def test_spec_override_applies(self):
        frames, names = clip(lambda p: {"hip_y": 0.95 - 0.45 * p, "knee": 180 - 110 * p,
                                        "lean": 25 * p})
        spec = {"movement": {"pattern": "squat", "qa": {"hip_drop_m": [0.9, None]}}}
        res = anatomy_qa.evaluate(frames, TIMES, names, spec)
        self.assertFalse(all(r["ok"] for r in res))

    def test_unknown_pattern_is_an_error(self):
        frames, names = clip(lambda p: {})
        with self.assertRaises(KeyError):
            anatomy_qa.evaluate(frames, TIMES, names, {"movement": {"pattern": "yoga"}})


class SpecsDeclareAPattern(unittest.TestCase):
    def test_every_spec_has_a_known_pattern(self):
        for path in sorted((REPO / "exercises").glob("*.json")):
            spec = json.loads(path.read_text())
            with self.subTest(spec=path.name):
                pat = (spec.get("movement") or {}).get("pattern")
                self.assertIn(pat, anatomy_qa.PATTERNS)
                for metric, bound in (spec["movement"].get("qa") or {}).items():
                    self.assertTrue(isinstance(bound, bool) or len(bound) == 2, metric)


if __name__ == "__main__":
    unittest.main()
