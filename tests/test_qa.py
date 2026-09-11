"""The QA gate must catch what it claims to catch — proven on synthetic GLBs.

A tiny rig with the same bone names the real export carries is built in
memory, animated one way to be clean and another way to be broken, and
qa_glb has to grade each correctly:

  stretch a forearm      -> bone_length FAIL (limb coming apart)
  flip a wrist's roll    -> twist_flip FAIL   (the shortest-arc failure)
  barbell spec, no bar   -> prop_present FAIL (mime)
  bar drifts off hands   -> prop_contact FAIL
  clean rig              -> PASS, and the manifest lists it
  failing rig            -> the manifest leaves it out and says why

    python3 -m unittest tests.test_qa -v
"""

import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "pipeline"))
import qa_glb  # noqa: E402

# name -> (parent, local offset) — offsets are glTF Y-up metres
RIG = [
    ("root", None, (0, 0.95, 0)),
    ("spine03", "root", (0, 0.10, 0)),
    ("spine01", "spine03", (0, 0.25, 0)),
    ("neck01", "spine01", (0, 0.20, 0)),
    ("head", "neck01", (0, 0.08, 0)),
    ("upperarm01.L", "spine01", (0.18, 0.0, 0)),
    ("upperarm02.L", "upperarm01.L", (0.10, 0, 0)),
    ("lowerarm01.L", "upperarm02.L", (0.14, 0, 0)),
    ("lowerarm02.L", "lowerarm01.L", (0.12, 0, 0)),
    ("wrist.L", "lowerarm02.L", (0.12, 0, 0)),
    ("upperarm01.R", "spine01", (-0.18, 0.0, 0)),
    ("upperarm02.R", "upperarm01.R", (-0.10, 0, 0)),
    ("lowerarm01.R", "upperarm02.R", (-0.14, 0, 0)),
    ("lowerarm02.R", "lowerarm01.R", (-0.12, 0, 0)),
    ("wrist.R", "lowerarm02.R", (-0.12, 0, 0)),
    ("upperleg01.L", "root", (0.10, 0, 0)),
    ("upperleg02.L", "upperleg01.L", (0, -0.15, 0)),
    ("lowerleg01.L", "upperleg02.L", (0, -0.28, 0)),
    ("lowerleg02.L", "lowerleg01.L", (0, -0.20, 0)),
    ("foot.L", "lowerleg02.L", (0, -0.23, 0)),
    ("upperleg01.R", "root", (-0.10, 0, 0)),
    ("upperleg02.R", "upperleg01.R", (0, -0.15, 0)),
    ("lowerleg01.R", "upperleg02.R", (0, -0.28, 0)),
    ("lowerleg02.R", "lowerleg01.R", (0, -0.20, 0)),
    ("foot.R", "lowerleg02.R", (0, -0.23, 0)),
]
DURATION = 2.0
TIMES = [i * DURATION / 30 for i in range(31)]


def quat_y(deg):
    h = math.radians(deg) / 2
    return (0.0, math.sin(h), 0.0, math.cos(h))


def quat_x(deg):
    h = math.radians(deg) / 2
    return (math.sin(h), 0.0, 0.0, math.cos(h))


def quat_z(deg):
    h = math.radians(deg) / 2
    return (0.0, 0.0, math.sin(h), math.cos(h))


