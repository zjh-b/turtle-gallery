"""水晶花园：七枚棱晶、流动光源与艺术化色散。仅使用 Python 标准库。"""
import math
import random

from 舞台 import Paint, Stage, mix


THEMES = (
    ("冰蓝", "#3986A0", "#AEDCE1", "#E6FAF7", "#1E5A72"),
    ("紫晶", "#8773B1", "#CEC1E0", "#F3EBFC", "#5E477E"),
    ("蜜金", "#B78B43", "#E6D39B", "#FFF2C6", "#805F2C"),
)
SPECTRUM = ("#CFA285", "#C9B364", "#86B6A3", "#75AFC2", "#AB99C7")


def between(a, b, t):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def surface(quad, u, v):
    """A point inside a quadrilateral, with all texture confined to its face."""
    return between(between(quad[0], quad[1], u),
                   between(quad[3], quad[2], u), v)


class CrystalGarden:
    WORK_ID = 31
    DUST_COUNT = 32
    SEED = 31031

    def __init__(self):
        self.stage = Stage("水晶花园", "点击 移动光源    C 晶体配色    B 色散光束    ↑↓ 光线转速",
                           background="#EFF0EB", accent="#668D91", light=True)
        self.paint = Paint(self.stage, "crystal-garden")
        self.build_geometry()
        self.reset()
        self.stage.screen.onclick(self.illuminate)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("b", "B"):
            self.stage.screen.onkey(self.toggle_beams, key)
        self.stage.screen.onkey(lambda: self.change_speed(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.25), "Down")

    def reset(self):
        self.time = self.angle = 0.0
        self.theme, self.speed, self.beams = 0, 1.0, True
        self.source = [-82.0, 185.0]
        self.target = (-82.0, 185.0)

    def build_geometry(self):
        """Cache all prism faces and seeded inclusions; never generate them in a frame."""
        rng = random.Random(self.SEED)
        self.crystals = []
        # Back to front. Each prism has three body faces and three terminal facets.
        arrangement = ((221, -151, 306, 72, .14), (80, -150, 279, 65, -.11),
                       (10, -180, 210, 74, -.29), (306, -179, 231, 78, .29),
                       (157, -184, 388, 104, -.075), (88, -198, 214, 79, -.13),
                       (232, -201, 177, 82, .18))
        for index, (x, y, height, width, tilt) in enumerate(arrangement):
            co, si = math.cos(tilt), math.sin(tilt)

            def point(u, v):
                return x + u * co + v * si, y - u * si + v * co

            feet = [point(width * u, width * v)
                    for u, v in ((-.5, 0), (-.16, -.15), (.20, -.11), (.5, .025))]
            shoulders = [point(width * u, height * v)
                         for u, v in ((-.5, .76), (-.16, .72), (.20, .77), (.5, .82))]
            tip = point(.025 * width, height)
            faces = [tuple((feet[j], feet[j + 1], shoulders[j + 1], shoulders[j]))
                     for j in range(3)]
            strips, threads, fractures = [], [], []
            for face_index, quad in enumerate(faces):
                strips.append(tuple(tuple(surface(quad, u, v) for u, v in
                                    ((j / 9, 0), ((j + 1) / 9, 0),
                                     ((j + 1) / 9, 1), (j / 9, 1))) for j in range(9)))
                for _ in range(6):
                    u, low = rng.uniform(.08, .92), rng.uniform(.08, .55)
                    high = min(.95, low + rng.uniform(.16, .40))
                    threads.append((face_index, (surface(quad, u, low),
                                    surface(quad, u + rng.uniform(-.025, .025), high)),
                                    rng.randrange(3)))
                for level in (.20, .37, .53, .69, .84):
                    fractures.append((face_index,
                                      (surface(quad, .07, level),
                                       surface(quad, .47, level + .014),
                                       surface(quad, .94, level - .009))))
            # Narrow light-catching planes are geometric, so they never crawl.
            ribbons = [tuple(surface(quad, u, v) for u, v in
                             ((.12, .02), (.18, .02), (.30, .97), (.23, .97)))
                       for quad in faces]
            self.crystals.append(dict(base=(x, y), center=point(0, height * .52),
                                      feet=tuple(feet), shoulders=tuple(shoulders), tip=tip,
                                      faces=tuple(faces), strips=tuple(strips),
                                      threads=tuple(threads), fractures=tuple(fractures),
                                      ribbons=tuple(ribbons), index=index))
        self.dust = tuple((rng.uniform(-80, 414), rng.uniform(-120, 215),
                           rng.uniform(.6, 1.35), rng.uniform(0, math.tau),
                           rng.uniform(.35, .85)) for _ in range(self.DUST_COUNT))
        self.pebbles = tuple((rng.uniform(-7, 347), rng.uniform(-213, -195),
                             rng.uniform(2, 7), rng.uniform(0, math.tau)) for _ in range(19))
        self.background = tuple(mix("#F2F2ED", "#E4E8E3", i / 31) for i in range(32))
        self.halo = tuple(mix("#EFF0EB", "#FFFFFF", i / 11 * .64) for i in range(12))
        self.shadow = tuple(mix("#E3E7E1", "#A6B4AD", i / 9 * .43) for i in range(10))
        self.materials = []
        for _, body, soft, clear, dark in THEMES:
            self.materials.append(dict(
                body=tuple(mix(dark, soft, .21 + i / 63 * .75) for i in range(64)),
                cap=tuple(mix(body, clear, .30 + i / 31 * .62) for i in range(32)),
                line=tuple(mix(body, clear, .43 + i / 31 * .50) for i in range(32)),
                darkline=mix(body, dark, .26),
                inclusion=tuple(mix(body, clear, k) for k in (.48, .62, .77)),
                glow=tuple(mix("#EEF0E9", clear, .12 + i / 31 * .84) for i in range(32)),
                accent=mix(body, dark, .32),
                pebble=mix(soft, "#D4DDD5", .68),
                dust=tuple(mix("#E9EDE6", body, .12 + i / 31 * .38) for i in range(32)),
            ))
        self.beam_colors = tuple(tuple(mix("#E5E9E3", color, .13 + k / 7 * .32)
                                      for k in range(8)) for color in SPECTRUM)

    def change_theme(self):
        if not self.stage.paused:
            self.theme = (self.theme + 1) % len(THEMES)

    def change_speed(self, amount):
        if not self.stage.paused and math.isfinite(amount):
            self.speed = max(.25, min(2.5, self.speed + amount))

    def toggle_beams(self):
        if not self.stage.paused:
            self.beams = not self.beams

    def illuminate(self, x, y):
        if self.stage.paused or not (math.isfinite(x) and math.isfinite(y)):
            return
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            self.target = (max(-440, min(430, x)), max(-230, min(230, y)))

    def update(self, dt):
        if self.stage.paused or not math.isfinite(dt) or dt <= 0:
            return
        self.time = (self.time + dt) % 3600
        angular_speed = self.speed * .42
        turn = (dt % (math.tau / angular_speed)) * angular_speed
        self.angle = (self.angle + turn) % math.tau
        response = -math.expm1(-dt * 3.1)
        for axis in (0, 1):
            self.source[axis] += (self.target[axis] - self.source[axis]) * response

    def light_position(self):
        return (max(-454, min(445, self.source[0] + 12 * math.cos(self.angle))),
                max(-242, min(234, self.source[1] + 9 * math.sin(self.angle))))

    def draw_background(self, p, material):
        w, h = self.stage.view
        for i, color in enumerate(self.background):
            p.rect(-w / 2 - 2, h / 2 - i * h / 32 + 1,
                   w / 2 + 2, h / 2 - (i + 1) * h / 32 - 1, color)
        # Broad, quiet studio illumination, with no stars or decorative frame.
        for i, color in enumerate(self.halo):
            p.oval(185, 25, 243 - i * 10, 212 - i * 8, color)
        p.line([(-451, -151), (453, -151)], "#D7DED7", .8)
        for i, color in enumerate(self.shadow):
            p.oval(179, -218, 247 - i * 7, 24 - i * 1.4, color)
        p.text(-439, 192, "M I N E R A L   S T U D I E S", "#7F9189", 9, "w")
        p.text(-442, 130, "水晶花园", "#354E4B", 33, "w", True)
        p.text(-439, 86, "CRYSTAL GARDEN", material["accent"], 13, "w")
        p.line([(-439, 49), (-400, 49)], material["accent"], 1.3)
        p.text(-439, 16, "让光，经过一座微小的山。", "#72877F", 11, "w")
        p.text(-439, -9, "七枚棱晶 · 一束流动的光", "#86988E", 10, "w")
        p.text(-439, -111, "0" + str(self.theme + 1) + "  /  " + THEMES[self.theme][0],
               material["accent"], 12, "w")
        p.text(-439, -134, "点击留白，改变光的方向", "#8A9A90", 9, "w")
        p.text(-439, -227, "FACETS  /  LIGHT  /  STILLNESS", "#91A097", 8, "w")

    def draw_beams(self, p, light):
        entry = (123, 116)
        # Beam paths are an artistic illustration, not a physical optics solver.
        dx, dy = entry[0] - light[0], entry[1] - light[1]
        distance = max(1, math.hypot(dx, dy))
        nx, ny = -dy / distance, dx / distance
        incoming = ((light[0] + nx * 1.3, light[1] + ny * 1.3),
                    (entry[0] + nx * 6, entry[1] + ny * 6),
                    (entry[0] - nx * 6, entry[1] - ny * 6),
                    (light[0] - nx * 1.3, light[1] - ny * 1.3))
        p.poly(incoming, "#F8F8EF" if self.beams else "")
        p.line([light, entry], "#FAFBF4" if self.beams else "", 1.1)
        origin = (181, -9)
        turn = .11 * math.sin(self.angle) + .12 * math.tanh((light[1] - 100) / 150)
        for index, colors in enumerate(self.beam_colors):
            angle = -.39 - index * .062 + turn
            vx, vy = math.cos(angle), math.sin(angle)
            length = min((453 - origin[0]) / vx, (-246 - origin[1]) / vy)
            nx, ny = -vy, vx
            for segment in range(8):
                t0, t1 = segment / 8, (segment + 1) / 8
                a = (origin[0] + vx * length * t0, origin[1] + vy * length * t0)
                b = (origin[0] + vx * length * t1, origin[1] + vy * length * t1)
                wa, wb = 1.1 + t0 * 3, 1.1 + t1 * 3
                p.poly(((a[0] - nx * wa, a[1] - ny * wa),
                        (b[0] - nx * wb, b[1] - ny * wb),
                        (b[0] + nx * wb, b[1] + ny * wb),
                        (a[0] + nx * wa, a[1] + ny * wa)),
                       colors[7 - segment] if self.beams else "")
            end = (origin[0] + vx * length, origin[1] + vy * length)
            p.line([origin, end], colors[2] if self.beams else "", .8)
            t = (.19 * self.time + index * .18) % 1
            shimmer = (origin[0] + vx * length * t, origin[1] + vy * length * t)
            shimmer_end = (shimmer[0] - vx * 18, shimmer[1] - vy * 18)
            p.line([shimmer_end, shimmer], colors[6] if self.beams else "", 1.2)

    def draw_plinth(self, p, material):
        p.oval(175, -206, 222, 35, "#9BAEA5")
        p.rect(-47, -195, 397, -205, "#A8BAB0")
        p.oval(175, -195, 222, 34, "#CED8CD", "#E8EDE2", .8)
        p.oval(175, -191, 196, 25, "#D5DED3")
        p.line([(-8, -212), (60, -224), (176, -232), (278, -224), (350, -211)],
               "#B8C8BA", .8, smooth=True)
        for x, y, size, phase in self.pebbles:
            p.poly(((x - size, y), (x - size * .3, y + size * .7),
                    (x + size * .7, y + size * .6), (x + size, y - size * .3),
                    (x, y - size * .6)), material["pebble"])
        for crystal in self.crystals:
            x, y = crystal["base"]
            p.oval(x + 12, y - 2, 45, 9, "#BBCBBC")

    def draw_crystal(self, p, crystal, material, light):
        dx, dy = light[0] - crystal["center"][0], light[1] - crystal["center"][1]
        norm = max(1, math.hypot(dx, dy))
        dx, dy = dx / norm, dy / norm
        phase = crystal["index"] * .8
        pulse = .5 + .5 * math.sin(self.angle + phase)
        strengths = (.42 + .20 * -dx + .08 * dy,
                     .70 + .10 * dx + .07 * dy,
                     .29 + .20 * dx + .07 * dy)
        for face, strips in enumerate(crystal["strips"]):
            for stripe, quad in enumerate(strips):
                shine = strengths[face] + .10 * math.sin(stripe * .43 + phase)
                index = round(max(0, min(1, shine)) * 63)
                p.poly(quad, material["body"][index])
            p.poly(crystal["ribbons"][face], material["line"][5 + round(pulse * 5)])
        shoulders, feet, tip = crystal["shoulders"], crystal["feet"], crystal["tip"]
        for j in range(3):
            strength = max(0, min(1, strengths[j] + .13))
            p.poly((shoulders[j], shoulders[j + 1], tip), material["cap"][round(strength * 31)])
        for face, points in crystal["fractures"]:
            p.line(points, material["inclusion"][0], .5)
        for face, points, shade in crystal["threads"]:
            p.line(points, material["inclusion"][shade], .55)
        for j in range(4):
            color = material["line"][25 if j in (0, 2) else 10]
            p.line([feet[j], shoulders[j], tip], color, 1.05 if j == 2 else .7)
        p.line(shoulders, material["line"][21], .8)
        p.line(feet, material["darkline"], .8)
        # Each tip has a restrained moving highlight, smaller than the facets.
        radius = 1.2 + 1.9 * pulse ** 4
        tx, ty = tip
        p.line([(tx - radius * 1.5, ty), (tx + radius * 1.5, ty)], "#FFFFFF", .9)
        p.line([(tx, ty - radius * 2), (tx, ty + radius * 2)], "#FFFFFF", .9)

    def draw_light(self, p, material, light):
        x, y = light
        # The little orbit makes a click's destination easy to see without a cursor trail.
        p.circle(x, y, 10, "", "#B7C6B8", .6)
        p.circle(x, y, 5.5, "#F5F7EB", "#D0D9BF", .7)
        p.circle(x, y, 2.1, "#FFFFFF")
        p.line([(x - 15, y), (x - 12, y)], "#C1CCB8", .7)
        p.line([(x + 12, y), (x + 15, y)], "#C1CCB8", .7)
        p.line([(x, y - 15), (x, y - 12)], "#C1CCB8", .7)
        p.line([(x, y + 12), (x, y + 15)], "#C1CCB8", .7)
        # A refracted hairline travels inside the tallest crystal.
        p.line([(123, 116), (151, 58), (181, -9)],
               material["line"][27] if self.beams else "", .7)

    def frame(self, dt):
        self.update(dt)
        p = self.paint
        p.begin()
        material = self.materials[self.theme]
        light = self.light_position()
        self.draw_background(p, material)
        self.draw_beams(p, light)
        self.draw_plinth(p, material)
        for crystal in self.crystals:
            self.draw_crystal(p, crystal, material, light)
        self.draw_light(p, material, light)
        for x, y, size, phase, speed in self.dust:
            dx = 5 * math.sin(self.time * .23 * speed + phase)
            dy = 7 * math.sin(self.time * .17 * speed + phase * 1.7)
            strength = round((.5 + .5 * math.sin(self.time * speed + phase)) * 31)
            p.circle(x + dx, y + dy, size, material["dust"][strength])
        p.end()
        self.stage.hud(f"{THEMES[self.theme][0]}晶簇  ·  光线 {self.speed:.2f}×  ·  "
                       f"色散{'开启' if self.beams else '关闭'}")

    def run(self):
        self.stage.run(self.frame, self.reset)


if __name__ == "__main__":
    CrystalGarden().run()
