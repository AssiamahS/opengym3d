"""Probe MPFB2 headless: install the extension, build a muscular male human
with the default MakeHuman rig, and dump bone hierarchy + vertex groups.
Run in CI; the output drives the retargeting map in build_exercise.py.

    blender -b -noaudio --python-exit-code 1 -P pipeline/probe_mpfb.py -- probe_out
"""

import importlib
import os
import sys
import zipfile
import urllib.request

import bpy

MPFB_URL = ("https://extensions.blender.org/download/"
            "sha256:b5cdc8b08147e0c6463e4faa01147491b13a0b062f73415363f029debd11c934/"
            "add-on-mpfb-v2.0.16.zip?repository=%2Fapi%2Fv1%2Fextensions%2F"
            "&blender_version_min=4.2.0")

out_dir = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out_dir, exist_ok=True)


def ensure_mpfb():
    version = f"{bpy.app.version[0]}.{bpy.app.version[1]}"
    ext_root = os.path.expanduser(f"~/.config/blender/{version}/extensions/user_default")
    dest = os.path.join(ext_root, "mpfb")
    if not os.path.isdir(dest):
        os.makedirs(ext_root, exist_ok=True)
        zpath = "/tmp/mpfb.zip"
        if not os.path.exists(zpath):
            print("downloading mpfb…")
            req = urllib.request.Request(          # site 403s python's default UA
                MPFB_URL, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
            with urllib.request.urlopen(req) as resp, open(zpath, "wb") as f:
                f.write(resp.read())
        with zipfile.ZipFile(zpath) as z:
            names = z.namelist()
            if any(n.split("/")[0] == "blender_manifest.toml" for n in names):
                z.extractall(dest)          # manifest at zip root
            else:
                z.extractall(ext_root)      # zip already wraps a folder
                top = names[0].split("/")[0]
                if top != "mpfb":
                    os.rename(os.path.join(ext_root, top), dest)
    bpy.ops.preferences.addon_enable(module="bl_ext.user_default.mpfb")


def dynamic_import(absolute_package_str, key):
    """MPFB's own quirk: extensions land at unknown module paths."""
    for amod in list(sys.modules):
        if amod.endswith(absolute_package_str):
            mod = importlib.import_module(amod)
            return getattr(mod, key)
    raise ValueError(f"no module ending in {absolute_package_str}")


ensure_mpfb()
HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
HumanObjectProperties = dynamic_import("mpfb.entities.objectproperties",
                                       "HumanObjectProperties")
TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")

basemesh = HumanService.create_human()
HumanObjectProperties.set_value("gender", 1.0, entity_reference=basemesh)
HumanObjectProperties.set_value("muscle", 0.9, entity_reference=basemesh)
HumanObjectProperties.set_value("weight", 0.55, entity_reference=basemesh)
TargetService.reapply_macro_details(basemesh)
rig = HumanService.add_builtin_rig(basemesh, "default")

print("=== BONES ===")
for b in rig.data.bones:
    parent = b.parent.name if b.parent else "-"
    head = tuple(round(c, 3) for c in b.head_local)
    tail = tuple(round(c, 3) for c in b.tail_local)
    print(f"BONE {b.name} parent={parent} head={head} tail={tail}")
print("=== VGROUPS ===")
print(sorted(g.name for g in basemesh.vertex_groups))
print(f"=== MESH verts={len(basemesh.data.vertices)} "
      f"dims={tuple(round(c, 2) for c in basemesh.dimensions)} ===")

# quick look render
scene = bpy.context.scene
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
cam.location = (1.7, -2.6, 1.35)
scene.collection.objects.link(cam)
target = bpy.data.objects.new("T", None)
target.location = (0, 0, 0.9)
scene.collection.objects.link(target)
cam.constraints.new("TRACK_TO").target = target
scene.camera = cam
sun_data = bpy.data.lights.new("Sun", "SUN")
sun_data.energy = 4.0
sun = bpy.data.objects.new("Sun", sun_data)
sun.rotation_euler = (0.9, -0.25, 0.5)
scene.collection.objects.link(sun)
world = bpy.data.worlds.new("W")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.94, 0.95, 0.96, 1)
scene.world = world
scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.render.resolution_x = scene.render.resolution_y = 512
scene.render.filepath = os.path.join(out_dir, "probe.png")
bpy.ops.render.render(write_still=True)
print("PROBE OK")
