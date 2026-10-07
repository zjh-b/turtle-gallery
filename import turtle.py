"""方块螺旋：保留原作的 230 步数学规则，加入精细线稿与构造演示。

直接运行：python "import turtle.py"
原规则：前进 i → 右转 44° → 绘制边长 5 + i / 8 的正方形。
"""
import math

from 社团展示.舞台 import Paint, Stage, mix, polar


ANGLE_PRESETS = (36, 44, 52)
# 名称、底色、内层光、外层光、最亮描边；低饱和背景让线条交叠仍清楚。
PALETTES = (
    ("青金刻线", "#091721", "#417D92", "#56CCBC", "#F2D194"),
    ("紫晶晨光", "#171321", "#685AAB", "#CB87C5", "#F4CAA7"),
    ("珊瑚星图", "#151D25", "#376E92", "#77CACD", "#F39580"),
)


def square_geometry(angle=44, count=230):
    """按原 Turtle 命令生成方块顶点，不缩放、不增加连接线。

    heading 为向右的 0°；Turtle.right 对应减角度。四次右转后
    朝向不变，因此下一步从当前方块起点继续前进。每块末点复用
    首点，避免累计浮点误差留下肉眼可见的小缝。
    """
    x = y = heading = 0.0
    squares = []
    for i in range(count):
        x += i * math.cos(math.radians(heading))
        y += i * math.sin(math.radians(heading))
        heading -= angle
        side = 5 + i / 8
        points = [(x, y)]
        px, py = x, y
        for j in range(3):
            direction = math.radians(heading - 90 * j)
            px += side * math.cos(direction)
            py += side * math.sin(direction)
            points.append((px, py))
        points.append(points[0])
        squares.append(tuple(points))
    return tuple(squares)


def fit_geometry(squares, radius=224):
    """只做统一缩放和平移，保留所有边长比例与角度关系。"""
    points = [point for square in squares for point in square[:-1]]
    if not points:
        return ()
    cx = (max(x for x, _ in points) + min(x for x, _ in points)) / 2
    cy = (max(y for _, y in points) + min(y for _, y in points)) / 2
    extent = max(math.hypot(x - cx, y - cy) for x, y in points)
    scale = radius / max(extent, 1)
    return tuple(tuple(((x - cx) * scale, (y - cy) * scale - 3)
                       for x, y in square) for square in squares)


