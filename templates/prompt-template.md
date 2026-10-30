# 分镜出图提示词模板（每条都这样归档）

> 原则：提示词即工程。每条落盘到 `02-提示词/`，标注轮次/目的/参数/产出，全片可复现。

## 模板

```text
【轮次】第 N 轮（开头 / 中间①…④ / 最后）
【目的】一句话：这轮要锁定/生成什么，为什么
【风格前缀】轻薄半赛璐淡彩动漫风格：弱化黑色轮廓线、改用深蓝灰与暖褐彩色线稿，
赛璐平涂阴影上叠加极淡水彩晕染与纸张颗粒纹理，柔和漫射空气光，
朦胧体积光不做强光束，阴影内带微弱环境色晕染，无厚涂笔触，水彩绘本质感
【角色定义】角色名/年龄/发型/校服（+ 原创识别符号，如"左胸校徽空白凹槽"）——跨轮逐字复用
【画面】具体构图：景别、人物动作与表情、光源与色温、明暗对照关系、留白用途
【技术参数】分辨率(如1280×720) / 步数(≈25) / CFG / 种子(固定)
【产出】04-分镜图/镜头/Sxx-名称.png
```

## 示例（高潮镜：明暗分屏）

```text
[风格前缀] 左右分屏：左侧冷色现实中疲惫的林一（黑短碎发、深蓝水手领校服、
左胸校徽空白凹槽、眼下淡淡青黑），右侧明亮完美的一林（同脸同身高、头发一丝不乱、
全身青蓝色柔光描边、校徽发光圆环），中缝是一道屏幕光带，情绪压抑，16:9，无文字。
```

## 负面提示词（全轮通用）

```text
文字, 汉字, 水印, 署名, 真实学校标识, 品牌logo, 二次元知名IP角色, 崩坏的手,
多指, 多余肢体, 畸变脸, 血腥, 恐怖, 成人内容, 低清, 噪点, 过饱和, 粗糙黑线, 厚涂, 油画笔触
```

## 跨工具迁移风格后缀

```text
(masterpiece, best quality, soft semi-cel anime, colored lineart instead of black,
light watercolor wash over cel shading, paper grain texture, diffused ambient light,
hazy soft volumetric light, subtle ambient color bleed in shadows, no thick impasto,
hand-drawn picture-book feel, chinese high school setting) --ar 16:9
```
