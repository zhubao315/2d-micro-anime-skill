#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2D 网格形变引擎（Live2D 风格的骨骼 / 局部形变）。

把一张插画当作一张可形变的皮肤：
  - 每个 Deformer（形变器）有一个支点 pivot、作用半径 sigma、以及变换；
  - 各形变器按高斯权重平滑融合，得到全图位移场；
  - 依据位移场对原图做双线性重采样，得到「角色在动、背景基本不动」的一帧。

这样得到的是真正的角色表演（呼吸 / 点头 / 转头 / 抬手 / 眨眼挤压），
不是把整张图片平移缩放。

性能：权重图与网格只按镜头计算一次（支点/半径固定），每帧只更新变换参数、
按形变器影响范围的包围盒重采样，单帧约几十毫秒。
"""
import numpy as np


def _bilinear(img, xs, ys):
    """在 img(H,W,C) 上按浮点坐标 xs,ys(H,W) 双线性采样。"""
    H, W = img.shape[:2]
    xs = np.clip(xs, 0, W - 1.001)
    ys = np.clip(ys, 0, H - 1.001)
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    x1 = x0 + 1
    y1 = y0 + 1
    wx = (xs - x0)[..., None]
    wy = (ys - y0)[..., None]
    a = img[y0, x0]
    b = img[y0, x1]
    c = img[y1, x0]
    d = img[y1, x1]
    top = a + (b - a) * wx
    bot = c + (d - c) * wx
    return top + (bot - top) * wy


class Deformer:
    """一个局部形变器。

    kind:
      'translate' : 平移 (tx,ty)
      'affine'    : 绕 pivot 旋转 angle(deg) + 缩放 (sx,sy) + 平移 (tx,ty)
      'squash'    : 绕 pivot 压缩 (sy 竖向, sx 横向)，用于眨眼 / 呼吸挤压
      'bend'      : 越靠近 pivot 上方横移越多（转身 / 侧倾 / 头发摆动）
    """

    def __init__(self, pivot, sigma, kind="translate", tx=0.0, ty=0.0,
                 angle=0.0, sx=1.0, sy=1.0, amount=0.0):
        self.pivot = tuple(pivot)
        self.sigma = float(sigma)
        self.kind = kind
        self.tx, self.ty = float(tx), float(ty)
        self.angle = float(angle)
        self.sx, self.sy = float(sx), float(sy)
        self.amount = float(amount)

    def set(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        return self

    def is_identity(self):
        return (self.tx == 0 and self.ty == 0 and self.angle == 0
                and self.sx == 1.0 and self.sy == 1.0 and self.amount == 0.0)

    def field(self, xx, yy):
        px, py = self.pivot
        if self.kind == "translate":
            return np.full_like(xx, self.tx), np.full_like(yy, self.ty)
        if self.kind == "affine":
            a = np.deg2rad(self.angle)
            ca, sa = np.cos(a), np.sin(a)
            rx = (xx - px) * self.sx
            ry = (yy - py) * self.sy
            nx = ca * rx - sa * ry + px + self.tx
            ny = sa * rx + ca * ry + py + self.ty
            return nx - xx, ny - yy
        if self.kind == "squash":
            nx = xx + (xx - px) * (self.sx - 1.0) + self.tx
            ny = py + (yy - py) * self.sy + self.ty
            return nx - xx, ny - yy
        if self.kind == "bend":
            span = max(1.0, self.sigma)
            t = np.clip((py - yy) / span, -1.5, 1.5)
            return self.amount * t + self.tx, np.zeros_like(yy) + self.ty
        return np.zeros_like(xx), np.zeros_like(yy)


class WarpRig:
    """固定支点/半径的形变组；每帧只改参数，按包围盒重采样。"""

    def __init__(self, W, H, deformers, margin=2.6):
        self.W, self.H = W, H
        self.deformers = deformers
        self.margin = margin
        self.xx, self.yy = np.meshgrid(
            np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        self._weights = []
        for d in deformers:
            px, py = d.pivot
            r2 = (self.xx - px) ** 2 + (self.yy - py) ** 2
            self._weights.append(
                np.exp(-r2 / (2.0 * d.sigma * d.sigma)).astype(np.float32))
        # 影响范围的包围盒
        x0, y0, x1, y1 = W, H, 0, 0
        for d in deformers:
            px, py = d.pivot
            r = d.sigma * margin
            x0 = min(x0, px - r); x1 = max(x1, px + r)
            y0 = min(y0, py - r); y1 = max(y1, py + r)
        self.bbox = (max(0, int(x0)), max(0, int(y0)),
                     min(W, int(x1)), min(H, int(y1)))

    def params(self):
        return [(d.tx, d.ty, d.angle, d.sx, d.sy, d.amount) for d in self.deformers]

    def restore(self, params):
        for d, p in zip(self.deformers, params):
            d.tx, d.ty, d.angle, d.sx, d.sy, d.amount = p

    def apply(self, img):
        bx0, by0, bx1, by1 = self.bbox
        if bx1 <= bx0 or by1 <= by0:
            return img
        xx = self.xx[by0:by1, bx0:bx1]
        yy = self.yy[by0:by1, bx0:bx1]
        num_x = np.zeros_like(xx)
        num_y = np.zeros_like(yy)
        wsum = np.zeros_like(xx)
        for d, wfull in zip(self.deformers, self._weights):
            if (d.tx == 0 and d.ty == 0 and d.angle == 0
                    and d.sx == 1.0 and d.sy == 1.0 and d.amount == 0.0):
                continue
            w = wfull[by0:by1, bx0:bx1]
            dx, dy = d.field(xx, yy)
            num_x += w * dx
            num_y += w * dy
            wsum += w
        dx = num_x / (wsum + 1e-6)
        dy = num_y / (wsum + 1e-6)
        sx = xx - dx - bx0
        sy = yy - dy - by0
        patch = _bilinear(img[by0:by1, bx0:bx1], sx, sy)
        out = img.copy()
        out[by0:by1, bx0:bx1] = np.clip(patch, 0, 255)
        return out


def ease(t, p=2.0):
    """0..1 缓入缓出（默认二次）。"""
    t = min(1.0, max(0.0, t))
    if t < 0.5:
        return 0.5 * (2 * t) ** p
    return 1 - 0.5 * (2 * (1 - t)) ** p


def ease_out(t, p=2.0):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** p


def ease_in(t, p=2.0):
    t = min(1.0, max(0.0, t))
    return t ** p


def seg(t, start, end):
    """把绝对进度 t 映射到 [start,end] 区间内的 0..1 局部进度。"""
    if end <= start:
        return 1.0 if t >= end else 0.0
    return min(1.0, max(0.0, (t - start) / (end - start)))
