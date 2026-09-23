"""星空彼岸花：曲线花瓣、弯曲花丝与缓缓绽放的星夜。仅使用 Python 标准库。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = [
    ("赤色彼岸", "#FA4358", "#FFABB1", "#FBD8A0"),
    ("蓝紫星梦", "#9B82F6", "#DAD8FF", "#A9EAF5"),
    ("鎏金月夜", "#E7AA52", "#FFE4AB", "#FFEDC0"),
]


def bezier(a, b, c, d, steps=20):
    """Sample a cubic curve. Used for petals, filaments and the stem."""
    return [tuple((1-t)**3*a[k] + 3*(1-t)**2*t*b[k] +
                  3*(1-t)*t*t*c[k] + t**3*d[k] for k in (0, 1))
            for t in (i / steps for i in range(steps + 1))]


def ribbon(points, width):
    """A narrow tapered petal following a curve, with gently rippled edges."""
    left, right = [], []
    for i, (x, y) in enumerate(points):
        before, after = points[max(0, i-1)], points[min(len(points)-1, i+1)]
        dx, dy = after[0]-before[0], after[1]-before[1]
        length = max(0.001, math.hypot(dx, dy))
        t = i / (len(points)-1)
        w = width * math.sin(math.pi * t)**0.7 * (0.85 + 0.15*math.sin(t*29)) + 0.06
        left.append((x-dy*w/length, y+dx*w/length))
        right.append((x+dy*w/length, y-dx*w/length))
    return left + right[::-1]


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


class StarryLily:
    def __init__(self):
        self.stage = Stage("星空彼岸花", "点击 落下一颗流星    G 重播绽放    C 切换花色    ↑↓ 调整速度", accent="#F299AA")
        self.paint = Paint(self.stage, "starry-lily")
        rng = random.Random(2506)
        self.stars = [(rng.uniform(-495, 495), rng.uniform(-252, 255),
                       rng.uniform(0.55, 1.65), rng.uniform(0, math.tau)) for _ in range(115)]
        self.dust = []
        for _ in range(130):
            x = rng.uniform(-495, 495)
            y = 135 + 0.24*x + rng.gauss(0, 28)
            if -245 < y < 248:
                self.dust.append((x, y, rng.uniform(0.45, 1.05), rng.random()))
        self.florets = []
        # An umbel of six flowers, each with six recurved ribbon petals.
        for index, (x, y, angle, size) in enumerate([
            (-43, 113, 0.21, 0.80), (36, 123, -0.22, 0.84),
            (-76, 70, 0.52, 0.94), (81, 69, -0.45, 0.93),
            (-32, 44, 0.25, 1.00), (36, 41, -0.24, 1.03),
        ]):
            petals, stamens = [], []
            for j in range(6):
                a = angle + j*math.tau/6 + rng.uniform(-0.12, 0.12)
                length = rng.uniform(0.84, 1.14) * size
                curve = bezier((0, 0), (23, 9), (49, 36), (68, 23), 17)
                curve += bezier((68, 23), (91, 4), (69, -17), (50, -3), 12)[1:]
                ca, sa = math.cos(a), math.sin(a)
                curve = [((px*ca-py*sa)*length, (px*sa+py*ca)*length*0.85) for px, py in curve]
                petals.append((ribbon(curve, 4.3*size), curve, j))
            for j in range(7):
                a = math.pi * (0.06 + 0.89*j/6) + angle*0.5
                reach = rng.uniform(89, 119)*size
                dx, dy = math.cos(a)*reach, math.sin(a)*reach*0.95
                curve = bezier((0, 0), (dx*0.16, 20), (dx*0.74, dy+19), (dx, dy), 22)
                stamens.append((curve, rng.uniform(-0.65, 0.65)))
            self.florets.append((x, y, size, petals, stamens, index))
        self.stem = bezier((20, -249), (14, -120), (36, 7), (20, 87), 48)
        self.reset()
        self.stage.screen.onclick(self.meteor)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.replay, key)
        self.stage.screen.onkey(lambda: self.change_speed(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-0.25), "Down")

    def reset(self):
        self.time, self.bloom, self.theme, self.speed = 0.0, 0.0, 0, 1.0
        self.meteors = []

    def replay(self):
        if not self.stage.paused:
            self.bloom = 0.0

    def change_theme(self):
        self.theme = (self.theme + 1) % len(THEMES)

    def change_speed(self, amount):
        self.speed = max(0.25, min(2.5, self.speed + amount))

    def meteor(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            self.meteors = (self.meteors + [[x, y, 0.0]])[-5:]

    def flower_point(self, point, cx, cy, opening):
        x, y = point
        # Petals unfold from an upright bud; whole flower bends gently in the air.
        return (20 + cx + x*opening + math.sin(self.time*0.65)*3.2*(cy+y+250)/480,
                cy + y*opening + (1-opening)*abs(x)*0.58)

    def frame(self, dt):
        if dt > 0:
            elapsed = dt * self.speed
            self.time += elapsed
            self.bloom = min(7.0, self.bloom + elapsed)
            self.meteors = [[x, y, age+dt] for x, y, age in self.meteors if age+dt < 1.65]
        name, red, light, gold = THEMES[self.theme]
        p = self.paint
        p.begin()
        p.gradient("#070E23", "#17142B")
        # Softly layered moon halo and a fine diagonal milky way.
        for radius, amount in [(75, .018), (58, .025), (45, .045), (34, .085)]:
            p.circle(-310, 171, radius, mix("#0A1024", "#E3D4BF", amount))
        p.circle(-310, 171, 25, "#CBC7C1")
        p.circle(-301, 178, 24, "#10172B")
        p.circle(-326, 165, 1.5, "#F2E4D0")
        for x, y, r, shade in self.dust:
            p.circle(x, y, r, mix("#10152F", "#9B98CF", .18 + shade*.22))
        for i, (x, y, radius, phase) in enumerate(self.stars):
            intensity = .31 + .28*(.5+.5*math.sin(self.time*.9+phase))
            color = mix("#202741", "#D5E1FA", intensity)
            p.circle(x, y, radius, color)
            if i % 23 == 0:
                p.line([(x-3.5, y), (x+3.5, y)], mix("#182039", color, .6))
                p.line([(x, y-3.5), (x, y+3.5)], mix("#182039", color, .6))
        constellation = [(293, 157), (323, 191), (372, 168), (397, 215)]
        p.line(constellation, "#26354A")
        for x, y in constellation:
            p.circle(x, y, 2.0, "#8391B0")
        p.text(-422, 67, "彼岸有星河", "#D5C4CC", 24, "w")
        p.text(-419, 31, "LYCORIS · UNDER THE STARS", "#7B809C", 8, "w")
        p.line([(-419, 9), (-345, 9)], "#76505D")
        p.text(-419, -17, "花开一瞬，星河长明。", "#89839C", 10, "w")
        # The ground is kept quiet: one shadow and a few points of fallen light.
        p.oval(29, -251, 111, 12, "#111425")
        p.oval(26, -249, 61, 5, "#181B2C")
        stem_progress = smoothstep(self.bloom / 2.2)
        visible = max(2, int(len(self.stem)*stem_progress))
        stem = [(x+math.sin(self.time*.65)*3.2*(y+250)/480, y) for x, y in self.stem[:visible]]
        p.line(stem, "#183D3F", 7)
        p.line([(x-1.3, y) for x, y in stem], "#42655B", 2)
        if self.bloom > 1.8:
            opening = smoothstep((self.bloom-1.8)/1.6)
            for cx, cy, size, petals, stamens, index in self.florets:
                branch = bezier((20, 42), (20+cx*.15, 57), (20+cx*.7, cy-12), (20+cx, cy), 13)
                p.line(branch, mix("#172A35", "#759073", .6*opening), 2)
        for cx, cy, size, petals, stamens, index in self.florets:
            opening = smoothstep((self.bloom-2.1-index*.15)/2.75)
            if opening <= .001:
                continue
            transform = lambda points: [self.flower_point(point, cx, cy, opening) for point in points]
            for shape, curve, j in petals:
                shade = .62 + .06*((index+j) % 4)
                p.poly(transform(shape), mix("#3B1730", red, shade), smooth=False)
                p.line(transform(curve), mix(red, light, .20), 1)
                # A second edge catches moonlight near the recurved tip.
                p.line(transform(curve[20:]), mix(red, light, .40), 1)
            for j, (curve, tilt) in enumerate(stamens):
                points = transform(curve)
                p.line(points, mix(red, light, .22+.08*(j%3)), 1)
                x, y = points[-1]
                p.line([(x-2.3, y-1.2+tilt), (x+2.3, y+1.2-tilt)], gold, 2)
            x, y = self.flower_point((0, 0), cx, cy, opening)
            p.circle(x, y, 2.2, light)
        for i in range(18):
            phase = i*2.39996
            x = 23 + math.sin(phase+self.time*.12)*(112+i*3)
            y = -238 + (i*41+self.time*(7+i%3)) % 419
            if y < 207:
                p.circle(x, y, .7+(i%3)*.2, mix("#2B243B", gold, .25+.2*math.sin(phase+self.time)**2))
        for x, y, age in self.meteors:
            xx, yy = x-125*age, y-66*age
            if -250 < yy < 243:
                fade = max(0, 1-age/1.65)
                for j in range(6):
                    p.line([(xx+j*10, yy+j*5.3), (xx+(j+1)*10, yy+(j+1)*5.3)],
                           mix("#12192D", "#F5E3D8", fade*(1-j/6)), 1.6)
                p.circle(xx, yy, 2, mix("#12192D", "#FFF2DC", fade))
        p.text(414, -259, "25 / STARRY LYCORIS", "#77677E", 8, "e")
        p.end()
        self.stage.hud(f"{name}   ·   {'正在绽放' if self.bloom < 6 else '花已盛开'}   ·   速度 × {self.speed:.2f}")


if __name__ == "__main__":
    app = StarryLily()
    app.stage.run(app.frame, app.reset)
