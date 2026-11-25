# ⑦ 可选动画路线：MiniMax H3 图生视频（I2V）

> 验收门：每镜首帧来自已定稿分镜图，运动提示词来自逐镜动画分镜表；生成片段按时间轴精确拼接，套回原配音与字幕。
> 适用：想让分镜图产生**真实连续运动**（人物表演、镜头运动、光影变化），而不只是 2D 网格形变。
> 本路线与 `engine/` 网格形变路线是**替代关系**，不是必选项——两者可并存，先小样对比再决定全片用哪条。

## 1. 什么时候用这条路线

| 场景 | 推荐 |
|---|---|
| 已有定稿角色/分镜图，要求"画面真的动起来" | H3 I2V |
| 镜数多（30–50 镜）、有 GPU 与几小时预算 | H3 I2V |
| 要求逐帧可控、可重复、离线无大模型依赖 | 网格形变 `engine/` |
| 片头字卡、信息图、纯黑场、文字多的镜头 | **不要用 AI 生成**（易出乱码字），用原帧/程序化卡片 |
| 需要严格同机位变体帧之间的表情缓动 | 网格形变更可控；H3 可改传 `last_frame` 但一致性风险高 |

## 2. 模型与量化选择

官方仓库 `Comfy-Org/MiniMax-H3`（Hugging Face；国内用 `hf-mirror.com` 镜像）。
**PyTorch 带 CUDA 13（cu130）时优先 `int8_convrot`**；cu12 环境用 `fp8_scaled`。

| 组件 | 文件 | 大小 | 目录 |
|---|---|---|---|
| 主模型（T2V/I2V/首尾帧） | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | ~21 GB | `models/diffusion_models/` |
| 文本编码器 | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | ~15.7 GB | `models/text_encoders/` |
| 视频 VAE | `minimax_h3_video_vae_int8_convrot.safetensors` | ~2.8 GB | `models/vae/` |
| 音频 VAE | `minimax_h3_audio_vae_fp32.safetensors` | ~0.6 GB | `models/vae/` |
| Turbo LoRA（8 步） | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors` | ~2 GB | `models/loras/` |

参考-to-video 另需 `minimax_h3_ref2va_pruned_int8_convrot.safetensors`。
下载后**必须校验 SHA256**（官方仓库 `api/models/Comfy-Org/MiniMax-H3?blobs=true` 的 `lfs.sha256`），失败常因拿到 HTML 错误页。
用 `aria2c -c -x 4 -s 4` 断点续传，国内镜像单连接常只有几百 KB/s，全套约 40 GB 需 1–2 小时。

## 3. ComfyUI 环境

- ComfyUI ≥ 0.30（推荐 0.45+），PyTorch ≥ cu130（本机实测 `2.15.0+cu132`）。
- 启动：`python3 main.py --listen 0.0.0.0 --port 8188 --cuda-device 0,1`（多卡可见；单卡省略）。
- 模型按上表挂到 `models/` 对应子目录；`CLIPLoader` 的 `type` 必须是 `minimax`。
- 容器部署时把模型目录 bind-mount 进去，并把启动脚本的"预热完成"信号作为 healthcheck——H3 首次加载 + 编译约需 5 分钟，预热期间提交任务会失败。

**双坑**：
1. ComfyUI 的 DynamicVRAM 常把所有模型都放在 `cuda:0`，即使挂了多卡也未必并行；`SelectModelDevice/SelectCLIPDevice/SelectVAEDevice` 节点在动态显存模式下可能被忽略。要真正并行可跑两个独立实例各占一卡。
2. 容器编排文件（compose.yaml）可能被其他流程还原，重跑前确认视频模型挂载与 GPU 映射仍在。

## 4. 图生视频工作流（API 摊平）

官方 `blueprints/Image to Video (MiniMax H3).json` 是 subgraph，可直接在前端用。批量生成建议走 `/prompt` API，把 subgraph 摊平成节点图：

```text
LoadImage(首帧) ─┐
MiniMaxH3ImageToVideo(clip, vae, prompt, width, height, length, first_frame) ─┬─ positive ─▶ BasicGuider
CLIPLoader(minimax) ───────────────────────────────────────────────────────┘         └─ LATENT ─▶ SamplerCustomAdvanced
UNETLoader → LoraLoaderModelOnly(Turbo) → ComfySwitchNode → BasicGuider ──────────────▶ GUIDER
RandomNoise + KSamplerSelect(res_multistep) + BasicScheduler(simple) ─────────────────▶ SAMPLER/SIGMAS
SamplerCustomAdvanced → VAEDecode(video VAE) / VAEDecodeAudio(audio VAE) → CreateVideo → SaveVideo
```

- **必须带输出节点**（`SaveVideo`），否则 `/prompt` 报 `prompt_no_outputs`。
- 图片先用 `/upload/image` 上传到容器 input 目录，`LoadImage` 引用其文件名。
- 提交格式：`{"prompt": {node_id: {"class_type":..., "inputs":...}}, "front": true}`；轮询 `/history/<prompt_id>` 判断 `status.completed`。
- H3 自带 AAC 音轨；若成片沿用原配音，合成时丢弃该音轨。

## 5. 批量生成参数模板

| 参数 | 建议值 | 说明 |
|---|---|---|
| 分辨率 | 960×544 或 1280×720 | 各边 32 的倍数；先小样确认 |
| 帧数 | 按镜长档位 `[73,90,107,124,141,158,175,192,204]` 取最接近 `dur×24` 的值 | 24fps |
| 步数 | 8（开 Turbo LoRA） | 不用 LoRA 时 20 步 `res_multistep` |
| 种子 | `1000 + 镜号` | 可复现、可单镜重跑 |
| 首帧 | 分镜图 cover-crop 到目标比例 | 保持人物构图一致 |

提示词由**逐镜动画分镜表字段**拼装，而不是另写一套：

```text
[风格前缀] + 镜头内容 + 起始姿势
+ 动作：action_beats
+ 表情/身体/镜头运动/前景/背景/光影：逐镜导演表相应字段
```

这样剧本/分镜仍是单一事实源，AI 视频只是换了一个"渲染器"。

**执行策略**：每镜单独提交（失败只影响一镜）、日志落盘（镜号 / 状态 / prompt / 帧数）、支持 `--shots s03 s04` 单镜调试与断点续跑。先跑 1 镜抽帧验收，再跑全片。

## 6. 合成（与现有音频/字幕对齐）

1. 按 `timeline_3min.json`（或单一事实源解析出的每镜起点）计算每段时长。
2. 每镜片段 `-stream_loop -1 -t <dur>` 循环填充到目标时长，统一 scale/crop/fps/像素格式。
3. 片头字卡从原成片截取（避免 AI 生成乱码文字），纯黑场用 `lavfi color=c=black`。
4. `ffmpeg concat` 拼接；最后一步 `-vf subtitles=xxx.ass -map 0:v -map 1:a` 烧字幕 + 套回原配音版音轨。
5. 验收：ffprobe 核对时长/帧率/流；抽查 3–5 个时间点画面与字幕。

**已知取舍**：直接 concat 是硬切；原流程要求 0.5s 交叉溶解时，可在 concat 前逐段做 `xfade`。极长镜（>15s）会明显重复循环，建议单独生成更长片段。

## 7. 可复用脚本

`templates/h3-video-template.py` 提供了完整的批量生成器骨架：配置区（模型文件名/分辨率/API 地址/素材目录）+ 提示词拼装 + 首帧预处理 + 单镜提交/轮询 + 断点续跑。
按项目实际目录改配置区即可用。
