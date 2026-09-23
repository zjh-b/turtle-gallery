"""脉动伞盖、发光触手与海中浮游物；点击放下一束引路的光。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = [("蓝紫深海", "#75D8EF", "#BC9CEB"), ("珊瑚晚霞", "#F3B1D1", "#F5C99A"),
          ("翡翠微光", "#7CE6CA", "#B8DB92")]


class Jellyfish:
    def __init__(self):
        self.stage = Stage("深海来信", "点击 放置引路光点    C 切换色彩    ↑↓ 调整水流", accent="#8ECFEA")
        self.paint = Paint(self.stage, "jellyfish")
        rng = random.Random(71)
        self.specks = [(rng.uniform(-520, 520), rng.uniform(-290, 280), rng.uniform(0.5, 2), rng.random() * 6)
                       for _ in range(70)]
        self.time, self.theme, self.current = 0, 0, 1
        self.target = None
        self.offset = [0.0, 0.0]
        self.stage.screen.onclick(self.light)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        self.stage.screen.onkey(lambda: self.change_current(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_current(-0.25), "Down")

    def reset(self):
        self.time, self.theme, self.current = 0, 0, 1
        self.target = None
        self.offset = [0.0, 0.0]

    def light(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            self.target = [max(-360, min(360, x)), max(-130, min(200, y)), 6]

    def change_theme(self):
        self.theme = (self.theme + 1) % len(THEMES)

    def change_current(self, amount):
        self.current = max(0.25, min(2.5, self.current + amount))

    def jelly(self, p, x, y, radius, phase, color, depth):
        pulse = 1 + math.sin(self.time * 1.8 + phase) * 0.055
        rx = radius * pulse
        ry = radius * (0.66 - 0.12 * math.sin(self.time * 1.8 + phase))
        # 细触手先画，伞盖覆盖连接处；不同振幅让触手有水流感。
        for i in range(11):
            root_x = x + (i - 5) * rx * 0.15
            length = radius * (1.55 + 0.46 * math.sin(i * 1.9))
            points = []
            for j in range(23):
                t = j / 22
                xx = root_x + math.sin(t * 7 - self.time * 1.6 + phase + i * 0.5) * radius * 0.22 * t
                xx += math.sin(self.time * 0.5 + phase) * t * 14
                points.append((xx, y - length * t))
            p.line(points, mix("#102437", color, depth * (0.48 if i % 2 else 0.8)), 1 if i % 2 else 2, True)
        for i in range(3):
            points = [(x + (i - 1) * rx * 0.22 + math.sin(t * 9 - self.time * 2 + i) * radius * 0.13,
                       y - t * radius * 1.35) for t in [j / 20 for j in range(21)]]
            p.line(points, mix("#13283C", color, depth * 0.3), 6, True)
            p.line(points, mix("#13283C", color, depth * 0.6), 1.4, True)
        for layer in range(9):
            scale = 1 - layer * 0.06
            dome = [(x + rx * scale * math.cos(a), y + ry * scale * math.sin(a) + layer * 0.8)
                    for a in [j * math.pi / 36 for j in range(37)]]
            dome += [(x - rx * scale, y), (x, y - radius * 0.12), (x + rx * scale, y)]
            p.poly(dome, mix("#0B2238", color, depth * (0.10 + layer * 0.025)), smooth=True)
        for k in (-0.68, -0.35, 0, 0.35, 0.68):
            points = [(x + rx * k * math.sin(a), y + ry * math.cos(a)) for a in [j * math.pi / 2 / 22 for j in range(23)]]
            p.line(points, mix("#203349", color, depth * 0.55), 1, True)
        rim = [(x - rx + 2 * rx * j / 44, y - 3 - abs(math.sin(j / 44 * math.pi * 8)) * radius * 0.06)
               for j in range(45)]
        p.line(rim, mix("#2A4560", color, depth), 2, True)
        for i in range(12):
            xx = x - rx * 0.9 + i * rx * 1.8 / 11
            p.circle(xx, y - 4, 1.5, mix("#31506A", "#E4FCFF", depth * 0.8))
        p.oval(x - rx * 0.25, y + ry * 0.7, rx * 0.2, ry * 0.08,
               mix("#16334A", color, depth * 0.8))

    def frame(self, dt):
        self.time += dt * self.current
        if dt > 0:
            if self.target:
                self.target[2] -= dt
                if self.target[2] <= 0:
                    self.target = None
            tx, ty = (self.target[0] * 0.18, self.target[1] * 0.13) if self.target else (0, 0)
            self.offset[0] += (tx - self.offset[0]) * min(1, dt * 0.8)
            self.offset[1] += (ty - self.offset[1]) * min(1, dt * 0.8)
        name, color1, color2 = THEMES[self.theme]
        p = self.paint
        p.begin()
        p.gradient("#071526", "#10354A")
        for i in range(4):
            x = -440 + i * 285
            for j in range(12):
                t = j / 12
                y = 280 - j * 48
                base = mix("#071526", "#10354A", (360 - y) / 720)
                color = mix(base, "#598C9D", 0.10 * (1 - t))
                left = x + t * 65
                width = 35 + t * 55
                p.poly([(left, y), (left + width, y), (left + width + 8, y - 49),
                        (left + 5, y - 49)], color)
        for x, y, size, phase in self.specks:
            yy = (y + self.time * (4 + size) + 295) % 585 - 295
            p.circle(x + math.sin(self.time * 0.5 + phase) * 8, yy, size,
                     mix("#1B3D51", color1, 0.25 + size * 0.07))
        if self.target:
            x, y, life = self.target
            p.glow(x, y, 29 + math.sin(self.time * 3) * 3, color1, "#102B40", 8)
            p.circle(x, y, 3, "#E5FCED")
        for i, (x, y, radius, phase, depth) in enumerate([(-140, -42, 29, 4.1, 0.4), (285, -85, 26, 1, 0.45),
                                                         (-284, 102, 60, 0.2, 0.9), (13, 139, 80, 2, 1),
                                                         (292, 117, 55, 4.1, 0.9)]):
            xx = x + math.sin(self.time * 0.35 + phase) * 18 + self.offset[0] * depth
            yy = y + math.sin(self.time * 0.6 + phase) * 14 + self.offset[1] * depth
            self.jelly(p, xx, yy, radius, phase, color1 if i % 2 == 0 else color2, depth)
        for x in range(-520, 560, 33):
            height = 16 + 17 * (1 + math.sin(x))
            points = [(x, -305), (x + 9, -280), (x + math.sin(self.time + x) * 7, -300 + height)]
            p.line(points, "#163E4C", 5, True)
        p.text(-443, -268, "让光慢一点，让海安静一点。", "#71A8BA", 10, "w")
        p.end()
        self.stage.hud(f"{name}   ·   水流 × {self.current:.2f}   ·   水母会缓缓靠近你留下的光")


if __name__ == "__main__":
    app = Jellyfish()
    app.stage.run(app.frame, app.reset)
