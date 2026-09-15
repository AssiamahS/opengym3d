"""Merge exercises/*.json into one site manifest (metadata only, no keyframes).

    python3 pipeline/make_manifest.py exercises site/exercises.json [site/assets]

With an assets dir, each exercise's QA report (<id>.glb.qa.json, written by
pipeline/qa_glb.py) is read and an exercise with a CRITICAL failure is left
out of the manifest — it stays rendered on disk for the inspector, but the
public grid never lists a barbell exercise with empty hands or an arm whose
roll flips mid-rep. No "close enough", no silent fallback: the exclusions are
printed, and written to <dest dir>/qa_report.json for the inspector page.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_library import Library  # noqa: E402

LIB = Library()


def motion_info(spec):
    """Where the motion came from and whether the render may be sold: the
    asset library's answer, never a guess from the path."""
    ref = spec.get("mocap")
    if not ref:
        return {"lane": "keyed", "license": "MIT", "source": "hand-keyed pose JSON",
                "pack": True}
    asset = LIB.motion_for_ref(ref)
    lane = ref.split("/")[0]
    if asset is None:
        return {"lane": lane, "license": "unknown", "source": ref, "pack": False}
    return {"lane": lane, "license": asset["license"],
            "source": asset.get("name", ref), "pack": LIB.redistributable(asset)}


def entry(spec):
    return {
        "license": motion_info(spec),
        "id": spec["id"],
        "name": spec["name"],
        "equipment": spec.get("equipment", "None"),
        "difficulty": spec.get("difficulty", "Beginner"),
        "primary": spec.get("primary", []),
        "secondary": spec.get("secondary", []),
        "steps": spec.get("steps", []),
        "glb": f"assets/{spec['id']}.glb",
        "thumb": f"assets/{spec['id']}.png",
        "strip": f"assets/{spec['id']}.strip.png",
        "motion": "mocap" if spec.get("mocap") else "keyed",
        "camera": spec.get("camera", "front"),
    }


def main(src, dest, assets=None):
    src, dest = Path(src), Path(dest)
    assets = Path(assets) if assets else None
    manifest, report = [], []
    for path in sorted(src.glob("*.json")):
        spec = json.loads(path.read_text())
        if spec.get("status") == "draft":
            continue                      # not rendered, so not listed
        e = entry(spec)
        qa_path = assets / f"{spec['id']}.glb.qa.json" if assets else None
        if qa_path is not None:
            if not qa_path.exists():
                print(f"QA MISSING {spec['id']}: no report, excluded")
                report.append({"id": spec["id"], "verdict": "MISSING"})
                continue
            qa = json.loads(qa_path.read_text())
            summary = qa["summary"]
            e["qa"] = {"pass": summary["pass"], "fails": summary["fails"],
                       "critical_fails": summary["critical_fails"],
                       "report": f"assets/{spec['id']}.glb.qa.json"}
            crit = [r for r in qa["results"]
                    if r["status"] == "FAIL" and r["critical"]]
            report.append({"id": spec["id"],
                           "verdict": "PASS" if summary["pass"] else "FAIL",
                           "fails": summary["fails"],
                           "critical": [f"{r['check']} {r['joint']}: {r['detail']}"
                                        for r in crit]})
            if not summary["pass"]:
                print(f"QA FAIL {spec['id']}: {len(crit)} critical — excluded")
                for r in crit:
                    print(f"    {r['check']:13s} {r['joint']:26s} {r['detail']}")
                continue
        manifest.append(e)
    dest.write_text(json.dumps(manifest, indent=2))
    if assets:
        (dest.parent / "qa_report.json").write_text(json.dumps(report, indent=1))
        excluded = [r["id"] for r in report if r["verdict"] != "PASS"]
        print(f"QA gate: {len(manifest)} listed, {len(excluded)} excluded "
              f"{excluded}")
    print(f"manifest: {len(manifest)} exercises -> {dest}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
