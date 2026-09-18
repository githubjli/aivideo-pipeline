"""Shared Blender helpers for the math-lesson shots: fence enclosure, flat-shaded render setup,
depth compositor, camera orbits, and OpenPose-style joint export from an armature.
Imported by render-rigged-shot.py (run inside Blender, `bpy` available)."""
import json
import math
import os

import bpy
from bpy_extras.object_utils import world_to_camera_view

# ----------------------------------------------------------------------------- scene basics

def reset_scene(width, height, fps, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = frames
    return scene


def add_ground(size=60):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    bpy.context.active_object.name = "Ground"


def add_lights():
    # key sun plus a soft fill from the camera side so the character never turns into a black silhouette
    bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
    bpy.context.active_object.data.energy = 3
    bpy.ops.object.light_add(type="SUN", location=(-5, -10, 6))
    fill = bpy.context.active_object
    fill.data.energy = 1.2
    fill.rotation_euler = (math.radians(60), 0, math.radians(-30))
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("World") if scene.world is None else scene.world
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.35, 0.35, 0.35, 1)
        bg.inputs[1].default_value = 1.0


def build_fence(W=12.0, H=8.0, cut=2.0, post_h=1.2, post_r=0.08):
    """Rectangular fence W x H centred at origin; the +x,+y corner is cut diagonally by `cut`.
    Returns the corner coordinates."""
    def add_post(x, y):
        bpy.ops.mesh.primitive_cylinder_add(radius=post_r, depth=post_h, location=(x, y, post_h / 2))
        bpy.context.active_object.name = f"Post_{x:.1f}_{y:.1f}"

    def add_rail(x0, y0, x1, y1, z):
        length = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, z))
        ob = bpy.context.active_object
        ob.scale = (length, 0.06, 0.12)
        ob.rotation_euler = (0, 0, ang)
        ob.name = "Rail"

    hx, hy = W / 2, H / 2
    corners = [(-hx, -hy), (hx, -hy), (hx, hy - cut), (hx - cut, hy), (-hx, hy)]
    for i, (x0, y0) in enumerate(corners):
        x1, y1 = corners[(i + 1) % len(corners)]
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(round(seg / 2.0)))
        for k in range(n + 1):
            t = k / n
            add_post(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        for z in (0.45, 0.95):
            add_rail(x0, y0, x1, y1, z)
    return corners


def figure_spot(W=12.0, H=8.0, cut=2.0):
    """Where the character stands: just inside the cut corner."""
    return (W / 2 - cut - 1.2, H / 2 - 1.5)


def add_camera(target_loc, radius, height, sweep_deg, start_deg, frames, lens=35, center=(0.0, 0.0), descend=0.3):
    bpy.ops.object.camera_add(location=(0, -10, 5))
    cam = bpy.context.active_object
    cam.name = "Camera"
    cam.data.lens = lens
    bpy.context.scene.camera = cam
    bpy.ops.object.empty_add(location=target_loc)
    target = bpy.context.active_object
    target.name = "CamTarget"
    con = cam.constraints.new(type="TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    for f in range(1, frames + 1):
        t = (f - 1) / max(1, frames - 1)
        ang = math.radians(start_deg + sweep_deg * t)
        cam.location = (center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang), height - descend * t)
        cam.keyframe_insert(data_path="location", frame=f)
    return cam


def setup_outputs(out_dir, near=8.0, far=28.0):
    """Composite: image -> preview PNGs; Z pass -> normalized depth PNGs (near white)."""
    scene = bpy.context.scene
    scene.use_nodes = True
    scene.view_layers[0].use_pass_z = True
    tree = scene.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)
    rl = tree.nodes.new("CompositorNodeRLayers")
    map_range = tree.nodes.new("CompositorNodeMapRange")
    map_range.inputs["From Min"].default_value = near
    map_range.inputs["From Max"].default_value = far
    map_range.inputs["To Min"].default_value = 1.0
    map_range.inputs["To Max"].default_value = 0.0
    map_range.use_clamp = True
    out_depth = tree.nodes.new("CompositorNodeOutputFile")
    out_depth.base_path = os.path.join(out_dir, "depth")
    out_depth.file_slots[0].path = "depth_"
    out_depth.format.file_format = "PNG"
    out_depth.format.color_mode = "BW"
    out_depth.format.color_depth = "8"
    tree.links.new(rl.outputs["Depth"], map_range.inputs["Value"])
    tree.links.new(map_range.outputs["Value"], out_depth.inputs[0])
    comp = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(rl.outputs["Image"], comp.inputs["Image"])
    scene.render.filepath = os.path.join(out_dir, "preview", "preview_")
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.join(out_dir, "preview"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "depth"), exist_ok=True)

