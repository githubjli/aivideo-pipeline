"""Headless Blender: fence scene + a rigged humanoid (Mixamo FBX) playing a Mixamo animation,
rendered as flat preview, depth, and an OpenPose joint sequence (JSON) for VACE pose control.

Usage (project root):
  tools/blender/blender-4.2.23-windows-x64/blender.exe -b --python tools/blender/render-rigged-shot.py -- \
      --character productions/math/shared/characters/duo/rig/mom-character.fbx \
      --animation productions/math/shared/characters/duo/rig/anim-waving.fbx \
      --out productions/math/tests/depth/fence-v004-mixamo --frames 49 --shot medium

  --selftest-metarig   builds a Rigify metarig with a scripted turn + wave instead of loading FBX files,
                       so the pose export can be checked before Mixamo assets exist.
Then draw the pose maps with:  python tools/blender/draw-openpose.py <out>/pose/joints.json
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mathscene as ms  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--character", help="Mixamo FBX with skin (T-pose)")
p.add_argument("--animation", help="Mixamo FBX without skin; omitted = use the character's own animation")
p.add_argument("--selftest-metarig", action="store_true")
p.add_argument("--frames", type=int, default=49)
p.add_argument("--width", type=int, default=1280)
p.add_argument("--height", type=int, default=704)
p.add_argument("--fps", type=int, default=24)
p.add_argument("--shot", choices=["medium", "full"], default="medium")
p.add_argument("--height-m", type=float, default=1.65, help="character height in scene units after scaling")
p.add_argument("--facing", type=float, default=0.0, help="initial yaw in degrees; 0 = facing -Y, i.e. toward the default camera side (Mixamo and Rigify both face -Y on import)")
p.add_argument("--anim-start", type=int, default=1, help="first animation frame to use")
p.add_argument("--near", type=float, default=2.0)
p.add_argument("--far", type=float, default=20.0)
args = p.parse_args(argv)

out_dir = os.path.abspath(args.out)
os.makedirs(os.path.join(out_dir, "pose"), exist_ok=True)

scene = ms.reset_scene(args.width, args.height, args.fps, args.frames)
ms.add_ground()
ms.add_lights()
corners = ms.build_fence()
fx, fy = ms.figure_spot()

# ----------------------------------------------------------------------------- character
def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False, ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError(f"no armature in {path}")
    return arms[0], new


def object_height(objs):
    zs = []
    for o in objs:
        if o.type == "MESH":
            for v in o.bound_box:
                zs.append((o.matrix_world @ Vector(v)).z)
    return (max(zs) - min(zs)) if zs else 0.0


if args.selftest_metarig:
    bpy.ops.preferences.addon_enable(module="rigify")
    bpy.ops.object.armature_human_metarig_add()
    arm = bpy.context.active_object
    arm.name = "Metarig"
    rig = "rigify_metarig"
    # metarig is ~2 units tall; scale to target height
    bpy.context.view_layer.update()
    top = max((arm.matrix_world @ b.tail_local).z for b in arm.data.bones)
    arm.scale = (args.height_m / top,) * 3
    # scripted motion: whole body yaw sweep, right arm raised and waving
    arm.rotation_euler = (0, 0, math.radians(args.facing - 30))
    arm.keyframe_insert(data_path="rotation_euler", frame=1)
    arm.rotation_euler = (0, 0, math.radians(args.facing + 30))
    arm.keyframe_insert(data_path="rotation_euler", frame=args.frames)
    bpy.ops.object.mode_set(mode="POSE")
    ua, fa = arm.pose.bones["upper_arm.R"], arm.pose.bones["forearm.R"]
    ua.rotation_mode = fa.rotation_mode = "XYZ"
    for f in range(1, args.frames + 1):
        t = (f - 1) / max(1, args.frames - 1)
        ua.rotation_euler = (math.radians(-110), 0, math.radians(20 * math.sin(t * math.pi * 4)))
        fa.rotation_euler = (math.radians(-40 + 30 * math.sin(t * math.pi * 4)), 0, 0)
        ua.keyframe_insert(data_path="rotation_euler", frame=f)
        fa.keyframe_insert(data_path="rotation_euler", frame=f)
    bpy.ops.object.mode_set(mode="OBJECT")
    # give the armature a visible body for the preview: simple capsules parented to bones would be long; use a bone-shaped mesh via skin? Keep armature display only.
    arm.data.display_type = "STICK"
else:
    if not args.character:
        raise SystemExit("--character is required unless --selftest-metarig")
    arm, char_objs = import_fbx(os.path.abspath(args.character))
    rig = ms.detect_rig(arm)
    h = object_height(char_objs)
    if h > 0:
        s = args.height_m / h
        arm.scale = (arm.scale[0] * s, arm.scale[1] * s, arm.scale[2] * s)
    if args.animation:
        anim_arm, anim_objs = import_fbx(os.path.abspath(args.animation))
        action = anim_arm.animation_data.action if anim_arm.animation_data else None
        if action is None:
            raise RuntimeError("animation FBX has no action")
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = action
        for o in anim_objs:
            bpy.data.objects.remove(o, do_unlink=True)
    if arm.animation_data and arm.animation_data.action:
        a0, a1 = arm.animation_data.action.frame_range
        # Mixamo clips are 30 fps; remap so our 24 fps timeline plays them at natural speed
        scene.render.frame_map_old = 30
        scene.render.frame_map_new = args.fps
        scene.frame_start = int(a0) + args.anim_start - 1
        scene.frame_end = scene.frame_start + args.frames - 1
    arm.rotation_euler = (arm.rotation_euler[0], arm.rotation_euler[1], math.radians(args.facing))

arm.location = (fx, fy, 0)
bpy.context.view_layer.update()

# ----------------------------------------------------------------------------- camera + outputs
if args.shot == "medium":
    ms.add_camera((fx, fy, args.height_m * 0.6), radius=5.0, height=1.6, sweep_deg=40, start_deg=-110, frames=args.frames,
                  center=(fx, fy), descend=0.3)
else:
    ms.add_camera((fx - 1.5, fy - 2.0, 0.6), radius=17.0, height=6.0, sweep_deg=70, start_deg=-100, frames=args.frames,
                  center=(0.0, 0.0), descend=1.5)
ms.setup_outputs(out_dir, near=args.near, far=args.far)

# the scene frame range may be offset for animation clips; the camera keyframes were written on 1..frames, so shift them
cam = scene.camera
if scene.frame_start != 1 and cam.animation_data and cam.animation_data.action:
    for fc in cam.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.co.x += scene.frame_start - 1
            kp.handle_left.x += scene.frame_start - 1
            kp.handle_right.x += scene.frame_start - 1

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "scene.blend"))
ms.export_pose_sequence(arm, rig, os.path.join(out_dir, "pose", "joints.json"), scene.frame_end - scene.frame_start + 1) \
    if scene.frame_start == 1 else None
if scene.frame_start != 1:
    # export with the offset frame range
    import json
    from bpy_extras.object_utils import world_to_camera_view
    seq = []
    for f in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(f)
        pts = ms.joint_world_positions(arm, rig)
        frame = {}
        for name in ms.OPENPOSE_NAMES:
            v = pts.get(name)
            if v is None:
                frame[name] = None
            else:
                co = world_to_camera_view(scene, cam, v)
                frame[name] = [co.x, 1.0 - co.y, bool(co.z > 0)]
        seq.append(frame)
    with open(os.path.join(out_dir, "pose", "joints.json"), "w", encoding="utf-8") as fh:
        json.dump({"width": args.width, "height": args.height, "fps": args.fps, "order": ms.OPENPOSE_NAMES, "frames": seq}, fh)
bpy.ops.render.render(animation=True)
print(f"DONE rig={rig} frames={scene.frame_start}-{scene.frame_end} out={out_dir}")
