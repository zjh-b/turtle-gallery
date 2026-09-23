"""星河玫瑰：贝塞尔折叠花瓣、星尘与一朵慢慢生长的玫瑰。仅使用标准库。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = [
    ("玫瑰星云", "#D44B77", "#FFC3C9", "#F0C5A0"),
    ("冰蓝回声", "#688FCC", "#D2E6FA", "#B3DCD5"),
    ("香槟晨星", "#B88956", "#FFE4BE", "#F2C997"),
]


def bezier(a, b, c, d, steps=20):
    return [tuple((1-t)**3*a[k] + 3*(1-t)**2*t*b[k] +
                  3*(1-t)*t*t*c[k] + t**3*d[k] for k in (0, 1))
            for t in (i/steps for i in range(steps+1))]


def closed_curve(start, *segments):
    points = [start]
    for control1, control2, end in segments:
        points.extend(bezier(points[-1], control1, control2, end, 15)[1:])
    return points


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value*value*(3-2*value)


class GalaxyRose:
    def __init__(self):
        self.stage = Stage("星河玫瑰", "点击 洒下星尘    G 重播生长    C 切换花色    ↑↓ 调整速度", accent="#ECA4B9")
        self.paint = Paint(self.stage, "galaxy-rose")
        rng = random.Random(2718)
        self.stars = [(rng.uniform(-493, 493), rng.uniform(-260, 257), rng.uniform(.55, 1.6),
                       rng.uniform(0, math.tau)) for _ in range(102)]
        self.stem = bezier((44, -247), (-5, -130), (57, -28), (30, 77), 48)
        # Each outline is drawn by hand as curved folded cloth, back to front.
        # Coordinates are local to the flower, whose heart is at (35, 100).
        self.petals = [
            (closed_curve((-48, 14), ((-96, 73), (-51, 124), (-8, 102)),
                          ((26, 111), (51, 71), (36, 34)), ((17, 12), (-13, 1), (-48, 14))), .37, .78),
            (closed_curve((-8, 30), ((32, 114), (98, 102), (103, 60)),
                          ((135, 41), (115, -15), (66, -25)), ((34, -18), (9, 1), (-8, 30))), .48, .85),
            (closed_curve((-22, 8), ((-110, 100), (-158, 42), (-125, -17)),
                          ((-113, -57), (-63, -74), (-20, -39)), ((-6, -23), (-4, -8), (-22, 8))), .55, .78),
            (closed_curve((38, 14), ((140, 68), (169, 0), (120, -40)),
                          ((97, -88), (48, -92), (14, -54)), ((9, -26), (21, -3), (38, 14))), .53, .89),
            (closed_curve((-89, -12), ((-54, 14), (-35, 21), (-2, 7)),
                          ((39, 13), (98, -4), (111, -29)), ((88, -102), (10, -117), (-38, -88)),
                          ((-69, -70), (-93, -42), (-89, -12))), .65, .87),
            (closed_curve((-78, 0), ((-107, 38), (-70, 77), (-35, 61)),
                          ((-11, 73), (31, 40), (25, 12)), ((4, -20), (-54, -33), (-78, 0))), .60, .97),
            (closed_curve((-7, 27), ((28, 82), (91, 57), (89, 17)),
                          ((111, -12), (60, -47), (26, -28)), ((8, -7), (-6, 8), (-7, 27))), .65, .93),
            (closed_curve((-58, -14), ((-24, 10), (7, 16), (28, 2)),
                          ((51, 7), (82, -5), (88, -21)), ((62, -64), (-3, -80), (-41, -50)),
                          ((-53, -39), (-62, -26), (-58, -14))), .74, 1.0),
            (closed_curve((-39, 11), ((-57, 37), (-31, 57), (-4, 48)),
                          ((26, 56), (38, 28), (26, 10)), ((7, -3), (-23, -7), (-39, 11))), .70, .97),
            (closed_curve((4, 16), ((17, 46), (54, 36), (55, 11)),
                          ((68, -14), (30, -34), (6, -20)), ((-5, -9), (-5, 3), (4, 16))), .76, 1.0),
            (closed_curve((-33, -8), ((-9, 12), (17, 11), (34, -3)),
                          ((45, -17), (11, -41), (-14, -27)), ((-25, -23), (-31, -16), (-33, -8))), .84, 1.0),
            (closed_curve((-17, 8), ((-29, 30), (-5, 34), (7, 24)),
                          ((27, 20), (18, 0), (3, -5)), ((-6, -8), (-16, -1), (-17, 8))), .83, 1.0),
        ]
        self.fold_lines = [
            bezier((-124, 5), (-98, 26), (-80, 15), (-64, -8)),
            bezier((130, 17), (107, 23), (94, -6), (89, -29)),
            bezier((-87, -15), (-39, 11), (52, 2), (107, -30)),
            bezier((-74, 21), (-48, 54), (-12, 44), (21, 15)),
            bezier((15, 29), (42, 53), (75, 30), (88, 11)),
            bezier((-54, -15), (-10, 12), (48, -1), (84, -21)),
            bezier((-36, 18), (-17, 37), (9, 31), (24, 12)),
            bezier((-30, -9), (-8, 6), (16, 0), (32, -7)),
        ]
        self.reset()
        self.stage.screen.onclick(self.stardust)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.replay, key)
        self.stage.screen.onkey(lambda: self.change_speed(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.25), "Down")

    def reset(self):
        self.time, self.growth, self.theme, self.speed = 0.0, 0.0, 0, 1.0
        self.particles = []
        self._rng = random.Random(2701)

    def replay(self):
        if not self.stage.paused:
            self.growth = 0.0

    def change_theme(self):
        self.theme = (self.theme + 1) % len(THEMES)

    def change_speed(self, amount):
        self.speed = max(.25, min(2.5, self.speed+amount))

    def stardust(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            for _ in range(24):
                angle, speed = self._rng.uniform(0, math.tau), self._rng.uniform(12, 54)
                self.particles.append([x, y, math.cos(angle)*speed, math.sin(angle)*speed, 0.0])
            self.particles = self.particles[-144:]

    def transform(self, points, opening):
        sway = math.sin(self.time*.65)*3.3
        return [(35+x*opening+sway, 98+y*opening+(1-opening)*22) for x, y in points]

    def leaf(self, p, start, tip, width, light):
        dx, dy = tip[0]-start[0], tip[1]-start[1]
        length = math.hypot(dx, dy)
        nx, ny = -dy/length*width, dx/length*width
        a = start[0]+dx*.3+nx, start[1]+dy*.3+ny
        b = start[0]+dx*.72+nx, start[1]+dy*.72+ny
        c = start[0]+dx*.6-nx*.65, start[1]+dy*.6-ny*.65
        d = start[0]+dx*.2-nx*.8, start[1]+dy*.2-ny*.8
        outline = bezier(start, a, b, tip, 16) + bezier(tip, c, d, start, 16)[1:]
        p.poly(outline, "#254B45", "#466B58")
        p.poly(bezier(start, a, b, tip, 16)+[start], "#355B4D")
        p.line([start, tip], light, 1)
        for i in range(3, 9):
            t = i/10
            x, y = start[0]+dx*t, start[1]+dy*t
            reach = math.sin(t*math.pi)*.55
            p.line([(x, y), (x+nx*reach+dx*.09, y+ny*reach+dy*.09)], "#4B6B57")
            p.line([(x, y), (x-nx*reach*.6+dx*.08, y-ny*reach*.6+dy*.08)], "#3B5D4E")

    def frame(self, dt):
        if dt > 0:
            self.time += dt*self.speed
            self.growth = min(7.0, self.growth+dt*self.speed)
            for particle in self.particles:
                particle[0] += particle[2]*dt
                particle[1] += particle[3]*dt
                particle[3] -= dt*8
                particle[4] += dt
            self.particles = [particle for particle in self.particles if particle[4] < 2.4]
        name, color, light, gold = THEMES[self.theme]
        p = self.paint
        p.begin()
        p.gradient("#111026", "#1D192B")
        # A quiet elliptical star orbit frames the botanical silhouette.
        orbit = [(30+249*math.cos(a), -2+199*math.sin(a)) for a in [i*math.tau/144 for i in range(145)]]
        p.line(orbit, "#383044", 1)
        for x, y, radius, phase in self.stars:
            intensity = .24+.20*(.5+.5*math.sin(self.time*.8+phase))
            p.circle(x, y, radius, mix("#29253D", "#F7DBD6", intensity))
        for i in range(55):
            a = i*math.tau/55
            x, y = 30+249*math.cos(a), -2+199*math.sin(a)
            if i%5 == 0:
                p.circle(x, y, 1.5, mix("#383044", gold, .5))
        angle = self.time*.105 + 2.2
        sx, sy = 30+249*math.cos(angle), -2+199*math.sin(angle)
        p.circle(sx, sy, 6, "#51404C")
        p.circle(sx, sy, 2.7, gold)
        p.line([(sx-9, sy), (sx+9, sy)], "#987B79")
        p.line([(sx, sy-9), (sx, sy+9)], "#987B79")
        p.text(-430, 99, "把星河", "#DFC4D1", 22, "w")
        p.text(-430, 62, "赠予你", "#DFC4D1", 22, "w")
        p.text(-429, 26, "A ROSE FROM THE COSMOS", "#8C7F98", 8, "w")
        p.line([(-429, 6), (-366, 6)], "#885C72")
        p.text(332, -80, "每一次绽放", "#AC95A7", 10)
        p.text(332, -105, "都有自己的光", "#AC95A7", 10)
        p.oval(42, -249, 96, 8, "#181727")
        visible = max(2, int(len(self.stem)*smoothstep(self.growth/2.1)))
        stem = self.stem[:visible]
        p.line(stem, "#264A42", 7)
        p.line([(x-1.4, y) for x, y in stem], "#668572", 1.7)
        leaves = smoothstep((self.growth-.8)/2)
        if leaves > .01:
            self.leaf(p, (24, -98), (24-116*leaves, -98+63*leaves), 23*leaves, "#72927B")
            self.leaf(p, (27, -139), (27+109*leaves, -139+70*leaves), 23*leaves, "#789682")
            p.line([(15, -50), (5, -33), (17, -42)], "#6A806C", 2)
            p.line([(31, -190), (42, -176), (32, -181)], "#627D68", 2)
        opening = smoothstep((self.growth-1.6)/3.7)
        if opening > .001:
            # Sepals sit behind the rose cup and connect it to the stem.
            for shape in [[(28, 15), (-20, 45), (-40, 70), (8, 53)],
                          [(29, 13), (76, 54), (98, 70), (65, 23)],
                          [(30, 16), (24, 49), (35, 69), (42, 30)]]:
                shape = [(30+(x-30)*opening, 20+(y-20)*opening) for x, y in shape]
                p.poly(shape, "#315044", "#57725B", smooth=True)
            for index, (outline, shade, highlight) in enumerate(self.petals):
                local_open = opening*(.85+.15*smoothstep((self.growth-2-index*.11)/2))
                shape = self.transform(outline, local_open)
                base = mix("#351A36", color, shade)
                p.poly(shape, base, mix(base, light, .16))
                # Nested curved color planes shade each fold without external images.
                centerx = sum(x for x, y in outline)/len(outline)
                centery = sum(y for x, y in outline)/len(outline)
                for layer in range(1, 11):
                    amount = 1-layer*.042
                    inner = [(centerx+(x-centerx)*amount, centery+(y-centery)*amount+layer*.192)
                             for x, y in outline]
                    p.poly(self.transform(inner, local_open), mix(base, light, layer*.0136*highlight))
                rim = outline[:min(25, len(outline))]
                p.line(self.transform(rim, local_open), mix(color, light, .45*highlight), 1.2)
            for fold in self.fold_lines:
                p.line(self.transform(fold, opening), mix(color, light, .47), 1)
            spiral = []
            for i in range(73):
                a = i*math.tau/42
                radius = 1+i*.19
                spiral.append((2+radius*math.cos(a), 11+radius*.64*math.sin(a)))
            p.line(self.transform(spiral, opening), mix(color, light, .72), 1.5)
        for i in range(18):
            a = i*2.39996 + self.time*.025
            x = 40+math.cos(a)*(160+i*3)
            y = -221+(i*31+self.time*(3+i%4))%456
            p.circle(x, y, .7+i%3*.25, mix("#31253D", gold, .26+.13*math.sin(a+self.time)**2))
        for x, y, vx, vy, age in self.particles:
            if abs(x) < 485 and -275 < y < 249:
                fade = max(0, 1-age/2.4)
                p.circle(x, y, 1.6*fade+.3, mix("#251C34", gold, fade))
        p.text(425, -259, "27 / GALAXY ROSE", "#887286", 8, "e")
        p.end()
        self.stage.hud(f"{name}   ·   {'正在生长' if self.growth < 5.8 else '把这一朵星光送给你'}   ·   速度 × {self.speed:.2f}")


if __name__ == "__main__":
    app = GalaxyRose()
    app.stage.run(app.frame, app.reset)
