"""四弧生叶：保留原作的四条半圆交叠结构，画成一枚带露水的植物标本。

直接运行 ``python yeizi.py``；C 换色，V 切换叶脉，点击叶面落下一滴露水。
圆弧、叶脉和纸张纹理都由代码绘制，只使用 Python 标准库。
"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、纸色、底色、叶影、叶光、脉色、题签色。
PALETTES = (
    ("青玉", "#F5F5E9", "#E2EBDC", "#174E48", "#8DB890", "#CEE1AC", "#41796B"),
    ("鼠尾草", "#F4F1E6", "#E7E6D7", "#415C55", "#B6C6A0", "#DFE3B8", "#657668"),
    ("秋铜", "#F8F1E2", "#EAE0CB", "#734D38", "#D6A96C", "#F6D8A2", "#8E6649"),
)
LEAVES = ((276, math.pi / 4), (284, 3 * math.pi / 4),
          (258, 5 * math.pi / 4), (270, 7 * math.pi / 4))
DEW_LIFETIME = 2.8
DEW_SLOTS = 6
SHADE_BANDS = 24
ARC_STEPS = 40


def half_width(distance, length):
    """相交圆的透镜半宽；两侧轮廓仍是原作的四分之一圆弧。"""
    return max(0, math.sqrt(max(0, length * length / 2 -
                               (distance - length / 2) ** 2)) - length / 2)


def leaf_strip(length, lower, upper):
    samples = tuple((length * i / ARC_STEPS, half_width(length * i / ARC_STEPS, length))
                    for i in range(ARC_STEPS + 1))
    return tuple((u, width * lower) for u, width in samples) + tuple(
        (u, width * upper) for u, width in reversed(samples))


class ArcLeaves:
    def __init__(self):
        self.stage = Stage("圆弧叶影", "C 植物配色    V 叶脉    点击叶面 落露",
                           "#F5F5E9", "#41796B", light=True)
        self.paint = Paint(self.stage, "arc-leaves")
        self.paint.backdrop = Paint(self.stage, "arc-leaves-paper")
        self.paint.signature = None
        self.strips = tuple(tuple(leaf_strip(length, -1 + 2 * band / SHADE_BANDS,
                                           -1 + 2 * (band + 1) / SHADE_BANDS)
                                  for band in range(SHADE_BANDS)) for length, _ in LEAVES)
        self.contours = tuple(leaf_strip(length, -1, 1) for length, _ in LEAVES)
        rng = random.Random(417)
        self.fibers = tuple((rng.uniform(-465, 465), rng.uniform(-275, 254),
                             rng.uniform(2, 7)) for _ in range(64))
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.cycle_palette, key)
        for key in ("v", "V"):
            self.stage.screen.onkey(self.toggle_veins, key)
        self.stage.screen.onclick(self.add_dew)

    def reset(self):
        self.time, self.palette, self.veins = 0, 0, True
        self.drops, self.next_drop = [None] * DEW_SLOTS, 0

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def toggle_veins(self):
        self.veins = not self.veins

    def pose(self, index):
        length, angle = LEAVES[index]
        return length, angle + .016 * math.sin(self.time * .65 + index * .8)

    def project(self, points, angle, shadow=False):
        co, si = math.cos(angle), math.sin(angle)
        dx, dy = (5, -4) if shadow else (0, 0)
        return [(15 + u * co - v * si + dx, 13 + u * si + v * co + dy)
                for u, v in points]

    def add_dew(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        # 水珠只落在叶片内部，采用叶片局部坐标，随后随叶片一起轻动。
        for index in reversed(range(4)):
            length, angle = self.pose(index)
            dx, dy = x - 15, y - 13
            u = dx * math.cos(angle) + dy * math.sin(angle)
            v = -dx * math.sin(angle) + dy * math.cos(angle)
            if 12 < u < length - 12 and abs(v) + 5 < half_width(u, length):
                self.drops[self.next_drop] = (index, u, v, 0)
                self.next_drop = (self.next_drop + 1) % DEW_SLOTS
                return

    def draw_paper(self, colors):
        p = self.paint.backdrop
        signature = (self.palette, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        self.paint.signature = signature
        _, paper, ground, dark, light, _, accent = colors
        p.begin()
        p.gradient(paper, ground)
        for radius in range(250, 120, -14):
            p.oval(15, 15, radius * 1.26, radius * .84,
                   mix(paper, ground, .20 + (250 - radius) / 600))
        for x, y, width in self.fibers:
            p.line([(x, y), (x + width, y + .7)], mix(paper, ground, .70))
        # 两侧低对比度的蕨叶衬景，主叶仍保留足够的留白。
        for x, y, angle, length in ((-366, -189, 1.31, 300), (-414, -100, 1.05, 215),
                                     (354, -205, 1.84, 300), (402, -84, 2.04, 185)):
            axis = [polar(length * i / 20, angle + .08 * i / 20, x, y) for i in range(21)]
            ink = mix(ground, accent, .16)
            p.line(axis, ink, 1)
            for i in range(2, 11):
                u = length * i / 12
                bx, by = polar(u, angle + .08 * i / 12, x, y)
                size = (1 - i / 13) * 35 + 8
                for side in (-1, 1):
                    direction = angle + side * .86
                    tip = polar(size, direction, bx, by)
                    left = polar(size * .5, direction - .22, bx, by)
                    right = polar(size * .5, direction + .22, bx, by)
                    p.poly([(bx, by), left, tip, right], mix(ground, light, .27), smooth=True)
        p.line([(-438, 218), (-405, 218)], accent, 2)
        p.text(-438, 194, "四弧 / 一叶", accent, 12, "w")
        p.text(-438, 174, "CIRCULAR BOTANY", mix(ground, dark, .46), 8, "w")
        p.text(-438, -239, "四道圆弧，向光而生。", mix(ground, dark, .65), 10, "w")
        p.text(436, -232, "ARC STUDY   04", accent, 9, "e")
        p.text(436, -250, "叶面轻触 · 露水成珠", mix(ground, dark, .5), 8, "e")
        p.end()

    def draw_leaf(self, index, colors):
        p = self.paint
        _, _, ground, dark, light, vein, _ = colors
        length, angle = self.pose(index)
        transform = lambda points: self.project(points, angle)
        p.poly(self.project(self.contours[index], angle, shadow=True), mix(ground, dark, .10))
        # 多条圆弧曲面带模拟柔和侧光，保持每条外边界的圆弧来源。
        for band, points in enumerate(self.strips[index]):
            fraction = (band + .5) / SHADE_BANDS
            brightness = .18 + .69 * math.sin(math.pi * fraction) ** .85
            brightness *= (1, .88, .77, .91)[index]
            p.poly(transform(points), mix(dark, light, brightness))
        edge = [(length * i / ARC_STEPS, half_width(length * i / ARC_STEPS, length))
                for i in range(ARC_STEPS + 1)]
        p.line(transform(edge), mix(dark, light, .69), 1)
        if self.veins:
            p.line(transform([(0, 0), (length * .52, -1), (length, 0)]), mix(dark, vein, .61), 1.6)
            p.line(transform([(length * .09, 1), (length * .70, 1)]), mix(light, vein, .40), .8)
            for side in (-1, 1):
                for step in range(2, 12):
                    u = length * step / 14
                    end = min(length * .97, u + length * .11)
                    v = half_width(end, length) * side * .88
                    points = [(u, 0), (u + length * .045, v * .70), (end, v)]
                    p.line(transform(points), mix(dark, vein, .29 if side < 0 else .42), .75, smooth=True)
        # 固定的露珠带有暗缘与两点高光，避免把叶片画成发光粒子。
        for fraction, cross, radius in ((.43, -.39, 4), (.68, .39, 2.7), (.79, -.20, 1.7)):
            u = length * fraction
            x, y = transform([(u, half_width(u, length) * cross)])[0]
            p.oval(x + 1, y - 1, radius + .7, radius * .75, mix(dark, light, .25))
            p.oval(x, y, radius, radius * .76, mix(light, vein, .22), mix(light, vein, .65))
            p.circle(x - radius * .30, y + radius * .25, max(.7, radius * .25), "#FBFFF0")

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.drops = [None if drop is None or drop[3] + dt >= DEW_LIFETIME else
                          (*drop[:3], drop[3] + dt) for drop in self.drops]
        colors = PALETTES[self.palette]
        _, _, ground, dark, light, vein, _ = colors
        self.draw_paper(colors)
        p = self.paint
        p.begin()
        p.line([(15, 13), (9, -83), (38, -173), (16, -243)], mix(ground, dark, .30), 5, smooth=True)
        p.line([(15, 13), (9, -83), (38, -173), (16, -243)], mix(dark, light, .45), 2.5, smooth=True)
        for index in (2, 3, 1, 0):
            self.draw_leaf(index, colors)
        p.circle(15, 13, 4.2, mix(dark, light, .35))
        p.circle(14, 15, 1.3, mix(light, vein, .6))
        for drop in self.drops:
            if drop is None:
                continue
            index, u, v, age = drop
            _, angle = self.pose(index)
            x, y = self.project([(u, v)], angle)[0]
            fade = (1 - age / DEW_LIFETIME) ** 1.4
            for ripple in (0, 1):
                radius = 2 + (age * 8 + ripple * 4) % 15
                p.oval(x, y, radius, radius * .52, outline=mix(light, vein, fade * .55))
            p.oval(x, y, 4 * fade + .2, 2.8 * fade + .2, mix(light, vein, fade * .56))
            p.circle(x - fade, y + fade, max(.3, fade), mix(light, "#FFFFFF", fade))
        p.end()
        self.stage.hud(f"{colors[0]} · 四条半圆的交叠，成为四片叶    /    叶脉{'开' if self.veins else '关'}")


if __name__ == "__main__":
    app = ArcLeaves()
    app.stage.run(app.frame, app.reset)
