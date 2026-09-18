"""Check completed downloads against saved repository metadata before enabling them."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / 'ComfyUI_windows_portable/ComfyUI/models'
targets = [
    ('sdxl-metadata.json', 'sd_xl_base_1.0.safetensors', 'checkpoints'),
    ('wan-metadata.json', 'split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors', 'diffusion_models'),
    ('wan-metadata.json', 'split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'text_encoders'),
    ('wan-metadata.json', 'split_files/vae/wan2.2_vae.safetensors', 'vae'),
    ('wan-metadata.json', 'split_files/diffusion_models/wan2.2_fun_control_5B_bf16.safetensors', 'diffusion_models'),
]
log = ROOT / 'logs/model-verification.json'
records = json.loads(log.read_text(encoding='utf-8')) if log.exists() else {}
for metadata, remote, folder in targets:
    meta = json.loads((ROOT / 'downloads' / metadata).read_text(encoding='utf-8'))
    expected = next(x for x in meta['siblings'] if x['rfilename'] == remote)
    final = MODELS / folder / Path(remote).name
    part = final.with_suffix(final.suffix + '.part')
    path = final if final.exists() else part
    if not path.exists() or path.stat().st_size != expected['size']:
        print('Pending:', final.name, flush=True)
        continue
    if final.exists() and records.get(final.name, {}).get('sha256') == expected['lfs']['sha256']:
        print('Previously verified:', final.name, flush=True)
        continue
    with path.open('rb') as handle:
        actual = hashlib.file_digest(handle, 'sha256').hexdigest()
    if actual != expected['lfs']['sha256']:
        raise RuntimeError(f'SHA256 mismatch: {path}')
    if path == part:
        part.rename(final)
    records[final.name] = {'path': str(final.relative_to(ROOT)), 'size': expected['size'], 'sha256': actual, 'repository_commit': meta['sha'], 'metadata_source': metadata}
    log.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Verified:', final.name, flush=True)
