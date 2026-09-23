"""以贝塞尔翼形、细密翅脉和渐变鳞片绘制一只在星夜里呼吸的蝶。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = [
    ("蓝紫幻梦", "#5CDCEB", "#9D80EF", "#EF9EE0"),
    ("玫瑰月光", "#FFAEC8", "#B47AF0", "#FFDACA"),
    ("翡翠流萤", "#89F0CE", "#529CE3", "#E6E99C"),
]


def bezier(a, b, c, d, count=18):
    return [((1 - t) ** 3 * a[0] + 3 * (1 - t) ** 2 * t * b[0]
             + 3 * (1 - t) * t ** 2 * c[0] + t ** 3 * d[0],
             (1 - t) ** 3 * a[1] + 3 * (1 - t) ** 2 * t * b[1]
             + 3 * (1 - t) * t ** 2 * c[1] + t ** 3 * d[1])
            for t in [index / count for index in range(count + 1)]]


def wing_curve(segments):
    points = []
    for segment in segments:
        points.extend(bezier(*segment)[1:] if points else bezier(*segment))
    return points


class NeonButterfly:
    def __init__(self):
        self.stage = Stage("霓光蝶舞", "点击 引蝶追光    C 切换色彩    M 悬停 / 漫游", accent="#B5B1FD")
        self.paint = Paint(self.stage, "neon-butterfly")
        self.upper = wing_curve([
            ((12, 10), (56, 127), (233, 226), (261, 186)),
            ((261, 186), (289, 146), (236, 54), (182, 25)),
            ((182, 25), (119, -8), (56, 22), (12, 10)),
        ])
        self.lower = wing_curve([
            ((13, -3), (57, 1), (136, -2), (172, -46)),
            ((172, -46), (203, -79), (184, -127), (145, -137)),
            ((145, -137), (133, -148), (142, -178), (118, -192)),
            ((118, -192), (123, -153), (58, -143), (35, -83)),
            ((35, -83), (23, -57), (14, -23), (13, -3)),
        ])
        self.upper_veins = [bezier((14, 12), (58, 41 + 15 * index), (170, 39 + 29 * index), tip, 22)
                            for index, tip in enumerate([(181, 30), (215, 54), (244, 88),
                                                         (262, 125), (268, 156), (256, 185)])]
        self.lower_veins = [bezier((14, -4), (33, -36), (54 + index * 15, -115), tip, 22)
                            for index, tip in enumerate([(81, -130), (118, -186), (151, -133),
                                                         (174, -111), (183, -80)])]
        rng = random.Random(280)
        self.stars = [(rng.uniform(-472, 472), rng.uniform(-269, 245), rng.uniform(0.6, 1.7),
                       rng.random() * math.tau) for _ in range(68)]
        # Sparse scale-like marks follow the upper and lower wing contours.
        self.scales = []
        for upper, boundary in ((True, self.upper), (False, self.lower)):
            for layer in (0.78, 0.86, 0.94):
                for index in range(7, len(boundary) - 10, 4):
                    x, y = boundary[index]
                    self.scales.append((x * layer, y * layer, rng.uniform(0.9, 1.8), upper))
        self.reset()
        self.stage.screen.onclick(self.attract)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("m", "M"):
            self.stage.screen.onkey(self.toggle_motion, key)

    def reset(self):
        self.time = 0.0
        self.theme = 0
        self.motion = True
        self.offset = [0.0, 0.0]
        self.target = None

    def change_theme(self):
        if not self.stage.paused:
            self.theme = (self.theme + 1) % len(THEMES)

    def toggle_motion(self):
        if not self.stage.paused:
            self.motion = not self.motion

    def attract(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            self.target = [max(-290, min(290, x)), max(-150, min(165, y)), 6.0]

    def frame(self, dt):
        self.time += dt
        if dt > 0:
            if self.target:
                self.target[2] -= dt
                if self.target[2] <= 0:
                    self.target = None
            if self.motion:
                tx, ty = (self.target[0] * 0.28, self.target[1] * 0.10) if self.target else (
                    math.sin(self.time * 0.31) * 27, math.sin(self.time * 0.62) * 10)
                self.offset[0] += (tx - self.offset[0]) * min(1, dt * 1.3)
                self.offset[1] += (ty - self.offset[1]) * min(1, dt * 1.3)
        name, cyan, purple, pink = THEMES[self.theme]
        p = self.paint
        p.begin()
        p.gradient("#080D23", "#15142A")
        for index in range(15):
            radius = 320 - index * 14
            p.oval(0, 15, radius, radius * 0.66, mix("#0E1127", purple, index * 0.0022))
        for x, y, radius, phase in self.stars:
            brightness = 0.20 + 0.16 * (1 + math.sin(self.time * 0.65 + phase))
            p.circle(x, y, radius, mix("#1B233C", cyan, brightness))
        # A broken lunar ring frames the silhouette and leaves breathing space.
        for start in (0.19, math.pi + 0.19):
            points = [(math.cos(start + index * 2.2 / 65) * 342,
                       14 + math.sin(start + index * 2.2 / 65) * 222) for index in range(66)]
            p.line(points, "#292B48", 1)
        if self.target:
            x, y, life = self.target
            p.glow(x, y, 20 + math.sin(self.time * 2) * 3, pink, "#11142A", 5)
            p.circle(x, y, 2, "#FFEEFC")
            p.circle(x, y, 28 + (6 - life) % 1.5 * 12, "", mix("#15172E", pink, life / 20))
        flutter = 0.87 + 0.13 * math.cos(self.time * 2.3)
        tilt = math.sin(self.time * 0.61) * 0.025
        tilt_cos, tilt_sin = math.cos(tilt), math.sin(tilt)
        ox, oy = self.offset[0], self.offset[1] + 10

        def project(points, side, scale=1.0):
            result = []
            for x, y in points:
                xx = side * x * flutter * scale
                yy = y * scale
                result.append((ox + xx * tilt_cos - yy * tilt_sin,
                               oy + xx * tilt_sin + yy * tilt_cos))
            return result

        for side in (-1, 1):
            for upper, boundary, base in ((False, self.lower, purple), (True, self.upper, cyan)):
                outline = project(boundary, side)
                p.poly(outline, mix("#12152F", base, 0.12), mix("#192340", base, 0.35), 6)
                # Contours shrink towards the wing root. The wide luminous border
                # surrounds translucent-looking, darker cells and tiny scales.
                for index in range(17):
                    scale = 1 - index * 0.025
                    tint = 0.18 + 0.13 * math.sin(index / 16 * math.pi)
                    color = mix("#13152F", mix(base, purple if upper else cyan, index / 22), tint)
                    p.poly(project(boundary, side, scale), color)
                p.line(outline + outline[:1], mix(base, pink, 0.28), 1.3, True)
                p.line(project(boundary, side, 0.93), mix("#1C2945", base, 0.48), 1, True)
                p.line(project(boundary, side, 0.84), mix("#1C2945", base, 0.37), 1, True)
                veins = self.upper_veins if upper else self.lower_veins
                for index, vein in enumerate(veins):
                    projected_vein = project(vein, side)
                    p.line(projected_vein, mix("#242443", base, 0.50), 3, True)
                    p.line(projected_vein, mix(base, pink, 0.24), 1, True)
                    if upper:
                        # Small offshoots break up the large cells into fine scales.
                        for location in (10, 14, 18):
                            x, y = vein[location]
                            twig = [(x, y), (x + 11, y + 10), (x + 19, y + 20)]
                            p.line(project(twig, side), mix("#28314D", base, 0.32), 1, True)
                # Soft oval eyespots are drawn as nested contour polygons so their
                # shape follows the current wing fold, instead of flat circles.
                cx, cy, rx, ry = (194, 126, 18, 24) if upper else (121, -75, 17, 21)
                for factor, color in ((1.30, mix("#151A37", pink, 0.20)), (1, pink),
                                      (0.83, mix(purple, "#11172D", 0.58)), (0.43, cyan)):
                    ring = [(cx + rx * factor * math.cos(a), cy + ry * factor * math.sin(a))
                            for a in [index * math.tau / 26 for index in range(27)]]
                    p.poly(project(ring, side), color, smooth=True)
            for x, y, radius, upper in self.scales:
                xx, yy = project([(x, y)], side)[0]
                color = mix(cyan if upper else purple, pink, 0.40 + 0.22 * math.sin(x))
                p.circle(xx, yy, radius, color)
        # Fine antennae, a segmented abdomen, and highlights keep the silhouette
        # anatomically legible even while the wings gently fold.
        for side in (-1, 1):
            antenna = bezier((side * 4, 24), (side * 8, 48), (side * 34, 66), (side * 42, 56))
            p.line([(ox + x, oy + y) for x, y in antenna], pink, 1.4, True)
            p.circle(ox + side * 42, oy + 56, 2.4, "#F4D9FF")
        p.line([(ox, oy + 23), (ox, oy - 10), (ox, oy - 70)], "#323B66", 13, True)
        p.line([(ox, oy + 23), (ox, oy - 10), (ox, oy - 70)], mix(purple, cyan, 0.5), 6, True)
        for index in range(8):
            p.oval(ox, oy - 9 - index * 8, 4.4 - index * 0.30, 2.1, "#222A49", mix(purple, pink, 0.48))
        p.oval(ox, oy + 8, 6, 16, mix(purple, cyan, 0.25))
        p.circle(ox, oy + 24, 5, pink)
        p.line([(ox - 1.5, oy + 17), (ox - 1.5, oy - 1)], "#D8F8FF", 1)
        # Slow, asymmetric fireflies around the wings provide motion at the edges.
        for index in range(12):
            a = index * math.tau / 12 + self.time * 0.08
            x = math.cos(a) * (322 + 16 * math.sin(index))
            y = 8 + math.sin(a) * 204
            p.circle(x, y, 3.8, mix("#171E36", pink, 0.20))
            p.circle(x, y, 1.3, mix(cyan, pink, (math.sin(a) + 1) / 2))
        p.text(0, -259, "循着微光，轻轻振翅。", "#9097BA", 11)
        p.text(0, 244, "A   S M A L L   M I R A C L E   W I T H   W I N G S", "#737F9F", 8)
        p.end()
        motion_label = "漫游" if self.motion else "悬停"
        self.stage.hud(f"{name}   ·   {motion_label}   ·   贝塞尔翼形 / 翅脉与鳞片 / 点击追光")


if __name__ == "__main__":
    app = NeonButterfly()
    app.stage.run(app.frame, app.reset)
