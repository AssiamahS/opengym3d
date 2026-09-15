"""The normalized motion format and the canonical skeleton, proven on real
motion from three sources — no Blender:

  CANONICAL == build_exercise.BONES        the FK skeleton is the driver rig
  video capture -> FK -> lunge gate PASS   same numbers the rendered GLB gave
  Mesh2Motion Pushup -> FK -> push_up PASS the CC0 adapter
  CMU 13_29 squat -> FK -> squat PASS, hinge FAIL   the ASF/AMC adapter
  save/load round trip keeps every frame

    python3 -m unittest tests.test_motion -v
"""

import ast
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import anatomy_qa  # noqa: E402
import motion  # noqa: E402


def gate(m, spec_or_pattern):
    spec = spec_or_pattern if isinstance(spec_or_pattern, dict) else \
        {"movement": {"pattern": spec_or_pattern}}
    frames, times, names = motion.skeleton_frames(m)
    res = anatomy_qa.evaluate(frames, times, names, spec)
    return all(r["ok"] for r in res), [r["detail"] for r in res if not r["ok"]]


class CanonicalSkeleton(unittest.TestCase):
    def test_matches_the_blender_driver_rig(self):
        src = (REPO / "pipeline" / "build_exercise.py").read_text()
        block = re.search(r"^BONES = (\{.*?^\})", src, re.S | re.M).group(1)
        bones = ast.literal_eval(block)
        self.assertEqual({k: tuple(map(tuple, v)) for k, v in bones.items()},
                         {k: tuple(map(tuple, v)) for k, v in motion.CANONICAL.items()})

    def test_fk_joint_names_feed_the_gates(self):
        m = motion.load(REPO / "motions" / "video" / "lunge_demo.json")
        frames, times, names = motion.skeleton_frames(m)
        for nm in ("root", "neck01", "head", "upperleg01.L", "lowerleg01.R", "foot.L",
                   "upperarm01.L", "lowerarm01.R", "wrist.L", "finger3-1.R"):
            self.assertIn(nm, names)
        self.assertEqual(len(frames), len(m["frames"]))


class Adapters(unittest.TestCase):
    def test_video_capture_is_a_lunge(self):
        m = motion.load(REPO / "motions" / "video" / "lunge_demo.json")
        ok, why = gate(m, json.loads((REPO / "exercises" / "lunge_video.json").read_text()))
        self.assertTrue(ok, why)
        self.assertFalse(gate(m, "squat")[0])       # feet are split

    def test_mesh2motion_pushup(self):
        m = motion.from_m2m(REPO / "motions" / "cc0" / "mesh2motion" / "human-addon-animations.glb",
                            "Pushup")
        self.assertEqual(m["format"], motion.FORMAT)
        self.assertEqual(set(m["frames"][0]["dirs"]), set(motion.DIR_BONES))
        ok, why = gate(m, json.loads((REPO / "exercises" / "push_up.json").read_text()))
        self.assertTrue(ok, why)
        self.assertFalse(gate(m, "squat")[0])

    def test_cmu_squat_is_a_squat_not_a_hinge(self):
        idx = json.loads((REPO / "motions" / "cmu" / "index.json").read_text())["trials"]["13_29"]
        m = motion.from_cmu(REPO / "motions" / "cmu" / "13.asf", REPO / "motions" / "cmu" / "13_29.amc",
                            start=idx["start"], end=idx["end"])
        self.assertGreater(len(m["frames"]), 60)
        hh = [f["hip_height"] for f in m["frames"]]
        self.assertGreater(max(hh) - min(hh), 0.4)
        ok, why = gate(m, "squat")
        self.assertTrue(ok, why)
        self.assertFalse(gate(m, "hinge")[0])

    def test_round_trip(self):
        m = motion.from_m2m(REPO / "motions" / "cc0" / "mesh2motion" / "human-addon-animations.glb",
                            "Jumping Jacks")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "jj.json"
            motion.save(m, p)
            back = motion.load(p)
        self.assertEqual(back["frames"], m["frames"])
        self.assertTrue(gate(back, "jumping_jack")[0])


if __name__ == "__main__":
    unittest.main()
