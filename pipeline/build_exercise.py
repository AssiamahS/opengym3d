"""Build a rigged, animated exercise figure and export GLB + thumbnail.

Runs headless inside Blender (no addons, no GPU needed):

    blender -b -noaudio -P pipeline/build_exercise.py -- exercises/squat.json site/assets

Reads one exercise spec (metadata + pose keyframes), builds a procedural
humanoid armature with a rigid-skinned capsule body, keys the animation,
then writes <id>.glb (skinned + animated) and <id>.png (Cycles thumbnail
of the mid-rep frame).
"""

import json
import math
import sys

import bpy
from mathutils import Vector

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

LIMB_RADIUS = {
    "pelvis": 0.115, "spine": 0.11, "chest": 0.13, "neck": 0.05, "head": 0.11,
    "upper_arm": 0.045, "forearm": 0.04, "hand": 0.035,
    "thigh": 0.07, "shin": 0.055, "foot": 0.04,
}

# Muscle name (lowercased) -> bones whose body part gets highlighted
MUSCLE_BONES = {
    "quads": ["thigh.L", "thigh.R"], "hamstrings": ["thigh.L", "thigh.R"],
    "glutes": ["pelvis"], "calves": ["shin.L", "shin.R"],
    "core": ["spine"], "abs": ["spine"], "lower back": ["spine"],
    "chest": ["chest"], "lats": ["chest"], "back": ["chest"],
    "traps": ["neck"],
    "shoulders": ["upper_arm.L", "upper_arm.R"],
    "front delts": ["upper_arm.L", "upper_arm.R"],
    "biceps": ["upper_arm.L", "upper_arm.R"],
    "triceps": ["upper_arm.L", "upper_arm.R"],
    "forearms": ["forearm.L", "forearm.R"],
}

BODY_COLOR = (0.44, 0.47, 0.52, 1.0)
PRIMARY_COLOR = (0.85, 0.10, 0.12, 1.0)
SECONDARY_COLOR = (0.95, 0.55, 0.10, 1.0)


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


def make_material(name, color, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.6
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


def highlight_sets(spec):
    primary, secondary = set(), set()
    for group, out in ((spec.get("primary", []), primary),
                       (spec.get("secondary", []), secondary)):
        for muscle in group:
            out.update(MUSCLE_BONES.get(muscle.lower(), []))
    return primary, secondary - primary


def build_body(arm_obj, bones, materials, primary, secondary):
    pieces = []
    for name, (head, tail) in bones.items():
        radius = LIMB_RADIUS[name.split(".")[0]]
        axis = tail - head
        if name == "head":
            bpy.ops.mesh.primitive_uv_sphere_add(
                radius=radius, location=head + axis / 2, segments=16, ring_count=12)
        else:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=radius, depth=axis.length * 0.98,
                location=head + axis / 2, vertices=12)
            bpy.context.object.rotation_mode = "QUATERNION"
            bpy.context.object.rotation_quaternion = axis.to_track_quat("Z", "Y")
        piece = bpy.context.object
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        group = piece.vertex_groups.new(name=name)
        group.add(list(range(len(piece.data.vertices))), 1.0, "REPLACE")
        if name in primary:
            piece.data.materials.append(materials["primary"])
        elif name in secondary:
            piece.data.materials.append(materials["secondary"])
        else:
            piece.data.materials.append(materials["body"])
        pieces.append(piece)

    bpy.ops.object.select_all(action="DESELECT")
    for piece in pieces:
        piece.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "Body"
    body.parent = arm_obj
    body.modifiers.new("Armature", "ARMATURE").object = arm_obj
    return body


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
    cam.location = (1.9, -2.7, 1.5)
    scene.collection.objects.link(cam)
    cam.constraints.new("TRACK_TO").target = target
    scene.camera = cam

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.5
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))
    scene.collection.objects.link(sun)

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.09, 0.10, 0.12, 1.0)
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
        "body": make_material("Body", BODY_COLOR),
        "primary": make_material("Primary", PRIMARY_COLOR, emission=0.6),
        "secondary": make_material("Secondary", SECONDARY_COLOR, emission=0.3),
    }
    primary, secondary = highlight_sets(spec)
    build_body(arm_obj, bones, materials, primary, secondary)
    animate(arm_obj, spec, frame_end)

    setup_render(frame_end)
    scene.render.filepath = f"{out_dir}/{spec['id']}.png"
    bpy.ops.render.render(write_still=True)

    bpy.ops.export_scene.gltf(filepath=f"{out_dir}/{spec['id']}.glb")
    print(f"OK {spec['id']}: {frame_end} frames -> {out_dir}")


main()
