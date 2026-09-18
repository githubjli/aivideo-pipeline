"""Pinned, resumable avatar assets; run with an existing huggingface_hub Python."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent
os.environ['HF_HOME'] = str(ROOT / 'cache' / 'huggingface')
os.environ['HF_HUB_DISABLE_XET'] = '1'
os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'
import json, argparse, hashlib, concurrent.futures, time
import requests
from huggingface_hub import HfApi, hf_hub_download

def local_path(row):
    """Files land in Wan2GP/ckpts/<file> unless the manifest row names another Wan2GP-relative target (LoRAs)."""
    return ROOT/'Wan2GP'/row['target'] if row.get('target') else ROOT/'Wan2GP'/'ckpts'/row['file']

def assets():
    rows=[]; targets={}
    def add(repo, folder, names, target_dir=None):
        for name in names.split():
            file='/'.join(filter(None,[folder,name])); rows.append((repo, file))
            if target_dir: targets[(repo,file)]=target_dir+'/'+name
    wan='DeepBeepMeep/Wan2.1'; hy='DeepBeepMeep/HunyuanVideo'; lc='DeepBeepMeep/LongCat'
    add(wan,'','wan2.1_image2video_480p_14B_quanto_mbf16_int8.safetensors wan2.1_infinitetalk_single_14B_quanto_mbf16_int8.safetensors Wan2.1_VAE.safetensors Wan2.1_VAE_bf16.safetensors Wan2.1_VAE_upscale2x_imageonly_real_v1.safetensors')
    add(wan,'umt5-xxl','models_t5_umt5-xxl-enc-quanto_int8.safetensors special_tokens_map.json spiece.model tokenizer.json tokenizer_config.json')
    add(wan,'xlm-roberta-large','models_clip_open-clip-xlm-roberta-large-vit-huge-14-bf16.safetensors sentencepiece.bpe.model special_tokens_map.json tokenizer.json tokenizer_config.json')
    add(wan,'chinese-wav2vec2-base','config.json pytorch_model.bin preprocessor_config.json')
    add(hy,'','hunyuan_video_avatar_720_quanto_bf16_int8.safetensors hunyuan_video_720_quanto_int8_map.json hunyuan_video_custom_VAE_fp32.safetensors hunyuan_video_custom_VAE_config.json hunyuan_video_VAE_fp32.safetensors hunyuan_video_VAE_config.json')
    add(hy,'llava-llama-3-8b','llava-llama-3-8b-v1_1_vlm_quanto_int8.safetensors config.json special_tokens_map.json tokenizer.json tokenizer_config.json preprocessor_config.json')
    add(hy,'clip_vit_large_patch14','text_config.json merges.txt model.safetensors preprocessor_config.json special_tokens_map.json tokenizer.json tokenizer_config.json vocab.json')
    add(hy,'whisper-tiny','config.json model.safetensors preprocessor_config.json special_tokens_map.json tokenizer_config.json')
    add(hy,'det_align','detface.pt')
    add(lc,'','longcat_avatar_v1_5_quanto_bf16_int8.safetensors')
    add(lc,'longcat_avatar_v1_5','dmd_lora.safetensors')
    add(lc,'whisper-large-v3','config.json generation_config.json model.safetensors preprocessor_config.json')
    # Shared assets Wan2GP checks before loading any model (wgp.py query_core_shared_model_files + MatAnyone v1).
    add(wan,'pose','dw-ll_ucoco_384.onnx yolox_l.onnx')
    add(wan,'scribble','netG_A_latest.pth')
    add(wan,'flow','raft-things.pth')
    add(wan,'depth','depth_anything_v2_vitl.pth')
    add(wan,'wav2vec','config.json feature_extractor_config.json model.safetensors preprocessor_config.json special_tokens_map.json tokenizer_config.json vocab.json')
    add(wan,'roformer','model_bs_roformer_ep_317_sdr_12.9755.ckpt model_bs_roformer_ep_317_sdr_12.9755.yaml download_checks.json')
    add(wan,'pyannote','pyannote_model_wespeaker-voxceleb-resnet34-LM.bin pytorch_model_segmentation-3.0.bin')
    add(wan,'mask','sam_vit_h_4b8939_fp16.safetensors matanyone.safetensors config.json')
    # 4-step accelerator LoRA used by the bundled InfiniteTalk template; Wan2GP looks for it in loras/wan_i2v.
    add(wan,'loras_accelerators','Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors',target_dir='loras/wan_i2v')
    # VACE FusioniX 14B (defaults/vace_14B_fusionix.json): distilled T2V base + VACE control module, INT8.
    # Text encoder, xlm-roberta, Wan2.1 VAEs are already listed above.
    add(wan,'','Wan14BT2VFusioniX_quanto_bf16_int8.safetensors wan2.1_Vace_14B_module_quanto_mbf16_int8.safetensors')
    # Multitalk module: with the same FusioniX base + VACE module gives defaults/vace_multitalk_14B.json (talking + control + refs).
    add(wan,'','wan2.1_multitalk_14B_quanto_mbf16_int8.safetensors')
    # Audio stack (file lists dumped from each handler's query_model_files + URLs, int8 variants where offered):
    tts='DeepBeepMeep/TTS'
    # Index TTS 2 (voice cloning)
    add(tts,'','index_tts2_gpt_fp16.safetensors')
    add(tts,'index_tts2','bpe.model feat1.pt feat2.pt s2mel.safetensors wav2vec2bert_stats.pt campplus_cn_common.bin index_tts2_semantic_codec.safetensors')
    add(tts,'qwen0.6bemo4-merge','Modelfile added_tokens.json chat_template.jinja config.json generation_config.json merges.txt model.safetensors special_tokens_map.json tokenizer.json tokenizer_config.json vocab.json')
    add(tts,'bigvgan_v2_22khz_80band_256x','config.json bigvgan_generator.pt')
    add(tts,'w2v-bert-2.0','config.json preprocessor_config.json model_fp16.safetensors')
    # Stable Audio Open 3 small music (instrumental background music)
    add(tts,'','stable_audio3_small_music_bf16.safetensors stable_audio3_same_s_bf16.safetensors')
    add(tts,'t5gemma-b-b-ul2','t5gemma-b-b-ul2_bf16.safetensors config.json special_tokens_map.json tokenizer.json tokenizer.model tokenizer_config.json')
    # ACE-Step 1.5 turbo with 1.7B LM (songs with vocals)
    add(tts,'','ace_step_v1_5_transformer_quanto_bf16_int8.safetensors')
    add(tts,'acestep-5Hz-lm-1.7B','acestep-5Hz-lm-1.7B_quanto_bf16_int8.safetensors config.json tokenizer.json tokenizer_config.json special_tokens_map.json added_tokens.json merges.txt vocab.json chat_template.jinja')
    add(tts,'ace_step15','ace_step_v1_5_audio_vae_bf16.safetensors silence_latent.pt')
    add(tts,'Qwen3-Embedding-0.6B','model.safetensors config.json tokenizer.json tokenizer_config.json special_tokens_map.json')
    # MMAudio v2 (video-to-soundtrack post-processing; config mmaudio.mode=1 selects the v2 checkpoint)
    add(wan,'mmaudio','synchformer_state_dict.pth v1-44.pth mmaudio_large_44k_v2.pth')
    add(wan,'DFN5B-CLIP-ViT-H-14-378','open_clip_config.json open_clip_pytorch_model.bin')
    add(wan,'bigvgan_v2_44khz_128band_512x','config.json bigvgan_generator.pt')
    return rows, targets

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true')
    parser.add_argument('--only',nargs='*',default=None,help='restrict to files under these top-level folders (e.g. pose mask)')
    a=parser.parse_args()
    manifest_path=ROOT/'model-manifest.json'
    manifest=json.loads(manifest_path.read_text('utf-8')) if manifest_path.exists() else []
    known={(x['repo'],x['file']) for x in manifest}
    rows,targets=assets()
    new=[(r,f) for r,f in rows if (r,f) not in known]
    if new:
        # Pin newly listed assets at the revision already recorded for that repo, so the manifest stays on one commit per repo.
        api=HfApi(); revisions={x['repo']:x['revision'] for x in manifest}
        infos={r:api.model_info(r,revision=revisions.get(r),files_metadata=True) for r in sorted({r for r,f in new})}
        for repo,file in new:
            info=infos[repo]; meta=next(x for x in info.siblings if x.rfilename==file)
            row=dict(repo=repo,revision=info.sha,file=file,size=meta.size,sha256=meta.lfs.sha256 if meta.lfs else None)
            if (repo,file) in targets: row['target']=targets[(repo,file)]
            manifest.append(row)
        manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        print(f'Added {len(new)} files to manifest',flush=True)
    print(f'Pinned {len(manifest)} files: {sum(x["size"] for x in manifest)/2**30:.2f} GiB',flush=True)
    if a.only is not None:
        manifest=[x for x in manifest if x['file'].split('/')[0] in a.only]
        print(f'Selected {len(manifest)} files: {sum(x["size"] for x in manifest)/2**30:.2f} GiB',flush=True)
    if not a.download:return
    def get(row):
        print('Downloading '+row['file'],flush=True)
        p=local_path(row)
        p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists() or p.stat().st_size!=row['size']:
            parts=ROOT/'cache'/'parts'/hashlib.sha256(row['file'].encode()).hexdigest()[:20]
            parts.mkdir(parents=True,exist_ok=True)
            chunk=16*1024*1024
            def block(i):
                start=i*chunk; end=min(start+chunk,row['size'])-1
                dest=parts/str(i)
                if dest.exists() and dest.stat().st_size==end-start+1:return dest
                url=f"https://huggingface.co/{row['repo']}/resolve/{row['revision']}/{row['file']}?chunk={i}"
                for attempt in range(5):
                    try:
                        with requests.get(url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(20,40)) as r:
                            r.raise_for_status()
                            if r.status_code==206 and not r.headers.get('Content-Range','').startswith(f'bytes {start}-'):raise ValueError('range mismatch')
                            if r.status_code==200 and row['size']>chunk:raise ValueError('range ignored')
                            with dest.open('wb') as f:
                                for data in r.iter_content(1024*1024):f.write(data)
                        if dest.stat().st_size!=end-start+1:raise ValueError('partial block')
                        return dest
                    except Exception as exc:
                        if attempt==4:raise RuntimeError(f"{row['file']} block {i}: {type(exc).__name__}") from None
                        time.sleep(2*(attempt+1))
            count=(row['size']+chunk-1)//chunk
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as blocks:
                for i,_ in enumerate(blocks.map(block,range(count))):
                    if i%32==0:print(f"PROGRESS {row['file']}: {min((i+1)*chunk,row['size'])/row['size']:.1%}",flush=True)
            partial=p.with_suffix(p.suffix+'.assembling')
            with partial.open('wb') as out:
                for i in range(count):
                    with (parts/str(i)).open('rb') as f:
                        for b in iter(lambda:f.read(8*1024*1024),b''):out.write(b)
            partial.replace(p)
        if p.stat().st_size!=row['size']:raise ValueError('size mismatch '+str(p))
        if row['sha256']:
            h=hashlib.sha256()
            with p.open('rb') as f:
                for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
            if h.hexdigest()!=row['sha256']:raise ValueError('hash mismatch '+str(p))
        # Only discard our verified, per-file blocks inside the project cache.
        parts=ROOT/'cache'/'parts'/hashlib.sha256(row['file'].encode()).hexdigest()[:20]
        if parts.exists():
            for blockpath in parts.iterdir():
                if blockpath.is_file() and blockpath.name.isdigit():blockpath.unlink()
        print('VERIFIED '+row['file'],flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(get,manifest))
    print('ALL VERIFIED',flush=True)
if __name__=='__main__':main()
