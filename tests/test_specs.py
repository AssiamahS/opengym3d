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

VALID_PROPS = {"dumbbell", "barbell", "kettlebell"}
VIDEO_DIRS = {"spine", "chest", "neck", "head",
              "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R",
              "upper_arm.L", "forearm.L", "hand.L",
              "upper_arm.R", "forearm.R", "hand.R"}
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
                for field in ("id", "name", "primary", "steps"):
                    self.assertIn(field, spec)
                self.assertTrue(spec.get("keyframes") or spec.get("mocap"),
                                "needs keyframes or a mocap file")
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

    def test_mocap_paths_are_well_formed(self):
        """Three motion lanes. mixamo/*.fbx lives in the private mocap/
        checkout (Adobe terms forbid redistributing the FBX), so only the
        reference is checkable. cc0/*.glb#Clip and video/*.json are public
        and vendored under motions/, so the file must exist and a pack clip
        must name its animation."""
        for stem, spec in specs():
            mocap = spec.get("mocap")
            if not mocap:
                continue
            with self.subTest(stem):
                self.assertFalse(mocap.startswith("/"))
                vendor = mocap.split("/")[0]
                self.assertIn(vendor, {"mixamo", "cc0", "video"})
                file, _, clip = mocap.partition("#")
                if vendor == "mixamo":
                    self.assertTrue(file.endswith(".fbx"))
                    self.assertFalse(clip)
                elif vendor == "cc0":
                    self.assertTrue(file.endswith((".glb", ".gltf")))
                    self.assertTrue(clip, "a CC0 pack reference needs '#Clip Name'")
                    self.assertTrue((REPO / "motions" / file).exists(), file)
                else:
                    self.assertTrue(file.endswith(".json"))
                    path = REPO / "motions" / file
                    self.assertTrue(path.exists(), file)
                    doc = json.loads(path.read_text())
                    self.assertEqual(doc.get("format"), "opengym3d-motion/1")
                    self.assertGreaterEqual(len(doc["frames"]), 2)
                    for fr in doc["frames"][:2]:
                        self.assertEqual(set(fr["dirs"]), VIDEO_DIRS)
                        self.assertEqual(set(fr["pelvis"]), {"left", "forward", "up"})
                self.assertNotEqual(spec.get("status"), "draft",
                                    "mocap specs are the live ones")

    def test_every_motion_is_in_the_asset_library(self):
        """Licensing is data: a spec's motion must be a library entry so the
        manifest can say whether the render may ship in the pack."""
        sys.path.insert(0, str(REPO / "pipeline"))
        import asset_library
        lib = asset_library.Library()
        for stem, ref, asset, _status in lib.check_specs(REPO / "exercises"):
            with self.subTest(stem):
                self.assertIsNotNone(asset, f"{ref} is not in assets/ASSET_LIBRARY.json")
                self.assertIn("license", asset)
                self.assertIn("commercial_use", asset)

    def test_asset_library_files_exist(self):
        sys.path.insert(0, str(REPO / "pipeline"))
        import asset_library
        lib = asset_library.Library()
        for a in lib.find_motion():
            if a.get("file", "").startswith("mixamo/"):
                continue                       # private checkout
            with self.subTest(a.id):
                self.assertTrue((REPO / "motions" / a["file"]).exists(), a["file"])

    def test_keyframes_are_a_full_normalised_rep(self):
        for stem, spec in specs():
            if not spec.get("keyframes"):
                continue
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
            for kf in spec.get("keyframes", []):
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

    def test_camera_override_is_a_side(self):
        for stem, spec in specs():
            if "camera" in spec:
                with self.subTest(stem):
                    self.assertIn(spec["camera"], ("front", "back", "side"))

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
                if equipment in ("Dumbbell", "Barbell", "Kettlebell"):
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
            live = [s for _, s in specs() if s.get("status") != "draft"]
            self.assertEqual(len(manifest), len(live))
            self.assertGreaterEqual(len(live), 12)
            for entry in manifest:
                self.assertTrue(entry["glb"].endswith(".glb"))
                self.assertTrue(entry["thumb"].endswith(".png"))
                self.assertTrue(entry["steps"], "viewer renders steps")


if __name__ == "__main__":
    unittest.main()
