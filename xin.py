"""圆弧心笺：两段半圆与两条直线，成为一枚会轻轻跳动的珐琅心。

运行 ``python xin.py``。C 换色；G 重描轮廓；↑↓ 心跳速度；点击心面寄出微光。
保留原作的圆弧构造，只用 Python 标准库和项目内的共享舞台。
"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


RADIUS = 110
TRACE_SECONDS = 4.2
BURST_SECONDS = 2.4
# 名称、桌面、纸张、心面暗部、心面亮部、反光、金属边、墨色。
PALETTES = (
    ("朱砂情书", "#E7DED0", "#FBF3E3", "#731D36", "#DA5964", "#FFDBBD", "#BE9354", "#86634D"),
    ("青瓷来信", "#DCE6DF", "#F4F5E7", "#174F55", "#70AAA0", "#E0F3CF", "#B09B62", "#52776C"),
    ("暮紫心语", "#E4DEE8", "#F7F0EA", "#483454", "#A980A7", "#FBE2DC", "#B6A07A", "#79647D"),
)


def heart_point(progress, radius=RADIUS):
    """沿原作轮廓等速行走：半圆、直线、直线、半圆；0 与 1 闭合。

    两个圆心在 (±r/√2, 0)，圆弧半径 r，每条直线长度为 2r。
    总周长 r(2π+4)，所以重描笔尖经过直线与圆弧时不会忽快忽慢。
    """
    distance = max(0, min(1, progress)) * (2 * math.pi + 4)
    q = radius / math.sqrt(2)
    if distance <= math.pi:
        return polar(radius, 3 * math.pi / 4 - distance, q, 0)
    if distance <= math.pi + 2:
        amount = (distance - math.pi) / 2
        return 2 * q * (1 - amount), -q - 2 * q * amount
    if distance <= math.pi + 4:
        amount = (distance - math.pi - 2) / 2
        return -2 * q * amount, -3 * q + 2 * q * amount
    return polar(radius, 5 * math.pi / 4 - (distance - math.pi - 4), -q, 0)


def inside_heart(x, y, radius=RADIUS):
    """圆弧与直线的解析内点判定；不把两瓣之间的留白当作心面。"""
    q = radius / math.sqrt(2)
    if y < -3 * q or y > radius:
        return False
    if y < -q:
        return abs(x) <= y + 3 * q
    if y <= q:
        return abs(x) <= q + math.sqrt(max(0, radius * radius - y * y))
    return (abs(x) - q) ** 2 + y * y <= radius * radius


class ArcHeart:
    def __init__(self):
        self.stage = Stage("圆弧红心", "C 心笺配色    G 重描圆弧    ↑↓ 心跳速度    点击心面 微光",
                           PALETTES[0][1], PALETTES[0][6], light=True)
        self.paint = Paint(self.stage, "arc-heart")
        self.paint.paper = Paint(self.stage, "arc-heart-paper")
        self.paint.effects = Paint(self.stage, "arc-heart-effects")
        self.paint.signature = None
        # 在圆弧和直线的连接处保留精确顶点，缩放后仍是闭合心形。
        perimeter = 2 * math.pi + 4
        self.parameters = tuple(sorted({i / 100 for i in range(101)} |
                                      {math.pi / perimeter, .5, (math.pi + 4) / perimeter}))
        self.contour = tuple(heart_point(t) for t in self.parameters)
        self.shells = tuple(tuple((x * (1 - i / 68) - 29 * i / 68,
                                  y * (1 - i / 68) + 12 * i / 68)
                                 for x, y in self.contour) for i in range(1, 65))
        rng = random.Random(108)
        self.fibers = tuple((rng.uniform(-450, 450), rng.uniform(-265, 245),
                             rng.uniform(2, 7)) for _ in range(48))
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.cycle_palette, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.replay, key)
        self.stage.screen.onkey(lambda: self.change_speed(.15), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.15), "Down")
        self.stage.screen.onclick(self.pulse)

    def reset(self):
        self.time = self.phase = 0
        self.speed = 1
        self.palette = 0
        self.progress = 1
        self.burst_age = None
        self.burst_origin = (0, 0)

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def change_speed(self, amount):
        self.speed = max(.25, min(2, round(self.speed + amount, 2)))

    def replay(self):
        if not self.stage.paused:
            self.progress = 0
            self.burst_age = None

    def pose(self):
        # 一次短促收缩与较轻的第二拍；幅度克制，静态展示也保持清晰。
        wave = max(0, math.sin(self.phase)) ** 8
        echo = max(0, math.sin(self.phase - .65)) ** 14
        extra = 0 if self.burst_age is None else \
            .035 * math.sin(self.burst_age * math.pi * 3) * math.exp(-self.burst_age * 1.8)
        return 0, 55, 1 + .014 * wave + .006 * echo + extra

    def pulse(self, x, y):
        if self.stage.paused or self.progress < 1:
            return
        x, y = self.stage.point(x, y)
        cx, cy, zoom = self.pose()
        u, v = (x - cx) / zoom, (y - cy) / zoom
        if self.stage.in_scene(x, y) and inside_heart(u, v):
            self.burst_age = 0
            self.burst_origin = (u, v)

    def paper(self, colors):
        signature = (self.palette, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        self.paint.signature = signature
        _, ground, paper, dark, light, glint, metal, ink = colors
        p = self.paint.paper
        p.begin()
        p.gradient(mix(ground, paper, .43), ground)
        for x, y, width in self.fibers:
            p.line([(x, y), (x + width, y + .5)], mix(ground, ink, .065))
        # 背面的信封和斜角折线让卡片具有实体厚度。
        envelope = [(-330, 160), (300, 212), (338, -217), (-300, -257)]
        p.poly([(x + 8, y - 7) for x, y in envelope], mix(ground, ink, .10))
        p.poly(envelope, mix(ground, metal, .17), mix(ground, metal, .28))
        p.line([envelope[0], (22, -54), envelope[1]], mix(ground, ink, .23), 1.1)
        p.line([envelope[3], (22, -54), envelope[2]], mix(ground, paper, .6), 1.2)
        for inset in range(7, 0, -1):
            p.rect(-285 + inset, 224 - inset, 285 + inset, -228 - inset,
                   mix(ground, ink, .024 * (8 - inset)))
        p.rect(-285, 224, 285, -228, paper)
        p.rect(-274, 213, 274, -217, "", mix(paper, metal, .42))
        p.rect(-269, 208, 269, -212, "", mix(paper, metal, .20))
        # 角花由小圆弧与短线构成，与主画面的圆弧主题呼应。
        for side in (-1, 1):
            for sign in (-1, 1):
                x, y = side * 259, sign * 195
                p.line([(x - side * 22, y), (x, y), (x, y - sign * 22)], metal, 1.1)
                p.line([polar(13, angle, x - side * 9, y - sign * 9)
                        for angle in [i * math.pi / 12 for i in range(25)]], mix(paper, metal, .56), .7)
                p.circle(x - side * 9, y - sign * 9, 1.8, metal)
        # 细碎纸纹只在边缘可见，不抢心面高光。
        for index in range(24):
            y = -175 + index * 15
            p.line([(-249, y), (-211, y + .8)], mix(paper, ink, .035))
            p.line([(209, y), (249, y - .6)], mix(paper, ink, .035))
        p.line([(-74, -201), (-29, -201)], mix(paper, metal, .60))
        p.line([(29, -201), (74, -201)], mix(paper, metal, .60))
        p.text(0, -201, "心 笺", ink, 9)
        p.text(-432, 196, "圆弧", ink, 17, "w")
        p.text(-432, 170, "成心", ink, 17, "w")
        p.line([(-431, 144), (-395, 144)], metal, 1.8)
        p.text(-432, 122, "ARC LETTER", mix(ground, ink, .68), 8, "w")
        p.text(430, -210, "TWO ARCS", ink, 9, "e")
        p.text(430, -231, "ONE HEART", mix(ground, ink, .65), 8, "e")
        p.text(-430, -239, "将心意，写进圆弧。", mix(ground, ink, .67), 9, "w")
        p.end()
        self.paint.shades = tuple(mix(dark, light, .12 + .88 * math.sin(i / 68 * math.pi / 2) ** .72)
                                  for i in range(1, 65))

    def enamel(self, p, colors):
        _, _, paper, dark, light, glint, metal, ink = colors
        # 从边缘暗红到左上方柔光，所有曲面层预先计算并由 Paint 统一缩放。
        p.poly([(x + 5, y - 7) for x, y in self.contour], mix(paper, ink, .13))
        p.poly(self.contour, mix(metal, dark, .16), mix(metal, paper, .40), 1.1)
        for points, shade in zip(self.shells, self.paint.shades):
            p.poly(points, shade)
        p.line(self.contour, metal, 2.0)
        p.line([(x * .983, y * .983) for x, y in self.contour], mix(dark, metal, .40), 1)
        # 左瓣柔和的弧形反光。宽反光逐层变细，形成透明釉面的亮边。
        q = RADIUS / math.sqrt(2)
        for band in range(8):
            radius = RADIUS - 18 - band * .9
            curve = [polar(radius, .70 + i * .024, -q, 0) for i in range(62)]
            p.line(curve, mix(light, glint, .10 + .25 * math.sin((band + 1) * math.pi / 9)), 1.5)
        curve = [polar(RADIUS - 12, .87 + i * .035, -q, 0) for i in range(36)]
        p.line(curve, mix(light, glint, .54), 2.1)
        p.line([(-113, -95), (-85, -123), (-55, -153)], mix(dark, light, .63), 1.1)
        p.line([(147, 57), (153, 41), (155, 27)], mix(dark, glint, .28), 1, smooth=True)
        # 两处微小反光与低对比压纹，把大面积色面收束为一枚珐琅饰物。
        p.oval(-110, 77, 8, 2.4, mix(light, glint, .67))
        p.circle(-125, 67, 1.4, mix(light, glint, .69))
        p.line([(-18, -64), (0, -83), (18, -64)], mix(light, dark, .13), 1.1)
        p.line([(-12, -67), (0, -79), (12, -67)], mix(light, glint, .10), .7)

    def tracing(self, p, colors):
        _, _, paper, dark, light, glint, metal, _ = colors
        p.line(self.contour, mix(paper, metal, .19), 1, dash=(2, 6))
        q = RADIUS / math.sqrt(2)
        for cx in (-q, q):
            p.circle(cx, 0, 2, mix(paper, metal, .55))
        path = [heart_point(t) for t in self.parameters if t < self.progress]
        tip = heart_point(self.progress)
        path.append(tip)
        if len(path) > 1:
            p.line(path, mix(dark, metal, .36), 3.5)
            p.line(path, mix(metal, glint, .35), 1.1)
        p.circle(*tip, 4, mix(paper, metal, .38))
        p.circle(*tip, 2, glint)

    def effects(self, colors):
        p = self.paint.effects
        p.begin()
        if self.burst_age is not None:
            age = self.burst_age
            fade = (1 - age / BURST_SECONDS) ** 1.5
            cx, cy, zoom = self.pose()
            p.transform(zoom, cx, cy)
            x, y = self.burst_origin
            # 固定十二枚微光，连续点击只重新开始这一组，不追加画布对象。
            for i in range(12):
                angle = math.tau * i / 12 + .17
                reach = 7 + age * (24 + i % 3 * 7)
                px, py = polar(reach, angle, x, y)
                py += age * 13
                if inside_heart(px, py):
                    p.star(px, py, (2 + i % 3 * .7) * fade + .2,
                           mix(colors[4], colors[5], fade * .90), angle=angle + age)
        p.end()

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.phase = (self.phase + dt * self.speed * math.tau * .7) % math.tau
            self.progress = min(1, self.progress + dt / TRACE_SECONDS)
            if self.burst_age is not None:
                self.burst_age += dt
                if self.burst_age >= BURST_SECONDS:
                    self.burst_age = None
        colors = PALETTES[self.palette]
        self.paper(colors)
        p = self.paint
        p.begin()
        cx, cy, zoom = self.pose()
        p.transform(zoom, cx, cy)
        if self.progress >= 1:
            self.enamel(p, colors)
        else:
            self.tracing(p, colors)
        p.end()
        self.effects(colors)
        mode = "两段半圆 + 两条直线" if self.progress == 1 else f"圆弧重描 {self.progress:.0%}"
        self.stage.hud(f"{colors[0]} · {mode}    /    心跳 {self.speed:.2g}×")


if __name__ == "__main__":
    app = ArcHeart()
    app.stage.run(app.frame, app.reset)
