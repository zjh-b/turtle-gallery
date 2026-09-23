"""同一棵递归生成的树，在春夏秋冬之间变换；G 可观察逐层生长。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar


SEASONS = [
    ("春 · 樱色", "#F5E9DE", "#D9DFCA", "#E5A5AE", "#FAD8D9"),
    ("夏 · 浓荫", "#DDEEDC", "#A8CAB4", "#477F63", "#85B875"),
    ("秋 · 金风", "#F4E4C9", "#D9BA91", "#CF7449", "#EFBA59"),
    ("冬 · 初雪", "#DCE5EB", "#B6C8CF", "#E5EDF0", "#FFFFFF"),
]


class SeasonTree:
    def __init__(self):
        self.stage = Stage("一树四季", "1～4 春夏秋冬    S 下一季    G 重新生长    ↑↓ 调整风力",
                           "#F5E9DE", "#9F6A6E", light=True)
        self.paint = Paint(self.stage, "tree")
        self.branches = []
        rng = random.Random(39)

        def branch(parent, length, angle, level):
            index = len(self.branches)
            self.branches.append((parent, length, angle, level, rng.random()))
            if level < 7:
                branch(index, length * rng.uniform(0.71, 0.80), rng.uniform(0.32, 0.62), level + 1)
                branch(index, length * rng.uniform(0.71, 0.80), -rng.uniform(0.32, 0.62), level + 1)

        branch(-1, 119, math.pi / 2, 0)
        self.falling = [(rng.uniform(-240, 240), rng.uniform(-240, 240), rng.random() * 6,
                         rng.uniform(2, 4)) for _ in range(38)]
        self.time, self.season, self.wind, self.growth = 0, 0, 1, 8
        for i in range(4):
            self.stage.screen.onkey(lambda i=i: self.set_season(i), str(i + 1))
        for key in ("s", "S"):
            self.stage.screen.onkey(lambda: self.set_season((self.season + 1) % 4), key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.regrow, key)
        self.stage.screen.onkey(lambda: self.change_wind(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_wind(-0.25), "Down")

    def reset(self):
        self.time, self.season, self.wind, self.growth = 0, 0, 1, 8

    def set_season(self, season):
        self.season = season % 4

    def regrow(self):
        self.growth = 0

    def change_wind(self, delta):
        self.wind = max(0, min(3, self.wind + delta))

    def leaf(self, p, x, y, phase, colors):
        if self.season == 0:
            for k in range(5):
                px, py = polar(3.8, k * math.tau / 5 + phase, x, y)
                p.oval(px, py, 4.3, 3.5, colors[0] if k % 2 else colors[1])
            p.circle(x, y, 1.7, "#FFF1B4")
        elif self.season in (1, 2):
            for k in range(3):
                a = phase + k * 2.2
                p.poly([polar(0, a, x, y), polar(8, a - 0.5, x, y), polar(14, a, x, y),
                        polar(8, a + 0.5, x, y)], colors[k % 2], smooth=True)
        else:
            p.oval(x, y + 2, 4.5, 2, "#F4F7F6")

    def frame(self, dt):
        self.time += dt
        self.growth = min(8, self.growth + dt * 1.45)
        name, sky, ground, leaf1, leaf2 = SEASONS[self.season]
        p = self.paint
        p.begin()
        p.gradient(sky, ground)
        edge = self.stage.view[0] / 2 + 8
        p.circle(290, 175, 48, mix(sky, "#FFF5CA", 0.68))
        for i, y in enumerate((-149, -192, -228)):
            points = [(-edge, -310), (-edge, y)]
            points += [(x, y + math.sin(x * 0.007 + i) * (28 - i * 6)) for x in range(-600, 601, 40)]
            points += [(edge, y), (edge, -310)]
            p.poly(points, mix(ground, "#7F9B8A", 0.12 + i * 0.13), smooth=True)
        p.oval(0, -227, 162, 16, mix(ground, "#5B7165", 0.3))
        endpoints = []
        tips = []
        for index, (parent, length, turn, level, seed) in enumerate(self.branches):
            if parent < 0:
                x, y, angle = 0, -220, turn
            else:
                x, y, previous_angle = endpoints[parent]
                sway = math.sin(self.time * 0.85 + level * 0.6) * self.wind * level * 0.008
                angle = previous_angle + turn + sway
            growth = min(1, max(0, self.growth - level))
            xx, yy = polar(length * growth, angle, x, y)
            endpoints.append((xx, yy, angle))
            if growth <= 0:
                continue
            width = max(1, 16 * 0.67 ** level) * growth
            color = mix("#62534C", "#AD8871", seed * 0.5)
            mid = ((x + xx) / 2 + math.sin(angle) * length * 0.04, (y + yy) / 2)
            p.line([(x, y), mid, (xx, yy)], color, width, True)
            if level < 3:
                p.line([(x - 2, y + 2), (xx - 1, yy)], mix(color, sky, 0.3), max(1, width * 0.17))
            if self.season == 3 and level > 3:
                p.line([(x, y + 1.5), (xx, yy + 1.5)], "#EDF2F2", 1.7)
            if level == 7 and growth > 0.85:
                tips.append((xx, yy, seed))
        for x, y, seed in tips:
            self.leaf(p, x, y, seed * math.tau, (leaf1, leaf2))
        for x, y, phase, size in self.falling:
            drift = self.time * (11 if self.season != 3 else 6)
            yy = (y - drift + 260) % 500 - 240
            xx = x + math.sin(self.time * 0.8 + phase) * 18 + self.wind * self.time * 5
            xx = (xx + 330) % 660 - 330
            if self.season == 3:
                p.circle(xx, yy, size * 0.55, "#F6F8F8")
            elif self.season != 1:
                p.oval(xx, yy, size, size * (0.3 + abs(math.sin(self.time + phase)) * 0.5),
                       leaf1 if phase > 3 else leaf2)
        p.text(-416, 177, name, "#765F5B", 23, "w", True)
        p.text(-413, 142, "一枝生两枝，四季又一年。", "#85776D", 10, "w")
        p.text(411, -268, f"风力 × {self.wind:.2f}", "#6A7168", 10, "e")
        p.end()
        self.stage.hud(f"{name}   ·   {len(self.branches)} 段递归枝条   ·   按 G 观察它一层层长大")


if __name__ == "__main__":
    app = SeasonTree()
    app.stage.run(app.frame, app.reset)
