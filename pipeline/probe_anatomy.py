"""Census the Z-Anatomy muscular system so the écorché build is written
against what the atlas actually contains, not against a guess.

Z-Anatomy (https://www.z-anatomy.com, CC-BY-SA 4.0) is a Blender-native
atlas derived from BodyParts3D. Every muscle is a separate object named
with its Terminologia Anatomica (TA2) English term, which is exactly the
handle we need: highlighting "Biceps brachii muscle" becomes selecting an
object, not painting skin-weight territories and hoping.

The atlas is a 307 MB startup .blend with ten body systems in it. This
probe appends only the muscular system, then dumps: object names, sides,
triangle counts, world bounding boxes and the overall body extents. That
report drives the curated muscle list, the poly budget and the alignment
transform in build_exercise.py.

    blender -b -noaudio --python-exit-code 1 -P pipeline/probe_anatomy.py -- probe_out
"""

import json
import os
import sys
import urllib.request
import zipfile

import bpy

ZANATOMY_URL = ("https://github.com/Z-Anatomy/Models-of-human-anatomy/"
                "raw/master/Z-Anatomy.zip")
# The atlas ships 1944 collections — one per anatomical structure — with the
# ten body systems numbered at the top ("4: Muscular system"). The addon
# renames them to dot-prefixed at runtime, so match on the suffix instead of
# either literal.
MUSCLE_COLLECTION_SUFFIX = "muscular system"

# What an exercise spec calls a muscle -> TA2 substrings we expect to find.
# Only used here to report coverage; the build gets the real names from the
# census output.
WANTED = {
    "quads": ["rectus femoris", "vastus lateralis", "vastus medialis",
              "vastus intermedius"],
    "hamstrings": ["biceps femoris", "semitendinosus", "semimembranosus"],
    "glutes": ["gluteus maximus", "gluteus medius", "gluteus minimus"],
    "calves": ["gastrocnemius", "soleus"],
    "abs": ["rectus abdominis", "obliquus externus abdominis"],
    "lower back": ["erector spinae", "longissimus", "iliocostalis"],
    "chest": ["pectoralis major", "pectoralis minor"],
    "lats": ["latissimus dorsi"],
    "traps": ["trapezius"],
    "shoulders": ["deltoid"],
    "biceps": ["biceps brachii", "brachialis"],
    "triceps": ["triceps brachii"],
    "forearms": ["brachioradialis", "flexor carpi", "extensor carpi"],
}

out_dir = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out_dir, exist_ok=True)


