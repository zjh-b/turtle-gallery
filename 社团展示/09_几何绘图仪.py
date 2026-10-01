"""内旋轮线光纹：一支圆规，织出层叠星花；G 可展开滚圆机构。"""
import math
import random
from bisect import bisect_right

from 舞台 import Paint, Stage, mix, polar


PRESETS = [("八瓣星花", 200, 75, 101, 0.47), ("十重回环", 200, 60, 111, 0.85),
           ("五叶风轮", 200, 80, 102, 0.06), ("二十瓣织锦", 200, 70, 101, 0.61)]
PALETTES = [
    ("星河青", "#80E1DB", "#8FA9F4", "#D1A7EB", "#FFE4B3"),
    ("玫瑰金", "#EE9EB7", "#D5A3D8", "#F4CB91", "#FFF0CB"),
    ("月光蓝", "#A5BCF2", "#79C7E0", "#A1E5D1", "#E7F5FC"),
]
LAYERS = ((1, 0), (.92, .045), (.78, -.04), (.60, .09), (.38, -.06))
TRACE_ERROR_PX = .3


def simplify_indices(points, tolerance):
    """Keep every original vertex within tolerance of its display segment.

    The reference curve stays untouched. Scaling the tolerance to the actual
    viewport keeps the fine petals intact when a projector/window grows.
    """
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    limit = tolerance * tolerance
    while pending:
        left, right = pending.pop()
        ax, ay = points[left]
        bx, by = points[right]
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        farthest, distance = left, limit
        for i in range(left + 1, right):
            x, y = points[i]
            t = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / length)) if length else 0
            error = (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2
            if error > distance:
                farthest, distance = i, error
        if farthest != left:
            keep.add(farthest)
            pending.extend(((left, farthest), (farthest, right)))
    return sorted(keep)


class Spirograph:
    def __init__(self):
        self.stage = Stage("圆在画花", "1～4 图案   P 配色   L 叠层   C 重绘   G 圆盘   ↑↓ 调速", accent="#91E0D8")
        self.paint = Paint(self.stage, "spirograph")
        rng = random.Random(109)
        self.stars = [(rng.uniform(-460, 460), rng.uniform(-260, 250), rng.uniform(.5, 1.4))
                      for _ in range(76)]
        self.reset()
        for i in range(4):
            self.stage.screen.onkey(lambda i=i: self.choose(i), str(i + 1))
        for key, action in (("c", self.redraw), ("g", self.toggle_gears),
                            ("p", self.change_palette), ("l", self.toggle_layers)):
            for binding in (key, key.upper()):
                self.stage.screen.onkey(action, binding)
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
        # Decorative copies are computed once; the original curve remains the
        # actual rolling-gear trace. Color/layer changes never advance drawing.
        self.traces = [[(scale * (x * math.cos(turn) - y * math.sin(turn)),
                         scale * (x * math.sin(turn) + y * math.cos(turn)))
                        for x, y in self.points] for scale, turn in LAYERS]
        self.prepare_display(self.stage.scale)

    def prepare_display(self, scale):
        self.display_scale = scale
        self.display_indices = [simplify_indices(trace, TRACE_ERROR_PX / scale)
                                for trace in self.traces]
        self.display_traces = [[trace[i] for i in indices]
                               for trace, indices in zip(self.traces, self.display_indices)]

    def reset(self):
        self.preset, self.palette = 3, 0
        self.speed, self.theta, self.progress, self.time = 1, 0, 1, 0
        self.gears, self.layered = False, True
        self.prepare()

    def choose(self, index):
        self.preset = index % len(PRESETS)
        self.theta, self.progress = 0, 1
        self.prepare()

    def redraw(self):
        self.theta, self.progress = 0, 0

    def toggle_gears(self):
        self.gears = not self.gears

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def toggle_layers(self):
        self.layered = not self.layered

    def change_speed(self, amount):
        self.speed = max(0.25, min(4, self.speed + amount))

    def draw_dial(self, p, colors):
        p.glow(0, -4, 254, "#21354B", "#0A1223", 12)
        for radius, color in ((250, "#273347"), (257, "#333A4C"), (264, "#1F2B3E")):
            p.circle(0, -4, radius, outline=color)
        for i in range(96):
            angle = i * math.tau / 96
            major = i % 8 == 0
            p.line([polar(251, angle, 0, -4), polar(257 if major else 254, angle, 0, -4)],
                   "#8B8490" if major else "#3A465A", 1)
        for i in range(12):
            angle = i * math.tau / 12
            p.circle(*polar(261, angle, 0, -4), 1.4, mix(colors[4], "#162033", .48))
        p.circle(0, -4, 9, outline="#44516A")
        p.circle(0, -4, 3, colors[4])

    def draw_traces(self, p, colors):
        if self.display_scale != p.scale:
            self.prepare_display(p.scale)
        end = round(self.progress * 1600)
        start = p.index
        key = (self.preset, self.palette, self.layered, end, self.progress < 1,
               p.scale, p.offset, start)
        cached = getattr(p, "trace_cache", None)
        if cached and cached[0] == key:
            # Paint owns these items and their stacking positions. Advancing its
            # cursor preserves them without flattening/rounding thousands of
            # unchanged coordinates on every moving-pen frame.
            p.index += cached[1]
            return
        active = range(len(self.traces) if self.layered else 1)
        for index in reversed(active):
            trace = self.display_traces[index]
            color = colors[1 + index % 3]
            if self.progress < 1:
                p.line(trace, "#28344B", .8)
            if end < 1:
                continue
            indices = self.display_indices[index]
            count = bisect_right(indices, end)
            points = trace[:count]
            if indices[count - 1] != end:
                points.append(self.traces[index][end])
            p.line(points, mix("#10182C", color, .12), 6.5)
            p.line(points, mix("#10182C", color, .34), 2.8)
            p.line(points, mix(color, "#FFFFFF", .12), 1.15 if index < 2 else 1)
        p.trace_cache = key, p.index - start

    def frame(self, dt):
        self.time += dt
        self.theta += dt * self.speed * 2.2
        if self.progress < 1:
            self.progress = min(1, self.theta / self.period)
        self.theta %= self.period
        name, big, small, distance, _ = PRESETS[self.preset]
        colors = PALETTES[self.palette]
        p = self.paint
        p.begin()
        p.gradient("#080F20", "#131B30")
        for x, y, radius in self.stars:
            if math.hypot(x, y + 4) > 285:
                p.circle(x, y, radius, "#46516B")
        self.draw_dial(p, colors)
        p.transform(y=-4)
        self.draw_traces(p, colors)
        cx, cy = (big - small) * math.cos(self.theta), (big - small) * math.sin(self.theta)
        px, py = self.curve(self.theta)
        if self.gears:
            p.circle(0, 0, big, outline="#52697A")
            p.circle(cx, cy, small, outline="#93A8B5", width=1.2)
            p.line([(0, 0), (cx, cy), (px, py)], "#E4CAA0", 1.2)
            p.circle(cx, cy, 3.5, colors[4])
            for i in range(16):
                angle = i * math.tau / 16 - self.theta * (big - small) / small
                p.circle(cx + math.cos(angle) * small * .91, cy + math.sin(angle) * small * .91, 1.2, "#6E8099")
        # A short moving pen trail makes the closed pattern feel alive, without
        # appending points to an ever-growing list.
        for i in range(14, 0, -1):
            angle = self.theta - i * .027
            if self.progress < 1 and angle < 0:
                continue
            a, b = self.curve(angle), self.curve(angle + .025)
            p.line([a, b], mix("#28334A", colors[4], (1 - i / 16) ** 2), 1.8)
        p.glow(px, py, 10, colors[4], "#111A2C", 5)
        p.circle(px, py, 2.5, "#FFF8DD")
        if self.layered:
            for index, (scale, turn) in enumerate(LAYERS[1:], 1):
                x, y = scale * (px * math.cos(turn) - py * math.sin(turn)), scale * (px * math.sin(turn) + py * math.cos(turn))
                p.circle(x, y, 2, colors[1 + index % 3])
        p.transform()
        p.text(-440, 206, "LUMINOUS / 09", "#6E91A5", 9, "w")
        p.text(-441, 166, name, "#D6EDE9", 20, "w", True)
        p.text(-439, 130, "让一条线，织成星河。", "#8BA3B7", 10, "w")
        p.line([(-438, 105), (-328, 105)], "#344456")
        for i, color in enumerate(colors[1:]):
            p.circle(-432 + i * 22, 83, 3.5, color)
        p.text(-439, 51, colors[0] + " / P 换色", "#8299AD", 9, "w")
        p.text(-439, -171, "层叠光纹" if self.layered else "单线轨迹", colors[1], 11, "w")
        p.text(-439, -200, "L 切换层次 · G 查看圆盘", "#748CA3", 9, "w")
        for i, (label, value) in enumerate((("外圆 R", big), ("内圆 r", small), ("偏心距 d", distance))):
            p.text(335, 127 - i * 73, label, "#7790A7", 9, "w")
            p.text(334, 99 - i * 73, str(value), colors[1 + i], 22, "w")
        p.text(335, -153, f"速度 × {self.speed:.2f}", "#91A7BA", 10, "w")
        p.text(335, -184, "C 重绘这朵花", "#71879C", 9, "w")
        p.line([(-235, -282), (235, -282)], "#293A4D", 2)
        if self.progress > 0:
            p.line([(-235, -282), (-235 + 470 * self.progress, -282)], colors[1], 2)
        p.text(282, -282, f"{self.progress:.0%}", colors[1], 10, "w")
        p.end()
        self.stage.hud(f"{name} · {colors[0]} · 装饰叠层来自同一条旋轮线，按 G 看滚圆原理")


if __name__ == "__main__":
    app = Spirograph()
    app.stage.run(app.frame, app.reset)
