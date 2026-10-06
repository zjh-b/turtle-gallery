"""雨落有声：从圆弧雨伞升级的雨夜小景，只使用 Python 标准库。"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix


SCHEMES = (
    ("珊瑚晚灯", ("#893845", "#C75858", "#EF927A", "#A7484C"), "#FFD5AA"),
    ("青瓷听雨", ("#24505A", "#377D80", "#74B3AB", "#315F6E"), "#CBE8D1"),
    ("鸢尾暮色", ("#493E6B", "#7C5E93", "#B493BA", "#654B7B"), "#EAC8EA"),
)


class RainUmbrella:
    """静态伞面分层缓存；雨线和涟漪复用固定数量的 Canvas 对象。"""

    def __init__(self):
        self.stage = Stage("圆弧雨伞", "C 伞面配色    ↑↓ 雨量    点击水面 泛起涟漪",
                           "#0B1822", "#E9AC91")
        self.paint = Paint(self.stage, "umbrella")
        self.paint.backdrop = Paint(self.stage, "umbrella-backdrop")
        self.paint.weather = Paint(self.stage, "umbrella-rain")
        self.paint.water = Paint(self.stage, "umbrella-water")
        self.paint.signature = None
        rng = random.Random(721)
        self.rain = tuple((rng.uniform(-460, 470), rng.uniform(0, 550),
                           rng.uniform(110, 220), rng.uniform(.4, 1)) for _ in range(112))
        self.pond = tuple((rng.uniform(-435, 435), rng.uniform(-266, -184),
                           rng.uniform(0, 3), rng.uniform(8, 24)) for _ in range(26))
        self.bokeh = tuple((rng.uniform(-435, 435), rng.uniform(-105, 168),
                            rng.uniform(1, 3), rng.random()) for _ in range(24))
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_scheme, key)
        self.stage.screen.onkey(lambda: self.change_rain(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_rain(-.25), "Down")
        self.stage.screen.onclick(self.ripple)

    def reset(self):
        self.time, self.scheme, self.strength = 0, 0, 1
        self.ripples = [[0, 0, -1] for _ in range(8)]
        self.ripple_cursor = 0

    def change_scheme(self):
        self.scheme = (self.scheme + 1) % len(SCHEMES)

    def change_rain(self, delta):
        self.strength = max(.25, min(2, self.strength + delta))

    def ripple(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        if -450 < x < 450 and -270 < y < -178:
            self.ripples[self.ripple_cursor] = [x, y, self.time]
            self.ripple_cursor = (self.ripple_cursor + 1) % len(self.ripples)

    @staticmethod
    def rib(u, t):
        """将半椭圆按横向比例压缩，保留原作圆弧伞骨的构造。"""
        return 48 + u * 224 * math.sin(t * math.pi / 2), 50 + 168 * math.cos(t * math.pi / 2)

    @staticmethod
    def scallop(left, right):
        return [(48 + 224 * (left + (right - left) * k / 16),
                 50 + 24 * math.sin(k * math.pi / 16)) for k in range(17)]

    def background(self):
        p = self.paint.backdrop
        p.begin()
        p.gradient("#081520", "#1B353D")
        # 远处的雾与灯，只留低对比轮廓，让伞面成为画面焦点。
        for i in range(12, 0, -1):
            p.oval(-216, 77, 150 + i * 7, 132 + i * 4,
                   mix("#0E212B", "#24484F", (1 - i / 13) * .55))
        for x, height, width in ((-425, 92, 45), (-360, 144, 55), (-290, 104, 46),
                                 (327, 116, 54), (406, 164, 47)):
            p.rect(x - width / 2, -160, x + width / 2, -160 + height, "#152C35")
            for level in range(2, int(height / 24)):
                p.rect(x - 7, -159 + level * 23, x - 3, -153 + level * 23, "#294349")
        for x, y, radius, warm in self.bokeh:
            color = "#64837C" if warm < .7 else "#A89377"
            p.circle(x, y, radius * 2.5, mix("#172D36", color, .09))
            p.circle(x, y, radius, mix("#172D36", color, .35))
        for i in range(14):
            y = -170 - i * 8
            p.rect(-500, y, 500, y - 9, mix("#1C353C", "#0C1D29", i / 13))
        p.line([(-470, -173), (470, -173)], "#2A4449", 1)
        p.text(-420, 204, "RAIN / STUDY 01", "#8FA6A4", 9, "w")
        p.line([(-420, 184), (-357, 184)], "#526E72")
        p.text(-420, 154, "留一场雨，\n听世界慢下来。", "#789698", 12, "nw")
        p.end()

    def umbrella(self):
        p = self.paint
        p.begin()
        _, colors, light = SCHEMES[self.scheme]
        # 弯钩仍由半圆生成；三道不同宽度的描边表现金属和木柄质感。
        hook = [(48, 83), (48, -138)] + [
            (20 + 28 * math.cos(-k * math.pi / 32), -138 + 28 * math.sin(-k * math.pi / 32))
            for k in range(33)]
        p.line(hook, "#0A1720", 14)
        p.line(hook, "#977B68", 9)
        p.line([(46, 64), (46, -129)], "#D9CDB5", 2)
        p.line(hook[1:], "#BB8B66", 6)
        p.line([(19 + 27 * math.cos(-k * math.pi / 32),
                 -136 + 27 * math.sin(-k * math.pi / 32)) for k in range(3, 30)], "#E0AC7B", 1.4)
        p.line([(48, 215), (48, 229)], "#A89881", 4)
        p.circle(48, 230, 3, light)
        splits = (-1, -.5, 0, .5, 1)
        # 细分着色带，最后一带从 t=.9 开始：其上沿高于伞沿凹弧，
        # 避免加密渐变时让收口多边形交叉。每侧仍沿椭圆采样。
        for panel in range(4):
            left, right, color = splits[panel], splits[panel + 1], colors[panel]
            for band in range(25):
                t0, t1 = band * .9 / 24, (band + 1) * .9 / 24
                if band == 24:
                    t1 = 1
                border = [self.rib(left, t0), self.rib(right, t0)]
                border += [self.rib(right, t0 + (t1 - t0) * k / 4) for k in range(1, 5)]
                if band == 24:
                    border += list(reversed(self.scallop(left, right)))
                else:
                    border.append(self.rib(left, t1))
                border += [self.rib(left, t1 - (t1 - t0) * k / 4) for k in range(1, 4)]
                tint = mix(color, light, .27 * (1 - t0) ** 1.8)
                tint = mix(tint, "#241E30", .22 * t0 * t0)
                p.poly(border, tint)
            # 略微偏心的窄亮纹构成布面反光，不盖住相邻伞骨。
            shine = left + (right - left) * .17
            p.line([self.rib(shine, k / 28) for k in range(4, 25)],
                   mix(color, light, .24), 2.8)
            p.line(self.scallop(left, right), "#572F3B", 4)
            p.line(self.scallop(left, right), mix(color, light, .44), 1.3)
        for u in splits:
            points = [self.rib(u, k / 32) for k in range(33)]
            p.line(points, "#6A4145", 2.3)
            p.line([(x - .8, y + .5) for x, y in points], mix(light, "#B87570", .35), .8)
            x, y = self.rib(u, 1)
            p.circle(x, y, 2.6, light)
        # 局部水珠随布面透视排列。
        for u, t in ((-.82, .62), (-.63, .37), (-.37, .79), (-.16, .34),
                     (.18, .63), (.31, .46), (.66, .73), (.84, .86)):
            x, y = self.rib(u, t)
            p.oval(x, y, 1.3, 3, "", mix(light, "#FFFFFF", .2), .8)
            p.circle(x - .4, y + 1, .7, "#FFF5DA")
        p.end()

    def water(self):
        p = self.paint.water
        p.begin()
        _, colors, light = SCHEMES[self.scheme]
        # 碎开的倒影，波长随远近改变，永远留在池面内。
        for i in range(16):
            y = -186 - i * 4.8
            half = 91 * (1 - i / 22)
            shift = math.sin(self.time * 1.1 + i * .86) * (2 + i * .35)
            tint = mix("#142731", colors[2], .12 * (1 - i / 20))
            p.line([(48 - half + shift, y), (48 + half + shift, y)], tint, 2.1)
        for x, y, phase, size in self.pond:
            cycle = (self.time * (.65 + self.strength * .3) + phase) % 3 / 3
            color = mix("#172F39", "#7A9697", (1 - cycle) * .24)
            p.oval(x, y, 2 + cycle * size, .6 + cycle * size * .2, "", color, .8)
        for x, y, started in self.ripples:
            age = self.time - started
            active = started >= 0 and 0 <= age < 2.8
            for ring in range(3):
                radius = max(0, age - ring * .18) * 31 if active else 0
                alpha = max(0, 1 - age / 2.8) * (.6 - ring * .13) if active else 0
                p.oval(x, y, radius, radius * .2, "", mix("#162C36", light, alpha), 1)
        # 五根伞骨的滴水：离开伞沿后加速下落，落点只绘制固定涟漪。
        for index, u in enumerate((-1, -.5, 0, .5, 1)):
            x, _ = self.rib(u, 1)
            fall = (self.time * .67 + index * .213) % 1
            y = 44 - 221 * fall * fall
            p.line([(x, y + 3), (x, y - 2)], mix("#1B343D", light, .5), 1.1)
        p.text(360, -240, "雨落有声", "#B1AAA0", 13, "e")
        p.text(360, -261, "A MOMENT UNDER THE RAIN", "#607C82", 8, "e")
        p.end()

    def frame(self, dt):
        if dt > 0:
            self.time += dt
        signature = (self.scheme, self.stage.scale, self.stage.view)
        if signature != self.paint.signature:
            self.background()
            self.umbrella()
            self.paint.signature = signature
        self.stage.canvas.tag_raise(self.paint.backdrop.tag)
        p = self.paint.weather
        p.begin()
        for index, (x, phase, speed, depth) in enumerate(self.rain):
            y = 258 - (phase + self.time * speed * (.65 + self.strength * .35)) % 525
            x += 8 * math.sin(index)
            color = mix("#17303A", "#9CB6B7", depth * .32 * min(1, self.strength))
            p.line([(x, y), (x - 3 * depth, max(-276, y - 14 * depth))], color, depth)
        p.end()
        self.stage.canvas.tag_raise(self.paint.tag)
        self.water()
        self.stage.hud(f"{SCHEMES[self.scheme][0]}  ·  雨量 {self.strength:.2f}  ·  圆弧、织物与水面")


if __name__ == "__main__":
    app = RainUmbrella()
    app.stage.run(app.frame, app.reset)