# ----------------------------------------------------------------------------- colours (optional)

def _mat(name, rgb):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.9
    return m


def colorize_scene(palette=None):
    """Assign flat colours so a 'keep unchanged' VACE pass can carry them into the generated video."""
    palette = palette or {}
    base = {
        "Ground": (0.32, 0.62, 0.20), "Post": (0.55, 0.32, 0.13), "Rail": (0.62, 0.38, 0.16),
        "mom_Head": (0.96, 0.80, 0.69), "mom_Torso": (0.18, 0.45, 0.50), "mom_Leg": (0.93, 0.90, 0.82),
        "mom_Foot": (0.95, 0.95, 0.95), "mom_Arm": (0.18, 0.45, 0.50), "mom_Hand": (0.96, 0.80, 0.69),
        "kid_Head": (0.96, 0.80, 0.69), "kid_Torso": (0.93, 0.72, 0.18), "kid_Leg": (0.93, 0.72, 0.18),
        "kid_Foot": (0.15, 0.35, 0.80), "kid_Arm": (0.97, 0.97, 0.95), "kid_Hand": (0.96, 0.80, 0.69),
    }
    base.update(palette)
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        key = None
        for k in base:
            if ob.name == k or ob.name.startswith(k):
                key = k
        if key is None:
            for k in base:
                if "_" in k and ob.name.startswith(k.split("_")[0] + "_") and ob.name.split("_", 1)[1].startswith(k.split("_")[1]):
                    key = k
        if key:
            ob.data.materials.clear()
            ob.data.materials.append(_mat(key, base[key]))
    world = bpy.context.scene.world
    if world and world.use_nodes:
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs[0].default_value = (0.55, 0.75, 0.95, 1)  # sky blue

# ----------------------------------------------------------------------------- mannequin

