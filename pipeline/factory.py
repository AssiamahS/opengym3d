"""The exercise factory: one entry point from "we need exercise X" to a
graded GLB, with every step's answer coming from data in the repo.

    python3 pipeline/factory.py status                 # every spec: lane, licence, pattern, tier
    python3 pipeline/factory.py resolve deadlift lunge  # where motion for these can come from
    python3 pipeline/factory.py ingest lunge --video ~/Downloads/lunge.mov [--mirror]
    python3 pipeline/factory.py ingest lunge --motion motions/video/lunge.json
    python3 pipeline/factory.py grade site/assets/*.glb # joint gate + anatomy gate + sheets

resolve walks the motion lanes in licence order — the asset library first
(CC0 packs, own captures), then the app-only Mixamo clips the project holds,
then the video lane — and says which one covers the exercise or, when none
does, that a capture is needed and how to shoot it. Nothing is guessed from
a path: the library and the real files on disk answer.

ingest is the "record yourself" lane end to end: run video_mocap.py on the
clip (or take a motion JSON already extracted), write the motion under
motions/video/, point the spec at it, drop its draft status, put the camera
on the side, register the motion in the asset library, and print the spike
command that renders and grades it in CI.

grade runs everything the deploy runs on a GLB — joint integrity, the
exercise's anatomy rules, the two-view skeleton sheet — so a spike artifact
can be judged locally in seconds.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
from asset_library import Library  # noqa: E402
import anatomy_qa  # noqa: E402
import qa_glb  # noqa: E402
import sheet_glb  # noqa: E402

EXERCISES = REPO / "exercises"
MOTIONS = REPO / "motions"
MIXAMO = REPO / "mocap" / "mixamo"          # private clone, gitignored
LIB_PATH = REPO / "assets" / "ASSET_LIBRARY.json"

# how hard each pattern is to capture and retarget cleanly, from what the
# first two video captures and the Mixamo batch actually needed
TIER = {
    "curl": "easy", "calf_raise": "easy", "wall_sit": "easy", "supine_curl": "easy",
    "high_knees": "easy", "seated_hold": "easy", "locomotion": "easy",
    "jumping_jack": "easy", "plank": "easy",
    "lunge": "medium", "raise_lateral": "medium", "raise_front": "medium",
    "press_vertical": "medium", "squat": "medium", "tricep_overhead": "medium",
    "push_up": "medium", "bridge": "medium", "plyometric": "medium",
    "hinge": "hard", "swing": "hard", "row": "hard", "prone_lift": "hard",
    "olympic": "hard", "crawl": "hard",
}

# exercise id -> words a library clip, a Mixamo file or a M2M action would
# carry. Only used to SEARCH; the spec's "mocap" field is the truth once set.
ALIASES = {
    "bent_over_row": ["row", "bent over row"], "calf_raise": ["calf", "calf raise"],
    "crunch": ["crunch"], "deadlift": ["deadlift", "lifting heavy"],
    "dumbbell_shoulder_press": ["shoulder press", "overhead press"],
    "glute_bridge": ["glute bridge", "hip thrust"], "good_morning": ["good morning"],
    "hammer_curl": ["hammer curl", "curl"], "high_knees": ["high knees"],
    "lateral_raise": ["lateral raise", "side raise"], "lunge": ["lunge"],
    "overhead_press": ["overhead press", "shoulder press"],
    "overhead_tricep_extension": ["tricep", "triceps extension"],
    "reverse_lunge": ["reverse lunge", "lunge"],
    "romanian_deadlift": ["romanian deadlift", "rdl", "deadlift", "lifting heavy"],
    "sumo_squat": ["sumo squat"], "superman": ["superman"],
    "wall_sit": ["wall sit"],
}


def _hit(words, text):
    """Whole-word match: 'row' must not find 'throw', 'press' not 'pushup'."""
    import re
    t = re.sub(r"[_\-]", " ", text.lower())
    return any(re.search(r"\b" + re.escape(w) + r"\b", t) for w in words)


def specs():
    for p in sorted(EXERCISES.glob("*.json")):
        yield p, json.loads(p.read_text())


def load_spec(eid):
    p = EXERCISES / f"{eid}.json"
    if not p.exists():
        sys.exit(f"no spec exercises/{eid}.json")
    return p, json.loads(p.read_text())


def _words(eid):
    return ALIASES.get(eid, [eid.replace("_", " ")])


def _m2m_actions():
    """(pack file, action name) for every clip in the CC0 packs on disk."""
    import struct
    out = []
    for g in sorted((MOTIONS / "cc0" / "mesh2motion").glob("*.glb")):
        b = g.read_bytes()
        ln = struct.unpack("<I", b[12:16])[0]
        j = json.loads(b[20:20 + ln])
        for a in j.get("animations", []):
            out.append((g.relative_to(MOTIONS).as_posix(), a["name"]))
    return out


def resolve(eid, lib=None):
    """{'lane', 'ref', 'licence', 'pack', 'candidates', 'action'} for one exercise."""
    lib = lib or Library()
    _, spec = load_spec(eid)
    ref = spec.get("mocap")
    if ref:
        a = lib.motion_for_ref(ref)
        if a:
            return {"id": eid, "lane": ref.split("/")[0], "ref": ref,
                    "licence": a["license"], "pack": lib.redistributable(a),
                    "candidates": [], "action": "rendered — nothing to do"}
        return {"id": eid, "lane": ref.split("/")[0], "ref": ref, "licence": "unknown",
                "pack": False, "candidates": [],
                "action": "spec references motion the library does not know — add the entry"}

    words = [w.lower() for w in _words(eid)]
    cands = []
    for a in lib.of_type("motion"):
        hay = " ".join([a.get("name", ""), " ".join(a.get("tags", [])),
                        a.get("clip", "")]).lower()
        if _hit(words, hay):
            cands.append(("library", f"{a['file']}#{a['clip']}" if a.get("clip") else a["file"],
                          a["license"]))
    for pack, name in _m2m_actions():
        if _hit(words, name):
            cands.append(("cc0", f"{pack}#{name}", "CC0-1.0"))
    if MIXAMO.exists():
        for f in sorted(MIXAMO.glob("*.fbx")):
            if _hit(words, f.stem):
                cands.append(("mixamo", f"mixamo/{f.name}", "Mixamo"))
    for f in sorted((MOTIONS / "video").glob("*.json")):
        if f.stem.startswith(eid) or _hit(words, f.stem):
            meta = json.loads(f.read_text())
            cands.append(("video", f"video/{f.name}", meta.get("license", "?")))
    # dedupe, keep first sighting
    seen, uniq = set(), []
    for c in cands:
        if c[1] not in seen:
            seen.add(c[1])
            uniq.append(c)
    if uniq:
        action = f"candidate motion exists — set \"mocap\": \"{uniq[0][1]}\" and spike it"
    else:
        action = ("CAPTURE NEEDED — phone on a tripod, side view, whole body incl. feet, "
                  f"one clean rep, then: python3 pipeline/factory.py ingest {eid} --video <clip>")
    return {"id": eid, "lane": None, "ref": None, "licence": None, "pack": False,
            "candidates": uniq, "action": action}


def status():
    lib = Library()
    rows = []
    for _, spec in specs():
        pat = (spec.get("movement") or {}).get("pattern", "?")
        r = resolve(spec["id"], lib)
        rows.append((spec["id"], spec.get("status", "live"), pat, TIER.get(pat, "?"),
                     r["lane"] or "-", r["licence"] or "-",
                     "pack" if r["pack"] else ("app-only" if r["lane"] else "-"),
                     "" if r["lane"] else ("candidates: " + ", ".join(c[1] for c in r["candidates"])
                                           if r["candidates"] else "capture needed")))
    print(f"{'exercise':26s} {'status':6s} {'pattern':14s} {'tier':6s} {'lane':7s} {'licence':10s} {'sale':8s} next")
    for row in rows:
        print(f"{row[0]:26s} {row[1]:6s} {row[2]:14s} {row[3]:6s} {row[4]:7s} {row[5]:10s} {row[6]:8s} {row[7]}")
    live = [r for r in rows if r[1] != "draft"]
    drafts = [r for r in rows if r[1] == "draft"]
    print(f"\n{len(live)} live ({sum(1 for r in live if r[6] == 'pack')} pack-eligible), "
          f"{len(drafts)} drafts waiting on motion")
    for tier in ("easy", "medium", "hard"):
        ids = [r[0] for r in drafts if r[3] == tier]
        if ids:
            print(f"  {tier:6s} {', '.join(ids)}")


def ingest(eid, video=None, motion=None, mirror=False, python=None, source=None):
    spec_path, spec = load_spec(eid)
    out = MOTIONS / "video" / f"{eid}.json"
    if video:
        py = python or str(REPO / ".venv" / "bin" / "python")
        if not Path(py).exists():
            sys.exit(f"{py} missing — docs/ASSET_PIPELINE.md has the one-line venv recipe")
        cmd = [py, str(HERE / "video_mocap.py"), str(video), str(out), "--auto-rep",
               "--source", source or "own capture, iPhone, side view", "--license", "own"]
        if mirror:
            cmd.append("--mirror")
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True)
    elif motion:
        src = Path(motion)
        if src.resolve() != out.resolve():
            out.write_text(src.read_text())
    else:
        sys.exit("ingest needs --video <clip> or --motion <motion.json>")
    meta = json.loads(out.read_text())
    if meta.get("format") != "opengym3d-motion/1":
        sys.exit(f"{out} is not opengym3d-motion/1")
    licence = meta.get("license", "own")

    spec["mocap"] = f"video/{eid}.json"
    spec.pop("status", None)
    spec.setdefault("camera", "side")
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")

    lib = json.loads(LIB_PATH.read_text())
    aid = f"motion/video/{eid.replace('_', '-')}"
    entry = {
        "id": aid, "type": "motion",
        "name": f"{spec['name']} (video capture)",
        "source": meta.get("source", "pipeline/video_mocap.py"),
        "license": licence,
        "commercial_use": licence in ("own", "CC0-1.0", "CC-BY-4.0", "MIT"),
        "format": "opengym3d-motion/1",
        "file": f"video/{eid}.json",
        "rig": "driver-directions",
        "compatible_rigs": ["makehuman-default (via animate_video)"],
        "tags": sorted({eid, *(w.replace(" ", "_") for w in _words(eid)),
                        *(m.lower() for m in spec.get("primary", []))}),
        "quality": 5,
    }
    if meta.get("frames") and meta.get("fps"):
        entry["duration_s"] = round(len(meta["frames"]) / meta["fps"], 2)
    lib["assets"] = [a for a in lib["assets"] if a["id"] != aid] + [entry]
    LIB_PATH.write_text(json.dumps(lib, indent=1, ensure_ascii=False) + "\n")

    print(f"\n{eid}: motion -> {out.relative_to(REPO)} ({licence}), spec live, "
          f"library entry {aid}")
    print("next:")
    print(f"  python3 -m unittest discover -s tests")
    print(f"  git add -A && git commit -m 'feat: {eid} from own capture'")
    print(f"  gh workflow run spike.yml -f exercise={eid}     # ~8 min, then:")
    print(f"  gh run download <run id> -n spike && python3 pipeline/factory.py grade spike/{eid}.glb")


def grade(glbs):
    code = 0
    for g in glbs:
        gid = Path(g).stem
        sp = EXERCISES / f"{gid}.json"
        spec = json.loads(sp.read_text()) if sp.exists() else None
        results, times = qa_glb.run_qa(g, spec)
        summary = qa_glb.summarise(results)
        Path(g + ".qa.json").write_text(json.dumps(
            {"id": gid, "duration": round(times[-1], 3), "samples": len(times),
             "summary": summary, "thresholds": qa_glb.THRESH, "results": results}, indent=1))
        sheet, _ = sheet_glb.sheet(g)
        pat = ((spec or {}).get("movement") or {}).get("pattern", "-")
        print(f"== {gid}: {'PASS' if summary['pass'] else 'FAIL'}  pattern={pat}  "
              f"{summary['critical_fails']} critical / {summary['fails']} fails  sheet={sheet.name}")
        for r in results:
            if r["status"] == "FAIL":
                print(f"   {'CRIT' if r['critical'] else 'warn'} {r['check']:10s} {r['joint']:30s} {r['detail']}")
        code |= 0 if summary["pass"] else 1
    return code


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, *rest = argv
    if cmd == "status":
        status()
        return 0
    if cmd == "resolve":
        lib = Library()
        for eid in rest or [s["id"] for _, s in specs() if s.get("status") == "draft"]:
            r = resolve(eid, lib)
            print(f"{eid:26s} {(r['lane'] or 'none'):7s} {r['action']}")
            for c in r["candidates"]:
                print(f"{'':26s}   {c[0]:8s} {c[1]}  ({c[2]})")
        return 0
    if cmd == "ingest":
        eid = rest[0]
        opts = {"video": None, "motion": None, "mirror": False, "python": None, "source": None}
        it = iter(rest[1:])
        for a in it:
            if a == "--mirror":
                opts["mirror"] = True
            elif a in ("--video", "--motion", "--python", "--source"):
                opts[a[2:]] = next(it)
            else:
                sys.exit(f"unknown option {a}")
        ingest(eid, **opts)
        return 0
    if cmd == "grade":
        return grade(rest)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
