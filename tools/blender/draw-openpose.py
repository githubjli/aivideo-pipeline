"""Draw OpenPose-style (COCO-18) pose maps from the joints.json exported by render-rigged-shot.py.
Run with any Python that has Pillow, e.g. ComfyUI_windows_portable/python_embeded/python.exe:
  python tools/blender/draw-openpose.py <shot>/pose/joints.json [--stick 4]
Writes <shot>/pose/pose_0001.png ... in the same size as the render, black background, ControlNet colours."""
import argparse
import json
import math
import os

from PIL import Image, ImageDraw

# ControlNet / openpose reference colours and limb sequence (1-indexed COCO-18)
COLORS = [[255, 0, 0], [255, 85, 0], [255, 170, 0], [255, 255, 0], [170, 255, 0], [85, 255, 0], [0, 255, 0],
          [0, 255, 85], [0, 255, 170], [0, 255, 255], [0, 170, 255], [0, 85, 255], [0, 0, 255], [85, 0, 255],
          [170, 0, 255], [255, 0, 255], [255, 0, 170], [255, 0, 85]]
LIMBS = [[2, 3], [2, 6], [3, 4], [4, 5], [6, 7], [7, 8], [2, 9], [9, 10], [10, 11], [2, 12], [12, 13], [13, 14],
         [2, 1], [1, 15], [15, 17], [1, 16], [16, 18], [3, 17], [6, 18]]

ap = argparse.ArgumentParser()
ap.add_argument("joints")
ap.add_argument("--stick", type=int, default=4)
a = ap.parse_args()

data = json.load(open(a.joints, encoding="utf-8"))
W, H, order = data["width"], data["height"], data["order"]
out_dir = os.path.dirname(os.path.abspath(a.joints))

for i, frame in enumerate(data["frames"], 1):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = []
    for name in order:
        v = frame.get(name)
        pts.append(None if (v is None or not v[2]) else (v[0] * W, v[1] * H))
    for k, (s, e) in enumerate(LIMBS):
        ps, pe = pts[s - 1], pts[e - 1]
        if ps is None or pe is None:
            continue
        mx, my = (ps[0] + pe[0]) / 2, (ps[1] + pe[1]) / 2
        length = math.hypot(pe[0] - ps[0], pe[1] - ps[1])
        ang = math.degrees(math.atan2(pe[1] - ps[1], pe[0] - ps[0]))
        # ellipse along the limb: draw on a temp layer and rotate
        layer = Image.new("RGBA", (int(length) + a.stick * 2 + 2, a.stick * 2 + 2), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse([0, 0, layer.width - 1, layer.height - 1], fill=tuple(COLORS[k % len(COLORS)]) + (255,))
        layer = layer.rotate(-ang, expand=True, resample=Image.BICUBIC)
        img.paste(layer, (int(mx - layer.width / 2), int(my - layer.height / 2)), layer)
    d = ImageDraw.Draw(img)
    for j, pt in enumerate(pts):
        if pt is None:
            continue
        r = a.stick
        d.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=tuple(COLORS[j]))
    img.save(os.path.join(out_dir, f"pose_{i:04d}.png"))
print(f"wrote {len(data['frames'])} pose maps to {out_dir}")
