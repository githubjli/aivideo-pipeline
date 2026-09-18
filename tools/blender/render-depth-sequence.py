"""Headless Blender: build a simple math-lesson scene (a fenced rectangle with one corner cut off),
orbit the camera, and render a normalized depth sequence plus a plain viewport-style preview.

Usage (from project root):
  tools/blender/blender-4.2.23-windows-x64/blender.exe -b --python tools/blender/render-depth-sequence.py -- \
      --out productions/math/tests/depth/fence-v001 --frames 49 --width 1280 --height 704 --fps 24
Outputs <out>/depth/depth_0001.png ... (8-bit grayscale, near=white far=black) and <out>/scene.blend.
"""
import argparse
import math
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--frames", type=int, default=49)
parser.add_argument("--width", type=int, default=1280)
parser.add_argument("--height", type=int, default=704)
parser.add_argument("--fps", type=int, default=24)
parser.add_argument("--cut", type=float, default=2.0, help="size of the cut-off corner (scene units)")
parser.add_argument("--figure", action="store_true", help="add a simple articulated mannequin near the cut corner that turns toward the camera and waves")
parser.add_argument("--focus-figure", action="store_true", help="frame the camera on the mannequin (medium shot) instead of the whole enclosure")
parser.add_argument("--near", type=float, default=8.0, help="depth mapped to white")
parser.add_argument("--far", type=float, default=28.0, help="depth mapped to black")
args = parser.parse_args(argv)

out_dir = os.path.abspath(args.out)
os.makedirs(os.path.join(out_dir, "depth"), exist_ok=True)

# --- fresh scene ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "SceneEEVEE") and bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
scene.render.resolution_x = args.width
scene.render.resolution_y = args.height
scene.render.resolution_percentage = 100
scene.render.fps = args.fps
scene.frame_start = 1
scene.frame_end = args.frames

def add_box(name, size, location):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    return ob

# ground
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
bpy.context.active_object.name = "Ground"

# fence: rectangle 12 x 8 (x by y), posts every 2 units, one corner (+x,+y) cut off diagonally by `cut`
W, H, cut = 12.0, 8.0, args.cut
post_h, post_r = 1.2, 0.08

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

# corner points clockwise from (-W/2,-H/2); the +x,+y corner is replaced by a diagonal
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

# a small figure-sized marker box near the cut corner, for scale (replaced by the mannequin when --figure)
if not args.figure:
    add_box("Marker", (0.5, 0.5, 1.6), (hx - cut - 1.2, hy - 1.5, 0.8))
else:
    # Simple mannequin: head sphere, torso capsule-ish box, two legs, two arms; parented to a root empty.
    fx, fy = hx - cut - 1.2, hy - 1.5
    bpy.ops.object.empty_add(location=(fx, fy, 0))
    root = bpy.context.active_object
    root.name = "FigureRoot"
    def part(name, kind, loc, scale, parent):
        if kind == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=loc, segments=24, ring_count=12)
        else:
            bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.0, location=loc, vertices=24)
        ob = bpy.context.active_object
        ob.name = name
        ob.scale = scale
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
        return ob
    part("Head", "sphere", (fx, fy, 1.55), (0.24, 0.24, 0.26), root)
    part("Torso", "cyl", (fx, fy, 1.05), (0.28, 0.18, 0.62), root)
    part("LegL", "cyl", (fx - 0.12, fy, 0.38), (0.10, 0.10, 0.76), root)
    part("LegR", "cyl", (fx + 0.12, fy, 0.38), (0.10, 0.10, 0.76), root)
    arm_l = part("ArmL", "cyl", (fx - 0.36, fy, 1.05), (0.08, 0.08, 0.60), root)
    arm_r = part("ArmR", "cyl", (fx + 0.36, fy, 1.05), (0.08, 0.08, 0.60), root)
    # animation: root turns 60 degrees toward the camera over the shot, right arm waves
    for f, rz in ((1, math.radians(-30)), (args.frames, math.radians(30))):
        root.rotation_euler = (0, 0, rz)
        root.keyframe_insert(data_path="rotation_euler", frame=f)
    arm_r.rotation_mode = "XYZ"
    for f in range(1, args.frames + 1):
        t = (f - 1) / max(1, args.frames - 1)
        arm_r.rotation_euler = (0, math.radians(-150 + 25 * math.sin(t * math.pi * 4)), 0)
        arm_r.keyframe_insert(data_path="rotation_euler", frame=f)
    arm_r.location = (fx + 0.36, fy, 1.30)

# camera orbiting the enclosure, slightly above eye level, looking at the cut corner region
bpy.ops.object.camera_add(location=(0, -16, 6))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 35
scene.camera = cam
if args.focus_figure and args.figure:
    # medium shot: orbit 40 degrees around the mannequin at ~5 units, aim at its chest
    fx, fy = hx - cut - 1.2, hy - 1.5
    bpy.ops.object.empty_add(location=(fx, fy, 1.0))
    target = bpy.context.active_object
    target.name = "CamTarget"
    radius, height, sweep, start = 5.0, 1.6, 40, -110
    center = (fx, fy)
else:
    bpy.ops.object.empty_add(location=(hx - cut - 1.5, hy - 2.0, 0.6))
    target = bpy.context.active_object
    target.name = "CamTarget"
    radius, height, sweep, start = 17.0, 6.0, 70, -100
    center = (0.0, 0.0)
con = cam.constraints.new(type="TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
for f in range(1, args.frames + 1):
    t = (f - 1) / max(1, args.frames - 1)
    ang = math.radians(start + sweep * t)
    cam.location = (center[0] + radius * math.cos(ang), center[1] + radius * math.sin(ang), height - (1.5 if not args.focus_figure else 0.3) * t)
    cam.keyframe_insert(data_path="location", frame=f)

# light (irrelevant for depth, keeps preview readable)
bpy.ops.object.light_add(type="SUN", location=(5, -5, 10))
bpy.context.active_object.data.energy = 3

# --- depth output via compositor: normalize Z between near/far then invert (near = white) ---
scene.use_nodes = True
scene.view_layers[0].use_pass_z = True
tree = scene.node_tree
for n in list(tree.nodes):
    tree.nodes.remove(n)
rl = tree.nodes.new("CompositorNodeRLayers")
map_range = tree.nodes.new("CompositorNodeMapRange")
map_range.inputs["From Min"].default_value = args.near
map_range.inputs["From Max"].default_value = args.far
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "scene.blend"))
bpy.ops.render.render(animation=True)
print(f"DONE frames={args.frames} out={out_dir}")
