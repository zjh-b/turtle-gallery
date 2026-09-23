"""会缓慢呼吸、旋转的花瓣万花筒，也可用鼠标手绘。"""
import math
from collections import deque

from 舞台 import Paint, Stage, hsv, mix, polar


class Kaleidoscope:
    def __init__(self):
        self.stage = Stage("一笔生花", "拖动画画    ↑↓ 对称份数    C 清空    D 自动花瓣    P 换色", accent="#D5B6FA")
        self.paint = Paint(self.stage, "kaleidoscope")
        self.count = 10
        self.auto = True
        self.time = self.hue = 0
        self.palette = 0
        self.previous = None
        self.paths = deque(maxlen=900)
        self.ink = deque()
        self.ink_scale = self.stage.scale
        self.stage.canvas.bind("<Button-1>", self.press, add="+")
        self.stage.canvas.bind("<B1-Motion>", self.drag, add="+")
        self.stage.canvas.bind("<ButtonRelease-1>", self.release, add="+")
        for key in ("c", "C"):
            self.stage.screen.onkey(self.clear, key)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.toggle_auto, key)
        for key in ("p", "P"):
            self.stage.screen.onkey(self.change_palette, key)
        self.stage.screen.onkey(lambda: self.change_count(1), "Up")
        self.stage.screen.onkey(lambda: self.change_count(-1), "Down")

    @property
    def strokes(self):
        return len(self.paths)

    def clear(self):
        self.paths.clear()
        self.ink.clear()
        self.stage.canvas.delete("ink")
        self.previous = None
        self.auto = False

    def reset(self):
        self.clear()
        self.count, self.auto, self.time, self.hue = 10, True, 0, 0
        self.palette = 0

    def change_palette(self):
        self.palette = (self.palette + 1) % 3

    def ink_color(self, phase):
        if self.palette == 1:
            return mix("#5CB7C4", "#E0F9D6", (1 + math.sin(phase * math.tau)) / 2)
        if self.palette == 2:
            return mix("#D47765", "#FFE4A1", (1 + math.sin(phase * math.tau)) / 2)
        return hsv(phase, 0.48)

    def change_count(self, amount):
        self.count = max(3, min(16, self.count + amount))
        self.previous = None

    def toggle_auto(self):
        self.auto = not self.auto
        self.previous = None

    def press(self, event):
        if not self.stage.paused:
            if math.hypot(*self.stage.event_point(event)) > 246:
                return
            self.auto = False
            self.previous = self.stage.event_point(event)

    def drag(self, event):
        if not self.stage.paused:
            self.draw(*self.stage.event_point(event))

    def release(self, event):
        self.previous = None

    def draw(self, x, y):
        if math.hypot(x, y) > 246:
            self.previous = None
            return
        if self.previous and math.dist(self.previous, (x, y)) >= 2:
            self.hue = (self.hue + 0.006) % 1
            if len(self.paths) == self.paths.maxlen:
                for item in self.ink.popleft():
                    self.stage.canvas.delete(item)
            stroke = (self.previous, (x, y), self.ink_color(self.hue), self.count)
            self.paths.append(stroke)
            self.add_ink(stroke)
        self.previous = (x, y)

    def add_ink(self, stroke):
        # 手绘只添加新线段；保留的线段不随动画每帧重画。
        a, b, color, count = stroke
        scale = self.stage.scale
        items = []
        for i in range(count):
            angle = i * math.tau / count
            c, s = math.cos(angle), math.sin(angle)
            for mirror in (-1, 1):
                coords = []
                for x, y in (a, b):
                    coords.extend(((x * c - y * mirror * s) * scale,
                                   -(x * s + y * mirror * c) * scale))
                items.append(self.stage.canvas.create_line(*coords, fill=color, width=max(1, 1.5 * scale),
                                                           capstyle="round", tags=("ink",)))
        self.ink.append(items)

    def petal(self, p, angle, inner, outer, spread, color):
        # 四个控制点形成平滑的叶瓣；填色、轮廓和叶脉分别绘制。
        middle = (inner + outer) / 2
        points = [polar(inner, angle), polar(middle, angle - spread),
                  polar(outer, angle), polar(middle, angle + spread)]
        p.poly(points, mix("#10152A", color, 0.20), mix("#15182D", color, 0.72), 1.3, True)
        p.line([polar(inner, angle), polar(middle, angle), polar(outer - 7, angle)],
               mix("#17182E", color, 0.4), 1, True)
        p.circle(*polar(outer - 13, angle), 1.6, mix(color, "#FFFFFF", 0.35))

    def frame(self, dt):
        if self.auto:
            self.time += dt
        p = self.paint
        p.begin()
        p.gradient("#0D1125", "#181329")
        p.circle(0, 0, 256, "#11152A", "#393650")
        p.circle(0, 0, 249, outline="#5A4D67")
        for i in range(80):
            a = i * math.tau / 80
            p.line([polar(253, a), polar(258 if i % 5 == 0 else 255, a)], "#8B768C" if i % 5 == 0 else "#454059")
        if self.auto:
            for layer, (inner, outer, spread) in enumerate([(46, 243, 0.22), (31, 197, 0.27), (22, 148, 0.31), (10, 98, 0.36)]):
                phase = self.time * (0.038 if layer % 2 == 0 else -0.045)
                phase += layer * math.pi / self.count
                breath = 1 + 0.025 * math.sin(self.time * 1.2 + layer)
                for i in range(self.count):
                    angle = i * math.tau / self.count + phase
                    color = self.ink_color(i / self.count * 0.38 + layer * 0.12 + self.time * 0.015 + 0.48)
                    self.petal(p, angle, inner, outer * breath, spread, color)
            for radius, color in [(65, "#73608F"), (40, "#A389B2"), (20, "#D0B4C9")]:
                p.circle(0, 0, radius, outline=color)
            for i in range(self.count * 2):
                a = i * math.tau / (self.count * 2) - self.time * 0.1
                p.poly([polar(8, a), polar(28, a - 0.08), polar(44, a), polar(28, a + 0.08)],
                       "#29263D", "#A995BD", smooth=True)
            p.glow(0, 0, 17, "#E7C4DA", "#29263D", 5)
            p.circle(0, 0, 4, "#FFF0D6")
        else:
            p.circle(0, 0, 3, "#E4CCDB")
            if not self.paths:
                p.text(0, 10, "在圆内画一笔", "#C4B4D5", 17)
                p.text(0, -23, "看看对称会带来什么", "#7F7998", 10)
        for x, direction in [(-365, 1), (365, -1)]:
            p.line([(x, 100), (x, -100)], "#3B354E")
            for y in (-100, 0, 100):
                p.poly([(x, y + 5), (x + 4, y), (x, y - 5), (x - 4, y)], "#B19AAE")
            p.text(x + direction * 20, 45, "旋转", "#A69AB6", 11, "w" if direction == 1 else "e")
            p.text(x + direction * 20, 17, "镜像", "#A69AB6", 11, "w" if direction == 1 else "e")
            p.text(x + direction * 20, -35, f"{self.count:02d}", "#E0C7DE", 24, "w" if direction == 1 else "e")
        p.text(0, -278, "对 称 之 美  /  SYMMETRY IN BLOOM", "#887A9B", 9)
        p.end()
        if self.ink_scale != self.stage.scale:
            self.ink_scale = self.stage.scale
            self.stage.canvas.delete("ink")
            self.ink.clear()
            for stroke in self.paths:
                self.add_ink(stroke)
        self.stage.canvas.itemconfigure("ink", state="hidden" if self.auto else "normal")
        self.stage.canvas.tag_raise("ink")
        self.stage.hud(f"{self.count} 份旋转对称   ·   " + ("花瓣正在缓慢绽放，拖动画笔即可接管" if self.auto else "自由创作中，D 键返回自动花瓣"))


if __name__ == "__main__":
    app = Kaleidoscope()
    app.stage.run(app.frame, app.reset)
