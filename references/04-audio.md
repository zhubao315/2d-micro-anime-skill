# ④ 音频：配乐 · 配音 · 音效 · 混音

> 验收门：三段配乐情绪与五幕对齐、四类音色互不相同、任何两句配音不重叠、
> 成片响度 −16 LUFS / TP −1.5dBTP、第五幕科普段旁白清楚。

## 1. 配乐（BGM）· 纯器乐三段

用本地 ACE-Step v1（或同类器乐模型）依据**纯器乐提示词**（tags，`lyrics=[inst]`，
无 vocals、无歌词）生成三段情绪，交叉淡化后铺满全片：

| 段落 | 情绪定位 | tags 要点 |
|---|---|---|
| 开场 | 冷、悬、压抑 | cinematic instrumental, sparse piano notes, low sub-bass electronic ambience, soft phone notification blips, building quiet tension, no vocals |
| 冲突 | 紧张转清醒 | low frequency pulsing bass, sustained low string drone, slowly swelling strings, rising tension turning to clarity, sudden silence then a gentle single piano note, no vocals |
| 结尾 | 温暖希望 | warm cinematic instrumental, soft piano, light airy strings, hopeful and sincere, sunset campus, natural fade out, no vocals |

- 每段约 82s；合成时 3s `acrossfade` 串联，首 3s 淡入、片尾 6s 淡出。
- **情绪走向与画面同步**（冷焦虑 → 暖接纳）；第五幕科普段降低配乐音量。

## 2. 配音 · VoiceDesign 音色设计

用支持"自然语言描述音色"的 TTS（示例：Qwen3-TTS-12Hz-1.7B-VoiceDesign，
OpenAI 兼容 `POST /v1/audio/speech`，`task_type=VoiceDesign`，需带 `instructions`）。

| 角色 | 音色指令要点 | 定位 |
|---|---|---|
| 主角 | 同龄男生，清亮中音，略带疲惫，敏感克制，语速稍慢，压抑地自述 | 自然、疲惫 |
| 内心声音/虚拟自我 | 清晰稳定冷静，吐字利落，带距离感，干净少年播音腔，**不要机械电子音** | 冷、笃定 |
| 朋友 | 温暖明亮女生，自然随和，生活化，亲切不煽情 | 全片唯一暖色 |
| 旁白（含科普） | 成熟稳重男声播音员，字正腔圆，温和无评判 | 可信科普腔 |
| 特殊声（镜面声） | 主角音色压低、气声低语，克制中带压迫感 | 多个自己在耳边 |

设计原则：主角与虚拟自我"**同源不同调**"（隐喻两个自我）；科普旁白清晰可信、不作广告腔。

## 3. 配音排程 · 零重叠（硬约束）

排程器是唯一入口：先**去首尾静音**再计时，每句只占到「下一条起点 − 0.15s」；
超窗口句自动 `atempo` 收紧（上限 1.6×），仍超则 `atrim` + 淡出。混音前校验重叠数（应为 0）。

> ⚠️ **`atempo` 必须排在 `adelay` 之前**：否则加速会压缩前导静音，让整句提前落位互相压字。

## 4. 音效清单（程序化合成，无第三方素材）

按「镜号 + 镜内偏移」落位到 A5 轨。示例：手机提示音×3（密集但空洞）、快门咔嚓、
纸页摩擦、低频心跳、笔尖沙沙、像素上浮音、玻璃嗡鸣/多重回声、声音抽空、水滴涟漪、
笔迹浮现音、操场环境声、柔和提示音、信息图反馈音。纯 Python 合成（正弦/噪声 + 包络 + 滤波）。

## 5. 多轨组织与混音

| 轨道 | 内容 |
|---|---|
| V1 | 动画画面（含字幕） |
| A1–A3/A6 | 各角色对白 + 旁白 |
| A4 | 配乐（被对白**侧链闪避**） |
| A5 | 音效 |

混音策略（突出对白与音效、配乐融合垫底）：

- 对白：`highpass 90Hz` + 3kHz 存在感提升，整体抬升；
- 配乐：`sidechaincompress`（thr 0.05 / ratio 20）在对白出现时自动让位；
- 音效：高通 110Hz 后推出，保证提示音/镜面音/环境声清晰可辨；
- 响度：**两遍** `loudnorm(linear)` 静态归一至 −16 LUFS / TP −1.5dBTP
  （单遍动态归一会造成抽吸）。
