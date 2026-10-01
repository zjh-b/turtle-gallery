"""一树四季：繁花、浓荫、金叶与雪枝，点击画面唤起一阵风。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar


SEASONS = [
    ("春 · 樱色", "#F9EEE5", "#CFD9BF", "#C87899", "#FFE5E8"),
    ("夏 · 浓荫", "#DFEDE4", "#96B59A", "#245B47", "#AAC978"),
    ("秋 · 金风", "#FAEAD8", "#D9BD89", "#A95437", "#FFDC8C"),
    ("冬 · 初雪", "#DDE7EE", "#C2D2DB", "#7894A5", "#FFFFFF"),
]
CROWN_COLORS = (
    ("#CB829D", "#D99BB1", "#E7B0C1", "#F3C8D3", "#FFE7E7"),
    ("#35634D", "#447952", "#689456", "#90B970", "#CEE2A0"),
    ("#A96542", "#C28043", "#D89A48", "#EDB851", "#FFE09A"),
    ("#A9C0CD", "#C7D9E2", "#DDE9EC", "#F0F5F5", "#FFFFFF"),
)
POEMS = ("风过花梢，春色满枝。", "树荫深处，听见夏天。", "一树流金，半山秋色。", "雪落无声，静待新芽。")


class SeasonTree:
    """Fixed geometry and a fixed drifting pool keep a long exhibition bounded."""

    GUST_SECONDS = 3.6

    def __init__(self):
        self.stage = Stage("一树四季", "1～4 四季    S 下一季    G 重新生长    ↑↓ 风力    点击 唤风",
                           "#F9EEE5", "#9F6A6E", light=True)
        self.paint = Paint(self.stage, "tree")
        self.paint.backdrop = Paint(self.stage, "tree-backdrop")
        self.paint.backdrop_signature = None
        self.branches = []
        rng = random.Random(39)

        def branch(parent, length, angle, level):
            index = len(self.branches)
            self.branches.append((parent, length, angle, level, rng.random()))
            if level < 7:
                branch(index, length * rng.uniform(0.71, 0.80), rng.uniform(0.32, 0.62), level + 1)
                branch(index, length * rng.uniform(0.71, 0.80), -rng.uniform(0.32, 0.62), level + 1)

        branch(-1, 113, math.pi / 2 + 0.025, 0)
        self.branch_ink = tuple((max(.8, 21 * .68 ** level),
                                 mix("#574B46", "#8C7360", seed * .65),
                                 tuple(mix(mix("#574B46", "#8C7360", seed * .65),
                                           season[1], .34) for season in SEASONS))
                                for _, _, _, level, seed in self.branches)
        # Each tuft keeps its own silhouette and flowers while the branch sways.
        self.tufts = {}
        for index, (_, _, _, level, seed) in enumerate(self.branches):
            if level < 2:
                continue
            radius = (73, 56, 43, 32, 23, 17)[level - 2]
            contour = tuple((dx, dy * (.8 if level < 5 else 1) + (18 if level < 5 else 0))
                            for dx, dy in (polar(radius * rng.uniform(.8, 1.2), k * math.tau / 12)
                                           for k in range(12)))
            flowers = []
            if level in (4, 5, 7):
                dx, dy = rng.uniform(-radius * .7, radius * .7), rng.uniform(-radius * .6, radius * .7)
                size, phase = rng.uniform(3.5, 5.2), rng.random() * math.tau
                shape = tuple(polar(size * (1 if k % 2 == 0 else .48), phase + k * math.pi / 5)
                              for k in range(10))
                flowers.append((dx, dy, size, phase, rng.randrange(3, 5), shape))
            self.tufts[index] = (contour, tuple(flowers))
        self.falling = tuple((rng.uniform(-350, 350), rng.uniform(-250, 240),
                              rng.random() * math.tau, rng.uniform(1.8, 3.5))
                             for _ in range(56))
        self.meadow = tuple((rng.uniform(-455, 455), rng.uniform(-276, -224),
                             rng.uniform(6, 18), rng.random() * math.tau)
                            for _ in range(48))
        self.petals = tuple((rng.uniform(-275, 300), rng.uniform(-252, -212),
                             rng.uniform(1, 3), rng.randrange(2, 5)) for _ in range(72))
        self.reset()
        for i in range(4):
            self.stage.screen.onkey(lambda i=i: self.set_season(i), str(i + 1))
        for key in ("s", "S"):
            self.stage.screen.onkey(lambda: self.set_season((self.season + 1) % 4), key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.regrow, key)
        self.stage.screen.onkey(lambda: self.change_wind(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_wind(-0.25), "Down")
        self.stage.screen.onclick(self.blow)

    def reset(self):
        self.time, self.season, self.wind, self.growth = 0, 0, 1, 8
        self.gust, self.gust_side = 0, 1

    def set_season(self, season):
        self.season = season % 4

    def regrow(self):
        self.growth = 0

    def change_wind(self, delta):
        self.wind = max(0, min(3, self.wind + delta))

    def blow(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        self.gust = self.GUST_SECONDS
        self.gust_side = -1 if x < 0 else 1

    def branch_positions(self, breeze):
        endpoints = []
        for parent, length, turn, level, _ in self.branches:
            if parent < 0:
                x, y, angle = 25, -214, turn
            else:
                x, y, previous_angle, _ = endpoints[parent]
                sway = math.sin(self.time * .85 + level * .6) * breeze * level * .005
                angle = previous_angle + turn + sway
            growth = min(1, max(0, self.growth - level))
            xx, yy = polar(length * growth, angle, x, y)
            endpoints.append((xx, yy, angle, growth))
        return endpoints

    def background(self, p, sky, ground):
        p.gradient(sky, ground)
        edge = self.stage.view[0] / 2 + 8
        sun = "#F9FCFC" if self.season == 3 else "#FFF7D9"
        for radius, opacity in ((79, .10), (63, .16), (49, .22), (37, .8)):
            p.circle(333, 163, radius, mix(sky, sun, opacity))
        # Broad low-contrast ridges leave the crown as the sharp focal point.
        for i, (base, height) in enumerate(((-102, 48), (-141, 35), (-181, 20))):
            points = [(-edge, -390)]
            points += [(x, base + math.sin(x * .006 + i * 1.3) * height +
                        math.sin(x * .013 + i) * height * .27)
                       for x in (-edge + 2 * edge * k / 32 for k in range(33))]
            points += [(edge, -390)]
            p.poly(points, mix(ground, "#73948C" if self.season != 3 else "#8DA7B9",
                               .11 + i * .065), smooth=True)
        p.poly([(-edge, -220), (-210, -198), (90, -207), (edge, -177),
                (edge, -310), (-edge, -310)], mix(ground, "#F5F4E6", .2), smooth=True)
        p.poly([(-90, -204), (-56, -220), (-115, -255), (-230, -296),
                (-105, -296), (5, -252), (19, -225), (-7, -203)],
               mix(ground, sky, .42), smooth=True)
        for k in range(3):
            p.oval(28, -220 + k * 2, 170 - k * 35, 15 - k * 3,
                   mix(ground, "#455E50" if self.season != 3 else "#849CAF", .13 + k * .07))

    def crown(self, p, endpoints, colors, front=False):
        for index, (contour, flowers) in self.tufts.items():
            x, y, angle, growth = endpoints[index]
            level, seed = self.branches[index][3:]
            amount = max(0, (growth - .6) / .4)
            if amount <= 0:
                continue
            if self.season == 3:
                if front and level >= 6:
                    p.oval(x, y + 2, 5.5 * amount, 2.8 * amount, colors[3])
                continue
            if not front:
                if level == 7:
                    continue
                p.poly([(x + dx * amount, y + dy * amount) for dx, dy in contour],
                       colors[0 if level < 4 else 1], smooth=True)
                continue
            if level in (2, 6):
                continue
            # Overlapping inner boughs make a canopy, with glimpses of the fork
            # between them. Alternate shades avoid a uniform outlined rim.
            shade = 1 if level == 3 else (2 if seed < .55 else 3)
            scale = .88 if level < 6 else 1
            p.poly([(x + dx * amount * scale, y + 5 + dy * amount * scale)
                    for dx, dy in contour], colors[shade], smooth=True)
            if level in (4, 5):
                p.poly([(x - 4 + dx * amount * .60, y + 12 + dy * amount * .45)
                        for dx, dy in contour], colors[min(3, shade + 1)], smooth=True)
            for dx, dy, size, phase, color, shape in flowers:
                xx, yy = x + dx * amount, y + dy * amount
                if self.season == 0:
                    points = [(xx + sx * amount, yy + sy * amount) for sx, sy in shape]
                    p.poly(points, colors[color], smooth=True)
                    p.circle(xx, yy, .7 * amount, "#F8E8BA")
                else:
                    a = angle + phase * .6
                    p.poly([polar(size * amount * 1.8, a, xx, yy),
                            polar(size * amount * .7, a + math.pi / 2, xx, yy),
                            polar(size * amount * 1.8, a + math.pi, xx, yy),
                            polar(size * amount * .7, a - math.pi / 2, xx, yy)],
                           colors[color], smooth=True)

    def trunk(self, p, endpoints, sky):
        for index, (parent, length, _, level, seed) in enumerate(self.branches):
            xx, yy, angle, growth = endpoints[index]
            if growth <= 0:
                continue
            if level >= 6 and self.season != 3 and growth >= .9:
                # Fine twigs are concealed by the mature outer foliage.
                continue
            x, y = (25, -214) if parent < 0 else endpoints[parent][:2]
            base_width, color, highlights = self.branch_ink[index]
            width = base_width * growth
            mid = ((x + xx) / 2 + math.sin(angle) * length * .055, (y + yy) / 2)
            p.line([(x, y), mid, (xx, yy)], color, width, True)
            if level < 4:
                p.line([(x - width * .23, y + 1),
                        (mid[0] - width * .2, mid[1]), (xx - width * .14, yy)],
                       highlights[self.season], max(.8, width * .19), True)
            if self.season == 3 and level > 0:
                p.line([(x, y + width * .45 + 1),
                        (mid[0], mid[1] + width * .45 + 1), (xx, yy + 1.5)],
                       "#F6FAFA", max(1.5, width * .65), True)
        if self.growth > .8:
            for side in (-1, 1):
                p.poly([(25, -186), (25 + side * 9, -212), (25 + side * 41, -221),
                        (25 + side * 15, -219), (25 - side * 5, -214)], "#66574B", smooth=True)

    def foreground(self, p, colors, ground, breeze):
        for x, y, height, phase in self.meadow:
            color = mix(ground, "#607B59" if self.season != 3 else "#869EA7", .44)
            lean = math.sin(self.time + phase) * breeze * 1.7
            p.line([(x - 3, y), (x + lean, y + height), (x + 2, y)], color, .8, True)
            if self.season == 0:
                p.circle(x + lean, y + height, 1.8, "#FFF0E9")
            elif self.season == 2:
                p.line([(x + lean - 2, y + height - 4), (x + lean, y + height + 2)],
                       "#E4BF7C", 2.4)
            elif self.season == 3:
                p.oval(x, y, 8, 1.7, "#EAF2F4")
        for x, y, phase, size in self.falling:
            drift = self.time * (7 if self.season == 3 else 12)
            yy = (y - drift + 265) % 510 - 245
            xx = (x + math.sin(self.time * .75 + phase) * (17 + abs(breeze) * 5) +
                  self.wind * self.time * 5 + breeze * math.sin(phase) * 10 + 410) % 820 - 410
            if self.season == 3:
                p.circle(xx, yy, size * .64, "#F9FCFD")
            elif self.season == 1:
                # Sunlit motes are deliberately smaller than blossoms or snow.
                p.circle(xx, yy, size * .34, "#E4EDBD")
            else:
                a = phase + self.time * 1.3
                p.poly([polar(size * 1.6, a, xx, yy), polar(size * .65, a + 1.6, xx, yy),
                        polar(size * 1.6, a + math.pi, xx, yy),
                           polar(size * .65, a - 1.6, xx, yy)], colors[3 if phase > 3 else 4], smooth=True)

    def draw_backdrop(self, name, sky, ground, colors):
        signature = (self.season, self.stage.width, self.stage.height, self.stage.scale)
        if self.paint.backdrop_signature == signature:
            return
        p = self.paint.backdrop
        p.begin()
        self.background(p, sky, ground)
        if self.season != 1:
            for x, y, size, color in self.petals:
                p.oval(x, y, size * 1.5, size * .45, colors[color])
        p.text(-423, 193, name, "#715A56" if self.season != 3 else "#596F80", 24, "w", True)
        p.line([(-421, 164), (-372, 164)], colors[1], 1.2)
        p.text(-421, 145, POEMS[self.season], "#7E7B70", 10, "w")
        p.text(-421, 125, "一枝生两枝，四季又一年。", "#8C887C", 9, "w")
        p.end()
        self.paint.backdrop_signature = signature

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.growth = min(8, self.growth + dt * 1.45)
            self.gust = max(0, self.gust - dt)
        name, sky, ground, _, _ = SEASONS[self.season]
        colors = CROWN_COLORS[self.season]
        breeze = self.wind + math.sin(self.gust / self.GUST_SECONDS * math.pi) * 2.4 * self.gust_side
        endpoints = self.branch_positions(breeze)
        self.draw_backdrop(name, sky, ground, colors)
        p = self.paint
        p.begin()
        self.crown(p, endpoints, colors)
        self.trunk(p, endpoints, sky)
        self.crown(p, endpoints, colors, front=True)
        self.foreground(p, colors, ground, breeze)
        p.text(418, -271, "风起花落" if self.gust else f"风力 × {self.wind:.2f}",
               "#647464", 10, "e")
        p.end()
        self.stage.hud(f"{name}   ·   255 段枝条，层层生长   ·   点击画面，借一阵风")


if __name__ == "__main__":
    app = SeasonTree()
    app.stage.run(app.frame, app.reset)
