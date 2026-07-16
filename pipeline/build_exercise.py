"""Build a rigged, animated exercise figure and export GLB + thumbnail.

Runs headless inside Blender (no addons, no GPU needed):

    blender -b -noaudio -P pipeline/build_exercise.py -- exercises/squat.json site/assets

Reads one exercise spec (metadata + pose keyframes), builds one smooth
metaball-fused body over a procedural armature, skins it with distance
weights (joints bend instead of breaking), paints active muscle regions
straight onto the surface (primary red / secondary orange), keys the
animation, then writes <id>.glb and <id>.png (mid-rep frame).
"""

import json
import math
import sys

import bpy
from mathutils import Vector, geometry

# Rest skeleton, world coords, character faces -Y. name: (head, tail)
BONES = {
    "pelvis":      ((0.00, 0.0, 0.95), (0.00, 0.0, 1.06)),
    "spine":       ((0.00, 0.0, 1.06), (0.00, 0.0, 1.30)),
    "chest":       ((0.00, 0.0, 1.30), (0.00, 0.0, 1.50)),
    "neck":        ((0.00, 0.0, 1.50), (0.00, 0.0, 1.58)),
    "head":        ((0.00, 0.0, 1.58), (0.00, 0.0, 1.76)),
    "upper_arm.L": ((0.18, 0.0, 1.46), (0.42, 0.0, 1.46)),
    "forearm.L":   ((0.42, 0.0, 1.46), (0.66, 0.0, 1.46)),
    "hand.L":      ((0.66, 0.0, 1.46), (0.78, 0.0, 1.46)),
    "thigh.L":     ((0.10, 0.0, 0.95), (0.10, 0.0, 0.52)),
    "shin.L":      ((0.10, 0.0, 0.52), (0.10, 0.0, 0.09)),
    "foot.L":      ((0.10, 0.0, 0.09), (0.10, -0.18, 0.02)),
}

PARENTS = {
    "spine": "pelvis", "chest": "spine", "neck": "chest", "head": "neck",
    "upper_arm.L": "chest", "forearm.L": "upper_arm.L", "hand.L": "forearm.L",
    "thigh.L": "pelvis", "shin.L": "thigh.L", "foot.L": "shin.L",
}

# Metaball skin: bone -> (start radius, end radius). Dense chains along each
# bone guarantee the fields overlap and fuse into one continuous body.
BODY_RADII = {
    "pelvis":      (0.105, 0.105),
    "spine":       (0.092, 0.102),
    "chest":       (0.108, 0.122),
    "neck":        (0.052, 0.052),
    "upper_arm.L": (0.056, 0.046),
    "forearm.L":   (0.046, 0.038),
    "thigh.L":     (0.088, 0.060),
    "shin.L":      (0.056, 0.042),
    "foot.L":      (0.045, 0.040),
}

# single placed balls: skull, jaw, shoulder caps, hip blend, hands
BODY_EXTRA_BALLS = [
    ((0.00, 0.00, 1.70), 0.100, "head"),
    ((0.00, -0.015, 1.61), 0.072, "head"),
    ((0.150, 0.0, 1.465), 0.068, "upper_arm.L"),
    ((-0.150, 0.0, 1.465), 0.068, "upper_arm.R"),
    ((0.085, 0.0, 0.94), 0.075, "thigh.L"),
    ((-0.085, 0.0, 0.94), 0.075, "thigh.R"),
    ((0.71, 0.0, 1.46), 0.044, "hand.L"),
    ((-0.71, 0.0, 1.46), 0.044, "hand.R"),
]

# exercise-metadata muscle names (lowercased) -> bones whose surface region
# gets painted red/orange
MUSCLE_BONES = {
    "quads": ["thigh.L", "thigh.R"], "hamstrings": ["thigh.L", "thigh.R"],
    "glutes": ["pelvis"], "calves": ["shin.L", "shin.R"],
    "core": ["spine"], "abs": ["spine"], "lower back": ["spine"],
    "chest": ["chest"], "lats": ["chest"], "back": ["chest"],
    "traps": ["neck"],
    "shoulders": ["upper_arm.L", "upper_arm.R"],
    "front delts": ["upper_arm.L", "upper_arm.R"],
    "delts": ["upper_arm.L", "upper_arm.R"],
    "biceps": ["upper_arm.L", "upper_arm.R"],
    "triceps": ["upper_arm.L", "upper_arm.R"],
    "forearms": ["forearm.L", "forearm.R"],
}

