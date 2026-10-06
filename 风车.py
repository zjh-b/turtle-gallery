"""旋转风车：四瓣折纸、花园微风。直接运行本文件即可展示。"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


PALETTES = (
    ("晴日糖纸", ("#ED8677", "#EBC267", "#77B6AA", "#94AED0")),
    ("海盐汽水", ("#5FABB7", "#A3CFC3", "#E6CF93", "#829CC7")),
    ("莓果花信", ("#C98CA5", "#E5A6A6", "#A59CC9", "#DCC38A")),
)


class PaperPinwheel:
    """固定数量的矢量图形；定时更新角度，不再清屏或占用忙循环。"""

    GUST_SECONDS = 3.2
    CENTER = (34, 32)
    # 每片保留一个方纸尖角，另一侧卷向中心。四片之间留出深凹口，
    # 旋转时仍能一眼认出纸风车，而不是连续的四色圆盘。
    BLADE = ((0, 0), (-145, 145), (0, 145), (35, 128),
             (56, 89), (48, 44))
    FOLD = ((0, 0), (0, 145), (35, 128), (56, 89), (48, 44))

    def __init__(self):
        self.stage = Stage("旋转风车", "点击 唤风    C 配色    ↑↓ 调速    D 反转",
                           "#F3F0DE", "#AE7650", light=True)
        self.paint = Paint(self.stage, "paper-pinwheel")
        self.paint.backdrop = Paint(self.stage, "pinwheel-garden")
        self.paint.backdrop_signature = None
        rng = random.Random(27)
        self.grass = tuple((rng.uniform(-465, 465), rng.uniform(-277, -223),
                            rng.uniform(9, 26), rng.uniform(-8, 8)) for _ in range(34))
        self.flowers = tuple((rng.choice((-1, 1)) * rng.uniform(160, 437),
                              rng.uniform(-273, -242), rng.uniform(15, 40),
                              rng.randrange(3), rng.random() * math.tau)
                             for _ in range(22))
        self.seeds = tuple((rng.uniform(-450, 450), rng.uniform(-175, 213),
                            rng.uniform(3, 7), rng.random() * math.tau)
                           for _ in range(15))
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_palette, key)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.reverse, key)
        self.stage.screen.onkey(lambda: self.change_speed(.2), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.2), "Down")
        self.stage.screen.onclick(self.blow)

    def reset(self):
        self.time = 0.0
        self.angle = -.15
        self.speed = 1.0
        self.direction = 1
        self.palette = 0
        self.gust = 0.0

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def change_speed(self, amount):
        self.speed = max(0, min(3, self.speed + amount))

    def reverse(self):
        self.direction *= -1

    def blow(self, x, y):
        x, y = self.stage.point(x, y)
        if not self.stage.paused and self.stage.in_scene(x, y):
            # 再次点击只续上这一阵风，不额外堆积粒子或回调。
            self.gust = self.GUST_SECONDS

    def rotated(self, points, angle, dx=0, dy=0):
        ca, sa = math.cos(angle), math.sin(angle)
        cx, cy = self.CENTER
        return [(cx + dx + x * ca - y * sa, cy + dy + x * sa + y * ca)
                for x, y in points]

    @staticmethod
    def cloud(p, x, y, size):
        p.oval(x + 8, y - 10, size, size * .2, "#E4E8D9")
        p.oval(x, y, size, size * .22, "#FFFFF4")
        for dx, dy, r in ((-.45, .08, .29), (-.10, .2, .40), (.35, .08, .28)):
            p.circle(x + dx * size, y + dy * size, r * size, "#FFFFF4")

    def backdrop(self):
        p = self.paint.backdrop
        signature = (self.stage.scale, self.stage.view)
        if self.paint.backdrop_signature == signature:
            return
        p.begin()
        p.gradient("#E6EEDE", "#FCF2D9")
        # 薄薄的同色光圈、云团和远近草坡，避免背景抢走折纸主体。
        p.circle(346, 176, 50, "#F6EAD0")
        p.circle(346, 176, 40, "#F8E3AF")
        p.circle(346, 176, 29, "#F8D88F")
        for i in range(12):
            a = i * math.tau / 12
            p.line([polar(57, a, 346, 176), polar(64, a, 346, 176)], "#E6D3A6", 1)
        self.cloud(p, -331, 166, 74)
        self.cloud(p, 254, 90, 43)
        p.poly([(-505, -180), (-400, -134), (-294, -155), (-186, -130),
                (-60, -181), (85, -153), (240, -125), (379, -159),
                (505, -139), (505, -310), (-505, -310)], "#DCE2C2", smooth=True)
        p.poly([(-505, -220), (-395, -180), (-238, -203), (-89, -172),
                (60, -209), (203, -183), (366, -206), (505, -186),
                (505, -310), (-505, -310)], "#C5D5B2", smooth=True)
        p.poly([(-505, -250), (-343, -228), (-140, -244), (60, -229),
                (250, -243), (505, -222), (505, -310), (-505, -310)],
               "#AEC6A2", smooth=True)
        p.oval(38, -263, 61, 8, "#92AE8D")
        for x, y, height, lean in self.grass:
            p.line([(x - 3, y), (x + lean * .3, y + height * .6),
                    (x + lean, y + height)], "#87A787", 1.2, smooth=True)
        for x, y, height, color, phase in self.flowers:
            self.flower(p, x, y, height, color, phase)
        # 木杆置于四片纸翼下方，边缘与木纹共用稳定的少量线条。
        p.poly([(27, -262), (40, -262), (39, 34), (30, 34)], "#BA8C56", "#A7794B")
        p.poly([(29, -260), (32, -260), (33, 31), (31, 31)], "#E2BD81")
        p.line([(37, -246), (35, -145), (37, -62), (35, 21)], "#A87947", 1)
        p.line([(31, -178), (34, -183), (36, -176)], "#A87947", 1)
        p.text(-433, -66, "把风折成四瓣", "#6D816A", 19, "w", True)
        p.text(-430, -96, "一张纸，一整个晴天。", "#899578", 10, "w")
        p.line([(-430, -124), (-382, -124)], "#BDA36D", 2)
        p.end()
        self.paint.backdrop_signature = signature

    @staticmethod
    def flower(p, x, y, height, color, phase):
        top = y + height
        p.line([(x, y), (x - 2, y + height * .55), (x + 2, top)], "#658B70", 1.4)
        p.poly([(x, y + height * .35), (x - 12, y + height * .58),
                (x - 8, y + height * .20)], "#86A676", smooth=True)
        fill = ("#FFF4D6", "#ECA99A", "#D5C6DF")[color]
        petals = [polar(5.5 if i % 2 == 0 else 2.6, phase + i * math.pi / 5, x + 2, top)
                  for i in range(10)]
        p.poly(petals, fill, smooth=True)
        p.circle(x + 2, top, 1.9, "#BE984C")

    def paper(self, p):
        _, colors = PALETTES[self.palette]
        # 淡投影跟随翼片转动；先画四片投影再叠纸，接缝不会互相穿透。
        for i in range(4):
            a = self.angle + i * math.pi / 2
            p.poly(self.rotated(self.BLADE, a, 3, -5), "#B9C2A6")
        for i, color in enumerate(colors):
            a = self.angle + i * math.pi / 2
            edge = mix(color, "#735C4A", .25)
            p.poly(self.rotated(self.BLADE, a), color, edge, .9)
            # 纸面大块柔和明暗与细窄折边，比反复发光更像真实折纸。
            p.poly(self.rotated(((0, 0), (-145, 145), (-52, 145), (-22, 61)), a),
                   mix(color, "#FFF7DA", .19))
            p.poly(self.rotated(((0, 0), (-22, 61), (-52, 145), (0, 145)), a), color)
            p.poly(self.rotated(self.FOLD, a), mix(color, "#756052", .29))
            p.poly(self.rotated(((0, 0), (0, 145), (24, 129), (33, 99), (24, 53)), a),
                   mix(color, "#FFF8DC", .28))
            p.line(self.rotated(((0, 3), (0, 143)), a), mix(color, "#FFF8E4", .68), 1.4)
            p.line(self.rotated(((-143, 143), (-1, 143), (33, 127), (54, 88), (46, 45)), a),
                   mix(color, "#FFFAE8", .59), 1.1)
            # 三条极淡的纸纤维，仅在纸面内出现，不让主画面变成密集线稿。
            for j in range(3):
                yy = 96 + j * 13
                p.line(self.rotated(((-78 + j * 4, yy), (-35 + j * 5, yy + 3)), a),
                       mix(color, "#FFF8E7", .23), .7)
        cx, cy = self.CENTER
        p.circle(cx + 1.5, cy - 2, 14, "#877957")
        p.circle(cx, cy, 12.5, "#B78A44", "#96703F", 1)
        p.circle(cx - 1, cy + 1, 9, "#E1B96C")
        p.circle(cx - 2, cy + 2, 5.8, "#F9DEA0")
        p.oval(cx - 3.5, cy + 4.5, 3.2, 1.7, "#FFF0C5")
        p.line([(cx - 2, cy - 2), (cx + 3, cy + 2)], "#BA904B", 1.2)

    def breeze(self, p, strength):
        # 风线在两侧舒展，固定十五颗种子循环经过画面，不会越画越多。
        for side in (-1, 1):
            x = -335 if side < 0 else 329
            for j in range(3):
                y = 8 + 28 * j + 4 * math.sin(self.time * .6 + j)
                length = 42 + 12 * j + strength * 9
                points = [(x + (k / 8 - .5) * length, y + 6 * math.sin(k * .5 + j))
                          for k in range(9)]
                p.line(points, "#A9BCAD", 1 if j else 1.6, smooth=True)
        for x, y, size, phase in self.seeds:
            xx = ((x + self.time * 13 * self.direction + 450) % 900) - 450
            yy = y + math.sin(self.time * .8 + phase) * 7
            # 主体中央留给纸面，不让漂浮点在折痕上制造脏点。
            if abs(xx - self.CENTER[0]) < 205 and abs(yy - self.CENTER[1]) < 205:
                p.oval(xx, yy, 0, 0, "")
                continue
            p.oval(xx, yy, size * .55, size * .23, "#FCF7DD")
        for x, y, offset, color in ((-281, -168, 0, "#D2986F"), (324, -127, 2, "#AF98B1")):
            yy = y + math.sin(self.time * 1.7 + offset) * 7
            span = 3 + 5 * abs(math.sin(self.time * 4 + offset))
            p.oval(x - span * .7, yy + 2, span, 5, color)
            p.oval(x + span * .7, yy + 2, span, 5, color)
            p.line([(x, yy - 4), (x, yy + 5)], "#827B66", 1)

    def frame(self, dt):
        dt = max(0, dt)
        self.time += dt
        self.gust = max(0, self.gust - dt)
        wind = math.sin(math.pi * self.gust / self.GUST_SECONDS) if self.gust else 0
        self.angle = (self.angle + self.direction * dt * (.7 * self.speed + 2.5 * wind)) % math.tau
        self.backdrop()
        p = self.paint
        p.begin()
        self.breeze(p, wind)
        self.paper(p)
        p.end()
        name = PALETTES[self.palette][0]
        state = "微风正好" if not self.gust else "风起了，纸翼加速"
        self.stage.hud(f"{name}  ·  四瓣折纸  ·  {self.speed:.1f} 倍风速  ·  {state}")


if __name__ == "__main__":
    app = PaperPinwheel()
    app.stage.run(app.frame, app.reset)
