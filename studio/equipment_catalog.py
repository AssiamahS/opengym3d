"""Standalone equipment catalog: reuse procedural geometry, never build motion.

Run with the pinned Blender. Local coordinates in metadata are glTF metres/Y-up.
"""
import hashlib
import json
import math
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from equipment_paths import OUT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def definitions():
    """Equipment descriptions do not infer compatible exercise techniques."""
    items = []
    for kind, description, dimensions, points in (
        ('dumbbell', 'Fixed dumbbell with a straight shaft and two polygonal heads.',
         dict(length=.251, width=.110, height=.110, handleRadius=.017, handleLength=.150),
         [[.018, .017, 0], [-.018, -.017, 0]]),
        ('kettlebell', 'Procedural spherical bell and rounded loop handle; no exercise variation has been validated.',
         dict(length=.190, width=.190, height=.306, handleTubeRadius=.014, handleMajorRadius=.062),
         [[-.020, math.sqrt(.076**2-.020**2), 0], [.020, math.sqrt(.076**2-.020**2), 0]]),
        ('barbell', 'Straight bar with two plates and collars; no exercise variation has been validated.',
         dict(length=1.600, width=.380, height=.380, handleRadius=.014, plateRadius=.190),
         [[-.250, .014, 0], [.250, .014, 0]]),
    ):
        items.append(dict(
            id=kind, name=kind.capitalize(), description=description,
            dimensions=dimensions, units='metres', geometry=kind+'.glb', thumbnail=kind+'.webp',
            configuration=dict(scale=dict(min=.75, max=1.25, default=1., scope='inspection only'),
                               finishes=['original', 'steel', 'dark'], massKg=None,
                               note='Visual configuration only; no load rating or automatic technique substitution.'),
            contactPoints=[dict(id=f'{kind}-site-{i+1}', position=p, kind='nominal inspection surface',
                                gripAxis=[1, 0, 0]) for i,p in enumerate(points)],
            compatibleVariations=['goblet-squat-experimental'] if kind=='dumbbell' else [],
            generator=f'pipeline/build_exercise.py:build_{kind}', license='MIT',
            provenance=dict(source='Existing OpenGym3D-derived procedural generator',
                            sourcePath='pipeline/build_exercise.py', licensePath='licenses/PROJECT-MIT.txt',
                            note='Generated geometry; no branded product or certified dimensions/load rating.')))
    return items


def validate_catalog(catalog):
    assert catalog['schema']=='equipment-catalog/1'
    assert {i['id'] for i in catalog['items']}=={'dumbbell','kettlebell','barbell'}
    assert len(catalog['items'])==3
    for item in catalog['items']:
        assert item['geometry']==item['id']+'.glb' and item['thumbnail']==item['id']+'.webp'
        assert item['license']=='MIT' and item['provenance']['sourcePath']=='pipeline/build_exercise.py'
        assert all(math.isfinite(v) and v>0 for v in item['dimensions'].values())
        assert item['compatibleVariations']==(['goblet-squat-experimental'] if item['id']=='dumbbell' else [])
        assert len(item['contactPoints'])>=2
        for contact in item['contactPoints']:
            assert len(contact['position'])==3 and all(math.isfinite(v) for v in contact['position'])
            assert abs(sum(v*v for v in contact['gripAxis'])-1)<1e-8


def main():
    import bpy
    from mathutils import Vector
    import shutil
    sys.path.insert(0, str(ROOT/'pipeline'))
    import build_exercise as generator
    OUT.mkdir(parents=True,exist_ok=True)
    generator_hash=sha(ROOT/'pipeline/build_exercise.py')
    cache_path=OUT/'catalog-cache.json'
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    records=[]
    items=definitions()
    for item in items:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene=bpy.context.scene
        path=OUT/item['geometry']
        old=cache.get(item['id'],{})
        # Accept the already validated standalone dumbbell cache from the proof.
        if item['id']=='dumbbell' and (OUT/'equipment-cache.json').exists():
            old=json.loads((OUT/'equipment-cache.json').read_text())
        reused=path.exists() and old.get('generator_sha256')==generator_hash and old.get('glb_sha256')==sha(path)
        if reused:
            bpy.ops.import_scene.gltf(filepath=str(path))
            obj=next(o for o in scene.objects if o.type=='MESH')
        else:
            steel=generator.make_material('Equipment steel',generator.STEEL_COLOR,roughness=.35)
            iron=generator.make_material('Equipment heads',generator.IRON_COLOR,roughness=.6)
            obj=getattr(generator,'build_'+item['id'])(item['name'],steel,iron)
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
            bpy.context.view_layer.objects.active=obj
            bpy.ops.export_scene.gltf(filepath=str(path),use_selection=True,export_format='GLB',export_animations=False)
        bounds=[obj.matrix_world@Vector(c) for c in obj.bound_box]
        lo=Vector([min(c[i] for c in bounds) for i in range(3)])
        hi=Vector([max(c[i] for c in bounds) for i in range(3)])
        center=(lo+hi)/2
        extent=max(hi-lo)
        item['bounds']=dict(min=[lo.x,lo.z,-hi.y],max=[hi.x,hi.z,-lo.y])
        item['sha256']=sha(path)
        item['provenance'].update(generatorSha256=generator_hash,checkpoint='ad14fa7',blender=bpy.app.version_string)
        # Thumbnail is rendered from the same geometry as the exported GLB.
        camera_data=bpy.data.cameras.new('Catalog camera');camera=bpy.data.objects.new('Catalog camera',camera_data)
        scene.collection.objects.link(camera);scene.camera=camera
        camera_data.type='ORTHO';camera_data.ortho_scale=extent*1.3
        camera.location=center+Vector((.55,-1,.45))*extent*3
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.world=bpy.data.worlds.new('Catalog world');scene.world.use_nodes=True
        scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.075,.105,1)
        scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
        for name,offset,energy in [('Key',(1,-2,3),120),('Fill',(-2,-1,1),70)]:
            data=bpy.data.lights.new(name,'AREA');data.energy=energy*extent*extent;data.shape='DISK';data.size=extent*2
            light=bpy.data.objects.new(name,data);scene.collection.objects.link(light)
            light.location=center+Vector(offset)*extent
            light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
        scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
        scene.render.resolution_x=320;scene.render.resolution_y=240;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/(item['id']+'.png'))
        bpy.ops.render.render(write_still=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',scene.render.filepath,'-c:v','libwebp',
                        '-quality','82',str(OUT/item['thumbnail'])],check=True)
        item['thumbnailSha256']=sha(OUT/item['thumbnail'])
        cache[item['id']]=dict(generator_sha256=generator_hash,glb_sha256=item['sha256'])
        records.append(dict(id=item['id'],geometry_reused=reused,bytes=path.stat().st_size,
                            thumbnail_bytes=(OUT/item['thumbnail']).stat().st_size))
    catalog=dict(schema='equipment-catalog/1',items=items,scope='Inspection assets; technique compatibility is explicit and separately validated.')
    validate_catalog(catalog)
    (OUT/'licenses').mkdir(exist_ok=True)
    shutil.copy2(ROOT/'LICENSE',OUT/'licenses/PROJECT-MIT.txt')
    (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2))
    cache_path.write_text(json.dumps(cache,indent=2))
    (OUT/'catalog-build.json').write_text(json.dumps(dict(status='GENERATED_NOT_VALIDATED',items=records,
        generator_sha256=generator_hash,builder_sha256=sha(__file__),exercise_build_invoked=False),indent=2))
    print(json.dumps(records,indent=2))


if __name__=='__main__':main()
