"""四向递归圆：保留原来的 1.5r 位移、r/2 半径规则，逐层观察几何生长。"""
from collections import namedtuple
import math

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、背景上色、背景下色、主线、辅线、文字、是否浅色。
PALETTES = (
    ("墨夜鎏金", "#121E2B", "#08121D", "#DFBE7A", "#769DAD", "#E5E3D8", False),
    ("冰川青辉", "#102D39", "#071B27", "#A7E0DA", "#719CBE", "#E4F5ED", False),
    ("纸上铜青", "#F5F1E5", "#E5DFCF", "#6E8274", "#B59661", "#384F4D", True),
)
Circle = namedtuple("Circle", "x y radius level path")
MAX_DEPTH = 4


def circle_tree(depth, radius=82):
    """每个父圆在东西南北生成四个相切的子圆；path 保存可选择的分支。"""
    depth = max(0, min(MAX_DEPTH, int(depth)))
    nodes = []

    def branch(x, y, r, level, path):
        nodes.append(Circle(x, y, r, level, path))
        if level < depth:
            for direction, (dx, dy) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                branch(x + dx * 1.5 * r, y + dy * 1.5 * r, r / 2,
                       level + 1, path + (direction,))

    branch(0, 0, radius, 0, ())
    return tuple(nodes)


def arc(x, y, radius, start, end, steps=16):
    return [polar(radius, start + (end-start) * i / steps, x, y)
            for i in range(steps+1)]


