# ⑤ 合成：FFmpeg 流水线 · 字幕 · 可编辑工程 · 一键复现

> 验收门：成片 1080p/25fps、H.264/AAC faststart、字幕无错别字、可编辑 .mlt 工程存在、
> 全流程脚本能一键重跑。

## 1. 成片组装（FFmpeg）

- **逐段编码**：每镜渲染 → 独立 mp4（clips/），失败可单镜重跑；
- **转场**：镜间接缝逐段手写交叉溶解（`xfade` 0.5s，缓入缓出）；信息图卡可用白闪；
- **质感**：叠加缓慢漂移柔光 + 受亮度约束的纸张颗粒纹理（保持"淡彩赛璐"观感）；
- **字幕**：ASS 覆写（libass 烧入）——淡入上浮 + 关键词颜色渐暖；同时输出 SRT 给平台；
- **封装**：`libx264` + `aac`（160–192kbps）+ `faststart`，1080p/25fps；
- **响度**：见 `references/04-audio.md` 第 5 节（两遍 loudnorm）。

## 2. 字幕与台词同步

- 台词在 `scene.py` 声明为 `(镜号, 镜内偏移, 说话人, 文本)`，绝对秒由脚本解析；
- 字幕文件（subs.ass）由同一数据源生成 → 字幕、配音、成片**永远对齐**。

## 3. 可编辑工程（.mlt）

`make_mlt.py` / `make_mlt_dub.py` 生成 Kdenlive/Shotcut/melt 可直接打开的 MLT XML：
`V1` 按分镜顺序排列全部片段（挂字幕效果），`A1` 环境音乐；配音版多轨见 04-audio.md。
用途：交片后他人可继续剪辑、调时长、换转场，渲染预设 `MP4 (H.264/AAC) 1080p 25fps`。

## 4. 一键复现脚本清单（build/ 约定）

| 脚本 | 职责 |
|---|---|
| `scene.py` | 镜头/台词/音效**单一事实源**（五幕 36 镜 + SHOTS/LINES/SFX/TR） |
| `anim_manifest.py` | 生成逐镜动画分镜表 md + 清单 json |
| `anim_build.py` | 逐帧渲染 + 交叉溶解 + 光效/纸纹 + 字幕 + 配乐 → 字幕版成片 |
| `ace_gen.py` / `tts_dub.py` / `sfx_gen.py` / `dlg_plan.py` / `mix_dub.py` | 配乐 → 配音 → 音效 → 排程 → 多轨混音 → 配音版成片 |
| `make_mlt.py` / `make_mlt_dub.py` | 生成可编辑工程 |
| `promo_gen.py` / `make_trailer.py` / `site_build.py` | 海报 / 预告片 / 宣传网站资源 |
| `tools_poster.py` / `html2pdf.py` | 技术栈海报 / 文档 PDF |

调试：`anim_build.py --shots s03 s04`（单镜重渲）、`--no-render`（只重装）、
`tts_dub.py track`（仅重排整轨不重新合成）。**这些开关要在写脚本时就留好。**

## 5. 验收核对

- [ ] 成片时长 ≈ Σ镜时长 − Σ溶解；两版本（字幕版/配音版）同步
- [ ] 文件名规范（如 `班级-姓名-作品名称.mp4`），体积远小于平台上限（如 <200MB）
- [ ] 字幕零错字；台词与配音逐句一致
- [ ] 片头有片名字幕卡；片尾有电影式滚动字幕（理念/工具/祝福/版权）+ 感谢观看定格
- [ ] 打开 .mlt 可继续编辑（用 Shotcut/melt 验证过）
