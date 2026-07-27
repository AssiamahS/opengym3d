"""Real muscle geometry for the exercise figure.

The v0.4-0.22 figure was a MakeHuman base mesh with muscle *territories*
painted onto smooth skin. It reads as a mannequin someone drew on, because
there is no anatomy under the paint — flat colour on a flat surface.

This module swaps in actual muscles: Z-Anatomy's BodyParts3D-derived
muscular system, where every muscle is its own mesh carrying its
Terminologia Anatomica name. Highlighting "the quads" stops being a
weight-painting problem and becomes object selection — anatomically
correct by construction, which is the only kind of correct that has ever
survived a round of review on this repo.

Z-Anatomy is CC-BY-SA 4.0. That is share-alike: anything derived from it
carries the same licence, so the exported assets are NOT MIT like the rest
of this repo. See ASSET-LICENSE.md — the code stays MIT, the renders don't.

Nothing here hardcodes an atlas object name. Names are resolved by
substring against what the file actually contains and the resolution is
logged, because on this repo every eyeballed mapping has broken and every
data-derived one has worked first try.
"""

import json
import os
import urllib.request
import zipfile

import bpy

ZANATOMY_URL = ("https://github.com/Z-Anatomy/Models-of-human-anatomy/"
                "raw/master/Z-Anatomy.zip")
MUSCLE_COLLECTION_SUFFIX = "muscular system"

# Exercise-spec muscle key -> TA2 substrings. One key can pull several
# muscles: "quads" is four separate heads in the atlas, and lighting up only
# rectus femoris would be a lie.
MUSCLE_QUERIES = {
    "quads": ["rectus femoris", "vastus lateralis", "vastus medialis",
              "vastus intermedius"],
    "hamstrings": ["biceps femoris", "semitendinosus", "semimembranosus"],
    "glutes": ["gluteus maximus", "gluteus medius", "gluteus minimus"],
    "calves": ["gastrocnemius", "soleus"],
    "core": ["rectus abdominis", "obliquus externus abdominis",
             "transversus abdominis"],
    "abs": ["rectus abdominis", "obliquus externus abdominis"],
    "lower back": ["erector spinae", "longissimus", "iliocostalis", "spinalis"],
    "chest": ["pectoralis major", "pectoralis minor"],
    "pecs": ["pectoralis major", "pectoralis minor"],
    "lats": ["latissimus dorsi"],
    "back": ["latissimus dorsi", "rhomboid", "teres major"],
    "traps": ["trapezius"],
    "shoulders": ["deltoid"],
    "delts": ["deltoid"],
    "front delts": ["deltoid"],
    "biceps": ["biceps brachii", "brachialis"],
    "triceps": ["triceps brachii"],
    "forearms": ["brachioradialis", "flexor carpi", "extensor carpi",
                 "pronator teres"],
}

# Structures that share a muscle's name but are not the muscle: keeping them
# would light up a tendon sheath or a fascia when the user asked for a belly.
EXCLUDE_TERMS = ("bursa", "tendon", "fascia", "aponeurosis", "sheath",
                 "insertion", "compartment", "region", "nerve", "artery",
                 "vein", "node", "ligament", "retinaculum", "raphe", "septum")


def ensure_atlas(root=None):
    """Download + unpack the atlas once. CI caches the unpacked tree."""
    root = root or os.path.expanduser("~/z-anatomy")
    blend = os.path.join(root, "Z-Anatomy", "Startup.blend")
    if os.path.exists(blend):
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
        raise RuntimeError(f"no Startup.blend in the atlas zip: {os.listdir(root)}")
    return blend


def _muscle_collection_name(blend):
    with bpy.data.libraries.load(blend, link=False) as (src, _dst):
        names = list(src.collections)
    hits = [n for n in names if n.lower().endswith(MUSCLE_COLLECTION_SUFFIX)]
    if not hits:
        raise RuntimeError("atlas has no muscular-system collection")
    return min(hits, key=len)      # not "Abdominal part of muscular system"


def load_muscles(blend=None):
    """Append the muscular system and return {object_name: object}."""
    blend = blend or ensure_atlas()
    name = _muscle_collection_name(blend)
    print(f"appending {name!r}")
    with bpy.data.libraries.load(blend, link=False) as (_src, dst):
        dst.collections = [name]
    collection = bpy.data.collections[name]
    bpy.context.scene.collection.children.link(collection)
    objs = {o.name: o for o in collection.all_objects if o.type == "MESH"}
    print(f"  {len(objs)} muscle meshes")
    return collection, objs