class SquareSpiral:
    COUNT = 230
    DRAW_RATE = 24

    def __init__(self):
        self.stage = Stage("方块螺旋", "C 配色    ←→ 转角    ↑↓ 构造速度    G / 点击 重播",
                           PALETTES[0][1], PALETTES[0][4])
        self.paint = Paint(self.stage, "square-spiral-tip")
        self.paint.backdrop = Paint(self.stage, "square-spiral-paper")
        self.paint.squares = Paint(self.stage, "square-spiral-lines")
        self.paint.signature = None
        self.paint.visible_count = None
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_palette, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.replay, key)
        self.stage.screen.onkey(lambda: self.change_angle(-1), "Left")
        self.stage.screen.onkey(lambda: self.change_angle(1), "Right")
        self.stage.screen.onkey(lambda: self.change_speed(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.25), "Down")
        self.stage.screen.onclick(self.click)

    def reset(self):
        self.palette, self.preset = 0, 1
        self.angle = ANGLE_PRESETS[self.preset]
        self.speed, self.time = 1.0, 0.0
        self.progress = float(self.COUNT)
        self.geometry = fit_geometry(square_geometry(self.angle, self.COUNT))
        self.stage.accent = PALETTES[self.palette][4]
        self.paint.signature = None

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)
        self.stage.accent = PALETTES[self.palette][4]

    def change_angle(self, direction):
        self.preset = (self.preset + direction) % len(ANGLE_PRESETS)
        self.angle = ANGLE_PRESETS[self.preset]
        self.geometry = fit_geometry(square_geometry(self.angle, self.COUNT))

    def change_speed(self, amount):
        self.speed = max(.25, min(3, self.speed + amount))

    def replay(self):
        if not self.stage.paused:
            self.progress = 0.0

    def click(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        self.replay()

    def line_color(self, index):
        _, _, inner, middle, outer = PALETTES[self.palette]
        amount = index / (self.COUNT - 1)
        return mix(inner, middle, amount / .58) if amount < .58 else mix(middle, outer, (amount - .58) / .42)

    def cache_drawing(self):
        signature = (self.palette, self.angle, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        _, ground, inner, middle, outer = PALETTES[self.palette]
        p = self.paint.backdrop
        p.begin()
        p.gradient(mix(ground, inner, .07), ground)
        # 极浅的圆形纸面光与刻度围住主图，不覆盖任何正方形。
        for i in range(24):
            p.circle(0, -3, 234 - i * 8.5, mix(ground, inner, .025 + i * .002))
        muted = mix(ground, middle, .45)
        for radius in (235, 242):
            p.circle(0, -3, radius, outline=mix(ground, middle, .13 if radius == 235 else .24))
        for i in range(60):
            angle = i * math.tau / 60
            radius = 237 if i % 5 == 0 else 240
            p.line([polar(radius, angle, y=-3), polar(243, angle, y=-3)],
                   muted if i % 5 == 0 else mix(ground, middle, .17), .7)
        p.line([(-435, 174), (-394, 174)], outer, 1.7)
        p.text(-435, 144, "方寸 / 成环", mix(outer, "#FFFFFF", .22), 21, "w")
        p.text(-433, 113, "SQUARE STUDIES", muted, 8, "w")
        p.text(-433, 70, "230", outer, 33, "w")
        p.text(-433, 40, "个方块 · 一条规则", muted, 10, "w")
        p.line([(-433, -112), (-321, -112)], mix(ground, middle, .24))
        p.text(-433, -136, "前进 i", muted, 11, "w")
        p.text(-433, -159, f"右转 {self.angle}°", muted, 11, "w")
        p.text(-433, -182, "边长 5 + i / 8", muted, 11, "w")
        p.text(432, 150, f"{self.angle}°", outer, 32, "e")
        p.text(432, 117, "TURN / ROTATION", muted, 8, "e")
        p.line([(311, 92), (432, 92)], mix(ground, middle, .28))
        for i, angle in enumerate(ANGLE_PRESETS):
            y = 64 - 29 * i
            selected = angle == self.angle
            p.circle(328, y, 2.5, outer if selected else mix(ground, middle, .28))
            p.text(431, y, f"{angle}°" + ("  原作" if angle == 44 else "  变奏"),
                   outer if selected else muted, 10, "e")
        p.text(432, -170, "向外生长，向内回望。", muted, 10, "e")
        p.text(432, -199, "GEOMETRY  /  230", mix(ground, outer, .57), 8, "e")
        p.line([(-68, -263), (-15, -263)], mix(ground, middle, .28))
        p.circle(0, -263, 2, outer)
        p.line([(15, -263), (68, -263)], mix(ground, middle, .28))
        p.end()
        p = self.paint.squares
        p.begin()
        self.paint.square_items = []
        for index, square in enumerate(self.geometry):
            color = self.line_color(index)
            start = p.index
            # 暗细底线托住清晰主线，短角线形成轻微金属刻面。
            p.line(square, mix(ground, color, .16), 3.1)
            p.line(square, mix(ground, color, .62 + .30 * index / self.COUNT), 1.05)
            x0, y0 = square[0]
            x1, y1 = square[1]
            p.line([(x0, y0), (x0 + (x1 - x0) * .17, y0 + (y1 - y0) * .17)],
                   mix(color, outer, .30), 1.3)
            self.paint.square_items.append(p.items[start:p.index])
        p.end()
        self.paint.signature, self.paint.visible_count = signature, None

    def show_completed(self):
        """构造阶段只改变新增方块的可见性，完整状态不重画 230 个方块。"""
        visible = min(self.COUNT, int(self.progress))
        previous = self.paint.visible_count
        if previous == visible:
            return
        changed = range(self.COUNT) if previous is None else range(min(previous, visible), max(previous, visible))
        for index in changed:
            state = "normal" if index < visible else "hidden"
            for item in self.paint.square_items[index]:
                self.stage.canvas.itemconfigure(item[1], state=state)
                item[3]["state"] = state
        self.paint.visible_count = visible

    def draw_tip(self):
        _, ground, _, _, outer = PALETTES[self.palette]
        p = self.paint
        p.begin()
        position = self.progress if self.progress < self.COUNT else (self.time * 9 + 180) % self.COUNT
        index = min(self.COUNT - 1, int(position))
        fraction = position - int(position)
        square = self.geometry[index]
        side = min(3, int(fraction * 4))
        along = fraction * 4 - side
        a, b = square[side], square[side + 1]
        x, y = a[0] + (b[0] - a[0]) * along, a[1] + (b[1] - a[1]) * along
        color = mix(self.line_color(index), "#FFF7DA", .58)
        p.line(list(square[:side + 1]) + [(x, y)], color, 1.6)
        for radius, amount in ((6, .10), (3.8, .25), (2.4, .68)):
            p.circle(x, y, radius, mix(ground, color, amount))
        p.circle(x, y, 1.25, color)
        p.text(432, -229, f"{int(self.progress):03d} / 230" if self.progress < self.COUNT else "G  观看构造", outer, 9, "e")
        p.end()

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.progress = min(float(self.COUNT), self.progress + dt * self.DRAW_RATE * self.speed)
        self.cache_drawing()
        self.show_completed()
        self.stage.canvas.tag_raise(self.paint.backdrop.tag)
        self.stage.canvas.tag_raise(self.paint.squares.tag)
        self.draw_tip()
        status = "完整构图" if self.progress >= self.COUNT else f"正在构造 {int(self.progress)} / 230"
        self.stage.hud(f"{PALETTES[self.palette][0]}  ·  {self.angle}° 转角  ·  {self.speed:g}×  ·  {status}")

    def run(self):
        self.stage.run(self.frame, self.reset)


if __name__ == "__main__":
    SquareSpiral().run()
