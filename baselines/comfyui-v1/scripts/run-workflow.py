"""Run one prepared workflow against the local ComfyUI and retain its history."""
import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('workflow', choices=['01-sdxl-image', '02-wan-text-to-video', '03-wan-image-to-video', '04-wan-fun-control-depth', '04b-wan-fun-control-canny', '04c-wan-fun-control-depth-tight', '04d-wan-fun-control-figure', '04e-wan-fun-control-figure-ref'])
args = parser.parse_args()
name = args.workflow

def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8188' + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

prompt = json.loads((ROOT / 'workflows' / f'{name}.api.json').read_text(encoding='utf-8'))
workflow = json.loads((ROOT / 'workflows' / f'{name}.json').read_text(encoding='utf-8'))
started = time.monotonic()
reply = request('/prompt', {'prompt': prompt, 'extra_data': {'extra_pnginfo': {'workflow': workflow}}})
prompt_id = reply['prompt_id']
print('Queued', prompt_id, flush=True)
stamp = time.strftime('%Y%m%d-%H%M%S')
record_path = ROOT / 'logs' / f'{name}-{stamp}.json'
record = {'workflow': name, 'prompt_id': prompt_id, 'submitted': stamp, 'state': 'running'}
record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
peak_gpu_mib = 0
while True:
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
    if gpu.returncode == 0:
        peak_gpu_mib = max(peak_gpu_mib, int(gpu.stdout.strip().splitlines()[0]))
    history = request('/history/' + prompt_id)
    if prompt_id in history:
        result = history[prompt_id]
        record.update(state=result['status']['status_str'], elapsed_seconds=round(time.monotonic() - started, 2), sampled_peak_total_gpu_mib=peak_gpu_mib, history=result)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Result:', record['state'], 'seconds:', record['elapsed_seconds'], 'record:', record_path, flush=True)
        if record['state'] != 'success':
            print(json.dumps(result['status'], ensure_ascii=False), flush=True)
            raise SystemExit(1)
        print(json.dumps(result['outputs'], ensure_ascii=False), flush=True)
        break
    time.sleep(3)