def make_glb(path, tracks, prop=None):
    """tracks: {node_name: {"rotation": [quat per TIMES] | "translation": [...]}}
    prop: (name, [position per TIMES]) adds a mesh node with that track."""
    names = [n for n, _, _ in RIG]
    nodes = []
    for name, parent, off in RIG:
        nodes.append({"name": name, "translation": list(off)})
    for name, parent, _ in RIG:
        if parent:
            nodes[names.index(parent)].setdefault("children", []).append(names.index(name))
    if prop:
        nodes.append({"name": prop[0], "mesh": 0, "translation": list(prop[1][0])})
        tracks = dict(tracks, **{prop[0]: {"translation": prop[1]}})
        names.append(prop[0])

    blob = bytearray()
    views, accessors = [], []

    def push(values, ncomp, amin=None, amax=None):
        flat = [c for v in values for c in (v if ncomp > 1 else (v,))]
        data = struct.pack("<%df" % len(flat), *flat)
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)})
        blob.extend(data)
        acc = {"bufferView": len(views) - 1, "componentType": 5126,
               "count": len(values),
               "type": {1: "SCALAR", 3: "VEC3", 4: "VEC4"}[ncomp]}
        if amin is not None:
            acc["min"], acc["max"] = [amin], [amax]
        accessors.append(acc)
        return len(accessors) - 1

    time_acc = push(TIMES, 1, TIMES[0], TIMES[-1])
    samplers, channels = [], []
    for node, paths in tracks.items():
        for tpath, values in paths.items():
            acc = push(values, 4 if tpath == "rotation" else 3)
            samplers.append({"input": time_acc, "output": acc, "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": names.index(node), "path": tpath}})
    # a one-triangle mesh so the prop node counts as an implement
    tri = push([(0, 0, 0), (0.1, 0, 0), (0, 0.1, 0)], 3)
    gltf = {"asset": {"version": "2.0"}, "scene": 0,
            "scenes": [{"nodes": [0] + ([len(names) - 1] if prop else [])}],
            "nodes": nodes,
            "meshes": [{"primitives": [{"attributes": {"POSITION": tri}}]}],
            "animations": [{"name": "clip", "samplers": samplers, "channels": channels}],
            "buffers": [{"byteLength": len(blob)}],
            "bufferViews": views, "accessors": accessors}
    js = json.dumps(gltf).encode()
    while len(js) % 4:
        js += b" "
    while len(blob) % 4:
        blob.append(0)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    Path(path).write_bytes(out)


def clean_tracks():
    """A slow, smooth elbow curl on both arms and a shallow knee bend."""
    def curl(t):
        return 70 * (0.5 - 0.5 * math.cos(2 * math.pi * t / DURATION))
    return {
        "lowerarm01.L": {"rotation": [quat_z(curl(t)) for t in TIMES]},
        "lowerarm01.R": {"rotation": [quat_z(-curl(t)) for t in TIMES]},
    }


def fails(results, check):
    return [r["joint"] for r in results if r["check"] == check and r["status"] == "FAIL"]


