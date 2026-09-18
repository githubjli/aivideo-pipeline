"""Prepare local baseline workflows from the bundled official templates."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / 'ComfyUI_windows_portable/python_embeded/Lib/site-packages/comfyui_workflow_templates_json/templates'
OUT = ROOT / 'workflows'
USER = ROOT / 'ComfyUI_windows_portable/ComfyUI/user/default/workflows'
USER.mkdir(parents=True, exist_ok=True)

WIDGETS = {
    'CheckpointLoaderSimple': ['ckpt_name'],
    'EmptyLatentImage': ['width', 'height', 'batch_size'],
    'CLIPTextEncode': ['text'],
    'KSampler': ['seed', None, 'steps', 'cfg', 'sampler_name', 'scheduler', 'denoise'],
    'SaveImage': ['filename_prefix'],
    'VAEDecode': [],
    'UNETLoader': ['unet_name', 'weight_dtype'],
    'CLIPLoader': ['clip_name', 'type', 'device'],
    'VAELoader': ['vae_name'],
    'CreateVideo': ['fps'],
    'SaveVideo': ['filename_prefix', 'format', 'codec'],
    'Wan22ImageToVideoLatent': ['width', 'height', 'length', 'batch_size'],
    'LoadImage': ['image', None],
    'ModelSamplingSD3': ['shift'],
    'LoadVideo': ['file', None],
    'GetVideoComponents': [],
    'Canny': ['low_threshold', 'high_threshold'],
    'PreviewImage': [],
    'Wan22FunControlToVideo': ['width', 'height', 'length', 'batch_size'],
}

def save(name, workflow):
    nodes = {n['id']: n for n in workflow['nodes']}
    links = {l[0]: l for l in workflow['links']}
    prompt = {}
    for node in nodes.values():
        if node.get('mode', 0) != 0 or node['type'] == 'MarkdownNote':
            continue
        inputs = {}
        for item in node.get('inputs', []):
            if item.get('link') is None:
                continue
            link = links[item['link']]
            if nodes[link[1]].get('mode', 0) == 0:
                inputs[item['name']] = [str(link[1]), link[2]]
        for key, value in zip(WIDGETS[node['type']], node.get('widgets_values') or []):
            if key is not None:
                inputs[key] = value
        prompt[str(node['id'])] = {'class_type': node['type'], 'inputs': inputs}
    text = json.dumps(workflow, ensure_ascii=False, indent=2)
    (OUT / f'{name}.json').write_text(text, encoding='utf-8')
    (USER / f'{name}.json').write_text(text, encoding='utf-8')
    (OUT / f'{name}.api.json').write_text(json.dumps(prompt, ensure_ascii=False, indent=2), encoding='utf-8')

sdxl = json.loads((TEMPLATES / 'image_sdxl_simple.json').read_text(encoding='utf-8'))
nodes = {n['id']: n for n in sdxl['nodes']}
nodes[10]['widgets_values'] = ['A cinematic photograph of a small red sailboat floating on a calm alpine lake, snow capped mountains, soft morning sunlight, gentle reflections, wide composition, highly detailed, natural colors']
nodes[11]['widgets_values'] = ['blurry, low quality, distorted, text, watermark, logo']
nodes[12]['widgets_values'] = [42, 'fixed', 25, 7, 'dpmpp_2m', 'karras', 1]
nodes[7]['widgets_values'] = ['sdxl/baseline']
save('01-sdxl-image', sdxl)

wan = json.loads((TEMPLATES / 'video_wan2_2_5B_ti2v.json').read_text(encoding='utf-8'))
nodes = {n['id']: n for n in wan['nodes']}
nodes[55]['widgets_values'] = [1280, 704, 49, 1]
nodes[3]['widgets_values'] = [42, 'fixed', 20, 5, 'uni_pc', 'simple', 1]
nodes[6]['widgets_values'] = ['A small red sailboat gently moves across a calm alpine lake. Soft ripples spread on the water, snow capped mountains in the background, warm morning sunlight. The camera slowly pans right. Cinematic realistic video, smooth natural motion.']
nodes[58]['widgets_values'] = ['wan/t2v_baseline', 'mp4', 'h264']
save('02-wan-text-to-video', wan)

i2v = copy.deepcopy(wan)
nodes = {n['id']: n for n in i2v['nodes']}
nodes[56]['mode'] = 0
nodes[56]['widgets_values'] = ['sdxl-reference.png', 'image']
nodes[58]['widgets_values'] = ['wan/i2v_baseline', 'mp4', 'h264']
save('03-wan-image-to-video', i2v)

# Depth-driven control video from Blender (tools/blender/render-depth-sequence.py) -> Wan2.2 Fun Control 5B.
fun = json.loads((TEMPLATES / 'video_wan2_2_5B_fun_control.json').read_text(encoding='utf-8'))
nodes = {n['id']: n for n in fun['nodes']}
nodes[66]['widgets_values'] = ['fence-v001-depth.mp4', 'image']
nodes[68]['mode'] = 4  # Canny stays bypassed: the control video is already a depth map
nodes[69]['mode'] = 4
nodes[70]['widgets_values'] = ['fence-v001-preview-0001.png', 'image']
nodes[70]['mode'] = 4  # baseline v1: depth control only, no reference image (Blender preview is flat grey)
nodes[60]['widgets_values'] = [1280, 704, 49, 1]
nodes[3]['widgets_values'] = [42, 'fixed', 20, 5, 'uni_pc', 'simple', 1]
nodes[6]['widgets_values'] = ['A bright 3D animated children\'s educational scene: a wooden garden fence enclosing a rectangular lawn, one corner of the fence is cut off diagonally, evenly spaced wooden posts with two horizontal rails, soft green grass, a small wooden crate near the cut corner, clear sky, warm sunlight, clean stylized Pixar-like rendering, smooth camera orbit.']
nodes[58]['widgets_values'] = ['wan/fun_control_depth_baseline', 'mp4', 'h264']
save('04-wan-fun-control-depth', fun)

# Variant B: Canny edges of the flat Blender preview render as the control signal (template's default path).
canny = copy.deepcopy(fun)
nodes = {n['id']: n for n in canny['nodes']}
nodes[66]['widgets_values'] = ['fence-v001-preview.mp4', 'image']
nodes[68]['mode'] = 0
nodes[68]['widgets_values'] = [0.1, 0.4]
nodes[58]['widgets_values'] = ['wan/fun_control_canny_baseline', 'mp4', 'h264']
# rewire: control_video input of node 60 must come from Canny (68) instead of GetVideoComponents (67)
for link in canny['links']:
    if link[3] == 60 and link[4] == 4:
        link[1], link[2] = 68, 0
for item in nodes[60]['inputs']:
    if item['name'] == 'control_video':
        item['link'] = next(l[0] for l in canny['links'] if l[3] == 60 and l[4] == 4)
save('04b-wan-fun-control-canny', canny)

# Variant C: depth re-rendered with a tighter near/far range (10-22) so posts and rails carry more contrast.
tight = copy.deepcopy(fun)
nodes = {n['id']: n for n in tight['nodes']}
nodes[66]['widgets_values'] = ['fence-v001-depth-tight.mp4', 'image']
nodes[58]['widgets_values'] = ['wan/fun_control_depth_tight', 'mp4', 'h264']
save('04c-wan-fun-control-depth-tight', tight)

# Variant D/E: fence scene plus a simple 3D mannequin (render-depth-sequence.py --figure); D lines only, E adds the
# character reference image so the model has an identity to paint onto the mannequin's silhouette.
FIGURE_PROMPT = ('A bright 3D animated children\'s educational scene: a wooden garden fence enclosing a rectangular lawn, '
                 'one corner of the fence is cut off diagonally, evenly spaced wooden posts with two horizontal rails. '
                 'Near the cut corner stands a friendly mother character with short dark hair, round glasses and a teal shirt, '
                 'turning toward the camera and waving one hand. Soft green grass, clear sky, warm sunlight, clean stylized '
                 'Pixar-like rendering, smooth camera orbit.')
fig = copy.deepcopy(canny)
nodes = {n['id']: n for n in fig['nodes']}
nodes[66]['widgets_values'] = ['fence-v002-figure-preview.mp4', 'image']
nodes[6]['widgets_values'] = [FIGURE_PROMPT]
nodes[58]['widgets_values'] = ['wan/fun_control_figure_lines', 'mp4', 'h264']
save('04d-wan-fun-control-figure', fig)

figref = copy.deepcopy(fig)
nodes = {n['id']: n for n in figref['nodes']}
nodes[70]['mode'] = 0
nodes[70]['widgets_values'] = ['mom-ref-front.png', 'image']
nodes[58]['widgets_values'] = ['wan/fun_control_figure_ref', 'mp4', 'h264']
save('04e-wan-fun-control-figure-ref', figref)
print('Saved workflows 01-04, 04b-04e: UI, API and sidebar copies.')
