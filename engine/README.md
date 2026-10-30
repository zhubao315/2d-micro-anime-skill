# engine/ · 自研 2D 网格形变动画引擎（可直接复用）

从《拥抱不完美的自己》项目中提炼的**通用核心**（Python + NumPy，无第三方依赖）：

| 文件 | 作用 |
|---|---|
| `warp.py` | `Deformer`（局部形变器：translate / affine / squash / bend）+ 高斯加权位移场 + 双线性重采样 |
| `render.py` | 把「逐镜仿射相机（推近/横移/旋转）」与「角色形变」合成成**一次重采样**，逐帧渲染 |

## 核心思想

把一张插画当作一张**可形变的皮肤**：

- 每个 `Deformer` 有支点 `pivot`、作用半径 `sigma`、以及变换（平移/旋转缩放/压缩/弯曲）；
- 各形变器按**高斯权重**平滑融合为全图位移场 → 只对角色局部形变，背景基本不动；
- 相机运动负责「镜头在动」，形变器负责「角色在表演」，两者一次采样完成（单帧约几十毫秒）。

这样得到的是**真正的角色表演**（呼吸 / 摆动 / 点头 / 抬手 / 捂耳 / 奔跑），
而不是把整张图平移缩放的 Ken Burns 推拉——后者正是「PPT 感」的根源。

## 快速验证

```bash
cd engine
python3 -c "
import numpy as np
from warp import Deformer
from render import render_frame

img = np.full((720, 1280, 3), 200, dtype=np.uint8)
img[300:420, 560:720] = [90, 120, 160]        # 假设的角色块
grid = None                                    # render_frame 内部按需建格
from render import _grid
grid = _grid(1280, 720)

# 呼吸：胸口支点竖向 squash；相机缓慢推近
d = Deformer(pivot=(640, 400), sigma=120, kind='squash', sy=1.04)
cam = dict(pivot=(640, 400), zoom=1.06)
frame = render_frame(img, [d], cam, grid)
print(frame.shape, frame.dtype)   # (720, 1280, 3) uint8
"
```

## 与本项目模板的关系

- `templates/scene-template.py`：镜头/台词/音效**单一事实源**（SHOTS / LINES / SFX / TR）；
- `templates/rig_template.py`：逐镜「导演表」（焦点、相机模式、表演预设）→ 装配 Deformer 列表；
- `references/03-animation.md`：完整渲染流水线（逐段编码 → 交叉溶解 → 光效/纸纹 → 字幕 → 混乐）。
