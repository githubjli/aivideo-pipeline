"""Decode local generated media and save basic validation data and video frames."""
import json
from pathlib import Path

import av
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
reports = []
for path in sorted((ROOT / 'outputs/sdxl').glob('*.png')):
    with Image.open(path) as im:
        pixels = np.asarray(im.convert('RGB'))
        reports.append({'path': str(path.relative_to(ROOT)), 'size': list(im.size), 'pixel_std': float(pixels.std()), 'has_workflow': 'workflow' in im.info})
for path in sorted((ROOT / 'outputs/wan').glob('*.mp4')):
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        frames = [f.to_ndarray(format='rgb24') for f in container.decode(video=0)]
        assert frames, f'Empty video: {path}'
        fps = float(stream.average_rate)
        report = {'path': str(path.relative_to(ROOT)), 'size': [stream.width, stream.height], 'decoded_frames': len(frames), 'fps': fps, 'seconds': len(frames) / fps, 'codec': stream.codec_context.name, 'pixel_std': float(frames[0].std()), 'first_last_mean_absolute_difference': float(np.abs(frames[0].astype(float) - frames[-1].astype(float)).mean())}
        reports.append(report)
        for label, frame in [('first', frames[0]), ('middle', frames[len(frames)//2]), ('last', frames[-1])]:
            Image.fromarray(frame).save(ROOT / 'logs' / f'{path.stem}-{label}.png')
(ROOT / 'logs/media-validation.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print(json.dumps(reports, indent=2))
