"""一架缓慢运行的黄铜星仪。标准库矢量绘制；R 保留主题并复位运动与视角。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = (
    ("午夜黄铜", "#07121E", "#101E2A", "#D4B77C", "#FFF0C0", "#52869C", "#BEDFE1"),
    ("月下白银", "#0C1422", "#172238", "#ABBBD0", "#F0F4FA", "#797CAE", "#DED5F1"),
    ("古铜松石", "#091C1E", "#112B2B", "#C49771", "#FFE1B4", "#499F97", "#CBEBDD"),
)


class Armillary:
    """Perspective annuli assembled from fixed, depth-sorted polygon pools."""

    CENTER = (145, 30)
    # radius, band width, segments, tick count; unit geometry is built once.
    RINGS = ((197, 10, 96, 96), (176, 8, 96, 72),
             (146, 6, 80, 48), (109, 3.5, 72, 0))

    def __init__(self):
        self.stage = Stage("机械星仪", "点击 转动视角    C 切换材质    D 反向    ↑↓ 调速",
                           background=THEMES[0][1], accent=THEMES[0][3])
        self.paint = Paint(self.stage, "armillary")
        self.paint.backdrop = Paint(self.stage, "armillary-backdrop")
        self.paint.foreground = Paint(self.stage, "armillary-foreground")
        self.paint.backdrop_signature = None
        self.theme = 0
        self.palettes = tuple(self.make_palette(theme) for theme in THEMES)
        self.units = tuple(tuple((math.cos(i * math.tau / count),
                                 math.sin(i * math.tau / count))
                                for i in range(count + 1))
                           for _, _, count, _ in self.RINGS)
        self.tick_units = tuple(tuple((math.cos(i * math.tau / count),
                                      math.sin(i * math.tau / count))
                                     for i in range(count)) if count else ()
                                for _, _, _, count in self.RINGS)
        self.disc = tuple((math.cos(i * math.tau / 48), math.sin(i * math.tau / 48))
                          for i in range(48))
        rng = random.Random(303)
        self.stars = tuple((rng.uniform(-465, 466), rng.uniform(-243, 246),
                            rng.choice((.45, .6, .8)), rng.randrange(3)) for _ in range(62))
        self.reset()
        self.stage.screen.onclick(self.select)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.reverse, key)
        self.stage.screen.onkey(lambda: self.change_speed(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.25), "Down")

    @staticmethod
    def make_palette(theme):
        _, background, panel, metal, highlight, globe, pale = theme
        return dict(background=background, panel=panel, metal=metal, highlight=highlight,
                    globe=globe, pale=pale,
                    brass=tuple(mix(mix(metal, background, .81), highlight, i / 47)
                                for i in range(48)),
                    sphere=tuple(mix(mix(globe, background, .77), pale, i / 31 * .79)
                                 for i in range(32)),
                    muted=mix(metal, background, .44),
                    faint=mix(metal, background, .84),
                    ink=mix(metal, background, .70),
                    shadow=mix(background, "#000000", .34),
                    star=tuple(mix(background, pale, a) for a in (.19, .29, .41)))

    def reset(self):
        """Reset angles, speed and direction while retaining the selected finish."""
        if self.stage.paused:
            return
        self.time, self.speed, self.direction = 0.0, 1.0, 1
        self.view_yaw, self.view_pitch = .27, .20
        self.target_yaw, self.target_pitch = self.view_yaw, self.view_pitch

    def change_theme(self):
        if not self.stage.paused:
            self.theme = (self.theme + 1) % len(THEMES)
            self.stage.accent = THEMES[self.theme][3]

    def change_speed(self, amount):
        if not self.stage.paused:
            self.speed = max(.25, min(2.5, self.speed + amount))

    def reverse(self):
        if not self.stage.paused:
            self.direction *= -1

    def select(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        self.target_yaw = max(-.62, min(.62, (x - self.CENTER[0]) / 430))
        self.target_pitch = max(-.15, min(.50, .20 - (y - self.CENTER[1]) / 680))

    @staticmethod
    def rotate(point, ax=0, ay=0, az=0):
        x, y, z = point
        c, s = math.cos(ax), math.sin(ax)
        y, z = y * c - z * s, y * s + z * c
        c, s = math.cos(ay), math.sin(ay)
        x, z = x * c + z * s, -x * s + z * c
        c, s = math.cos(az), math.sin(az)
        return x * c - y * s, x * s + y * c, z

    def bases(self):
        """Ring-local axes transformed by the limited orbiting camera."""
        t = self.time
        # Different projected major axes keep the nested rings legible. Small
        # gimbal precessions preserve their inclinations; a complete yaw turn
        # would collapse an annulus into disconnected, edge-on face fragments.
        angles = ((0, -.08, 0),
                  (.72, -.40 + .13 * math.sin(t * .045),
                   .67 + .08 * math.sin(t * .02)),
                  (.15, .77 + .13 * math.sin(t * .065),
                   .90 + .08 * math.sin(t * .035)),
                  (.70, -.40 - .12 * math.sin(t * .09),
                   -.30 - .10 * math.sin(t * .03)))
        result = []
        for ax, ay, az in angles:
            u = self.rotate((1, 0, 0), ax, ay, az)
            v = self.rotate((0, 1, 0), ax, ay, az)
            result.append((self.rotate(u, self.view_pitch, self.view_yaw),
                           self.rotate(v, self.view_pitch, self.view_yaw)))
        return result

    def project(self, point):
        x, y, z = point
        factor = 1150 / (1150 - z)
        return self.CENTER[0] + x * factor, self.CENTER[1] + y * factor, z

    def on_ring(self, basis, unit, radius):
        u, v = basis
        a, b = unit
        return self.project(tuple(radius * (a * u[i] + b * v[i]) for i in range(3)))

    @staticmethod
    def quad_path(a, b, width):
        """Screen-space line as a polygon, preserving one Canvas item type."""
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = max(.001, math.hypot(dx, dy))
        nx, ny = -dy * width / length / 2, dx * width / length / 2
        return ((a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny))

    def disc_path(self, x, y, radius):
        return tuple((x + a * radius, y + b * radius) for a, b in self.disc)

    def add_sphere(self, pieces, x, y, z, radius, shades, metal):
        """An opaque, directional gradient; depth stays local to this sphere."""
        pieces.append((z - .01, self.disc_path(x, y, radius + .8), metal))
        steps = 24 if radius > 20 else 12
        for i in range(steps):
            a = i / (steps - 1)
            points = self.disc_path(x - radius * .25 * a, y + radius * .29 * a,
                                    radius * (1 - a * .86))
            pieces.append((z + i * .0001, points, shades[round(a * 31)]))

    def geometry(self, palette):
        """All moving pieces have fixed counts and the same Canvas type."""
        pieces = []
        bases = self.bases()
        brass = palette["brass"]
        for index, ((radius, width, count, ticks), units, basis) in enumerate(
                zip(self.RINGS, self.units, bases)):
            outer = [self.on_ring(basis, u, radius + width / 2) for u in units]
            inner = [self.on_ring(basis, u, radius - width / 2) for u in units]
            for i in range(count):
                a, b, c, d = outer[i], outer[i + 1], inner[i + 1], inner[i]
                depth = (a[2] + b[2]) / 2
                light = .38 + .18 * (depth / radius) + .20 * units[i][1]
                light += .13 * math.sin(i / count * math.tau * 2 + index * .6)
                shade = max(4, min(42, round(light * 47)))
                pieces.append((depth, (a[:2], b[:2], c[:2], d[:2]), brass[shade]))
                # A metal band's edge retains thickness even when its broad
                # face is viewed side-on; projected coplanar strips vanish.
                pieces.append((depth + .012, self.quad_path(a, b, 1.1),
                               brass[min(47, shade + (13 if depth >= 0 else 7))]))
            for i, unit in enumerate(self.tick_units[index]):
                major = i % (8 if index == 0 else 6) == 0
                a = self.on_ring(basis, unit, radius - width / 2 + 1.1)
                b = self.on_ring(basis, unit, radius + width / 2 - 1.1 if major
                                 else radius - width / 2 + width * .45)
                depth = (a[2] + b[2]) / 2
                pieces.append((depth + .05, self.quad_path(a, b, 1.2 if major else .65),
                               brass[39 if depth > 0 else 23]))

        # A tilted central spindle passes through the globe and ends in ferrules.
        spindle = self.rotate((0, 1, 0), .18, self.view_yaw, -.18)
        a = self.project(tuple(v * -67 for v in spindle))
        b = self.project(tuple(v * 67 for v in spindle))
        pieces.append((-52, self.quad_path(a, b, 3), brass[29]))
        self.add_sphere(pieces, *self.CENTER, 0, 43, palette["sphere"], brass[14])
        # Celestial graticule hugs the visible sphere; fixed engraved arcs.
        for latitude in (-.50, 0, .50):
            arc = []
            for j in range(25):
                u = -1 + j / 12
                x = 40 * math.sqrt(1 - latitude * latitude) * u
                y = 40 * latitude + 3.4 * math.sqrt(max(0, 1 - u * u))
                arc.append((self.CENTER[0] + x, self.CENTER[1] + y))
            for a, b in zip(arc, arc[1:]):
                pieces.append((.06, self.quad_path(a, b, .55), palette["globe"]))
        for sign in (-1, 1):
            arc = [(self.CENTER[0] + sign * 19 * math.sin(j * math.pi / 30),
                    self.CENTER[1] + 40 * math.cos(j * math.pi / 30)) for j in range(31)]
            for a, b in zip(arc, arc[1:]):
                pieces.append((.07, self.quad_path(a, b, .55), palette["globe"]))
        for end in (-1, 1):
            x, y, z = self.project(tuple(v * 64 * end for v in spindle))
            self.add_sphere(pieces, x, y, z, 4.1, palette["sphere"], brass[34])

        # Three distinct orbital weights; each is occluded by nearer metalwork.
        for index, radius, phase, rate, size in ((1, 176, .42, .19, 8.0),
                                                 (2, 146, 2.7, -.14, 6.0),
                                                 (3, 109, 4.3, .27, 4.5)):
            angle = phase + self.time * rate
            x, y, z = self.on_ring(bases[index], (math.cos(angle), math.sin(angle)), radius)
            # The weight projects above its ring face to avoid being cut in half.
            self.add_sphere(pieces, x, y, z + size + .2, size,
                            palette["sphere"], brass[35])
        pieces.sort(key=lambda entry: entry[0])
        return pieces, bases[0]

    def draw_backdrop(self, palette):
        signature = (self.theme, self.stage.width, self.stage.height, self.stage.scale)
        if self.paint.backdrop_signature == signature:
            return
        p = self.paint.backdrop
        p.begin()
        p.gradient(palette["background"], palette["panel"])
        for x, y, radius, shade in self.stars:
            p.circle(x, y, radius, palette["star"][shade])
        # Sparse drafting marks lend scale without a grid over the instrument.
        for x, y in ((-444, 236), (448, 236), (448, -250)):
            p.line([(x - 6, y), (x + 6, y)], palette["ink"])
            p.line([(x, y - 6), (x, y + 6)], palette["ink"])
        p.line([(-430, 173), (-389, 173)], palette["metal"], 1.2)
        p.text(-430, 197, "C E L E S T I A L   /   3 0", palette["muted"], 9, "w")
        p.text(-434, 125, "机械星仪", palette["highlight"], 30, "w", True)
        p.text(-431, 79, "ARMILLARY", palette["metal"], 16, "w")
        p.text(-431, 53, "SPHERE", palette["metal"], 16, "w")
        p.line([(-430, 11), (-260, 11)], palette["faint"])
        p.text(-430, -21, "让时间，沿星轨缓缓流动。", palette["muted"], 10, "w")
        p.text(-430, -53, "黄道 · 子午 · 赤道", palette["ink"], 9, "w")
        p.text(-430, -162, "01  /  观察", palette["metal"], 9, "w")
        p.text(-430, -186, "轻触画布，改变凝望的角度", palette["muted"], 9, "w")
        p.text(-430, -224, "A STUDY OF TIME & ORBIT", palette["ink"], 8, "w")
        p.end()
        self.paint.backdrop_signature = signature

    def draw_base(self, p, palette, outer_basis):
        """Stationary pedestal and a socket that meets the outer meridian."""
        x = self.CENTER[0]
        brass = palette["brass"]
        p.oval(x + 12, -239, 152, 14, palette["shadow"])
        p.oval(x + 10, -240, 112, 8, palette["background"])
        p.poly([(x - 103, -222), (x + 103, -222), (x + 103, -236),
                (x + 68, -246), (x - 68, -246), (x - 103, -236)], brass[5])
        p.oval(x, -233, 105, 17, brass[10], brass[20], .9)
        p.oval(x, -227, 106, 17, brass[17], brass[33], 1)
        p.oval(x, -224, 96, 13, brass[7], brass[25], 1)
        p.poly([(x - 38, -219), (x - 15, -206), (x - 12, -182),
                (x + 12, -182), (x + 15, -206), (x + 38, -219)], brass[17])
        p.poly([(x - 15, -216), (x - 9, -185), (x - 3, -185),
                (x - 5, -218)], brass[35])
        p.oval(x, -217, 41, 7, brass[18], brass[30], .8)
        p.oval(x, -219, 42, 6, brass[10], brass[22], .8)
        end = self.on_ring(outer_basis, (0, -1), 197)
        p.line([(x, -191), (x, -174), end[:2]], brass[8], 15, True)
        p.line([(x - 2, -190), (x - 2, -174), (end[0] - 2, end[1])], brass[25], 5, True)
        p.circle(end[0], end[1], 8.5, brass[10], brass[29], 1)
        p.circle(end[0], end[1], 4, brass[38], brass[12], 1)

    def frame(self, dt):
        if dt > 0 and not self.stage.paused:
            self.time = (self.time + dt * self.speed * self.direction) % (math.tau * 1200)
            blend = -math.expm1(-dt * 3.4)
            self.view_yaw += (self.target_yaw - self.view_yaw) * blend
            self.view_pitch += (self.target_pitch - self.view_pitch) * blend
        palette = self.palettes[self.theme]
        self.draw_backdrop(palette)
        pieces, outer_basis = self.geometry(palette)
        p = self.paint
        p.begin()
        self.draw_base(p, palette, outer_basis)
        for _, points, color in pieces:
            p.poly(points, color)
        p.end()
        p = self.paint.foreground
        p.begin()
        # Small museum plaque, separate from the moving object's depth pool.
        p.rect(98, -224, 192, -238, palette["background"], palette["brass"][22], .7)
        p.text(145, -231, "O R B I T  /  X X X", palette["metal"], 7)
        p.text(420, -215, "∞", palette["metal"], 19)
        p.text(420, -240, "CONTINUUM", palette["muted"], 7)
        p.end()
        self.stage.hud(f"{THEMES[self.theme][0]}    ·    {self.speed:.2f}×    ·    "
                       f"{'顺行' if self.direction > 0 else '逆行'}")


if __name__ == "__main__":
    app = Armillary()
    app.stage.run(app.frame, app.reset)
