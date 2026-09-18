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
        # bone-local axes: Y along the bone (up); Z is forward for Mixamo heads, -Y/… varies, so use X for sideways only
        side = (hmat.to_3x3() @ __import__("mathutils").Vector((1, 0, 0))).normalized()
        fwd = up.cross(side).normalized()
        centre = h_head + up * (0.55 * length)
        out["nose"] = centre + fwd * (0.45 * length)
        out["r_eye"] = centre + fwd * (0.40 * length) + side * (0.15 * length) + up * (0.12 * length)
        out["l_eye"] = centre + fwd * (0.40 * length) - side * (0.15 * length) + up * (0.12 * length)
        out["r_ear"] = centre + side * (0.45 * length) + up * (0.05 * length)
        out["l_ear"] = centre - side * (0.45 * length) + up * (0.05 * length)
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
