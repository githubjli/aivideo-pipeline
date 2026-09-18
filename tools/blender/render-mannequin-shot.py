"""Headless Blender: fence scene with one or two primitive mannequins, rendered as flat preview + depth.

Usage (project root):
  blender.exe -b --python tools/blender/render-mannequin-shot.py -- --out <dir> --shot close|medium|wide|full \
      --figures mom:wave[,kid:jump] [--frames 49]
Figures: name:action where name is mom or kid (heights 1.65 / 1.15) and action in idle|wave|point|jump|turn.
The first figure stands at the cut corner spot; a second figure stands 1.1 units to its left.
"""
import argparse
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mathscene as ms  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--shot", choices=["close", "medium", "wide", "full"], default="medium")
p.add_argument("--figures", default="mom:wave")
p.add_argument("--frames", type=int, default=49)
p.add_argument("--width", type=int, default=1280)
p.add_argument("--height", type=int, default=704)
p.add_argument("--fps", type=int, default=24)
p.add_argument("--facing", type=float, default=0.0)
args = p.parse_args(argv)

HEIGHTS = {"mom": 1.65, "kid": 1.15}
out_dir = os.path.abspath(args.out)
scene = ms.reset_scene(args.width, args.height, args.fps, args.frames)
ms.add_ground()
ms.add_lights()
ms.build_fence()
fx, fy = ms.figure_spot()

figs = []
for i, spec in enumerate([s for s in args.figures.split(",") if s]):
    name, _, action = spec.partition(":")
    action = action or "idle"
    h = HEIGHTS.get(name, 1.65)
    loc = (fx - 1.1 * i, fy + 0.15 * i, 0)
    root = ms.add_mannequin(name, loc, height=h, facing_deg=args.facing, action=action, frames=args.frames)
    figs.append((name, h, loc))

cx = sum(l[0] for _, _, l in figs) / len(figs)
cy = sum(l[1] for _, _, l in figs) / len(figs)
tall = max(h for _, h, _ in figs)
if args.shot == "close":
    ms.add_camera((cx, cy, tall * 0.80), radius=2.3, height=tall * 0.85, sweep_deg=30, start_deg=-105, frames=args.frames,
                  lens=50, center=(cx, cy), descend=0.05)
elif args.shot == "medium":
    ms.add_camera((cx, cy, tall * 0.60), radius=5.0 + 1.5 * (len(figs) - 1), height=1.6, sweep_deg=40, start_deg=-110,
                  frames=args.frames, center=(cx, cy), descend=0.3)
elif args.shot == "wide":
    ms.add_camera((cx, cy, tall * 0.5), radius=9.0, height=2.6, sweep_deg=50, start_deg=-105, frames=args.frames,
                  center=(cx, cy), descend=0.5)
else:
    ms.add_camera((fx - 1.5, fy - 2.0, 0.6), radius=17.0, height=6.0, sweep_deg=70, start_deg=-100, frames=args.frames,
                  center=(0.0, 0.0), descend=1.5)
ms.setup_outputs(out_dir, near=2.0 if args.shot != "full" else 8.0, far=20.0 if args.shot != "full" else 28.0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "scene.blend"))
bpy.ops.render.render(animation=True)
print(f"DONE shot={args.shot} figures={args.figures} out={out_dir}")
