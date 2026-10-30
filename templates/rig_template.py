#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rig_template.py · 逐镜"导演表" + 角色表演绑定模板。

每个镜头给出：焦点 focal、相机模式 cam、表演预设 perf、可选的头/手锚点与 shake。
Rig 依据导演表装配一组 Deformer（见 engine/warp.py）；update(t) 按归一化进度 t∈[0,1]
更新参数，产生呼吸/摆身/点头/抬手/捂耳/奔跑等真正的角色表演（非整图平移）。
坐标均为归一化 0..1，运行时换算到像素。
"""
import math
import numpy as np

from warp import Deformer, ease, ease_out, ease_in, seg   # engine/ 中的通用核心

def kf(t, knots):
    """分段关键帧插值：knots=[(t,value),...]（缓入缓出），用于预备→动作→缓冲→停顿。"""
    if t <= knots[0][0]:
        return knots[0][1]
    if t >= knots[-1][0]:
        return knots[-1][1]
    for (t0, v0), (t1, v1) in zip(knots[:-1], knots[1:]):
        if t0 <= t <= t1:
            w = ease((t - t0) / (t1 - t0))
            return v0 + (v1 - v0) * w
    return knots[-1][1]

# ------------------------------------------------------------------ 导演表
# cam: (z0, z1, panx, pany)  z=首尾缩放; pan 为整幅占比(可到 ±0.05), 需配合 pan=True
# perf: idle / sit / write / hand / phone / lookup / reach / cover / smile / run / abstract / still
DIR = {
    "s03": dict(focal=(0.36, 0.52), cam=(1.02, 1.12, -0.02, 0), perf="phone",
                arm=(0.40, 0.60)),
    "s07": dict(focal=(0.28, 0.38), cam=(1.16, 1.04, 0.04, 0.02), perf="slump",
                head=(0.27, 0.34), beat=0.56),
    "s13": dict(focal=(0.30, 0.50), cam=(1.00, 1.14, 0.03, 0), perf="cover",
                head=(0.30, 0.44), beat=0.52,
                shake=[(0.0, 2.8), (0.10, 3.0), (0.85, 3.0), (1.0, 2.6)]),
    # ... 逐镜填写；DEFAULT 兜底
}
DEFAULT = dict(focal=(0.5, 0.5), cam=(1.00, 1.08, 0, 0), perf="idle")
S = 2.1          # 表演幅度总增益（宁可略小，不可抽搐）
BREATH = 0.014   # 呼吸竖向 squash 幅度（相对）


# ------------------------------------------------------------------ Rig 装配
def build_rig(shot_id, img_w, img_h, dur):
    """依据导演表装配一组 Deformer；返回 update(t) 用于逐帧驱动。"""
    d = DIR.get(shot_id, DEFAULT)
    z0, z1, panx, pany = d["cam"]
    fx0, fy0 = d["focal"]
    W, H = float(img_w), float(img_h)

    def update(t):
        p = t / dur if dur > 0 else 0.0
        cam = dict(pivot=(int(fx0 * W), int(fy0 * H)),
                   zoom=1.0 + (z0 + (z1 - z0) * p) - 1.0,
                   zoomx=1.0 + (z0 + (z1 - z0) * p) - 1.0,
                   zoomy=1.0 + (z0 + (z1 - z0) * p) - 1.0,
                   tx=panx * W * seg(p, 0.15, 0.9),
                   ty=pany * H * seg(p, 0.15, 0.9), angle=0.0)
        # 微动示例：胸口支点呼吸 squash + 头锚点轻微点头
        breath = BREATH * S * math.sin(p * 2 * math.pi * dur / 3.2)  # ~3.2s 呼吸周期
        deformers = [
            Deformer(pivot=(int(0.5 * W), int(0.62 * H)), sigma=int(0.18 * W),
                     kind="squash", sy=1.0 + breath, sx=1.0 - breath * 0.6),
        ]
        if "head" in d:
            hx, hy = d["head"]
            nod = kf(p, [(0.0, 0.0), (d.get("beat", 0.5), 0.6), (1.0, 0.25)]) * S * 0.4
            deformers.append(Deformer(pivot=(int(hx * W), int(hy * H)),
                                      sigma=int(0.10 * W), kind="bend", amount=nod))
        # 手持晃动包络：多锚点小幅 translate（幅度见 shake 关键帧）
        if "shake" in d:
            amp = kf(p, d["shake"])
            deformers.append(Deformer(pivot=(int(0.5 * W), int(0.5 * H)),
                                      sigma=int(0.45 * W), kind="translate",
                                      tx=0.004 * W * amp * S / 2.1))
        return cam, deformers

    return update
