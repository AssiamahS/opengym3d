"""Merge exercises/*.json into one site manifest (metadata only, no keyframes).

    python3 pipeline/make_manifest.py exercises site/exercises.json
"""

import json
import sys
from pathlib import Path

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
manifest = []
for path in sorted(src.glob("*.json")):
    spec = json.loads(path.read_text())
    manifest.append({
        "id": spec["id"],
        "name": spec["name"],
        "equipment": spec.get("equipment", "None"),
        "difficulty": spec.get("difficulty", "Beginner"),
        "primary": spec.get("primary", []),
        "secondary": spec.get("secondary", []),
        "glb": f"assets/{spec['id']}.glb",
        "thumb": f"assets/{spec['id']}.png",
    })
dest.write_text(json.dumps(manifest, indent=2))
print(f"manifest: {len(manifest)} exercises -> {dest}")
