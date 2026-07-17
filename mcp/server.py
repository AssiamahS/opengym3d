#!/usr/bin/env python3
"""OpenGym3D MCP server — the exercise library as native AI-assistant tools.

Same idea as MuscleWiki's first-party @musclewiki/mcp: expose the whole
exercise database (metadata, form steps, muscle targets, and rendered asset
URLs) to any MCP client over stdio. Everything is read live from the repo's
exercises/*.json specs, so the tools never drift from what CI renders.

Register with:
    claude mcp add opengym3d -- python3 /Users/djsly/opengym3d/mcp/server.py
"""
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

REPO = Path(__file__).resolve().parent.parent
EXERCISES_DIR = REPO / "exercises"
SITE = "https://assiamahs.github.io/opengym3d"

mcp = FastMCP("opengym3d")


def _load_all() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(EXERCISES_DIR.glob("*.json"))]


def _assets(ex_id: str) -> dict:
    return {
        "glb": f"{SITE}/assets/{ex_id}.glb",
        "thumbnail": f"{SITE}/assets/{ex_id}.png",
        "gif": f"{SITE}/assets/{ex_id}.gif",
        "mp4": f"{SITE}/assets/{ex_id}.mp4",
        "viewer": f"{SITE}/",
    }


def _summary(spec: dict) -> dict:
    return {
        "id": spec["id"],
        "name": spec["name"],
        "equipment": spec.get("equipment", "None"),
        "difficulty": spec.get("difficulty", "Beginner"),
        "primary": spec.get("primary", []),
        "secondary": spec.get("secondary", []),
    }


@mcp.tool()
def list_exercises(muscle: str = "", equipment: str = "",
                   difficulty: str = "") -> str:
    """List exercises, optionally filtered by muscle (matches primary or
    secondary, e.g. 'quads'), equipment ('None', 'Dumbbell', 'Barbell'),
    or difficulty ('Beginner', 'Intermediate')."""
    out = []
    for spec in _load_all():
        s = _summary(spec)
        if muscle and not any(muscle.lower() in m.lower()
                              for m in s["primary"] + s["secondary"]):
            continue
        if equipment and equipment.lower() != s["equipment"].lower():
            continue
        if difficulty and difficulty.lower() != s["difficulty"].lower():
            continue
        out.append(s)
    return json.dumps(out, indent=2)


@mcp.tool()
def get_exercise(exercise_id: str) -> str:
    """Full record for one exercise by id (e.g. 'squat'): metadata, targeted
    muscles, step-by-step form instructions, equipment prop, and URLs for the
    animated GLB, thumbnail PNG, and watch-sized GIF/MP4."""
    path = EXERCISES_DIR / f"{exercise_id}.json"
    if not path.exists():
        ids = [p.stem for p in sorted(EXERCISES_DIR.glob("*.json"))]
        return json.dumps({"error": f"unknown exercise '{exercise_id}'",
                           "available": ids})
    spec = json.loads(path.read_text())
    record = _summary(spec)
    record["steps"] = spec.get("steps", [])
    record["prop"] = spec.get("prop")
    record["duration_seconds"] = spec.get("duration", 2.0)
    record["assets"] = _assets(spec["id"])
    return json.dumps(record, indent=2)


@mcp.tool()
def search_exercises(query: str) -> str:
    """Free-text search across exercise names, muscles, equipment, and form
    steps. Returns matching summaries."""
    q = query.lower()
    out = []
    for spec in _load_all():
        haystack = " ".join([
            spec["name"], spec.get("equipment", ""),
            " ".join(spec.get("primary", []) + spec.get("secondary", [])),
            " ".join(spec.get("steps", [])),
        ]).lower()
        if all(term in haystack for term in q.split()):
            out.append(_summary(spec))
    return json.dumps(out, indent=2)


@mcp.tool()
def library_stats() -> str:
    """Library overview: exercise count, muscles covered, equipment split."""
    specs = _load_all()
    muscles: dict[str, int] = {}
    equipment: dict[str, int] = {}
    for spec in specs:
        for m in spec.get("primary", []):
            muscles[m] = muscles.get(m, 0) + 1
        eq = spec.get("equipment", "None")
        equipment[eq] = equipment.get(eq, 0) + 1
    return json.dumps({
        "exercises": len(specs),
        "primary_muscle_coverage": dict(sorted(muscles.items())),
        "equipment": equipment,
        "site": SITE,
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
