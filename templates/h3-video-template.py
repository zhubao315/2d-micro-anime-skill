#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""h3-video-template.py · MiniMax H3 图生视频批量生成模板（ComfyUI /prompt API）。

用法：
  1. 改下面【配置区】的路径与模型文件名（模型需已在 ComfyUI 里可用）
  2. python3 h3-video-template.py --shots s03        # 单镜验证
  3. python3 h3-video-template.py                     # 全片，自动跳过已完成
  4. 用 references/07-ai-video-h3.md 第 6 节的合成流程套回配音字幕

依赖：Pillow（仅用于首帧裁切）、标准库 urllib。
"""
import argparse, json, os, shutil, time, urllib.request

# ------------------------------------------------------------------ 配置区
API = 'http://127.0.0.1:18198'                 # ComfyUI 地址:端口
MANIFEST = '/path/to/project/build/anim_manifest.json'  # 逐镜清单（dict 列表）
ASSET_ROOT = '/path/to/project'                # required_assets 的相对根
INPUT_DIR = '/path/to/comfyui/input'           # ComfyUI 的 input 目录（绝对路径）
OUTPUT_DIR = '/path/to/comfyui/output'         # ComfyUI 的 output 目录
CLIPS_DIR = '/path/to/project/build/h3_clips'  # 片段归档目录
LOG_PATH = '/path/to/project/build/h3_generate_log.json'
BASE_PROMPT_PATH = '/path/to/project/build/h3_api_prompt.json'  # 见下方说明

UNET = 'minimax_h3_fl2va_pruned_int8_convrot.safetensors'
CLIP = 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'
VIDEO_VAE = 'minimax_h3_video_vae_int8_convrot.safetensors'
AUDIO_VAE = 'minimax_h3_audio_vae_fp32.safetensors'
LORA = 'minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors'
STYLE_PREFIX = '轻薄半赛璐淡彩动漫风格，原创2D微动漫，无文字，无水印。'
WIDTH, HEIGHT = 960, 544
LENGTHS = [73, 90, 107, 124, 141, 158, 175, 192, 204]
SKIP_IDS = {'s01', 's02'}   # 片头字卡 / 纯黑场：不用 AI 生成

# BASE_PROMPT_PATH 是摊平后的 ComfyUI prompt 模板（dict: node_id -> {class_type, inputs}），
# 可用 workflows/Image to Video (MiniMax H3) 的 subgraph 摊平得到。关键节点：
#   "139": MiniMaxH3ImageToVideo  "135": UNETLoader  "136": CLIPLoader
#   "127"/"128": VAELoader  "137": RandomNoise  "900": SaveVideo（必须有）
# ------------------------------------------------------------------

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def api(path, payload=None, timeout=30):
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data=data, headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=timeout) as r:
        return json.load(r)

def clean(v):
    if not v or v == '—': return ''
    if isinstance(v, list): return '，'.join(clean(x) for x in v if x and x != '—')
    return str(v)

def build_prompt_text(shot):
    parts = [STYLE_PREFIX, f"镜头内容：{clean(shot.get('shot_type'))}。",
             f"画面：{clean(shot.get('starting_pose'))}。"]
    beats = clean(shot.get('action_beats'))
    if beats: parts.append(f'动作：{beats}。')
    for key, label in [('facial_animation', '表情'), ('body_animation', '身体'),
                       ('camera_motion', '镜头运动'), ('foreground_motion', '前景'),
                       ('background_motion', '背景'), ('lighting_effects', '光影')]:
        v = clean(shot.get(key))
        if v: parts.append(f'{label}：{v}。')
    return ''.join(parts)

def pick_length(dur):
    return min(LENGTHS, key=lambda x: abs(x - float(dur) * 24))

def prepare_image(shot, sid):
    for rel in shot.get('required_assets', []):
        src = os.path.join(ASSET_ROOT, rel)
        if os.path.isfile(src): break
    else:
        return None
    from PIL import Image
    im = Image.open(src).convert('RGB')
    ratio, w, h = WIDTH / HEIGHT, *im.size
    if w / h > ratio:
        nw = int(h * ratio); im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = int(w / ratio); im = im.crop((0, (h - nh) // 2, w, (h + nh) // 2))
    name = f'anime_{sid}.png'
    im.resize((WIDTH, HEIGHT), Image.LANCZOS).save(os.path.join(INPUT_DIR, name))
    return name

def make_prompt(shot, sid, image):
    p = json.load(open(BASE_PROMPT_PATH))
    p['901'] = {'class_type': 'LoadImage', 'inputs': {'image': image}}
    p['135']['inputs']['unet_name'] = UNET
    p['136']['inputs']['clip_name'] = CLIP
    p['127']['inputs']['vae_name'] = VIDEO_VAE
    p['128']['inputs']['vae_name'] = AUDIO_VAE
    # 若模板里有 LoraLoaderModelOnly 节点（如 "142"），填入 LORA
    for node in p.values():
        if node.get('class_type') == 'LoraLoaderModelOnly':
            node['inputs']['lora_name'] = LORA
    h3 = next(n for n in p.values() if n.get('class_type') == 'MiniMaxH3ImageToVideo')
    h3['inputs'].update(prompt=build_prompt_text(shot), width=WIDTH, height=HEIGHT,
                        length=pick_length(shot['duration']), first_frame=['901', 0])
    for node in p.values():
        if node.get('class_type') == 'RandomNoise':
            node['inputs']['noise_seed'] = 1000 + int(sid[1:]) if sid[1:].isdigit() else 1000
    p['900'] = {'class_type': 'SaveVideo', 'inputs': {
        'video': ['138', 0], 'filename_prefix': f'video/anime_{sid}',
        'format': 'auto', 'codec': 'auto'}}
    return p

def wait_job(pid, timeout=1800):
    end = time.time() + timeout
    while time.time() < end:
        entry = api('/history/' + pid).get(pid)
        if entry:
            st = entry.get('status', {})
            if st.get('status_str') == 'error': raise RuntimeError(json.dumps(st)[:2000])
            if st.get('completed'): return entry.get('outputs', {})
        time.sleep(10)
    raise TimeoutError(pid)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', nargs='*')
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    shots = json.load(open(MANIFEST))
    if a.shots: shots = [s for s in shots if s['shot_id'] in a.shots]
    if a.limit: shots = shots[:a.limit]
    os.makedirs(CLIPS_DIR, exist_ok=True)
    log = json.load(open(LOG_PATH)) if os.path.isfile(LOG_PATH) else {}
    for shot in shots:
        sid = shot['shot_id']
        if sid in SKIP_IDS or log.get(sid, {}).get('status') == 'done':
            continue
        image = prepare_image(shot, sid)
        if not image:
            print(f'SKIP {sid}: no image', flush=True); continue
        try:
            pid = api('/prompt', {'prompt': make_prompt(shot, sid, image), 'front': True})['prompt_id']
            outs = wait_job(pid)
            files = [os.path.join(OUTPUT_DIR, v.get('subfolder', ''), img['filename'])
                     for v in outs.values() for img in v.get('images', [])]
            if files:
                shutil.copy2(files[0], os.path.join(CLIPS_DIR, f'{sid}.mp4'))
            log[sid] = {'status': 'done', 'pid': pid}
            print(f'DONE {sid}', flush=True)
        except Exception as e:
            log[sid] = {'status': 'error', 'error': str(e)[:1000]}
            print(f'ERROR {sid}: {e}', flush=True)
        json.dump(log, open(LOG_PATH, 'w'), ensure_ascii=False, indent=2)
    print('ALL FINISHED', flush=True)

if __name__ == '__main__':
    main()
