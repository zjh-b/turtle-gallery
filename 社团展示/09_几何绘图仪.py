"""内旋轮线绘图仪：圆在大圆内滚动，偏心画笔留下闭合曲线。"""
import math

from 舞台 import Paint, Stage, hsv, mix


PRESETS = [("八瓣星花", 200, 75, 101, 0.47), ("十重回环", 200, 60, 111, 0.85),
           ("五叶风轮", 200, 80, 102, 0.06), ("二十瓣织锦", 200, 70, 101, 0.61)]


class Spirograph:
    def __init__(self):
        self.stage = Stage("圆在画花", "1～4 切换曲线    C 从头绘制    G 隐藏 / 显示圆盘    ↑↓ 调速", accent="#8BD9CF")
        self.paint = Paint(self.stage, "spirograph")
        self.preset, self.speed, self.theta, self.progress, self.gears = 0, 1, 0, 1, True
        self.points = []
        self.prepare()
        for i in range(4):
            self.stage.screen.onkey(lambda i=i: self.choose(i), str(i + 1))
        for key in ("c", "C"):
            self.stage.screen.onkey(self.redraw, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.toggle_gears, key)
        self.stage.screen.onkey(lambda: self.change_speed(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-0.25), "Down")

    def curve(self, angle):
        _, big, small, pen, _ = PRESETS[self.preset]
        center = big - small
        return (center * math.cos(angle) + pen * math.cos(center / small * angle),
                center * math.sin(angle) - pen * math.sin(center / small * angle))

    def prepare(self):
        _, big, small, _, _ = PRESETS[self.preset]
        self.period = math.tau * small / math.gcd(big, small)
        self.points = [self.curve(i * self.period / 1600) for i in range(1601)]

    def reset(self):
        self.preset, self.speed, self.theta, self.progress, self.gears = 0, 1, 0, 1, True
        self.prepare()

    def choose(self, index):
        self.preset = index % len(PRESETS)
        self.theta, self.progress = 0, 1
        self.prepare()

    def redraw(self):
        self.theta, self.progress = 0, 0

    def toggle_gears(self):
        self.gears = not self.gears

    def change_speed(self, amount):
        self.speed = max(0.25, min(4, self.speed + amount))

    def frame(self, dt):
        self.theta += dt * self.speed * 2.2
        if self.progress < 1:
            self.progress = min(1, self.theta / self.period)
        self.theta %= self.period
        name, big, small, distance, hue = PRESETS[self.preset]
        p = self.paint
        p.begin()
        p.gradient("#0C1829", "#182239")
        for coordinate in range(-250, 251, 25):
            p.line([(coordinate, -250), (coordinate, 250)], "#1D2C40")
            p.line([(-250, coordinate), (250, coordinate)], "#1D2C40")
        p.circle(0, 0, 256, outline="#38485B")
        for i in range(72):
            a = i * math.tau / 72
            p.line([(math.cos(a) * 256, math.sin(a) * 256),
                    (math.cos(a) * (261 if i % 6 == 0 else 258), math.sin(a) * (261 if i % 6 == 0 else 258))], "#667984")
        if self.progress < 1:
            p.line(self.points, "#263B4D", 1)
        end = round(self.progress * 1600)
        for index in range(0, end, 20):
            points = self.points[index:min(index + 21, end + 1)]
            if len(points) > 1:
                p.line(points, hsv(hue + index / 1600 * 0.25, 0.46), 1.4)
        cx, cy = (big - small) * math.cos(self.theta), (big - small) * math.sin(self.theta)
        px, py = self.curve(self.theta)
        if self.gears:
            p.circle(0, 0, big, outline="#70818D", width=1.2)
            p.circle(cx, cy, small, outline="#8BA3AB", width=1.2)
            p.line([(0, 0), (cx, cy), (px, py)], "#D1BC8A", 1.5)
            p.circle(0, 0, 4, "#82999F")
            p.circle(cx, cy, 4, "#D8CCA4")
            for i in range(12):
                a = i * math.tau / 12 - self.theta * (big - small) / small
                p.circle(cx + math.cos(a) * small * 0.9, cy + math.sin(a) * small * 0.9, 1.3, "#809CA7")
        p.circle(px, py, 5, "#FFF2BC")
        p.circle(px, py, 2, "#FFFFFF")
        p.text(-429, 164, name, "#D5E1DB", 19, "w", True)
        p.text(-427, 129, "一个圆，画出一朵花。", "#8DA5B2", 10, "w")
        for i, (label, value) in enumerate([("外圆半径", big), ("内圆半径", small), ("画笔偏心距", distance)]):
            p.text(338, 80 - i * 63, label, "#8CA1B4", 10, "w")
            p.text(338, 54 - i * 63, str(value), "#C5D7D8", 20, "w")
        p.line([(-245, -280), (245, -280)], "#354958", 3)
        if self.progress > 0:
            p.line([(-245, -280), (-245 + 490 * self.progress, -280)], "#80BFB9", 3)
        p.text(334, -268, f"{self.progress:.0%}", "#A7CEC8", 12, "w")
        p.end()
        self.stage.hud(f"{name}   ·   速度 × {self.speed:.2f}   ·   按 C 看画笔如何走完整条曲线")


if __name__ == "__main__":
    app = Spirograph()
    app.stage.run(app.frame, app.reset)
