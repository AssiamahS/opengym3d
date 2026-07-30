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
import math
import os
import urllib.request
import zipfile

import bpy
from mathutils import Vector

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
    # Freshly appended objects report an identity matrix_world until the view
    # layer evaluates. Skip this and every world-space measurement below reads
    # a 0.66-metre-tall human with its left and right sides in the same place.
    bpy.context.view_layer.update()
    objs = {o.name: o for o in collection.all_objects if o.type == "MESH"}
    # The atlas ships text-label meshes alongside the anatomy: names ending
    # in ".g" (the spike GLB carried 9 of them as loose objects) plus all-caps
    # group titles, all near-zero-thickness text outlines. Left in, they skip
    # the join and export as floating words. Delete them from the blend, not
    # just the dict, so nothing downstream can pick them up.
    labels = [n for n in objs
              if n.endswith(".g") or (n.upper() == n and n.lower() != n)
              or len(objs[n].data.polygons) < 8]
    for name in labels:
        bpy.data.objects.remove(objs.pop(name), do_unlink=True)
    print(f"  {len(objs)} muscle meshes ({len(labels)} label meshes stripped"
          + (f", e.g. {labels[0]}" if labels else "") + ")")
    stand_up(objs)
    return collection, objs


HEAD_LANDMARKS = ("frontalis", "temporalis", "occipito")


def _roots(objs):
    """Topmost ancestors of the meshes — rotating these carries every child,
    including meshes parented to empties that aren't in the mesh dict."""
    roots = set()
    for obj in objs.values():
        while obj.parent is not None:
            obj = obj.parent
        roots.add(obj)
    return roots


def _long_axis(lo, hi):
    spans = [hi[i] - lo[i] for i in range(3)]
    return spans.index(max(spans)), spans


def stand_up(objs):
    """Make the figure stand in the pipeline's Z-up frame, derived from
    measurement rather than assumption: the body's long axis must be Z and a
    head muscle must sit at the top. The atlas arrives lying on its back
    (long axis Y), which left the standing-figure camera framing empty air.
    A no-op when the figure already stands."""
    lo, hi = body_extents(objs)
    axis, spans = _long_axis(lo, hi)
    print(f"  extents before stand_up: spans {[round(s, 3) for s in spans]}, "
          f"long axis {'XYZ'[axis]}")
    if axis != 2:
        from mathutils import Matrix
        # rotate about the axis that is neither the long axis nor Z:
        # long axis Y -> pivot X (+90° maps +Y to +Z), long axis X -> pivot Y
        pivot = 1 - axis
        rot = Matrix.Rotation(math.radians(90), 4, "XYZ"[pivot])
        for obj in _roots(objs):
            obj.matrix_world = rot @ obj.matrix_world
        bpy.context.view_layer.update()
        lo, hi = body_extents(objs)
        axis, spans = _long_axis(lo, hi)
        if axis != 2:
            raise RuntimeError(f"stand_up failed: long axis still {'XYZ'[axis]}")
    # head must be at +Z, not -Z — check a landmark, flip if upside down
    heads = [o for n, o in objs.items()
             if any(t in n.lower() for t in HEAD_LANDMARKS)]
    if heads:
        head_z = sum((o.matrix_world @ Vector(c))[2]
                     for o in heads for c in o.bound_box) / (8 * len(heads))
        rel = (head_z - lo[2]) / (hi[2] - lo[2])
        print(f"  head landmark at {rel:.0%} of body height")
        if rel < 0.5:
            from mathutils import Matrix
            flip = Matrix.Rotation(math.radians(180), 4, "X")
            for obj in _roots(objs):
                obj.matrix_world = flip @ obj.matrix_world
            bpy.context.view_layer.update()
            print("  figure was upside down — flipped")
    else:
        print("  *** no head landmark matched — orientation sign unverified ***")


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
            world = obj.matrix_world @ Vector(corner)
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


def build_figure(collection, objs, index, primary, secondary, colors,
                 target_tris=180_000, floor_z=0.0, head_z=1.76):
    """The whole écorché in one call: import, colour by activation, fit to
    the driver rig's frame, decimate to budget, and join into a single mesh.

    Joining matters. Bone-heat weighting on 731 loose meshes is a coin flip
    per mesh — one failure and a muscle sticks to the world while the body
    moves. One mesh with per-muscle *materials* takes a single heat solve and
    still lets us recolour any muscle independently, which is the only thing
    the separate objects were buying us.
    """
    active = {name: "primary" for key in primary for name in index.get(key, [])}
    for key in secondary:
        for name in index.get(key, []):
            active.setdefault(name, "secondary")
    print(f"  {len(active)} muscle meshes activated")

    # The atlas shares mesh data between the .l and .r of a pair (the probe
    # reported mesh_users=2). Shared data means a material assigned to the
    # left biceps also paints the right one, and modifiers refuse to apply to
    # multi-user data at all — so break the link first.
    for obj in objs.values():
        if obj.data.users > 1:
            obj.data = obj.data.copy()

    for obj in objs.values():
        obj.data.materials.clear()
        obj.data.materials.append(colors[active.get(obj.name, "resting")])

    parent, scale = fit_to_rig(collection, objs, floor_z, head_z)
    decimate(objs, target_tris)

    # An atlas ships most of itself hidden — you look at one system at a time.
    # Those flags survive the append, and a joined object inherits the active
    # object's, which renders a scene containing a perfectly good 192k-face
    # figure as an empty grey backdrop.
    for obj in objs.values():
        obj.hide_render = False
        obj.hide_viewport = False
        obj.hide_set(False)

    bpy.ops.object.select_all(action="DESELECT")
    meshes = list(objs.values())
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.convert(target="MESH")      # bakes the decimate modifiers
    bpy.ops.object.join()
    figure = bpy.context.active_object
    figure.name = "Ecorche"
    figure.hide_render = False
    figure.hide_viewport = False
    # The join keeps the ACTIVE object's transform — an arbitrary muscle whose
    # origin sits wherever the atlas put it (the spike GLB shipped rotated,
    # origin at head height, which is exactly "lying on its back, floating").
    # Unparent keeping the fitted transform, then bake everything into the
    # vertices so the object is identity: local bbox == world bbox for the
    # camera, and the exporter has nothing left to misinterpret.
    bpy.ops.object.select_all(action="DESELECT")
    figure.select_set(True)
    bpy.context.view_layer.objects.active = figure
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.data.objects.remove(parent, do_unlink=True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    lo, hi = body_extents({figure.name: figure})
    print(f"  joined -> {len(figure.data.polygons):,} faces, "
          f"hide_render={figure.hide_render}, "
          f"world z {lo[2]:.3f}..{hi[2]:.3f}")
    if figure.hide_render or len(figure.data.polygons) == 0:
        raise RuntimeError("figure would render empty — refusing to continue")
    return figure


def skin(figure, rig):
    """Bone-heat the figure to the driver rig. Falls back to envelopes rather
    than dying: a slightly stiff joint still renders, a failed solve does not."""
    bpy.ops.object.select_all(action="DESELECT")
    figure.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        print("  skinned with automatic (bone heat) weights")
    except RuntimeError as exc:
        print(f"  bone heat failed ({exc}) — falling back to envelopes")
        bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
    return figure


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