SKIN_COLOR = (0.70, 0.72, 0.76, 1.0)
PRIMARY_COLOR = (0.80, 0.08, 0.10, 1.0)
SECONDARY_COLOR = (0.93, 0.50, 0.08, 1.0)


def mirror_name(name):
    return name[:-2] + ".R" if name.endswith(".L") else name


def full_skeleton():
    bones, parents = {}, {}
    for name, (head, tail) in BONES.items():
        bones[name] = (Vector(head), Vector(tail))
        if name.endswith(".L"):
            r = mirror_name(name)
            bones[r] = (Vector((-head[0], head[1], head[2])),
                        Vector((-tail[0], tail[1], tail[2])))
    for child, parent in PARENTS.items():
        parents[child] = parent
        if child.endswith(".L"):
            parents[mirror_name(child)] = mirror_name(parent)
    return bones, parents


def make_material(name, color, emission=0.0, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = color
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def build_armature(bones, parents):
    arm_data = bpy.data.armatures.new("Rig")
    arm_obj = bpy.data.objects.new("Rig", arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail) in bones.items():
        eb = arm_data.edit_bones.new(name)
        eb.head, eb.tail, eb.roll = head, tail, 0.0
    for child, parent in parents.items():
        arm_data.edit_bones[child].parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def skin_to_bones(mesh_obj, bones):
    """Distance-based smooth skinning; returns each vertex's dominant bone."""
    groups = {name: mesh_obj.vertex_groups.new(name=name) for name in bones}
    dominant = {}
    for v in mesh_obj.data.vertices:
        dists = []
        for name, (head, tail) in bones.items():
            closest, t = geometry.intersect_point_line(v.co, head, tail)
            t = max(0.0, min(1.0, t))
            closest = head + (tail - head) * t
            dists.append(((v.co - closest).length, name))
        dists.sort()
        (d1, b1), (d2, b2) = dists[0], dists[1]
        dominant[v.index] = b1
        if d2 > d1 * 1.6:                       # clearly one bone's territory
            groups[b1].add([v.index], 1.0, "REPLACE")
        else:                                    # joint area: blend
            w1 = 1.0 / max(d1, 1e-4) ** 4
            w2 = 1.0 / max(d2, 1e-4) ** 4
            total = w1 + w2
            groups[b1].add([v.index], w1 / total, "REPLACE")
            groups[b2].add([v.index], w2 / total, "REPLACE")
    return dominant


def paint_muscles(body, dominant, primary_bones, secondary_bones):
    """Assign red/orange material to faces whose region belongs to an
    active muscle's bone. Materials: 0 skin, 1 primary, 2 secondary."""
    for poly in body.data.polygons:
        votes = [dominant[i] for i in poly.vertices]
        top = max(set(votes), key=votes.count)
        if top in primary_bones:
            poly.material_index = 1
        elif top in secondary_bones:
            poly.material_index = 2


def build_smooth_body(arm_obj, bones, materials, primary_bones, secondary_bones):
    mball = bpy.data.metaballs.new("BodyMeta")
    mball.resolution = 0.035
    meta_obj = bpy.data.objects.new("BodyMeta", mball)
    bpy.context.scene.collection.objects.link(meta_obj)
    for name, (r_start, r_end) in BODY_RADII.items():
        names = [name, mirror_name(name)] if name.endswith(".L") else [name]
        for bone in names:
            head, tail = bones[bone]
            length = (tail - head).length
            steps = max(3, int(length / 0.035) + 1)
            for i in range(steps):
                frac = i / (steps - 1)
                el = mball.elements.new()
                el.co = head + (tail - head) * frac
                el.radius = r_start + (r_end - r_start) * frac
    for co, radius, _bone in BODY_EXTRA_BALLS:
        el = mball.elements.new()
        el.co = Vector(co)
        el.radius = radius

    bpy.ops.object.select_all(action="DESELECT")
    meta_obj.select_set(True)
    bpy.context.view_layer.objects.active = meta_obj
    bpy.ops.object.convert(target="MESH")
    body = bpy.context.object
    body.name = "Body"

    dec = body.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = 0.5
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bpy.ops.object.shade_smooth()

    body.data.materials.append(materials["skin"])
    body.data.materials.append(materials["primary"])
    body.data.materials.append(materials["secondary"])
    dominant = skin_to_bones(body, bones)
    paint_muscles(body, dominant, primary_bones, secondary_bones)

    body.parent = arm_obj
    body.modifiers.new("Armature", "ARMATURE").object = arm_obj
    return body


def highlight_sets(spec):
    primary, secondary = set(), set()
    for group, out in ((spec.get("primary", []), primary),
                       (spec.get("secondary", []), secondary)):
        for muscle in group:
            out.update(MUSCLE_BONES.get(muscle.lower(), []))
    return primary, secondary - primary


def pose_targets(kf_bones):
    """Expand 'thigh.*' wildcards into mirrored .L/.R transforms."""
    for name, xf in kf_bones.items():
        rot = xf.get("rot", [0, 0, 0])
        loc = xf.get("loc")
        if name.endswith(".*"):
            base = name[:-2]
            yield base + ".L", rot, loc
            mrot = [rot[0], -rot[1], -rot[2]]
            mloc = [-loc[0], loc[1], loc[2]] if loc else None
            yield base + ".R", mrot, mloc
        else:
            yield name, rot, loc


def animate(arm_obj, spec, frame_end):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    for kf in spec["keyframes"]:
        frame = 1 + round(kf["t"] * (frame_end - 1))
        for bone_name, rot, loc in pose_targets(kf.get("bones", {})):
            pb = arm_obj.pose.bones[bone_name]
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = [math.radians(a) for a in rot]
            pb.keyframe_insert("rotation_euler", frame=frame)
            if loc is not None:
                # spec gives world-space offsets; convert to bone-local space
                rest = pb.bone.matrix_local.to_3x3().inverted()
                pb.location = rest @ Vector(loc)
                pb.keyframe_insert("location", frame=frame)
    bpy.ops.object.mode_set(mode="OBJECT")


def setup_render(frame_end):
    scene = bpy.context.scene
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0, 0, 0.85)
    scene.collection.objects.link(target)

    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    cam.location = (1.7, -2.6, 1.35)
    scene.collection.objects.link(cam)
    cam.constraints.new("TRACK_TO").target = target
    scene.camera = cam

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 4.5
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))
    scene.collection.objects.link(sun)

    fill_data = bpy.data.lights.new("Fill", "SUN")
    fill_data.energy = 1.2
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.rotation_euler = (math.radians(60), math.radians(20), math.radians(-140))
    scene.collection.objects.link(fill)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.94, 0.95, 0.96, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.render.resolution_x = scene.render.resolution_y = 512
    scene.frame_set(1 + (frame_end - 1) // 2)  # mid-rep = most telling pose


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, out_dir = argv[0], argv[1]
    with open(spec_path) as f:
        spec = json.load(f)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = spec.get("fps", 30)
    frame_end = round(spec.get("duration", 2.0) * scene.render.fps)
    scene.frame_start, scene.frame_end = 1, frame_end

    bones, parents = full_skeleton()
    arm_obj = build_armature(bones, parents)
    materials = {
        "skin": make_material("Skin", SKIN_COLOR),
        "primary": make_material("Primary", PRIMARY_COLOR, emission=0.3),
        "secondary": make_material("Secondary", SECONDARY_COLOR, emission=0.15),
    }
    primary_bones, secondary_bones = highlight_sets(spec)
    build_smooth_body(arm_obj, bones, materials, primary_bones, secondary_bones)
    animate(arm_obj, spec, frame_end)

    setup_render(frame_end)
    scene.render.filepath = f"{out_dir}/{spec['id']}.png"
    bpy.ops.render.render(write_still=True)

    bpy.ops.export_scene.gltf(filepath=f"{out_dir}/{spec['id']}.glb")
    print(f"OK {spec['id']}: {frame_end} frames -> {out_dir}")


main()
