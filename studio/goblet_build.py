"""Isolated MPFB goblet-use proof. Run in pinned Blender; never writes baselines."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from equipment_paths import OUT
GOBLET_RECIPE=dict(center_armature_m=[0,-.33,1.31],palm_lateral_m=.038,
    axial_stagger_m=.018,finger_centerline_radius_m=.028,thumb_centerline_radius_m=.055,
    opposing_halfplane_m=.031)
GRIP_AIM_MODE=os.environ.get('FMS_GRIP_AIM_MODE','bounded-fingers')
if GRIP_AIM_MODE not in ('rest','transport','bounded','bounded-fingers','bounded-fingers-thumb10'):
    raise ValueError('Unknown grip aiming experiment')
FINGER_SWING_LIMITS=(90,85,65) if GRIP_AIM_MODE.startswith('bounded') else (180,180,180)
# Engineering bounds for this synthetic pose, not validated human joint limits.
THUMB_BLEND_FRACTION=.1 if GRIP_AIM_MODE=='bounded-fingers-thumb10' else 0.
THUMB_CORRECTION_CAP_DEGREES=5.


def elbow_position(shoulder,wrist,upper,lower,pole):
    shoulder=np.asarray(shoulder,float);wrist=np.asarray(wrist,float)
    vector=wrist-shoulder;distance=np.linalg.norm(vector)
    if not abs(upper-lower)<distance<upper+lower:
        raise ValueError('Unreachable hand target')
    axis=vector/distance
    direction=np.asarray(pole,float)-shoulder
    direction-=axis*np.dot(axis,direction)
    direction/=np.linalg.norm(direction)
    along=(upper*upper-lower*lower+distance*distance)/(2*distance)
    return shoulder+along*axis+math.sqrt(max(0,upper*upper-along*along))*direction


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def palm_rotation(longitudinal,knuckle_span,side_sign):
    """Map the actual knuckle plane to an inward palm, avoiding a guessed roll."""
    longitudinal=np.asarray(longitudinal,float);longitudinal/=np.linalg.norm(longitudinal)
    normal=np.cross(longitudinal,np.asarray(knuckle_span,float))*side_sign
    normal/=np.linalg.norm(normal)
    rest=np.column_stack([longitudinal,normal,np.cross(longitudinal,normal)])
    target_direction=np.array([0.,-1.,0.]);target_normal=np.array([-side_sign,0.,0.])
    target=np.column_stack([target_direction,target_normal,np.cross(target_direction,target_normal)])
    return target@rest.T


def transport_finger_rotation(current,target_direction,max_swing_degrees=180):
    """Apply only the required swing to the inherited pose, preserving roll.

    Reconstructing each phalanx from world rest axes discards the parent's
    wrist/finger rotation and shears the skin across neighboring influences.
    """
    current=np.asarray(current,float);target=np.array(target_direction,float)
    target/=np.linalg.norm(target);direction=current[:,1]
    cross=np.cross(direction,target);cosine=float(np.clip(np.dot(direction,target),-1,1))
    if cosine>1-1e-12:return current.copy()
    angle=math.acos(cosine)
    limit=math.radians(max_swing_degrees)
    if angle>limit:
        axis=cross/np.linalg.norm(cross) if np.linalg.norm(cross)>1e-10 else current[:,0]
        x,y,z=axis
        skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        return (np.eye(3)+math.sin(limit)*skew+(1-math.cos(limit))*skew@skew)@current
    if cosine< -1+1e-10:
        axis=current[:,0]
        swing=2*np.outer(axis,axis)-np.eye(3)
    else:
        x,y,z=cross
        skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        swing=np.eye(3)+skew+skew@skew/(1+cosine)
    return swing@current


def main():
    import bpy
    from mathutils import Vector,Matrix,Quaternion
    sys.path.insert(0,str(ROOT/'pipeline'))
    import build_exercise as existing
    adapter_hash=sha(Path(__file__))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'build-status.json').write_text(json.dumps(dict(status='BUILDING',technical='pending',visual='pending',movement='unapproved',human_approval='unapproved')))
    source=ROOT/'outputs/bodyweight/squat-technical.glb';source_hash=sha(source)
    protected={str(p.relative_to(ROOT)):sha(p) for folder in ['outputs/bodyweight','outputs/heatsy-repair','outputs/heatsy-attachment','outputs/equipment-use']
               for p in (ROOT/folder).rglob('*') if p.is_file() and p.name not in ('server.log','server-error.log')}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.fps=30
    bpy.ops.import_scene.gltf(filepath=str(source),bone_heuristic='BLENDER')
    rig=next(o for o in scene.objects if o.type=='ARMATURE')
    body=next(o for o in scene.objects if o.type=='MESH')
    scene.frame_start=0;scene.frame_end=90
    # Cache the source before replacing its action. Original source starts at 1/30 s.
    frames=[]
    for i in range(91):
        scene.frame_set(i+1)
        frames.append({p.name:p.matrix_basis.copy() for p in rig.pose.bones})
    scene.frame_set(1)
    rig.animation_data_clear()
    for p in rig.pose.bones:p.matrix_basis=frames[0][p.name]
    bpy.context.view_layer.update()
    cache=OUT/'equipment-cache.json';generator_hash=sha(ROOT/'pipeline/build_exercise.py')
    cached=json.loads(cache.read_text()) if cache.exists() else {}
    reused=(OUT/'dumbbell.glb').exists() and cached.get('generator_sha256')==generator_hash and cached.get('glb_sha256')==sha(OUT/'dumbbell.glb')
    if reused:
        before=set(scene.objects);bpy.ops.import_scene.gltf(filepath=str(OUT/'dumbbell.glb'))
        dumbbell=next(o for o in scene.objects if o not in before and o.type=='MESH')
        dumbbell.name='Dumbbell'
    else:
        steel=existing.make_material('Equipment steel',existing.STEEL_COLOR,roughness=.35)
        iron=existing.make_material('Equipment heads',existing.IRON_COLOR,roughness=.6)
        dumbbell=existing.build_dumbbell('Dumbbell',steel,iron)
        bpy.ops.object.select_all(action='DESELECT');dumbbell.select_set(True)
        bpy.context.view_layer.objects.active=dumbbell
        bpy.ops.export_scene.gltf(filepath=str(OUT/'dumbbell.glb'),use_selection=True,export_format='GLB',export_animations=False)
        cache.write_text(json.dumps(dict(generator_sha256=generator_hash,glb_sha256=sha(OUT/'dumbbell.glb')),indent=2))
    axis=Vector((0,0,1));center=Vector(GOBLET_RECIPE['center_armature_m'])
    dumbbell.rotation_mode='QUATERNION';dumbbell.rotation_quaternion=Vector((1,0,0)).rotation_difference(axis)
    dumbbell.location=rig.matrix_world@center
    arm_names=[p.name for p in rig.pose.bones if any(p.name.startswith(n) for n in ('clavicle','shoulder','upperarm','lowerarm','wrist','metacarpal','finger'))]
    for side,sign in [('L',1),('R',-1)]:
        suffix='.'+side;wrist=rig.pose.bones['wrist'+suffix]
        restdir=(rig.data.bones['finger3-1'+suffix].head_local-wrist.bone.head_local).normalized()
        across=rig.data.bones['finger2-1'+suffix].head_local-rig.data.bones['finger5-1'+suffix].head_local
        q=Matrix(palm_rotation(restdir,across,sign).tolist()).to_quaternion()
        rest_palm=(wrist.bone.head_local+sum((rig.data.bones[f'finger{f}-1'+suffix].head_local for f in (2,3,4,5)),Vector())/4)/2
        contact=center+Vector((sign*GOBLET_RECIPE['palm_lateral_m'],0,sign*GOBLET_RECIPE['axial_stagger_m']))
        target=contact-q@(rest_palm-wrist.bone.head_local)
        shoulder=rig.pose.bones['upperarm01'+suffix].head.copy()
        upper=sum(rig.data.bones[n+suffix].length for n in ('upperarm01','upperarm02'))
        lower=sum(rig.data.bones[n+suffix].length for n in ('lowerarm01','lowerarm02'))
        elbow=Vector(elbow_position(shoulder,target,upper,lower,shoulder+Vector((sign*.1,-.12,-.5))))
        for prefix,direction in [('upperarm',(elbow-shoulder).normalized()),('lowerarm',(target-elbow).normalized())]:
            for segment in ('01','02'):
                existing.aim_bone(rig.pose.bones[prefix+segment+suffix],direction,0)
        wrist.rotation_mode='QUATERNION'
        wrist.matrix=Matrix.Translation(wrist.head)@(q@wrist.bone.matrix_local.to_quaternion()).to_matrix().to_4x4()
        bpy.context.view_layer.update()
        # Curl around the vertical shaft with the existing procedural finger routine.
    for side,sign in [('L',1),('R',-1)]:
        for finger in range(1,6):
            for segment in (1,2,3):
                name=f'finger{finger}-{segment}.{side}'
                bone=rig.pose.bones[name]
                root=bone.head.copy();radial=Vector((root.x-center.x,root.y-center.y,0))
                distance=radial.length;radial.normalize()
                radius=GOBLET_RECIPE['thumb_centerline_radius_m' if finger==1 else 'finger_centerline_radius_m']
                length=bone.bone.length
                if distance>radius+length:
                    tip=root-radial*length
                else:
                    cosine=max(-1,min(1,(distance*distance+radius*radius-length*length)/(2*distance*radius)))
                    turn=-sign if finger!=1 else sign
                    direction=Quaternion(axis,turn*math.acos(cosine))@radial
                    tip=Vector((center.x,center.y,root.z))+direction*radius
                # Two simultaneous grips cannot each occupy the full cylinder.
                # Keep finger centerlines on opposing sides, preserving link
                # length, instead of allowing the fingertips to interleave.
                if sign*(tip.x-center.x)<GOBLET_RECIPE['opposing_halfplane_m']:
                    target_x=center.x+sign*GOBLET_RECIPE['opposing_halfplane_m']
                    dx=target_x-root.x
                    if abs(dx)<length:
                        dy=math.sqrt(max(0,length*length-dx*dx))
                        tip=Vector((target_x,root.y+math.copysign(dy,tip.y-root.y),root.z))
                direction=(tip-root).normalized()
                if GRIP_AIM_MODE=='rest' or (GRIP_AIM_MODE.startswith('bounded-fingers') and finger==1):
                    inherited=np.array(bone.matrix.to_quaternion().to_matrix())
                    existing.aim_bone(bone,direction,0)
                    if THUMB_BLEND_FRACTION:
                        previous=bone.matrix.to_quaternion()
                        proposed=Matrix(transport_finger_rotation(inherited,direction,FINGER_SWING_LIMITS[segment-1]).tolist()).to_quaternion()
                        angle=2*math.acos(min(1,abs(previous.dot(proposed))))
                        fraction=min(THUMB_BLEND_FRACTION,math.radians(THUMB_CORRECTION_CAP_DEGREES)/max(angle,1e-12))
                        bone.matrix=Matrix.Translation(root)@previous.slerp(proposed,fraction).to_matrix().to_4x4()
                        bpy.context.view_layer.update()
                        bone.keyframe_insert('rotation_quaternion',frame=0)
                else:
                    rotation=transport_finger_rotation(np.array(bone.matrix.to_quaternion().to_matrix()),direction,FINGER_SWING_LIMITS[segment-1])
                    bone.rotation_mode='QUATERNION'
                    bone.matrix=Matrix.Translation(root)@Matrix(rotation.tolist()).to_4x4()
                    bpy.context.view_layer.update()
                    bone.keyframe_insert('rotation_quaternion',frame=0)
    fixed={n:rig.pose.bones[n].matrix_basis.copy() for n in arm_names}
    chest=rig.pose.bones['spine01'];chest0=chest.matrix.copy()
    local_equipment=chest0.inverted()@rig.matrix_world.inverted()@dumbbell.matrix_world
    rig.animation_data_clear();dumbbell.animation_data_clear()
    for frame in range(91):
        scene.frame_set(frame)
        for p in rig.pose.bones:
            p.matrix_basis=fixed[p.name] if p.name in fixed else frames[frame][p.name]
            p.rotation_mode='QUATERNION'
            for channel in ('location','rotation_quaternion','scale'):p.keyframe_insert(channel,frame=frame,group=p.name)
        bpy.context.view_layer.update()
        dumbbell.matrix_world=rig.matrix_world@chest.matrix@local_equipment
        for channel in ('location','rotation_quaternion','scale'):dumbbell.keyframe_insert(channel,frame=frame)
    for owner in (rig,dumbbell):
        for curve in owner.animation_data.action.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(OUT/'goblet.glb'),export_format='GLB',export_animations=True,
        export_animation_mode='SCENE',export_frame_range=True,export_force_sampling=True,export_skins=True,export_morph=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'goblet.blend'))
    equipment=dict(id='dumbbell',name='Procedural dumbbell',description='One reusable fixed dumbbell. Inspection scale is visual configuration, not a load or technique prescription.',
        dimensions=dict(length=.251,handleRadius=.017,headRadius=.055),
        contactPoints=[dict(id='shaft-site-A',position=[.018,.017,0],kind='nominal inspection surface'),dict(id='shaft-site-B',position=[-.018,-.017,0],kind='nominal inspection surface')],
        compatibleVariations=['goblet-squat-experimental'],geometry='dumbbell.glb',generator='pipeline/build_exercise.py:build_dumbbell',license='MIT')
    variation=dict(id='goblet-squat-experimental',name='Experimental dumbbell goblet squat',equipment='dumbbell',movementSource='motions/synthetic/squat.json',
        demonstration='goblet.glb',duration=3,start_time=0,end_time=3,fps=30,frames=91,gripRecipe=dict(**GOBLET_RECIPE,aim_mode=GRIP_AIM_MODE,finger_swing_limits_degrees=FINGER_SWING_LIMITS,thumb_blend_fraction=THUMB_BLEND_FRACTION,thumb_correction_cap_degrees=THUMB_CORRECTION_CAP_DEGREES,thumb_baseline_preserved=GRIP_AIM_MODE in ('rest','bounded-fingers')),
        setupSteps=['Inspect the vertical dumbbell held in front of the chest.','Both hands close around the shaft; elbows point down.','Feet retain the synthetic bodyweight fixture placement.'],
        directionCues=['Lower with the equipment held close to the chest.','Return to the starting pose; the preview loops.'],
        technical='pending',visual='partial',movement='unapproved',humanApproval='unapproved',
        visualLimitations=['Thumb placement and web pinching remain unresolved; the selected bounded-fingers mode preserves the baseline thumb pose.','Finger shape is improved but remains a synthetic technical demonstration, not approved anatomy or exercise instruction.'] if GRIP_AIM_MODE=='bounded-fingers' else ['Experimental alternative grip pose; not selected or visually approved.'],
        scope='Already-held setup posture plus complete repetition; no pickup, load prescription or approved exercise instruction.')
    (OUT/'equipment.json').write_text(json.dumps(equipment,indent=2))
    (OUT/'variation.json').write_text(json.dumps(variation,indent=2))
    import shutil
    shutil.copytree(ROOT/'outputs/bodyweight/licenses',OUT/'licenses',dirs_exist_ok=True)
    shutil.copy2(ROOT/'outputs/bodyweight/ATTRIBUTION.md',OUT/'ATTRIBUTION.md')
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    if sha(Path(__file__))!=adapter_hash:
        raise RuntimeError('Grip builder changed during generation; rebuild from a frozen source')
    (OUT/'build-status.json').write_text(json.dumps(dict(status='GENERATED_NOT_VALIDATED',technical='pending',visual='partial',movement='unapproved',human_approval='unapproved',
        source_sha256=source_hash,motion_sha256=sha(ROOT/'motions/synthetic/squat.json'),generator_sha256=generator_hash,
        adapter_sha256=adapter_hash,grip_aim_mode=GRIP_AIM_MODE,finger_swing_limits_degrees=FINGER_SWING_LIMITS,glb_sha256=sha(OUT/'goblet.glb'),equipment_sha256=sha(OUT/'dumbbell.glb'),protected_files=len(protected),protected_unchanged=True,
        blender=bpy.app.version_string,equipment_cache_reused=reused,geometry_regenerated_per_exercise=not reused),indent=2))
    print('GENERATED',sha(OUT/'goblet.glb'))


if __name__=='__main__':main()
