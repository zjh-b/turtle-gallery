"""随机分形树：原来的左右随机分叉，长成溪岸上的一树花信。

N 换一棵树，G 重放生长，C 春樱 / 玉兰 / 金叶，点击画面吹落花瓣。
种子显示在窗口中；``generate_tree(seed)`` 可重现同一棵树。仅使用标准库。
"""
from collections import namedtuple
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、天空、近纸色、远山、溪水、树干、树干亮部、花暗部、花亮部、花心。
PALETTES = (
    ("春樱溪岸", "#F9EEE8", "#EDE8DA", "#93B2AA", "#AFCCC4", "#634D49",
     "#AE8C79", "#D87E9D", "#FFF1ED", "#BA785F"),
    ("月白玉兰", "#EAF0EA", "#DCE7DF", "#78978F", "#97B8B0", "#495C57",
     "#96A69B", "#CFB8AA", "#FFFDF0", "#BCA76F"),
    ("秋日金叶", "#FCF1D8", "#F1E1BC", "#B5AE7E", "#BFC8A4", "#695642",
     "#BFA579", "#C98535", "#FFE4A0", "#92723C"),
)
Branch = namedtuple("Branch", "points depth parent length start_width end_width turn")
DEFAULT_SEED = 202610
MAX_DEPTH = 7
MAX_BRANCHES = 255
MAX_FLOWERS = 220


def generate_tree(seed):
    """Pure seeded geometry: 10–40° forks and a 10–20 length reduction.

    The depth and node bounds prevent the original unrestricted recursion from
    growing expensive. A final uniform transform fits every seed into the scene.
    """
    rng = random.Random(seed)
    raw = []

    def branch(x, y, angle, length, depth, parent, turn):
        if len(raw) >= MAX_BRANCHES:
            return
        ex, ey = polar(length, angle, x, y)
        bend = rng.uniform(-.13, .13) * length
        cx, cy = (x + ex) / 2 - math.sin(angle) * bend, (y + ey) / 2 + math.cos(angle) * bend
        points = tuple(((1-t)**2*x + 2*(1-t)*t*cx + t*t*ex,
                        (1-t)**2*y + 2*(1-t)*t*cy + t*t*ey)
                       for t in (i / 8 for i in range(9)))
        index = len(raw)
        raw.append((points, depth, parent, length, turn))
        if depth < MAX_DEPTH and length > 25:
            for side in (-1, 1):
                fork = side * rng.randint(10, 40)
                child_length = length - rng.randint(10, 20)
                branch(ex, ey, angle + math.radians(fork), child_length, depth + 1, index, fork)

    branch(0, 0, math.pi / 2, 125, 0, -1, 0)
    points = [point for record in raw for point in record[0]]
    low, high = min(x for x, y in points), max(x for x, y in points)
    top = max(y for x, y in points)
    scale = min(630 / max(1, high-low), 400 / max(1, top))
    center = (low+high) / 2
    branches = tuple(Branch(tuple(((x-center)*scale + 20, y*scale - 184) for x, y in path),
                            depth, parent, length,
                            max(.8, 17 * .69**depth), max(.45, 10.8 * .69**depth), turn)
                     for path, depth, parent, length, turn in raw)
    parents = {branch.parent for branch in branches}
    tips = [i for i in range(len(branches)) if i not in parents]
    flowers = []
    # Each terminal twig owns a small cluster; large flowers have a clear
    # silhouette and spaces between clusters keep the recursive structure legible.
    for index in tips:
        branch = branches[index]
        for k in range(2):
            anchor = branch.points[-1 if k == 0 else 5]
            flowers.append((anchor[0] + rng.uniform(-7, 7), anchor[1] + rng.uniform(-4, 7),
                            rng.uniform(4.7, 8.5), rng.uniform(0, math.tau), index, rng.random()))
    # The bounded selection is balanced across the entire canopy, not a prefix
    # of the depth-first recursion that would favour one side of the tree.
    rng.shuffle(flowers)
    flowers = sorted(flowers[:MAX_FLOWERS], key=lambda flower: flower[1])
    return branches, tuple(flowers)