def add_mannequin(name, location, height=1.65, facing_deg=0.0, action="wave", frames=49, head_ratio=6.0, window=None):
    """Primitive mannequin with proper shoulder/hip pivots. `height` in scene units, `head_ratio` = body height /
    head height (6 = cartoon-ish, 7.5 = realistic). Actions: idle, wave, point, jump, turn. `window=(f0, f1)` limits
    the action to those frames (idle outside), which is how gestures get aligned to dialogue timing. Returns the root."""
    s = height / 1.65  # everything below is authored for a 1.65 unit figure
    head_h = height / head_ratio
    bpy.ops.object.empty_add(location=location)
    root = bpy.context.active_object
    root.name = name
    root.rotation_euler = (0, 0, math.radians(facing_deg))

    def prim(pname, kind, loc, scale, parent):
        if kind == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 0), segments=24, ring_count=12)
        else:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=(0, 0, 0), vertices=24)
        ob = bpy.context.active_object
        ob.name = f"{name}_{pname}"
        ob.parent = parent
        ob.location = loc
        ob.scale = scale
        return ob

    def pivot(pname, loc, parent):
        bpy.ops.object.empty_add(location=(0, 0, 0))
        e = bpy.context.active_object
        e.name = f"{name}_{pname}"
        e.parent = parent
        e.location = loc
        e.rotation_mode = "XYZ"
        return e

    torso_h, leg_h, arm_h = 0.60 * s, 0.78 * s, 0.58 * s
    hip_z = leg_h
    shoulder_z = hip_z + torso_h
    prim("Head", "sphere", (0, 0, shoulder_z + head_h * 0.55), (head_h * 0.92, head_h * 0.92, head_h), root)
    prim("Torso", "cyl", (0, 0, hip_z + torso_h / 2), (0.30 * s, 0.17 * s, torso_h), root)
    for side, sx in (("L", -1), ("R", 1)):
        hip = pivot(f"Hip{side}", (sx * 0.11 * s, 0, hip_z), root)
        prim(f"Leg{side}", "cyl", (0, 0, -leg_h / 2), (0.11 * s, 0.11 * s, leg_h), hip)
        prim(f"Foot{side}", "cyl", (0, -0.05 * s, -leg_h + 0.04 * s), (0.12 * s, 0.24 * s, 0.08 * s), hip)
        sh = pivot(f"Shoulder{side}", (sx * 0.19 * s, 0, shoulder_z - 0.04 * s), root)  # torso half-width 0.15 + arm radius
        prim(f"Arm{side}", "cyl", (0, 0, -arm_h / 2), (0.085 * s, 0.085 * s, arm_h), sh)
        prim(f"Hand{side}", "sphere", (0, 0, -arm_h - 0.05 * s), (0.09 * s, 0.09 * s, 0.10 * s), sh)

    def key(ob, frame, rot=None, loc=None):
        if rot is not None:
            ob.rotation_euler = rot
            ob.keyframe_insert(data_path="rotation_euler", frame=frame)
        if loc is not None:
            ob.location = loc
            ob.keyframe_insert(data_path="location", frame=frame)

    objs = {o.name.split("_", 1)[1]: o for o in bpy.data.objects if o.name.startswith(name + "_")}
    shR, shL = objs["ShoulderR"], objs["ShoulderL"]
    base_yaw = math.radians(facing_deg)
    w0, w1 = (1, frames) if window is None else (max(1, int(window[0])), min(frames, int(window[1])))
    for f in range(1, frames + 1):
        active = w0 <= f <= w1
        t = (f - w0) / max(1, w1 - w0) if active else 0.0
        act = action if active else "idle"
        if act == "turn":
            key(root, f, rot=(0, 0, base_yaw + math.radians(-30 + 60 * t)))
            key(shR, f, rot=(math.radians(6), 0, 0))
            key(shL, f, rot=(math.radians(6), 0, 0))
        elif act == "wave":
            # right arm raised sideways (rotate about Y at the shoulder), hand wags about X
            key(shR, f, rot=(math.radians(10 * math.sin(t * math.pi * 4)), math.radians(-150), 0))
            key(shL, f, rot=(math.radians(8), 0, 0))
        elif act == "point":
            key(shR, f, rot=(math.radians(-85), math.radians(-25), 0))  # arm forward-ish
            key(shL, f, rot=(math.radians(8), 0, 0))
            key(root, f, rot=(0, 0, base_yaw + math.radians(15 * t)))
        elif act == "jump":
            z = location[2] + max(0.0, 0.35 * s * math.sin(t * math.pi * 2)) if t < 0.5 else location[2]
            key(root, f, loc=(location[0], location[1], z))
            key(shR, f, rot=(0, math.radians(-40 - 100 * max(0.0, math.sin(t * math.pi * 2))), 0))
            key(shL, f, rot=(0, math.radians(40 + 100 * max(0.0, math.sin(t * math.pi * 2))), 0))
        else:  # idle: slight sway
            key(root, f, rot=(0, 0, base_yaw + math.radians(4 * math.sin(t * math.pi * 2))))
            key(shR, f, rot=(math.radians(6), 0, 0))
            key(shL, f, rot=(math.radians(6), 0, 0))
    return root

# ----------------------------------------------------------------------------- pose export

# OpenPose (COCO-18) keypoint order used by ControlNet/VACE pose maps.
OPENPOSE_NAMES = ["nose", "neck", "r_shoulder", "r_elbow", "r_wrist", "l_shoulder", "l_elbow", "l_wrist",
                  "r_hip", "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle", "r_eye", "l_eye", "r_ear", "l_ear"]