class TestQaGlb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def grade(self, tracks, spec=None, prop=None, name="ex"):
        glb = self.dir / f"{name}.glb"
        make_glb(glb, tracks, prop)
        results, _ = qa_glb.run_qa(str(glb), spec)
        return results

    def test_clean_rig_passes(self):
        results = self.grade(clean_tracks())
        self.assertTrue(qa_glb.summarise(results)["pass"],
                        [r for r in results if r["status"] == "FAIL"])

    def test_stretched_forearm_is_a_bone_length_failure(self):
        tracks = clean_tracks()
        tracks["lowerarm02.L"] = {"translation": [
            (0.12 + 0.06 * math.sin(math.pi * t / DURATION), 0, 0) for t in TIMES]}
        results = self.grade(tracks)
        self.assertIn("lowerarm01.L->lowerarm02.L", fails(results, "bone_length"))
        self.assertFalse(qa_glb.summarise(results)["pass"])

    def test_wrist_roll_flip_is_critical(self):
        tracks = clean_tracks()
        # roll about the bone's own axis: 0 -> 170 in a single sample
        rolls = [quat_y(0)] * 15 + [quat_y(170)] * 16
        tracks["wrist.L"] = {"rotation": rolls}
        results = self.grade(tracks)
        self.assertIn("wrist.L", fails(results, "twist_flip"))
        self.assertTrue([r for r in results if r["check"] == "twist_flip"][0]["critical"])

    def test_hyperextended_knee_fails_the_hinge_check(self):
        tracks = clean_tracks()
        # the figure faces +Z; a shin swung to +Z is a knee bent forwards
        tracks["lowerleg01.L"] = {"rotation": [quat_x(-40)] * len(TIMES)}
        results = self.grade(tracks)
        self.assertIn("knee.L", fails(results, "hinge"))

    def test_barbell_spec_without_a_bar_is_a_mime(self):
        results = self.grade(clean_tracks(), spec={"prop": {"type": "barbell"}})
        self.assertEqual(fails(results, "prop_present"), ["barbell"])

    def test_bar_on_the_hands_passes_and_off_them_fails(self):
        # the synthetic wrists start at x=±0.66, y=1.30 (root 0.95 + 0.35)
        # and rise with the 0.24 m forearm as the elbows curl
        def wrist_y(t):
            curl = 70 * (0.5 - 0.5 * math.cos(2 * math.pi * t / DURATION))
            return 1.30 + 0.24 * math.sin(math.radians(curl))
        on = [(0.0, wrist_y(t), 0.0) for t in TIMES]
        results = self.grade(clean_tracks(), spec={"prop": {"type": "barbell"}},
                             prop=("Barbell", on))
        self.assertEqual(fails(results, "prop_contact"), [])
        self.assertTrue(qa_glb.summarise(results)["pass"])
        off = on[:20] + [(0.0, 0.60, 0.4)] * 11
        results = self.grade(clean_tracks(), spec={"prop": {"type": "barbell"}},
                             prop=("Barbell", off), name="off")
        self.assertEqual(fails(results, "prop_contact"), ["Barbell"])

    def test_cli_writes_a_report_and_exits_nonzero_on_failure(self):
        glb = self.dir / "bad.glb"
        tracks = clean_tracks()
        tracks["wrist.R"] = {"rotation": [quat_y(0)] * 15 + [quat_y(170)] * 16}
        make_glb(glb, tracks)
        proc = subprocess.run([sys.executable, str(REPO / "pipeline" / "qa_glb.py"),
                               str(glb)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        report = json.loads(Path(str(glb) + ".qa.json").read_text())
        self.assertFalse(report["summary"]["pass"])
        self.assertIn("twist_flip", proc.stdout)


class TestManifestGate(unittest.TestCase):
    def test_critical_failure_is_excluded_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            specs, assets = tmp / "exercises", tmp / "assets"
            specs.mkdir()
            assets.mkdir()
            for eid, ok in (("good", True), ("bad", False)):
                (specs / f"{eid}.json").write_text(json.dumps({
                    "id": eid, "name": eid, "primary": ["Quads"],
                    "steps": ["a", "b", "c"], "mocap": "mixamo/x.fbx"}))
                results = [{"check": "twist_flip", "joint": "wrist.L",
                            "status": "PASS" if ok else "FAIL", "critical": True,
                            "detail": "roll flip", "value": 170, "t": 1.0}]
                (assets / f"{eid}.glb.qa.json").write_text(json.dumps({
                    "id": eid, "summary": {"pass": ok, "fails": 0 if ok else 1,
                                           "critical_fails": 0 if ok else 1},
                    "results": results}))
            dest = tmp / "exercises.json"
            proc = subprocess.run(
                [sys.executable, str(REPO / "pipeline" / "make_manifest.py"),
                 str(specs), str(dest), str(assets)],
                check=True, capture_output=True, text=True)
            manifest = json.loads(dest.read_text())
            self.assertEqual([e["id"] for e in manifest], ["good"])
            self.assertTrue(manifest[0]["qa"]["pass"])
            self.assertIn("QA FAIL bad", proc.stdout)
            report = json.loads((tmp / "qa_report.json").read_text())
            self.assertEqual({r["id"]: r["verdict"] for r in report},
                             {"good": "PASS", "bad": "FAIL"})


if __name__ == "__main__":
    unittest.main()