def branch_outline(branch, progress=1):
    """A curved tapered ribbon; endpoints meet the parent rather than float."""
    progress = max(0, min(1, progress))
    end = progress * (len(branch.points)-1)
    count = min(len(branch.points)-2, int(end))
    path = list(branch.points[:count+1])
    a, b = branch.points[count], branch.points[count+1]
    path.append((a[0] + (b[0]-a[0])*(end-count), a[1] + (b[1]-a[1])*(end-count)))
    left, right = [], []
    for i, (x, y) in enumerate(path):
        first, last = path[max(0, i-1)], path[min(len(path)-1, i+1)]
        dx, dy = last[0]-first[0], last[1]-first[1]
        length = max(.0001, math.hypot(dx, dy))
        width = (branch.start_width + (branch.end_width-branch.start_width) *
                 (i / max(1, len(path)-1)) * progress) / 2
        left.append((x-dy/length*width, y+dx/length*width))
        right.append((x+dy/length*width, y-dx/length*width))
    return left + right[::-1]


class BlossomTree:
    GROWTH_END = MAX_DEPTH + 2
    PETAL_LIMIT = 48
    PETAL_LIFETIME = 4.2

    def __init__(self):
        self.stage = Stage("随机分形树", "N 换一棵树    G 逐层生长    C 花信配色    点击 吹落花瓣",
                           PALETTES[0][1], "#A77184", light=True)
        self.paint = Paint(self.stage, "blossom-petals")
        self.paint.backdrop = Paint(self.stage, "blossom-landscape")
        self.paint.tree = Paint(self.stage, "blossom-tree")
        self.paint.background_signature = self.paint.tree_signature = None
        decoration = random.Random(824)
        self.fibers = tuple((decoration.uniform(-490, 490), decoration.uniform(-265, 255),
                             decoration.uniform(1, 5)) for _ in range(40))
        self.carpet = tuple((decoration.uniform(-255, 315), decoration.uniform(-208, -182),
                             decoration.uniform(1, 2.6), decoration.random()) for _ in range(42))
        self.drifters = tuple((decoration.random(), decoration.uniform(-260, 260),
                               decoration.uniform(1.5, 2.9), decoration.uniform(0, math.tau))
                              for _ in range(12))
        self.reset()
        for keys, action in ((('c', 'C'), self.cycle_palette), (('n', 'N'), self.next_tree),
                             (('g', 'G'), self.replay_growth)):
            for key in keys:
                self.stage.screen.onkey(action, key)
        self.stage.screen.onclick(self.blow)

    def reset(self):
        self.time, self.palette, self.seed = 0, 0, DEFAULT_SEED
        self.growth = self.GROWTH_END
        self.petals = []
        self.wind_rng = random.Random(53)
        self.branches, self.flowers = generate_tree(self.seed)

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def next_tree(self):
        if not self.stage.paused:
            self.seed = (self.seed * 1664525 + 1013904223) % (2**32)
            self.branches, self.flowers = generate_tree(self.seed)
            self.growth = self.GROWTH_END
            self.petals = []

    def replay_growth(self):
        if not self.stage.paused:
            self.growth = 0
            self.petals = []

    def blow(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        # 与 draw_tree 的离散生长进度一致：花尚未显示时不能吹落花瓣。
        growth = min(self.GROWTH_END, int(self.growth * 12) / 12)
        visible = [flower for flower in self.flowers if growth > self.branches[flower[4]].depth + 1]
        if not visible:
            return
        # A gust begins at nearby existing blossoms. It never invents flowers
        # in an unfinished crown, and repeated clicks use a fixed-size pool.
        nearby = sorted(visible, key=lambda flower: (flower[0]-x)**2 + (flower[1]-y)**2)[:24]
        for source in nearby[:16]:
            sx, sy, radius, angle, _, _ = source
            self.petals.append((sx, sy, self.wind_rng.uniform(25, 65),
                                self.wind_rng.uniform(-4, 18), 0, angle, radius * .38))
        self.petals = self.petals[-self.PETAL_LIMIT:]

    def draw_backdrop(self, colors):
        signature = self.palette, self.stage.scale, self.stage.view
        if signature == self.paint.background_signature:
            return
        self.paint.background_signature = signature
        _, sky, paper, mountain, water, bark, _, petal, _, _ = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(sky, paper)
        for r in range(77, 39, -3):
            p.circle(349, 154, r, mix(sky, "#FFF9E4", .08 + (77-r) * .012))
        p.circle(349, 154, 40, mix(sky, "#FFFAE9", .82))
        for x, y, length in self.fibers:
            p.line([(x, y), (x+length, y+.4)], mix(sky, paper, .6))
        p.poly([(-510, -108), (-438, -70), (-372, -92), (-285, -42), (-217, -106),
                (-112, -69), (-22, -99), (75, -59), (141, -96), (245, -43),
                (325, -84), (426, -59), (510, -119), (510, -183), (-510, -183)],
               mix(paper, mountain, .25), smooth=True)
        p.poly([(-510, -150), (-410, -105), (-326, -130), (-229, -86), (-103, -132),
                (20, -110), (135, -131), (279, -84), (390, -126), (510, -95),
                (510, -214), (-510, -214)], mix(paper, mountain, .4), smooth=True)
        p.poly([(-510, -161), (-351, -163), (-157, -178), (101, -166), (305, -184),
                (510, -165), (510, -271), (260, -249), (-27, -247), (-254, -268),
                (-510, -265)], mix(paper, water, .58), smooth=True)
        for i in range(21):
            y = -175-i*4
            x = 245 + math.sin(i*.7)*105
            p.line([(x-38-i*1.8, y), (x+49+i*1.8, y)], mix(water, sky, .47 + .2*math.sin(i)), .8)
        p.poly([(-510, -174), (-308, -170), (-176, -180), (-37, -172), (103, -182),
                (176, -198), (75, -214), (-78, -208), (-268, -223), (-510, -209)],
               mix(paper, mountain, .36), smooth=True)
        p.poly([(-510, -259), (-331, -246), (-172, -266), (4, -246), (163, -260),
                (366, -244), (510, -248), (510, -287), (-510, -287)],
               mix(paper, mountain, .32), smooth=True)
        for i in range(14):
            x = -452 + i*61
            y = -267 + math.sin(i*1.3)*7
            ink = mix(paper, mountain, .63)
            p.line([(x-5, y-4), (x-8, y+7), (x-12, y+13)], ink, 1, smooth=True)
            p.line([(x-5, y-4), (x, y+10), (x+7, y+16)], ink, 1, smooth=True)
        for x, y, radius, shade in self.carpet:
            p.oval(x, y, radius*1.6, radius*.54, mix(petal, sky, shade*.7))
        for x, y, rx, ry in ((-312, -196, 20, 7), (-284, -199, 12, 5), (152, -203, 18, 6)):
            p.oval(x+3, y-2, rx+3, ry, mix(paper, mountain, .43))
            p.oval(x, y, rx, ry, mix(paper, bark, .30))
            p.line([(x-rx*.55, y+ry*.3), (x+rx*.45, y+ry*.5)], mix(paper, sky, .65), 1)
        p.text(-445, 214, "一树花信", mix(paper, bark, .7), 18, "w")
        p.line([(-444, 192), (-406, 192)], mix(paper, petal, .65), 1.5)
        p.text(-445, 174, "风过枝头，花落溪间。", mix(paper, bark, .5), 9, "w")
        p.text(440, -274, "RANDOM BRANCHES · LIVING FORMS", mix(paper, bark, .5), 8, "e")
        p.end()

    def draw_tree(self, colors):
        # Growth redraws at twelve small steps per branch level; a mature tree
        # remains a cached static layer, even while petals are moving.
        growth = min(self.GROWTH_END, int(self.growth*12)/12)
        signature = self.seed, self.palette, growth, self.stage.scale, self.stage.view
        if signature == self.paint.tree_signature:
            return
        self.paint.tree_signature = signature
        _, sky, paper, mountain, _, bark, highlight, petal, light, center = colors
        p = self.paint.tree
        p.begin()
        root_x, root_y = self.branches[0].points[0]
        p.oval(root_x+10, root_y-3, 65, 9, mix(paper, mountain, .48))
        for branch in self.branches:
            progress = max(0, min(1, growth - branch.depth))
            if not progress:
                continue
            p.poly(branch_outline(branch, progress), mix(bark, highlight, branch.depth*.052))
            if branch.depth < 4 and progress >= 1:
                p.line([(x-branch.start_width*.12, y) for x, y in branch.points],
                       mix(bark, highlight, .62-branch.depth*.065), max(.6, branch.start_width*.13),
                       smooth=True)
        for x, y, radius, angle, index, shade in self.flowers:
            opening = max(0, min(1, (growth-self.branches[index].depth-1)*2))
            if opening <= 0:
                continue
            size = radius * (.35 + .65*opening)
            if self.palette == 2:
                points = [polar(size*k, angle+a, x, y) for k, a in
                          ((1, 0), (.62, .7), (.15, 2.5), (.3, math.pi), (.62, -.7))]
                p.poly(points, mix(petal, light, .18+shade*.64), smooth=True)
                p.line([polar(size*.7, angle, x, y), polar(size*.3, angle+math.pi, x, y)],
                       mix(petal, center, .5), .65)
            else:
                lobes = 5 if self.palette == 0 else 3
                face = mix(petal, light, .35+shade*.58)
                points = [polar(size*(.88+.12*math.cos(lobes*t)), t+angle, x, y)
                          for t in (math.tau*i/50 for i in range(50))]
                p.poly(points, face, mix(face, petal, .20), .55, smooth=True)
                # 较大花朵多一层浅内瓣；小花保留简洁轮廓与清晰花心。
                if size >= 6:
                    inner = [polar(size*.62*(.86+.14*math.cos(lobes*t)),
                                   t+angle+math.pi/lobes, x-size*.06, y+size*.06)
                             for t in (math.tau*i/40 for i in range(40))]
                    p.poly(inner, mix(face, light, .49), smooth=True)
                p.circle(x, y, max(.65, size*.13), mix(center, light, .30+shade*.28))
        p.end()

    def draw_petal(self, x, y, radius, angle, fill):
        self.paint.poly([polar(radius, angle, x, y), polar(radius*.62, angle+1.3, x, y),
                         polar(radius*.83, angle+math.pi, x, y),
                         polar(radius*.62, angle-1.3, x, y)], fill, smooth=True)

    def frame(self, dt):
        if dt > 0:
            self.time += dt
            self.growth = min(self.GROWTH_END, self.growth + dt*1.35)
            self.petals = [(x, y, vx, vy, age+dt, angle, radius)
                           for x, y, vx, vy, age, angle, radius in self.petals
                           if age+dt < self.PETAL_LIFETIME]
        colors = PALETTES[self.palette]
        self.draw_backdrop(colors)
        self.draw_tree(colors)
        # 静态画层在重绘时由 Paint.end 排序；每帧抬升整棵树会让 Tk
        # 重刷千余图元。普通帧只需把少量动态花瓣放在树冠上方。
        p = self.paint
        p.begin()
        if self.growth >= self.GROWTH_END:
            for phase, x, radius, angle in self.drifters:
                life = (self.time*.075+phase) % 1
                px, py = x+math.sin(life*6+angle)*22+life*40, 180-life*372
                self.draw_petal(px, py, radius, angle+self.time*.7,
                                mix(colors[7], colors[8], .48))
        for x, y, vx, vy, age, angle, radius in self.petals:
            px, py = x+vx*age+math.sin(age*4+angle)*6, y+vy*age-15*age*age
            if -495 < px < 495 and -272 < py < 247:
                fade = max(0, (age/self.PETAL_LIFETIME-.65)/.35)
                self.draw_petal(px, py, radius, angle+age*2.5, mix(colors[8], colors[2], fade))
        p.end()
        progress = "盛放" if self.growth >= self.GROWTH_END else f"生长 {round(self.growth/self.GROWTH_END*100)}%"
        self.stage.hud(f"{colors[0]} · {progress}    /    种子 {self.seed} · {len(self.branches)} 段枝条")


if __name__ == "__main__":
    app = BlossomTree()
    app.stage.run(app.frame, app.reset)
