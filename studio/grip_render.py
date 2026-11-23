"""Matched exported grip views; all writes limited to the new library lane."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'studio'))
from equipment_paths import output_path
args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]).resolve();out=output_path(args[1])
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(source),bone_heuristic='BLENDER')
scene=bpy.context.scene;scene.frame_set(0)
camera_data=bpy.data.cameras.new('Grip inspection');camera=bpy.data.objects.new('Grip inspection',camera_data)
scene.collection.objects.link(camera);scene.camera=camera
target=Vector((0,-.33,1.31));camera.location=(.48,-1.3,1.47)
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.type='ORTHO';camera_data.ortho_scale=.42
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.25
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='WORLD'
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('Grip background');scene.world.color=(.035,.045,.06)
scene.render.image_settings.file_format='PNG'
for size in (960,320):
    scene.render.resolution_x=size;scene.render.resolution_y=size;scene.render.resolution_percentage=100
    scene.render.filepath=str(out/f'grip-{size}.png')
    bpy.ops.render.render(write_still=True)
