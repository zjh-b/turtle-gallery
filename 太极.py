"""太极：精确双鱼、温纸墨色与缓缓转动的几何圆盘。只用标准库。"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、纸面、纸影、墨色、白瓷、金属纹饰；主盘始终保留鲜明黑白关系。
PALETTES = (
    ("温纸墨金", "#F5F0E4", "#E0DAC9", "#172A2A", "#FFFCED", "#A48B56"),
    ("青瓷月白", "#ECF3F1", "#CFDDDA", "#18313A", "#FCFFF7", "#6D9496"),
    ("松夜流金", "#1C302F", "#102123", "#0C181D", "#EAF0DE", "#BCA36B"),
)


def arc(radius, start, end, x=0, y=0, steps=96):
    return [polar(radius, start + (end - start) * i / steps, x, y)
            for i in range(steps + 1)]


def fish_path(radius):
    """一个外半圆与两个反向内半圆；面积为整圆的一半。

    上方墨鱼含白眼，下方白鱼含墨眼。内弧半径恰为外圆的一半，
    两条弧在圆心相切，不用平滑曲线近似来改变双鱼比例。
    """
    outer = arc(radius, math.pi / 2, -math.pi / 2, steps=160)
    lower = arc(radius / 2, -math.pi / 2, math.pi / 2, y=-radius / 2, steps=80)
    upper = arc(radius / 2, -math.pi / 2, -3 * math.pi / 2, y=radius / 2, steps=80)
    return outer + lower[1:] + upper[1:]


class YinYang:
    RADIUS = 184
    ROTATION_RATE = .18
    RIPPLE_SLOTS = 6
    RIPPLE_SECONDS = 2.8

    def __init__(self):
        self.stage = Stage("太极流转", "C 配色    ↑↓ 调速    D 反向    L 环纹    点击 泛起涟漪",
                           PALETTES[0][1], PALETTES[0][5], light=True)
        self.paint = Paint(self.stage, "yin-yang")
        self.paint.backdrop = Paint(self.stage, "yin-yang-paper")
        self.paint.signature = None
        self.fish = tuple(fish_path(self.RADIUS))
        rng = random.Random(184)
        self.fibers = tuple((rng.uniform(-473, 473), rng.uniform(-269, 250),
                             rng.uniform(1.8, 5.5)) for _ in range(64))
        self.dust = tuple((rng.choice((-1, 1)) * rng.uniform(258, 448),
                           rng.uniform(-220, 211), rng.uniform(.7, 1.7),
                           rng.uniform(0, math.tau)) for _ in range(18))
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_palette, key)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.reverse, key)
        for key in ("l", "L"):
            self.stage.screen.onkey(self.toggle_ornament, key)
        self.stage.screen.onkey(lambda: self.change_speed(.2), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.2), "Down")
        self.stage.screen.onclick(self.ripple)

    def reset(self):
        self.time = self.angle = 0.0
        self.speed, self.direction = 1.0, 1
        self.palette, self.ornament = 0, True
        self.ripples, self.ripple_cursor = [None] * self.RIPPLE_SLOTS, 0
        self.sync_stage()

    def sync_stage(self):
        colors = PALETTES[self.palette]
        self.stage.accent = colors[5]
        self.stage.light = self.palette != 2

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)
        self.sync_stage()

    def change_speed(self, amount):
        self.speed = max(0, min(3, self.speed + amount))

    def reverse(self):
        self.direction *= -1

    def toggle_ornament(self):
        self.ornament = not self.ornament

    def ripple(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not (-500 < x < 500 and -285 < y < 265):
            return
        if not self.stage.in_scene(x, y):
            return
        self.ripples[self.ripple_cursor] = (x, y, 0.0)
        self.ripple_cursor = (self.ripple_cursor + 1) % self.RIPPLE_SLOTS

    def rotated(self, points):
        co, si = math.cos(self.angle), math.sin(self.angle)
        return [(x * co - y * si, x * si + y * co) for x, y in points]

    def backdrop(self, colors):
        signature = (self.palette, self.ornament, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        _, paper, ground, ink, porcelain, brass = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(paper, ground)
        for x, y, length in self.fibers:
            p.line([(x, y), (x + length, y + .8)], mix(paper, ground, .64), .7)
        # 安静的边栏留白，让径向纹理只环绕主盘，不占据整个画面。
        muted = mix(ground, brass, .61)
        p.line([(-435, 153), (-393, 153)], brass, 1.7)
        p.text(-435, 120, "两仪 / 流转", mix(ground, ink, .70) if self.palette != 2 else porcelain,
               19, "w")
        p.text(-433, 93, "A STUDY IN BALANCE", muted, 8, "w")
        p.text(-433, -169, "一动一静，圆中相生。", muted, 10, "w")
        p.line([(327, -172), (434, -172)], mix(ground, brass, .44))
        p.text(434, -193, "TWO CURVES", brass, 9, "e")
        p.text(434, -214, "ONE CONTINUOUS CIRCLE", muted, 8, "e")
        p.text(434, -242, "TAIJI   /   01", muted, 8, "e")
        # 固定的浅浮雕投影与四道金属边缘。主体保持平面黑白几何。
        for i in range(7):
            p.circle(2, -4, 201 - i * 1.5,
                     mix(ground, ink, .025 + .01 * i))
        if self.ornament:
            self.draw_ornament(p, colors)
        p.circle(0, 0, 197, mix(ground, brass, .70))
        p.circle(0, 0, 195.7, mix(ground, porcelain, .73))
        p.circle(0, 0, 193, mix(ground, brass, .89))
        p.circle(0, 0, 190.6, mix(ink, brass, .36))
        p.circle(0, 0, 188.5, mix(brass, porcelain, .55))
        p.circle(0, 0, 186.6, ink)
        p.end()
        self.paint.signature = signature

    @staticmethod
    def draw_ornament(p, colors):
        _, paper, ground, ink, porcelain, brass = colors
        fine = mix(ground, brass, .52)
        p.circle(0, 0, 230, outline=mix(ground, brass, .30))
        p.circle(0, 0, 226, outline=fine)
        p.circle(0, 0, 207, outline=mix(ground, brass, .28))
        for i in range(120):
            a = i * math.tau / 120
            major = i % 10 == 0
            inner = 216 if major else (219 if i % 5 == 0 else 222)
            p.line([polar(inner, a), polar(226, a)], brass if major else fine,
                   1.3 if major else .65)
        for i in range(12):
            a = i * math.tau / 12
            p.line(arc(211, a + .075, a + math.pi / 6 - .075, steps=18), fine, .8)
            x, y = polar(211, a)
            p.circle(x, y, 1.3, brass)
        # 四个小菱形只作几何定位点，不借用卦象、方位文字等文化规则。
        for i in range(4):
            a = math.pi / 4 + i * math.pi / 2
            x, y = polar(230, a)
            p.poly([polar(3.2, a + j * math.pi / 2, x, y) for j in range(4)],
                   mix(ground, brass, .75))

    def draw_disc(self, colors):
        _, _, ground, ink, porcelain, brass = colors
        p, radius = self.paint, self.RADIUS
        p.circle(0, 0, radius, porcelain)
        p.poly(self.rotated(self.fish), ink)
        # 鱼眼与内半圆同心，大小为主盘直径的八分之一。
        for y, color in ((radius / 2, porcelain), (-radius / 2, ink)):
            x1, y1 = self.rotated(((0, y),))[0]
            p.circle(x1, y1, radius / 8, color)
        p.circle(0, 0, radius, outline=mix(ink, brass, .19), width=.9)

    def draw_atmosphere(self, colors):
        _, paper, ground, _, porcelain, brass = colors
        p = self.paint
        for x, y, size, phase in self.dust:
            xx = x + 4 * math.sin(self.time * .16 + phase)
            yy = y + 8 * math.sin(self.time * .23 + phase)
            gleam = .28 + .20 * math.sin(self.time * .6 + phase) ** 2
            p.circle(xx, yy, size, mix(paper, brass, gleam))
        for side in (-1, 1):
            for line in range(3):
                y = 16 + line * 12
                phase = self.time * .25 + line * .3
                points = [(side * (275 + i * 11), y + 7 * math.sin(i * .3 + phase))
                          for i in range(15)]
                p.line(points, mix(ground, brass, .16 + line * .025), .7, smooth=True)

    def draw_ripples(self, colors):
        p = self.paint
        _, paper, ground, ink, porcelain, brass = colors
        for ripple in self.ripples:
            if ripple is None:
                # 槽位保留相同图元类型，反复点击不会分配更多 Canvas 对象。
                for _ in range(3):
                    p.circle(0, 0, 0)
                continue
            x, y, age = ripple
            limit = max(0, min(54, x + 499, 499 - x, y + 284, 264 - y))
            fade = (1 - age / self.RIPPLE_SECONDS) ** 1.5
            for ring in range(3):
                progress = max(0, min(1, age / self.RIPPLE_SECONDS * 1.3 - ring * .13))
                radius = limit * progress
                # 涟漪在主盘上用中间金色，避免整圈白光盖住黑白鱼。
                p.circle(x, y, radius, outline=mix(ground, brass, fade * (.75 - ring * .17)),
                         width=1.1)

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.angle = (self.angle + self.direction * self.speed * self.ROTATION_RATE * dt) % math.tau
            self.ripples = [None if value is None or value[2] + dt >= self.RIPPLE_SECONDS
                            else (value[0], value[1], value[2] + dt) for value in self.ripples]
        colors = PALETTES[self.palette]
        self.backdrop(colors)
        # 缓存的背景只按标签调整层叠；避免每帧逐个提升静态刻度。
        self.stage.canvas.tag_raise(self.paint.backdrop.tag)
        self.paint.begin()
        self.draw_atmosphere(colors)
        self.draw_disc(colors)
        self.draw_ripples(colors)
        self.paint.end()
        direction = "逆时针" if self.direction > 0 else "顺时针"
        status = "静止" if not self.speed else f"{direction} {self.speed:.1f} 倍"
        self.stage.hud(f"{colors[0]}  ·  {status}  ·  环纹{'开' if self.ornament else '关'}")


if __name__ == "__main__":
    app = YinYang()
    app.stage.run(app.frame, app.reset)