def resolve(objs, queries):
    """Atlas objects matching any query substring, minus the non-muscle
    structures that share the name. Returns [] rather than raising — a
    missing muscle should dim a highlight, never fail a render."""
    found = []
    for obj_name in objs:
        low = obj_name.lower()
        if any(term in low for term in EXCLUDE_TERMS):
            continue
        if any(q in low for q in queries):
            found.append(obj_name)
    return sorted(found)


def build_muscle_index(objs):
    """Exercise muscle key -> [atlas object names], logged in full so the
    next person can see exactly what "quads" resolved to."""
    index = {}
    for key, queries in MUSCLE_QUERIES.items():
        hits = resolve(objs, queries)
        index[key] = hits
        print(f"  {key:<12} -> {len(hits):>3} objects"
              + (f"  e.g. {hits[0]}" if hits else "   *** NOTHING MATCHED ***"))
    return index


def body_extents(objs):
    """World-space bounding box of the whole musculature."""
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for obj in objs.values():
        for corner in obj.bound_box:
            world = obj.matrix_world @ __import__("mathutils").Vector(corner)
            for axis in range(3):
                lo[axis] = min(lo[axis], world[axis])
                hi[axis] = max(hi[axis], world[axis])
    return lo, hi


def fit_to_rig(collection, objs, floor_z, head_z):
    """Scale + translate the musculature so it stands in the driver rig's
    world frame: feet on `floor_z`, crown at `head_z`. Uniform scale only —
    a non-uniform fit would distort anatomy, which is the whole point of
    using a real atlas.

    Returns the (scale, offset) actually applied so the caller can log it.
    """
    lo, hi = body_extents(objs)
    height = hi[2] - lo[2]
    if height <= 0:
        raise RuntimeError(f"degenerate atlas extents: {lo} .. {hi}")
    scale = (head_z - floor_z) / height

    parent = bpy.data.objects.new("Musculature", None)   # empty as the handle
    bpy.context.scene.collection.objects.link(parent)
    for obj in objs.values():
        if obj.parent is None:
            obj.parent = parent
            obj.matrix_parent_inverse = parent.matrix_world.inverted()

    parent.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    lo2, _hi2 = body_extents(objs)
    parent.location = (
        parent.location.x - (lo2[0] + (hi[0] - lo[0]) * scale / 2),
        parent.location.y - (lo2[1] + (hi[1] - lo[1]) * scale / 2),
        parent.location.z - lo2[2] + floor_z,
    )
    bpy.context.view_layer.update()
    print(f"  fit: scale {scale:.4f}, extents {lo} .. {hi}")
    return parent, scale


def decimate(objs, target_tris):
    """Hold the web GLB to budget. Ratio is computed from the real triangle
    count, not guessed, and applied uniformly so no muscle is singled out."""
    total = 0
    for obj in objs.values():
        total += sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)
    if total <= target_tris:
        print(f"  {total:,} tris — under the {target_tris:,} budget, no decimation")
        return 1.0
    ratio = target_tris / total
    print(f"  {total:,} tris -> decimating to ratio {ratio:.3f}")
    for obj in objs.values():
        mod = obj.modifiers.new("Decimate", "DECIMATE")
        mod.ratio = ratio
    return ratio


def write_attribution(path):
    """CC-BY-SA obliges attribution and share-alike on the OUTPUT, not just
    the source. Ship it next to the assets or we are simply in breach."""
    with open(path, "w") as f:
        f.write(
            "# Asset licence\n\n"
            "The rendered figures in this directory are derived from\n"
            "**Z-Anatomy** (https://www.z-anatomy.com/), the libre 3D atlas of\n"
            "anatomy by Gauthier Kervyn and Marcin Zielinski, which is itself\n"
            "derived from **BodyParts3D** (The Database Center for Life Science).\n\n"
            "- Z-Anatomy — CC BY-SA 4.0\n"
            "- BodyParts3D — CC BY-SA 2.1 Japan\n\n"
            "Because CC BY-SA is a share-alike licence, these rendered assets\n"
            "(.glb, .png, .gif, .mp4) are distributed under **CC BY-SA 4.0**,\n"
            "not under this repository's MIT licence. The MIT licence covers the\n"
            "pipeline source code only.\n")