# bone whose *head* gives the joint, per rig family. Mixamo names are matched on the part after "mixamorig:".
BONE_MAPS = {
    "mixamo": {
        "neck": "Neck", "head": "Head", "head_top": "HeadTop_End",
        "r_shoulder": "RightArm", "r_elbow": "RightForeArm", "r_wrist": "RightHand",
        "l_shoulder": "LeftArm", "l_elbow": "LeftForeArm", "l_wrist": "LeftHand",
        "r_hip": "RightUpLeg", "r_knee": "RightLeg", "r_ankle": "RightFoot",
        "l_hip": "LeftUpLeg", "l_knee": "LeftLeg", "l_ankle": "LeftFoot",
    },
    "rigify_metarig": {
        "neck": "spine.004", "head": "spine.006", "head_top": None,
        "r_shoulder": "upper_arm.R", "r_elbow": "forearm.R", "r_wrist": "hand.R",
        "l_shoulder": "upper_arm.L", "l_elbow": "forearm.L", "l_wrist": "hand.L",
        "r_hip": "thigh.R", "r_knee": "shin.R", "r_ankle": "foot.R",
        "l_hip": "thigh.L", "l_knee": "shin.L", "l_ankle": "foot.L",
    },
}


def detect_rig(armature):
    names = {b.name for b in armature.data.bones}
    if any(n.split(":")[-1] == "Hips" and "mixamorig" in n for n in names):
        return "mixamo"
    if "spine.006" in names and "upper_arm.L" in names:
        return "rigify_metarig"
    raise RuntimeError("unknown rig; bones: " + ", ".join(sorted(names)[:20]))


def _find_bone(armature, short):
    for pb in armature.pose.bones:
        if pb.name == short or pb.name.split(":")[-1] == short:
            return pb
    return None


def joint_world_positions(armature, rig):
    """Return dict joint -> world Vector for the current frame."""
    m = BONE_MAPS[rig]
    mw = armature.matrix_world
    out = {}
    for joint in ["neck", "r_shoulder", "r_elbow", "r_wrist", "l_shoulder", "l_elbow", "l_wrist",
                  "r_hip", "r_knee", "r_ankle", "l_hip", "l_knee", "l_ankle"]:
        pb = _find_bone(armature, m[joint])
        if pb is not None:
            out[joint] = mw @ pb.head
    head = _find_bone(armature, m["head"])
    if head is not None:
        hmat = mw @ head.matrix
        h_head = mw @ head.head
        top = mw @ (_find_bone(armature, m["head_top"]).head) if m["head_top"] and _find_bone(armature, m["head_top"]) else mw @ head.tail
        up = (top - h_head)
        length = up.length if up.length > 1e-6 else 0.2
        up = up.normalized() if up.length > 1e-6 else hmat.to_3x3() @ __import__("mathutils").Vector((0, 1, 0))
        # person's right = shoulder line (bone-local X sign differs between rigs); forward = up x right
        if "r_shoulder" in out and "l_shoulder" in out:
            right = (out["r_shoulder"] - out["l_shoulder"]).normalized()
        else:
            right = (hmat.to_3x3() @ __import__("mathutils").Vector((1, 0, 0))).normalized()
        fwd = up.cross(right).normalized()
        centre = h_head + up * (0.55 * length)
        out["nose"] = centre + fwd * (0.45 * length)
        out["r_eye"] = centre + fwd * (0.40 * length) + right * (0.15 * length) + up * (0.12 * length)
        out["l_eye"] = centre + fwd * (0.40 * length) - right * (0.15 * length) + up * (0.12 * length)
        out["r_ear"] = centre + right * (0.45 * length) + up * (0.05 * length)
        out["l_ear"] = centre - right * (0.45 * length) + up * (0.05 * length)
    return out


def export_pose_sequence(armature, rig, out_path, frames):
    """Project joints to normalized image coordinates (x right, y down) for every frame and save JSON."""
    scene = bpy.context.scene
    cam = scene.camera
    seq = []
    for f in range(1, frames + 1):
        scene.frame_set(f)
        pts = joint_world_positions(armature, rig)
        frame = {}
        for name in OPENPOSE_NAMES:
            v = pts.get(name)
            if v is None:
                frame[name] = None
                continue
            co = world_to_camera_view(scene, cam, v)
            visible = co.z > 0
            frame[name] = [co.x, 1.0 - co.y, bool(visible)]
        seq.append(frame)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"width": scene.render.resolution_x, "height": scene.render.resolution_y, "fps": scene.render.fps,
                   "order": OPENPOSE_NAMES, "frames": seq}, fh)
    return out_path
