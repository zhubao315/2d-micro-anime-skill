<div align="center">

# 2D 微动漫全流程制作 Skill（2D Micro-Anime Skill）

**从剧本到成片的全流程方法论 + 可复用引擎与模板**

> 提炼自原创 2D 微动漫《拥抱不完美的自己》（约 2′57″ · 五幕结构 · 全流程脚本化、可一键复现）

</div>

## 是什么

一个面向 AI 编码代理的 **Agent Skill**（`SKILL.md` + 参考资料 + 模板 + 引擎代码），
把一部原创 2D 微动漫的**制作全过程**提炼为可复用的工作流：

```text
① 策划    五幕剧本 ─▶ 分镜表 ─▶ 逐镜动画分镜
② 视觉    风格前缀 + 角色一致性 + 6 轮提示词 ─▶ 文生图（Qwen-Image/即梦/可灵…）
③ 动画    分镜图 ─▶ 自研 2D 网格形变引擎（呼吸/摆动/点头/抬手…真实角色表演）+ 逐镜相机
④ 音频    ACE-Step 纯器乐配乐 + Qwen3-TTS VoiceDesign 配音 + 程序化音效 ─▶ 多轨
⑤ 合成    FFmpeg：交叉溶解 + 纸纹光效 + 呼吸字幕 ─▶ 成片（字幕版/配音版）
⑥ 宣传    主视觉海报 + 文案包 + 预告片 + 宣传网站 + 原创合规自查
```

## 仓库结构

```text
SKILL.md                  ← 主 skill：何时用、六阶段流水线、三条铁律、文件路由
references/               ← 六阶段深读文档（策划/提示词/动画/音频/合成/宣传）
templates/                ← scene 单一事实源、逐镜导演表、提示词模板、QA 核查清单
engine/                   ← 自研 2D 网格形变引擎（warp.py + render.py，可直接 import）
```

## 三条铁律

1. **单一事实源**：镜头/台词/音效/时长全在一个 `scene.py` 里，渲染、配音、混音、字幕各脚本共用，改节奏只改一处。
2. **真正的角色表演，不是整图推拉**：高斯加权局部形变让"角色在动、背景基本不动"——整图 Ken Burns 是 PPT 感的根源。
3. **情绪曲线先于画面**：先规划色彩（冷→暖）、音乐（悬→冲突→释然）、五幕节奏，再生成任何一张图。

## 快速体验引擎

```bash
cd engine
python3 -c "
import numpy as np, sys
sys.path.insert(0, '.')
from warp import Deformer
from render import render_frame, _grid
img = np.full((720, 1280, 3), 200, dtype=np.uint8); img[300:420, 560:720] = [90,120,160]
cam, d = dict(pivot=(640,400), zoom=1.06), Deformer(pivot=(640,400), sigma=120, kind='squash', sy=1.04)
print(render_frame(img, [d], cam, _grid(1280,720)).shape)"
```

## 如何使用（作为 skill）

把本仓库放入你的 agent harness 的 skills 目录（或按各平台规范安装），
agent 在"制作/复现/改编微动漫短片"场景下会读取 `SKILL.md` 并按需深读 `references/`、套用 `templates/`、直接调用 `engine/`。

## 来源与声明

- 方法论与引擎提炼自**原创作品《拥抱不完美的自己》**（校园心理主题，主角"现实自我 vs 理想自我"双自我叙事，心理学内核：自我差异理论 Higgins 1987）。
- 作品中角色、场景、剧情、台词、分镜、提示词均为原创设计；图像由本地 Qwen-Image-2.1 生成、配乐由本地 ACE-Step 生成、配音由本地 Qwen3-TTS 合成、音效由脚本程序化合成，不含任何第三方下载素材。
- 本仓库只发布**方法论、模板与通用引擎代码**，不含原作品的角色图像与成片资产。

## 许可

MIT（见 `LICENSE`）。若用于公开发布的作品，建议在片尾滚动字幕注明制作工具与原创声明。
