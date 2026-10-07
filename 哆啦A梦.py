"""圆圆的蓝色朋友：用圆、椭圆与曲线细化原来的哆啦 A 梦头像。

C 换背景，B 眨眼，M 换表情；点击让视线跟随，点铃铛看它轻轻摇动。
只使用标准库和项目共用舞台；直接运行本文件即可。
"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、纸底、纸影、题签、头部暗色、头部亮色。角色的蓝白红配色不变。
PALETTES = (
    ("晴蓝纸页", "#F6F3E8", "#E1EEE9", "#588B9A", "#086494", "#32B2E0"),
    ("云上汽水", "#E7F5FA", "#C9E7EF", "#4C8CA2", "#066C9A", "#46C4E6"),
    ("星夜口袋", "#0D2338", "#1C3B51", "#98C6CD", "#07577D", "#369DCB"),
)
INK = "#183D51"
WHITE = "#FFFEF7"
BELL = (0, -184)
BLINK_SECONDS = .32
TARGET_SECONDS = 4.


def curve(a, b, c, d, steps=40):
    """Sample a cubic curve without any third-party drawing library."""
    return [tuple((1 - t) ** 3 * a[k] + 3 * (1 - t) ** 2 * t * b[k] +
                  3 * (1 - t) * t * t * c[k] + t ** 3 * d[k] for k in (0, 1))
            for t in (i / steps for i in range(steps + 1))]


def pupil_offset(eye_x, target_x, target_y):
    """Constrain the centre of each pupil to a small ellipse inside its eye."""
    dx, dy = (target_x - eye_x) / 17, (target_y - 144) / 20
    length = math.hypot(dx / 9, dy / 11)
    if length > 1:
        dx, dy = dx / length, dy / length
    return dx, dy


class DoraemonPortrait:
    def __init__(self):
        self.stage = Stage("哆啦A梦头像", "点击 目光跟随    点铃铛 轻摇    B 眨眼    M 表情    C 背景",
                           PALETTES[0][1], PALETTES[0][3], light=True)
        self.paint = Paint(self.stage, "portrait-expression")
        self.paint.backdrop = Paint(self.stage, "portrait-paper")
        self.paint.signature = None
        rng = random.Random(318)
        self.specks = tuple((rng.choice((-1, 1)) * rng.uniform(220, 458),
                             rng.uniform(-220, 218), rng.uniform(1, 2.4)) for _ in range(32))
        self.reset()
        for key in ('c', 'C'):
            self.stage.screen.onkey(self.cycle_palette, key)
        for key in ('b', 'B'):
            self.stage.screen.onkey(self.blink, key)
        for key in ('m', 'M'):
            self.stage.screen.onkey(self.toggle_smile, key)
        self.stage.screen.onclick(self.look)

    def reset(self):
        self.time, self.palette, self.ring = 0., 0, 0.
        self.smile = True
        self.blink_age = self.target = None
        self.gaze = [0., 125.]

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def toggle_smile(self):
        self.smile = not self.smile

    def blink(self):
        if not self.stage.paused:
            self.blink_age = 0.

    def look(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not (-475 < x < 475 and -280 < y < 250):
            return
        self.target = (x, y, 0.)
        if math.hypot(x - BELL[0], y - BELL[1]) <= 26:
            self.ring = 1.4
            self.blink()

    def eye_open(self):
        age = self.blink_age
        if age is None:
            phase = self.time % 5.2
            age = phase - 4.65 if 4.65 <= phase < 4.65 + BLINK_SECONDS else None
        if age is None:
            return 1.
        return max(.035, 1 - math.sin(math.pi * age / BLINK_SECONDS) ** 2)

    def update(self, dt):
        if dt <= 0:
            return
        self.time += dt
        self.ring = max(0., self.ring - dt)
        if self.blink_age is not None:
            self.blink_age += dt
            if self.blink_age >= BLINK_SECONDS:
                self.blink_age = None
        if self.target is not None:
            x, y, age = self.target
            self.target = (x, y, age + dt) if age + dt < TARGET_SECONDS else None
        destination = self.target[:2] if self.target else (0., 125.)
        amount = 1 - math.exp(-7 * dt)
        for index in (0, 1):
            self.gaze[index] += (destination[index] - self.gaze[index]) * amount

    def backdrop(self, colors):
        signature = (self.palette, self.smile, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            self.stage.canvas.tag_raise(self.paint.backdrop.tag)
            return
        self.paint.signature = signature
        _, paper, ground, accent, blue_dark, blue = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(paper, ground)
        # Soft graphic motifs leave a clear silhouette around the character.
        for side in (-1, 1):
            for ring in range(3):
                p.circle(side * 337, -8, 101 + ring * 16, outline=mix(ground, accent, .12 - ring * .025))
        for x, y, size in self.specks:
            p.circle(x, y, size, mix(paper, accent, .20))
        for x, y, radius in ((-270, 198, 10), (286, 168, 12), (392, -84, 8), (-349, -137, 7)):
            p.star(x, y, radius, mix(ground, accent, .30), angle=math.pi / 2)
        title = mix(ground, '#244D61', .84) if self.palette < 2 else '#D7E7EB'
        p.line([(-444, 124), (-403, 124)], accent, 2)
        p.text(-444, 95, "圆圆的蓝色朋友", title, 18, 'w', True)
        p.text(-443, 68, "CIRCLES / CHARACTER STUDY", accent, 8, 'w')
        p.text(-443, -182, "点击，让目光跟随你。", accent, 10, 'w')
        p.text(439, -177, "画一个笑脸", title, 17, 'e')
        p.text(439, -205, "点一点铃铛，打个招呼。", accent, 10, 'e')
        p.line([(319, -229), (438, -229)], mix(ground, accent, .44))
        # Shoulder silhouette and a small glimpse of the white pocket.
        p.oval(0, -273, 157, 7, mix(ground, accent, .15))
        shoulders = [(-78, -139), (-127, -172), (-153, -258), (-134, -272),
                     (134, -272), (153, -258), (127, -172), (78, -139)]
        p.poly(shoulders, blue_dark, INK, 2.4, smooth=True)
        p.poly([(-75, -153), (-115, -192), (-129, -266), (124, -266),
                (111, -190), (74, -153)], blue, smooth=True)
        p.poly([(-64, -208), (-91, -227), (-84, -270), (84, -270),
                (91, -227), (64, -208)], WHITE, smooth=True)
        p.line(curve((-58, -244), (-52, -279), (52, -279), (58, -244)), '#BED9DE', 1.7)
        p.line([(-58, -244), (58, -244)], '#BED9DE', 1.7)
        # Blue head: inset, offset ovals produce a rounded upper-left light.
        p.oval(4, 28, 189, 198, mix(ground, blue_dark, .18))
        p.oval(0, 35, 187, 196, INK)
        for band in range(24):
            fraction = band / 23
            p.oval(-7 * fraction, 35 + 15 * fraction, 184 - band * 1.1,
                   193 - band * 1.2, mix(blue_dark, blue, fraction))
        p.line([(math.cos(a) * 177 - 1, 39 + math.sin(a) * 184)
                for a in (1.82 + i * .65 / 40 for i in range(41))], mix(blue, WHITE, .56), 3)
        # White muzzle, subtly shaded around the lower edge.
        p.oval(0, 4, 159, 161, INK)
        for band in range(16):
            p.oval(-band * .14, 5 + band * .45, 156 - band * .42, 158 - band * .43,
                   mix('#C8E3E7', WHITE, band / 15))
        # Six whiskers retain the original's simple line construction.
        for side in (-1, 1):
            for x1, y1, x2, y2 in ((58, 54, 150, 79), (63, 17, 159, 20), (60, -19, 151, -44)):
                p.line([(side * x1, y1), (side * x2, y2)], INK, 2.5)
            for band in range(4):
                p.oval(side * 112, -3, 22 - band * 3.3, 9 - band * 1.1,
                       mix(WHITE, '#F5C0BD', .13 + band * .075))
        if self.smile:
            upper = curve((-108, -23), (-48, -46), (48, -46), (108, -23))
            lower = curve((108, -23), (94, -129), (-94, -129), (-108, -23))
            p.poly(upper + lower[1:], '#7C303D', INK, 2.5)
            tongue = curve((-57, -79), (-30, -62), (30, -62), (57, -79))
            tongue += curve((57, -79), (29, -108), (-29, -108), (-57, -79))[1:]
            p.poly(tongue, '#EF8990')
            p.line([(0, -80), (0, -96)], '#CB6472', 1.2)
            stem_bottom = -39
        else:
            p.line(curve((-106, -25), (-63, -95), (63, -95), (106, -25)), INK, 3)
            stem_bottom = -76
        p.line([(0, 88), (0, stem_bottom)], INK, 2.5)
        # Nose layers: red body, reflected rim, soft highlight.
        p.circle(0, 107, 20, INK)
        for band in range(14):
            fraction = band / 13
            p.circle(-3 * fraction, 107 + 4 * fraction, 17.5 - band * .7,
                     mix('#AF3045', '#F97276', fraction))
        p.oval(-6, 114, 5.4, 3.7, '#FFF4E3')
        collar = [(-111, -139), (-83, -158), (83, -158), (111, -139),
                  (100, -171), (-100, -171)]
        p.poly(collar, '#C94151', INK, 2.3, smooth=True)
        p.line([(-96, -153), (-51, -164), (51, -164), (96, -153)], '#F08580', 3, smooth=True)
        p.end()

    def draw_eyes(self):
        p, opened = self.paint, self.eye_open()
        closed = opened < .12
        for x in (-38, 38):
            # Preserve the eye sockets while blinking; a closed lid is a curve,
            # rather than flattening the whole eye into a line on the forehead.
            p.oval(x, 144, 37, 48 * (.84 + .16 * opened), WHITE, INK, 2.2)
            dx, dy = pupil_offset(x, *self.gaze)
            px, py = x + dx, 144 + dy * opened
            p.oval(px, py, 11, 21 * opened, '' if closed else INK)
            p.oval(px - 3, py + 8 * opened, 3.8, 6 * opened, '' if closed else WHITE)
            p.oval(px + 3.4, py - 8 * opened, 1.8, 2.2 * opened, '' if closed else '#90B9C8')
            p.line(curve((x - 19, 141), (x - 9, 154), (x + 9, 154), (x + 19, 141), 20),
                   INK if closed else '', 2.5)

    def draw_bell(self, colors):
        p = self.paint
        x = math.sin(self.ring * 25) * 4 * min(1, self.ring)
        y = BELL[1]
        p.circle(x + 2, y - 3, 27, '#873F39')
        p.circle(x, y, 26, INK)
        for band in range(16):
            fraction = band / 15
            p.circle(x - 4 * fraction, y + 5 * fraction, 23.5 - band * .9,
                     mix('#C79031', '#FFEAA0', fraction))
        p.line([(x - 21, y + 6), (x + 21, y + 6)], '#957137', 3)
        p.line([(x - 21, y + 9), (x + 20, y + 9)], '#FFF1B9', 2)
        p.circle(x, y - 7, 4, INK)
        p.line([(x, y - 7), (x, y - 23)], INK, 2)
        p.oval(x - 10, y + 14, 5, 2.7, '#FFF9D8')
        for side in (-1, 1):
            for layer in (0, 1):
                radius = 34 + layer * 10
                points = [polar(radius, i * .8 / 18 - .4 + (math.pi if side < 0 else 0), x, y)
                          for i in range(19)]
                color = mix(colors[2], colors[3], min(.8, self.ring) * (.8 - layer * .25))
                # Empty lines keep their slots during idle frames.
                p.line(points if self.ring else [(0, -284), (0, -284)], color, 1.5)

    def frame(self, dt):
        self.update(dt)
        colors = PALETTES[self.palette]
        self.stage.light, self.stage.accent = self.palette < 2, colors[3]
        self.backdrop(colors)
        self.paint.begin()
        self.draw_eyes()
        self.draw_bell(colors)
        self.paint.end()
        self.stage.hud(f"{colors[0]} · {'开怀笑' if self.smile else '弯弯笑'}  /  目光跟随点击 · 铃铛轻摇")


if __name__ == '__main__':
    app = DoraemonPortrait()
    app.stage.run(app.frame, app.reset)
