"""Shot pipeline: one JSON spec -> (TTS lines) -> Blender mannequin render -> VACE / VACE+Multitalk settings -> run -> collect.

Run with the ComfyUI Python (has requests/PIL, not needed here but consistent):
  ComfyUI_windows_portable/python_embeded/python.exe -X utf8 tools/pipeline/shot.py productions/math/shots/<name>.json [--dry-run]

Spec (all paths relative to project root unless absolute):
{
  "name": "demo",                       # output folder productions/math/shots/<name>/
  "shot": "medium",                     # close | medium | wide | full
  "fps": 25, "seed": 42, "resolution": "832x480",
  "frames": 49,                         # ignored when dialogue is present (derived from audio)
  "colored": false,                     # render flat colours and use keep-unchanged control (UV) instead of edges (EV)
  "control": "EVI",                     # override control letters if you know what you want
  "prompt": "...",                      # scene description; characters are described from figures[].describe
  "figures": [
    {"name": "mom", "action": "point", "at": [1.0, 2.5],     # optional action window in seconds
     "ref": "productions/math/tests/avatar/mom-ref-front.png",
     "describe": "the mother with short dark hair, round glasses and a teal shirt",
     "voice": "productions/math/tests/avatar/mom-test-zh.wav"},   # voice sample for TTS lines of this speaker
    {"name": "kid", ...}
  ],
  "dialogue": [ {"speaker": "mom", "text": "..."}, {"speaker": "kid", "text": "...", "audio": "optional existing wav"} ]
}
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BLENDER = os.path.join(ROOT, "tools", "blender", "blender-4.2.23-windows-x64", "blender.exe")
FFMPEG = os.path.join(ROOT, "tools", "avatar", "Wan2GP", "ffmpeg_bins", "ffmpeg.exe")
FFPROBE = os.path.join(ROOT, "tools", "avatar", "Wan2GP", "ffmpeg_bins", "ffprobe.exe")
RUNNER = os.path.join(ROOT, "tools", "avatar", "run-avatar-test.ps1")
OUT_DIR = os.path.join(ROOT, "productions", "math", "tests", "avatar", "out")


def P(rel):
    return rel if os.path.isabs(rel) else os.path.join(ROOT, rel)


def sh(cmd, cwd=ROOT, check=True):
    print("$", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"command failed ({r.returncode})")
    return r


def duration(path):
    r = sh([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path])
    return float(r.stdout.strip())


def run_settings(settings_path, attention="sage2"):
    """Run one Wan2GP settings file through run-avatar-test.ps1 and return the newest output file(s)."""
    before = {f: os.path.getmtime(os.path.join(OUT_DIR, f)) for f in os.listdir(OUT_DIR)} if os.path.isdir(OUT_DIR) else {}
    sh(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", RUNNER, "-Settings", settings_path, "-Attention", attention])
    new = [f for f in os.listdir(OUT_DIR) if f not in before or os.path.getmtime(os.path.join(OUT_DIR, f)) > before[f]]
    return [os.path.join(OUT_DIR, f) for f in sorted(new, key=lambda f: os.path.getmtime(os.path.join(OUT_DIR, f)))]


def tts_line(speaker, text, voice, out_name, seed):
    tpl = json.load(open(P("productions/math/tests/avatar/tts-indextts2-kid-line.json"), encoding="utf-8"))
    tpl.update(prompt=text, audio_guide=P(voice).replace("\\", "/"), output_filename=out_name, seed=seed)
    sp = os.path.join(ROOT, "productions", "math", "shots", "_tmp", f"{out_name}.json")
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    json.dump(tpl, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    files = [f for f in run_settings(sp) if f.endswith(".wav")]
    if not files:
        raise SystemExit(f"TTS produced no wav for {out_name}")
    return files[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--dry-run", action="store_true", help="prepare everything but do not run the video model")
    ap.add_argument("--attention", default="sage2")
    a = ap.parse_args()
    spec = json.load(open(P(a.spec), encoding="utf-8"))
    name = spec["name"]
    fps = int(spec.get("fps", 25 if spec.get("dialogue") else 24))
    shot_dir = os.path.join(ROOT, "productions", "math", "shots", name)
    os.makedirs(os.path.join(shot_dir, "result"), exist_ok=True)
    figures = spec["figures"]
    by_name = {f["name"]: f for f in figures}
    t0 = time.time()

    # 1. dialogue -> audio files + timeline
    dialogue = spec.get("dialogue") or []
    audio_files, timeline, cursor = [], [], 0.0
    for i, line in enumerate(dialogue, 1):
        spk = line["speaker"]
        if line.get("audio"):
            wav = P(line["audio"])
        else:
            wav = tts_line(spk, line["text"], by_name[spk].get("voice", "productions/math/tests/avatar/mom-test-zh.wav"),
                           f"{name}-line{i}-{spk}", int(spec.get("seed", 42)) + i)
        d = duration(wav)
        dst = os.path.join(shot_dir, f"line{i}-{spk}.wav")
        shutil.copyfile(wav, dst)
        audio_files.append(dst)
        timeline.append({"line": i, "speaker": spk, "start": cursor, "end": cursor + d, "text": line.get("text", "")})
        cursor += d
    if dialogue:
        total = cursor + 0.3
        frames = int(math.ceil(total * fps))
        frames = frames + (4 - (frames - 1) % 4) % 4  # round up to 4n+1
    else:
        frames = int(spec.get("frames", 49))

    # 2. figures -> Blender spec (actions optionally windowed in seconds -> frames; a speaker's action defaults to its line)
    fig_specs = []
    for f in figures:
        action = f.get("action", "idle")
        win = f.get("at")
        if win is None and dialogue:
            mine = [t for t in timeline if t["speaker"] == f["name"]]
            if mine and action != "idle":
                win = [mine[0]["start"], mine[-1]["end"]]
        s = f"{f['name']}:{action}"
        if win:
            s += f"@{max(1, int(win[0] * fps) + 1)}-{min(frames, int(win[1] * fps) + 1)}"
        fig_specs.append(s)
    w, h = (1280, 704)
    cmd = [BLENDER, "-b", "--python", os.path.join(ROOT, "tools", "blender", "render-mannequin-shot.py"), "--",
           "--out", shot_dir, "--shot", spec.get("shot", "medium"), "--figures", ",".join(fig_specs),
           "--frames", str(frames), "--fps", str(fps), "--width", str(w), "--height", str(h)]
    if spec.get("colored"):
        cmd.append("--colored")
    sh(cmd)
    preview = os.path.join(shot_dir, "preview.mp4")
    sh([FFMPEG, "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(shot_dir, "preview", "preview_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "10", preview])

    # 3. VACE settings
    control = spec.get("control") or ("UVI" if spec.get("colored") else "EVI")
    describe = "; ".join(f"{f['name']}: {f.get('describe', '')}" for f in figures if f.get("describe"))
    prompt = spec.get("prompt", "") + (" Referenced characters: " + describe + "." if describe else "")
    base = json.load(open(P("productions/math/tests/avatar/s4-duo-dialogue.json" if dialogue else
                             "productions/math/tests/avatar/s3-duo-actions.json"), encoding="utf-8"))
    base.update(prompt=prompt, seed=int(spec.get("seed", 42)), resolution=spec.get("resolution", "832x480"),
                video_length=frames, video_prompt_type=control, video_guide=preview.replace("\\", "/"),
                image_refs=[P(f["ref"]).replace("\\", "/") for f in figures if f.get("ref")],
                output_filename=name)
    if dialogue:
        speakers = list(dict.fromkeys(t["speaker"] for t in timeline))
        if len(speakers) == 1:
            base.update(audio_prompt_type="A", audio_guide=audio_files[0].replace("\\", "/"))
            base.pop("audio_guide2", None)
        else:
            # merge each speaker's lines into one track per speaker, played in a row (CAB); positions from figure order:
            # figure 0 stands at the corner (right side of a medium shot), figure 1 to its left.
            tracks = []
            for spk in speakers[:2]:
                parts = [af for af, t in zip(audio_files, timeline) if t["speaker"] == spk]
                merged = os.path.join(shot_dir, f"track-{spk}.wav")
                lst = os.path.join(shot_dir, f"track-{spk}.txt")
                open(lst, "w", encoding="utf-8").write("".join(f"file '{p}'\n" for p in parts))
                sh([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", merged])
                tracks.append(merged)
            order = [f["name"] for f in figures]
            loc = {order[0]: "55:100", order[1] if len(order) > 1 else order[0]: "0:45"}
            base.update(audio_prompt_type="CAB", audio_guide=tracks[0].replace("\\", "/"), audio_guide2=tracks[1].replace("\\", "/"),
                        speakers_locations=" ".join(loc[s] for s in speakers[:2]))
    settings_path = os.path.join(shot_dir, "settings.json")
    json.dump(base, open(settings_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"spec": spec, "frames": frames, "fps": fps, "timeline": timeline, "figures": fig_specs, "control": control},
              open(os.path.join(shot_dir, "plan.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"plan: frames={frames} fps={fps} control={control} figures={fig_specs} timeline={timeline}")
    if a.dry_run:
        print("dry-run: settings written to", settings_path)
        return

    # 4. run + collect
    outs = [f for f in run_settings(settings_path, a.attention) if f.endswith(".mp4")]
    if not outs:
        raise SystemExit("no video produced; see logs/avatar-test-*")
    final = outs[-1]
    dst = os.path.join(shot_dir, "result", f"{name}.mp4")
    shutil.copyfile(final, dst)
    step = max(1, frames // 8)
    sh([FFMPEG, "-v", "error", "-y", "-i", dst, "-vf", f"select='not(mod(n\\,{step}))',scale=320:-1,tile=8x1",
        "-frames:v", "1", "-fps_mode", "passthrough", os.path.join(shot_dir, "result", f"{name}-strip.png")])
    print(f"DONE {name}: {dst}  ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
