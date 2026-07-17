"""Validate exercise specs and the manifest without launching Blender.

The pose maths needs bpy, but everything that actually breaks the site in
practice is plain data: a muscle name the painter doesn't know renders a
figure with nothing highlighted, a bad prop type ships an exercise with no
implement, an unsorted keyframe list animates backwards. Those are the bugs
this catches in seconds, so CI can fail before spending 40 minutes rendering.

    python3 -m unittest discover -s tests

Stdlib only — no pytest, no deps to install in CI.
"""

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXERCISES = sorted((REPO / "exercises").glob("*.json"))
PIPELINE = REPO / "pipeline" / "build_exercise.py"

VALID_PROPS = {"dumbbell", "barbell"}
VALID_DIFFICULTY = {"Beginner", "Intermediate", "Advanced"}


def painter_muscles():
    """MUSCLE_SPEC's keys, read from source — importing build_exercise needs
    bpy, but the vocabulary is what specs must agree with, so parse it out.
    This is what keeps metadata and painter from drifting apart."""
    tree = ast.parse(PIPELINE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "MUSCLE_SPEC" for t in node.targets):
            return {k.value for k in node.value.keys}
    raise AssertionError("MUSCLE_SPEC not found in build_exercise.py")


def specs():
    return [(p.stem, json.loads(p.read_text())) for p in EXERCISES]


class TestSpecs(unittest.TestCase):
    def test_exercises_exist(self):
        self.assertGreaterEqual(len(EXERCISES), 18)

    def test_filename_matches_id(self):
        for stem, spec in specs():
            self.assertEqual(stem, spec["id"])

    def test_required_fields(self):
        for stem, spec in specs():
            with self.subTest(stem):
                for field in ("id", "name", "primary", "keyframes", "steps"):
                    self.assertIn(field, spec)
                self.assertTrue(spec["primary"], "needs a primary muscle")
                self.assertIn(spec.get("difficulty", "Beginner"),
                              VALID_DIFFICULTY)
                self.assertGreaterEqual(len(spec["steps"]), 3,
                                        "form steps are a shipped feature")

    def test_every_muscle_is_paintable(self):
        """A muscle the painter doesn't know = a figure with no highlight."""
        known = painter_muscles()
        for stem, spec in specs():
            for muscle in spec.get("primary", []) + spec.get("secondary", []):
                with self.subTest(stem, muscle=muscle):
                    self.assertIn(muscle.lower(), known)

    def test_keyframes_are_a_full_normalised_rep(self):
        for stem, spec in specs():
            with self.subTest(stem):
                ts = [kf["t"] for kf in spec["keyframes"]]
                self.assertEqual(ts, sorted(ts), "keyframes out of order")
                self.assertEqual(ts[0], 0.0)
                self.assertEqual(ts[-1], 1.0)
                for t in ts:
                    self.assertGreaterEqual(t, 0.0)
                    self.assertLessEqual(t, 1.0)

    def test_bone_transforms_are_well_formed(self):
        for stem, spec in specs():
            for kf in spec["keyframes"]:
                for bone, xf in kf["bones"].items():
                    with self.subTest(stem, bone=bone, t=kf["t"]):
                        self.assertTrue(
                            {"rot", "loc", "aim_world"} & set(xf),
                            "bone entry does nothing")
                        for key in ("rot", "loc", "aim_world"):
                            if key in xf:
                                self.assertEqual(len(xf[key]), 3)
                        aim = xf.get("aim_world")
                        if aim:
                            self.assertGreater(
                                sum(c * c for c in aim), 1e-6,
                                "zero-length aim has no direction")
                            self.assertNotIn("rot", xf,
                                             "aim_world overrides rot; drop it")

    def test_props_are_buildable(self):
        for stem, spec in specs():
            prop = spec.get("prop")
            if not prop:
                continue
            with self.subTest(stem):
                self.assertIn(prop["type"], VALID_PROPS)
                self.assertIn(prop.get("hold", "each"), ("each", "both"))
                if "axis" in prop:
                    self.assertEqual(len(prop["axis"]), 3)
                    self.assertGreater(sum(c * c for c in prop["axis"]), 1e-6)

    def test_equipment_agrees_with_prop(self):
        """'Dumbbell' in the metadata but no prop = an exercise that mimes."""
        for stem, spec in specs():
            with self.subTest(stem):
                equipment = spec.get("equipment", "None")
                if equipment in ("Dumbbell", "Barbell"):
                    self.assertIsNotNone(spec.get("prop"),
                                         f"{equipment} exercise has no prop")
                    self.assertEqual(spec["prop"]["type"], equipment.lower())
                else:
                    self.assertIsNone(spec.get("prop"))


class TestManifest(unittest.TestCase):
    def test_manifest_builds_and_carries_the_site_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "exercises.json"
            subprocess.run(
                [sys.executable, str(REPO / "pipeline" / "make_manifest.py"),
                 str(REPO / "exercises"), str(dest)],
                check=True, capture_output=True)
            manifest = json.loads(dest.read_text())
            self.assertEqual(len(manifest), len(EXERCISES))
            for entry in manifest:
                self.assertTrue(entry["glb"].endswith(".glb"))
                self.assertTrue(entry["thumb"].endswith(".png"))
                self.assertTrue(entry["steps"], "viewer renders steps")


if __name__ == "__main__":
    unittest.main()
