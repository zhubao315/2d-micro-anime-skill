#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐帧渲染：把「相机变换」与「角色形变」合成成一次重采样。

顺序（输出像素 -> 源图坐标）：
  1. 逆相机：把输出像素映回「镜头空间」（缩放 / 旋转 / 平移，绕焦点）；
  2. 逆形变：减去各形变器在镜头空间的位移场（近似逆）；
  3. 双线性采样原图。

相机运动负责「镜头在动」，形变器负责「角色在表演」，两者一次采样完成，速度快。
"""
import numpy as np

from warp import _bilinear


def _grid(W, H):
    xx, yy = np.meshgrid(np.arange(W, dtype=np.float32),
                         np.arange(H, dtype=np.float32))
    return xx, yy


def render_frame(img, deformers, cam, grid):
    """img: HxWx3 float32/uint8；deformers: Deformer 列表；cam: dict。返回 uint8 HxWx3。"""
    xx, yy = grid
    px, py = cam["pivot"]
    a = np.deg2rad(cam.get("angle", 0.0))
    ca, sa = np.cos(a), np.sin(a)
    zx = cam.get("zoomx", cam.get("zoom", 1.0))
    zy = cam.get("zoomy", cam.get("zoom", 1.0))
    # 逆相机
    dx = xx - px - cam.get("tx", 0.0)
    dy = yy - py - cam.get("ty", 0.0)
    rx = (ca * dx + sa * dy) / zx
    ry = (-sa * dx + ca * dy) / zy
    u = rx + px
    v = ry + py
    # 逆形变（近似：out = in + field(in) => in ~= out - field(out)）
    offx = None
    offy = None
    for d in deformers:
        if d.is_identity():
            continue
        fx, fy = d.field(u, v)
        offx = fx if offx is None else offx + fx
        offy = fy if offy is None else offy + fy
    if offx is not None:
        u = u - offx
        v = v - offy
    out = _bilinear(img, u, v)
    return np.clip(out, 0, 255).astype(np.uint8)
