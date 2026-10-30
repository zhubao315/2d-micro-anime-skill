#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scene-template.py · 镜头/台词/音效"单一事实源"模板。

约定（与原项目 scene.py 一致）：
- SHOTS：镜头表。`src` 指向 04-分镜图/ 下的图；以 `#` 开头为卡片镜（#title/#black/#credits…）；
  `src2` 为同镜的表情/动作变体（用于镜内表情过渡）；`dur` 单镜时长(s)；
  `motion` 相机模式（hold/in/pan/…，实际运动由 rigs 的 DIR 导演表给出首尾参数）；
  `subs` 该镜内字幕/台词 (偏移s, 时长上限s, 说话人, 文本)。
- LINES：配音台词 = (镜号, 镜内偏移, 时长上限, 说话人, 文本)，时间基准为"镜号+偏移"，
  绝对秒由 timeline.json 解析；配音排程见 dlg_plan（零重叠硬约束）。
- SFX：音效同样按"镜号+镜内偏移"落位。
- TR：交叉溶解时长。

改镜头表/台词只改本文件，各脚本（渲染/配音/混音/字幕）自动对齐。
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
TR = 0.5

# ------------------------------------------------------------------ 镜头表
SHOTS = [
    # ============ 第一幕 · 钩子 · 0:00–0:35（示例，替换为你的故事） ============
    dict(id="s01", src="#title", dur=6.0, motion="hold", subs=[]),   # 片名字幕卡
    dict(id="s02", src="#black", dur=3.0, motion="hold", subs=[]),   # 黑场
    dict(id="s03", src="镜头/S02-点赞特写.png", dur=4.5, motion="in",
         subs=[(0.3, 3.6, "Narr", "旁白示例：他习惯在社交平台上展示阳光的一面。")]),
    # ... 按"镜号 | 时间 | 景别 | 时长 | 画面 | 声音 | 字幕"逐镜填充
]

# ------------------------------------------------------------------ 台词（配音）
# (镜号, 镜内偏移s, 时长上限s, 说话人, 文本) —— 说话人须与音色表一致
LINES = [
    ("s03", 0.3, 3.6, "Narr", "旁白示例：他习惯在社交平台上展示阳光的一面。"),
    ("s09", 0.3, 4.7, "VM",  "虚拟自我：别人都能做到，为什么你不行？"),
    ("s18", 0.3, 6.1, "FR",  "朋友：你是不是一直觉得，只有表现得足够好，别人才会喜欢你？"),
    # ...
]

# ------------------------------------------------------------------ 音效
# (镜号, 镜内偏移s, 音效名) —— 由 sfx_gen.py 程序化合成、mix 按此落位
SFX = [
    ("s03", 0.2, "phone_ping"),      # 手机提示音 ×3（密集但空洞）
    ("s07", 0.0, "heartbeat_low"),   # 低频心跳铺底
    ("s13", 1.0, "glass_warm"),      # 镜面浮现 / 多重回声（顺序逼近）
    ("s36", 0.0, "ambient_dusk"),    # 收尾环境声
]

# ------------------------------------------------------------------ 时间轴解析
def timeline():
    """绝对时间轴：把 (镜号, 偏移) 解析为绝对秒。总长 = Σdur − ΣTR。"""
    tl, t = {}, 0.0
    prev_id = None
    for sh in SHOTS:
        dur = sh["dur"]
        cut = TR if prev_id is not None else 0.0   # 首镜不扣
        tl[sh["id"]] = dict(start=t - cut, dur=dur)
        t += dur - cut
        prev_id = sh["id"]
    return tl

if __name__ == "__main__":
    tl = timeline()
    print(json.dumps({k: dict(v, end=v["start"] + v["dur"]) for k, v in tl.items()},
                     ensure_ascii=False, indent=2))
    print("total ≈ %.1fs" % (tl[SHOTS[-1]["id"]]["start"] + SHOTS[-1]["dur"]))