class RecursiveCircles:
    CENTER_Y = -8
    LAYERS_PER_SECOND = 1.2

    def __init__(self):
        self.stage = Stage("四向递归圆", "C 配色    ↑↓ 递归深度    G 逐层重播    点击圆 观察分支",
                           PALETTES[0][1], PALETTES[0][3])
        self.paint = Paint(self.stage, "recursive-motion")
        self.paint.backdrop = Paint(self.stage, "recursive-paper")
        self.paint.layers = [Paint(self.stage, f"recursive-level-{i}") for i in range(MAX_DEPTH+1)]
        self.paint.selection = Paint(self.stage, "recursive-selection")
        self.paint.signature = None
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_palette, key)
        for key in ("g", "G"):
            self.stage.screen.onkey(self.replay, key)
        self.stage.screen.onkey(lambda: self.change_depth(1), "Up")
        self.stage.screen.onkey(lambda: self.change_depth(-1), "Down")
        self.stage.screen.onclick(self.select)

    def reset(self):
        self.palette = 0
        self.depth = MAX_DEPTH
        self.growth = float(self.depth)
        self.time = 0.0
        self.selected = None
        self.nodes = circle_tree(self.depth)
        self.sync_stage()

    @property
    def visible_depth(self):
        return min(self.depth, int(self.growth))

    def sync_stage(self):
        colors = PALETTES[self.palette]
        self.stage.accent, self.stage.light = colors[3], colors[6]

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)
        self.sync_stage()

    def change_depth(self, amount):
        depth = max(0, min(MAX_DEPTH, self.depth + int(amount)))
        if depth != self.depth:
            self.depth = depth
            self.growth = float(depth)
            self.nodes = circle_tree(depth)
            self.selected = None

    def replay(self):
        if not self.stage.paused:
            self.growth = 0.0
            self.selected = None

    def select(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        y -= self.CENTER_Y
        hits = [node for node in self.nodes if node.level <= self.visible_depth
                and math.hypot(x-node.x, y-node.y) <= node.radius]
        if hits:
            # 相交处优先半径较小的圆，再选择距离圆心较近的那个。
            nearest = min(hits, key=lambda node: (node.radius, math.hypot(x-node.x, y-node.y)))
            self.selected = nearest.path

    def backdrop(self, colors):
        _, top, bottom, gold, blue, text, _ = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(top, bottom)
        fine = mix(bottom, gold, .26)
        quiet = mix(bottom, text, .55)
        for radius in (248, 251):
            p.circle(0, self.CENTER_Y, radius, outline=mix(bottom, gold, .18))
        for index in range(32):
            angle = math.tau * index / 32
            p.line([polar(248 if index % 8 else 244, angle, y=self.CENTER_Y),
                    polar(253, angle, y=self.CENTER_Y)], fine)
        for angle in (0, math.pi/2):
            p.line([polar(-237, angle, y=self.CENTER_Y),
                    polar(237, angle, y=self.CENTER_Y)], mix(bottom, blue, .12), dash=(2, 8))
        p.line([(-438, 168), (-399, 168)], gold, 1.6)
        p.text(-438, 136, "四向 / 递归", text, 20, "w")
        p.text(-437, 108, "FOUR DIRECTIONS", quiet, 8, "w")
        p.text(-437, 70, "同一个规则，", quiet, 11, "w")
        p.text(-437, 48, "在每一层重复。", quiet, 11, "w")
        p.line([(-437, 20), (-306, 20)], fine)
        p.text(-437, -9, "子圆半径   r / 2", gold, 11, "w")
        p.text(-437, -34, "圆心偏移   3r / 2", quiet, 10, "w")
        p.text(-437, -66, "↑  →  ↓  ←", gold, 16, "w")
        p.text(-437, -194, "RECURSIVE STUDY", quiet, 8, "w")
        p.text(-437, -217, "01 / CIRCLES", gold, 10, "w")

        p.text(314, 150, "层级  /  圆的数量", quiet, 10, "w")
        for level in range(MAX_DEPTH+1):
            y = 109 - level * 35
            active = level <= self.visible_depth
            color = mix(gold, blue, level / 5) if active else fine
            p.circle(321, y, 5-level*.65, outline=color, width=1.4)
            p.text(341, y, f"L{level:02d}", color, 10, "w")
            p.text(439, y, str(4**level), color, 10, "e")
        p.line([(314, -62), (439, -62)], fine)
        total = sum(4**level for level in range(self.visible_depth+1))
        p.text(314, -89, "已展开", quiet, 9, "w")
        p.text(439, -94, str(total), text, 24, "e")
        p.text(439, -124, f"DEPTH {self.visible_depth} / {self.depth}", gold, 8, "e")
        p.text(439, -210, "点击圆 · 追溯分支", quiet, 9, "e")
        p.end()

    def draw_structure(self, colors):
        signature = (self.palette, self.depth, self.visible_depth, self.selected,
                     self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        self.backdrop(colors)
        _, top, bottom, gold, blue, text, _ = colors
        for level, p in enumerate(self.paint.layers):
            p.begin()
            p.transform(y=self.CENTER_Y)
            if level <= self.visible_depth:
                for node in self.nodes:
                    if node.level != level:
                        continue
                    chosen = self.selected is None or node.path[:len(self.selected)] == self.selected
                    stroke = mix(gold, blue, level * .14)
                    stroke = mix(bottom, stroke, (1 - level*.065) if chosen else .26)
                    fill = mix(bottom, gold if level % 2 == 0 else blue,
                               (.052 + .012*(MAX_DEPTH-level)) if chosen else .025)
                    p.circle(node.x, node.y, node.radius, fill, stroke,
                             1.6 if level < 2 else 1.0)
                    # 细弧表现圆缘光泽，不改变原始相切关系。
                    p.line(arc(node.x, node.y, node.radius*.94, .35, 2.10, 12),
                           mix(fill, stroke, .35 if chosen else .22), .65)
                    p.circle(node.x, node.y, max(.6, 1.55-level*.23),
                             mix(fill, text, .40 if chosen else .14))
            p.end()
        p = self.paint.selection
        p.begin()
        if self.selected is not None:
            node = next(node for node in self.nodes if node.path == self.selected)
            p.circle(node.x, node.y+self.CENTER_Y, node.radius+3, outline=colors[5], width=1.3)
            p.text(439, -160, f"选择  L{node.level:02d}  /  r = {node.radius:g}", gold, 9, "e")
            branch_count = sum(node.path == item.path[:len(node.path)]
                               and item.level <= self.visible_depth for item in self.nodes)
            p.text(439, -182, f"此分支  {branch_count}  个圆", mix(bottom, text, .64), 9, "e")
        p.end()
        self.paint.signature = signature

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.growth = min(float(self.depth), self.growth + dt*self.LAYERS_PER_SECOND)
        colors = PALETTES[self.palette]
        self.draw_structure(colors)
        # 静态圆的几何与明暗均缓存；只有外圈四道很慢的短光弧移动。
        p = self.paint
        p.begin()
        for quarter in range(4):
            angle = quarter*math.pi/2 + self.time*.055
            p.line(arc(0, self.CENTER_Y, 249.5, angle-.11, angle+.025, 9),
                   mix(colors[2], colors[3], .53), 1.3)
            x, y = polar(249.5, angle+.025, y=self.CENTER_Y)
            p.circle(x, y, 1.65, colors[3])
        p.end()
        selected = "" if self.selected is None else f"  ·  已选 L{len(self.selected)} 分支"
        self.stage.hud(f"{colors[0]}  ·  深度 {self.visible_depth}/{self.depth}  ·  "
                       f"每层四分，半径减半{selected}")

    def run(self):
        self.stage.run(self.frame, self.reset)


if __name__ == "__main__":
    RecursiveCircles().run()
