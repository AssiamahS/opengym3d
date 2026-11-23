"""Process-local compatibility patch for the exact bundled Blender 4.5.11 importer.

No installed file is modified. Upstream mesh.py is Apache-2.0; the generated
patch is accompanied by an importer notice. Reject any other source revision.
"""
import hashlib
from pathlib import Path

MESH_SHA256 = '7c8204165da0b3cf0caf24af665642a7f29572cb4e056939ffca48ee1fb09b93'


def patched_source(source, normalized=True):
    replacements = [
        ('attributes = set({})', 'attributes = {}'),
        ('attributes.update(set(custom_attrs))', 'attributes.update(dict.fromkeys(custom_attrs))'),
    ]
    if normalized:
        old = 'attribute_component_type[attr] = gltf.data.accessors[prim.attributes[attr]].component_type'
        new = '''accessor = gltf.data.accessors[prim.attributes[attr]]
                # BinaryData already decodes normalized integers to float32.
                # Keep that decoded representation through Blender's mesh API.
                attribute_component_type[attr] = (ComponentType.Float
                    if accessor.normalized else accessor.component_type)'''
        replacements.append((old, new))
    for old, new in replacements:
        if source.count(old) != 1:
            raise RuntimeError(f'Importer patch context mismatch: {old}')
        source = source.replace(old, new)
    return source


def apply(normalized=True):
    import bpy
    import io_scene_gltf2
    import io_scene_gltf2.blender.imp.mesh as module
    if bpy.app.version != (4, 5, 11):
        raise RuntimeError('This compatibility patch requires Blender 4.5.11')
    if io_scene_gltf2.bl_info['version'] != (4, 5, 51):
        raise RuntimeError('This compatibility patch requires glTF importer 4.5.51')
    path = Path(module.__file__)
    if hashlib.sha256(path.read_bytes()).hexdigest() != MESH_SHA256:
        raise RuntimeError('Bundled glTF importer SHA256 mismatch; refusing patch')
    source = path.read_text(encoding='utf-8')
    modified = patched_source(source, normalized)
    exec(compile(modified, str(path) + ' [FMS process-local patch]', 'exec'), module.__dict__)
    return source, modified