def ensure_atlas():
    """Download + unzip the atlas once; CI caches ~/z-anatomy between runs."""
    root = os.path.expanduser("~/z-anatomy")
    blend = os.path.join(root, "Z-Anatomy", "Startup.blend")
    if os.path.exists(blend):
        print(f"atlas already present: {blend}")
        return blend
    os.makedirs(root, exist_ok=True)
    zpath = os.path.join(root, "Z-Anatomy.zip")
    if not os.path.exists(zpath):
        print("downloading Z-Anatomy (~87 MB)…")
        req = urllib.request.Request(
            ZANATOMY_URL, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
        with urllib.request.urlopen(req) as resp, open(zpath, "wb") as f:
            f.write(resp.read())
    with zipfile.ZipFile(zpath) as z:
        z.extractall(root)
    if not os.path.exists(blend):
        raise SystemExit(f"expected {blend} inside the zip, got: "
                         f"{os.listdir(root)}")
    return blend


def list_collections(blend):
    """What top-level systems does the atlas actually ship?"""
    with bpy.data.libraries.load(blend, link=False) as (src, _dst):
        names = list(src.collections)
    return sorted(names)


def find_muscle_collection(names):
    """The whole-system collection, not 'Abdominal part of muscular system'
    and not 'Muscular insertions' — shortest suffix match wins."""
    hits = [n for n in names if n.lower().endswith(MUSCLE_COLLECTION_SUFFIX)]
    if not hits:
        raise SystemExit(f"no muscular-system collection; have: "
                         f"{sorted(names)[:40]}")
    return min(hits, key=len)


def append_muscles(blend, collection_name):
    with bpy.data.libraries.load(blend, link=False) as (src, dst):
        dst.collections = [collection_name]
    collection = bpy.data.collections[collection_name]
    bpy.context.scene.collection.children.link(collection)
    return collection


def transform_diagnostic(collection):
    """Why do 'Rectus femoris.l' and '.r' come back with the SAME bounding
    box, and why is the whole musculature 0.66 units tall when a human is
    1.7? Either the depsgraph hasn't evaluated the freshly-appended objects
    (matrix_world still identity) or the placement lives on a parent that
    didn't come across. Ask, don't guess."""
    samples = [o for o in collection.all_objects if o.type == "MESH"][:6]
    for label in ("before update", "after update"):
        if label == "after update":
            bpy.context.view_layer.update()
        print(f"\n--- transforms {label} ---")
        for obj in samples:
            loc = tuple(round(v, 4) for v in obj.location)
            scale = tuple(round(v, 4) for v in obj.scale)
            translation = tuple(round(v, 4) for v in obj.matrix_world.translation)
            print(f"  {obj.name[:46]:<46} loc={loc} scale={scale} "
                  f"mw.t={translation} parent={obj.parent.name if obj.parent else None} "
                  f"mesh_users={obj.data.users}")


def census(collection):
    rows = []
    for obj in collection.all_objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        tris = sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
        corners = [obj.matrix_world @ v.co for v in mesh.vertices]
        if not corners:
            continue
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        zs = [c.z for c in corners]
        rows.append({
            "name": obj.name,
            "verts": len(mesh.vertices),
            "tris": tris,
            "bbox": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4),
                     round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
        })
    rows.sort(key=lambda r: -r["tris"])
    return rows


def coverage(rows):
    """Which exercise muscles the atlas can serve, and with which objects."""
    lowered = [(r["name"].lower(), r["name"]) for r in rows]
    result = {}
    for key, needles in WANTED.items():
        hits = []
        for needle in needles:
            hits += [original for low, original in lowered if needle in low]
        result[key] = sorted(set(hits))
    return result


def main():
    blend = ensure_atlas()

    collections = list_collections(blend)
    print(f"\n=== {len(collections)} collections in the atlas ===")
    for name in collections:
        if name[0].isdigit():        # the ten body systems
            print("  ", name)

    muscle_collection = find_muscle_collection(collections)
    print(f"\nusing collection: {muscle_collection!r}")
    collection = append_muscles(blend, muscle_collection)
    transform_diagnostic(collection)
    rows = census(collection)
    total_tris = sum(r["tris"] for r in rows)
    print(f"\n=== {len(rows)} muscle meshes, {total_tris:,} tris total ===")
    for row in rows[:40]:
        print(f"  {row['tris']:>8,}  {row['name']}")

    body = {
        "x": [min(r["bbox"][0] for r in rows), max(r["bbox"][3] for r in rows)],
        "y": [min(r["bbox"][1] for r in rows), max(r["bbox"][4] for r in rows)],
        "z": [min(r["bbox"][2] for r in rows), max(r["bbox"][5] for r in rows)],
    } if rows else {}
    print(f"\n=== body extents (atlas units) ===\n{json.dumps(body, indent=2)}")

    cover = coverage(rows)
    print("\n=== exercise-muscle coverage ===")
    for key, hits in cover.items():
        print(f"  {key:<12} {len(hits):>3} objects")
        for hit in hits[:6]:
            print(f"               {hit}")

    report = {
        "muscle_collection": muscle_collection,
        "systems": [c for c in collections if c[0].isdigit()],
        "muscle_count": len(rows),
        "total_tris": total_tris,
        "body_extents": body,
        "coverage": cover,
        "muscles": rows,
    }
    path = os.path.join(out_dir, "anatomy-census.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=1)
    print(f"\nwrote {path}")


main()
