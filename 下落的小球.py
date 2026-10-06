"""彩球碰撞：二十颗有光影的彩球，组成可触碰的微型运动展台。

运行 ``python 下落的小球.py``；C 换色，G 切换重力，↑↓ 调速，点击推开彩球。
球体由多层圆面与弧形高光绘制；运动使用固定时间步长和弹性碰撞。
"""
import math
import random

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、背景、展台底色、线色，以及五种彩球颜色。
PALETTES = (
    ("珠光夜游", "#091827", "#152F3B", "#759DB2",
     ("#77CEC0", "#E5AA71", "#E795AE", "#9697DF", "#79BDE3")),
    ("海盐晴空", "#EAF2F0", "#D9E9E9", "#608A93",
     ("#44A5A2", "#DFAB60", "#D27A86", "#8B8EC3", "#639DBD")),
    ("莓果霓光", "#171526", "#302437", "#A790BA",
     ("#D996D3", "#ECBA81", "#DF8A9A", "#9BACEB", "#81CEC7")),
)
BOUNDS = (-445., 445., -231., 200.)  # left, right, bottom, top
STEP = 1 / 120
MAX_SPEED = 280.
RIPPLE_SLOTS = 5
RIPPLE_SECONDS = 1.4
SHADE_LAYERS = 20


def collide(a, b):
    """Resolve overlapping circles, using their area as mass.

    Correct coincident positions too. Only approaching contacts receive an
    impulse; separating balls cannot bounce twice from the same contact.
    """
    dx, dy = b['x'] - a['x'], b['y'] - a['y']
    distance = math.hypot(dx, dy)
    reach = a['r'] + b['r']
    if distance >= reach:
        return
    nx, ny = (dx / distance, dy / distance) if distance > 1e-9 else (1., 0.)
    mass_a, mass_b = a['r'] ** 2, b['r'] ** 2
    share_a, share_b = mass_b / (mass_a + mass_b), mass_a / (mass_a + mass_b)
    overlap = reach - distance
    a['x'] -= nx * overlap * share_a
    a['y'] -= ny * overlap * share_a
    b['x'] += nx * overlap * share_b
    b['y'] += ny * overlap * share_b
    approach = (a['vx'] - b['vx']) * nx + (a['vy'] - b['vy']) * ny
    if approach > 0:
        a['vx'] -= 2 * approach * share_a * nx
        a['vy'] -= 2 * approach * share_a * ny
        b['vx'] += 2 * approach * share_b * nx
        b['vy'] += 2 * approach * share_b * ny
        if approach > 25:
            a['flash'] = b['flash'] = .26


class PrismBalls:
    def __init__(self):
        self.stage = Stage("彩球碰撞", "点击 推开彩球    G 重力    C 配色    ↑↓ 调速",
                           "#091827", "#99DDD0")
        self.paint = Paint(self.stage, "prism-balls")
        self.paint.backdrop = Paint(self.stage, "prism-room")
        self.paint.signature = None
        self.shades = tuple(tuple(tuple(mix(mix(color, "#081321", .75),
                                           mix(color, "#FFFFFF", .36), (i / (SHADE_LAYERS - 1)) ** .8)
                                        for i in range(SHADE_LAYERS))
                                  for color in colors[4]) for colors in PALETTES)
        self.reset()
        for key in ('c', 'C'):
            self.stage.screen.onkey(self.cycle_palette, key)
        for key in ('g', 'G'):
            self.stage.screen.onkey(self.toggle_gravity, key)
        self.stage.screen.onkey(lambda: self.change_speed(.25), 'Up')
        self.stage.screen.onkey(lambda: self.change_speed(-.25), 'Down')
        self.stage.screen.onclick(self.push)

    def reset(self):
        self.time, self.accumulator, self.palette, self.speed = 0., 0., 0, 1.
        self.gravity = False
        self.ripples, self.ripple_cursor = [None] * RIPPLE_SLOTS, 0
        rng = random.Random(216)
        self.balls = []
        for index in range(20):
            angle, velocity = rng.uniform(0, math.tau), rng.uniform(38, 88)
            self.balls.append(dict(x=-340 + index % 5 * 166 + rng.uniform(-20, 20),
                                   y=145 - index // 5 * 107 + rng.uniform(-12, 12),
                                   vx=math.cos(angle) * velocity, vy=math.sin(angle) * velocity,
                                   r=rng.uniform(22, 35), color=index % 5, flash=0.))

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def toggle_gravity(self):
        self.gravity = not self.gravity

    def change_speed(self, amount):
        self.speed = max(.25, min(2., self.speed + amount))

    def push(self, x, y):
        x, y = self.stage.point(x, y)
        left, right, bottom, top = BOUNDS
        if self.stage.paused or not (left < x < right and bottom < y < top):
            return
        self.ripples[self.ripple_cursor] = (x, y, self.time)
        self.ripple_cursor = (self.ripple_cursor + 1) % RIPPLE_SLOTS
        for item in self.balls:
            dx, dy = item['x'] - x, item['y'] - y
            distance = math.hypot(dx, dy)
            if distance < 270:
                nx, ny = (dx / distance, dy / distance) if distance > .01 else (0., 1.)
                strength = 225 * (1 - distance / 270)
                item['vx'] += nx * strength
                item['vy'] += ny * strength + (strength * .45 if self.gravity else 0)
                self.limit_velocity(item)
                item['flash'] = .26

    @staticmethod
    def limit_velocity(item):
        velocity = math.hypot(item['vx'], item['vy'])
        if velocity > MAX_SPEED:
            item['vx'] *= MAX_SPEED / velocity
            item['vy'] *= MAX_SPEED / velocity

    def walls(self, item):
        left, right, bottom, top = BOUNDS
        radius = item['r']
        for position, velocity, low, high in (('x', 'vx', left, right),
                                             ('y', 'vy', bottom, top)):
            if item[position] < low + radius:
                item[position] = low + radius
                item[velocity] = abs(item[velocity]) * (.94 if self.gravity else 1)
            elif item[position] > high - radius:
                item[position] = high - radius
                item[velocity] = -abs(item[velocity]) * (.94 if self.gravity else 1)

    def step(self):
        self.time += STEP
        for item in self.balls:
            item['flash'] = max(0., item['flash'] - STEP)
            if self.gravity:
                item['vy'] -= 170 * STEP
            self.limit_velocity(item)
            item['x'] += item['vx'] * STEP
            item['y'] += item['vy'] * STEP
            self.walls(item)
        # Two passes reduce remaining overlap in a cluster near the floor.
        for _ in range(2):
            for index, item in enumerate(self.balls):
                for other in self.balls[index + 1:]:
                    collide(item, other)
            for item in self.balls:
                self.walls(item)
        self.ripples = [None if ripple is None or self.time - ripple[2] >= RIPPLE_SECONDS
                        else ripple for ripple in self.ripples]

    def update(self, dt):
        if dt <= 0:
            return
        self.accumulator += min(dt, .25) * self.speed
        while self.accumulator + 1e-10 >= STEP:
            self.step()
            self.accumulator = max(0., self.accumulator - STEP)

    def draw_room(self, colors):
        signature = (self.palette, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            self.stage.canvas.tag_raise(self.paint.backdrop.tag)
            return
        self.paint.signature = signature
        _, sky, floor, accent, _ = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(sky, floor)
        # Match each fine guide to the gradient beneath it; no hard glow edge.
        height = self.stage.view[1]
        for y in range(-190, 191, 38):
            ground = mix(sky, floor, (height / 2 - y) / height)
            p.line([(-445, y), (445, y)], mix(ground, accent, .035), .7)
        p.rect(-447, -228, 447, -245, mix(sky, floor, .66))
        p.line([(-446, 202), (-446, -232), (446, -232), (446, 202)], mix(floor, accent, .27), 1)
        p.line([(-446, 202), (446, 202)], mix(floor, accent, .16), 1)
        p.line([(-446, -235), (446, -235)], mix(floor, accent, .12), 2)
        for x in range(-400, 401, 50):
            p.line([(x, -233), (x, -240 if x % 100 == 0 else -237)], mix(floor, accent, .45))
        p.text(-444, 237, "光的游乐场", mix(accent, '#FFFFFF', .40), 17, 'w', True)
        p.text(445, 239, "20 ORBS  /  CHROMATIC MOTION", accent, 9, 'e')
        p.text(-444, -260, "轻轻一碰，让色彩散开。", accent, 10, 'w')
        p.text(445, -260, "碰撞 · 反弹 · 光影", accent, 9, 'e')
        p.end()

    def draw_ball(self, item, colors):
        p = self.paint
        _, _, floor, _, swatches = colors
        x, y, radius = item['x'], item['y'], item['r']
        color = swatches[item['color']]
        speed = math.hypot(item['vx'], item['vy'])
        nx, ny = (item['vx'] / speed, item['vy'] / speed) if speed > 1 else (0., 1.)
        for i in range(3):
            distance = radius + 5 + i * 6
            p.line([(x - nx * distance, y - ny * distance),
                    (x - nx * (distance + 3), y - ny * (distance + 3))],
                   mix(floor, color, .22 - i * .055), 2)
        p.circle(x + radius * .09, y - radius * .13, radius + 1.5, mix(floor, '#030C15', .25))
        for i, shade in enumerate(self.shades[self.palette][item['color']]):
            fraction = i / (SHADE_LAYERS - 1)
            p.circle(x - radius * .25 * fraction, y + radius * .29 * fraction,
                     radius * (1 - .82 * fraction), shade)
        for start, end, tone in ((.38, 2.2, .62), (3.65, 5.3, .37)):
            p.line([polar(radius * .87, start + (end - start) * i / 18, x, y)
                    for i in range(19)], mix(color, '#FFFFFF', tone), 1.2)
        p.oval(x - radius * .30, y + radius * .38, radius * .23, radius * .12,
               mix(color, '#FFFFFF', .78))
        p.oval(x - radius * .33, y + radius * .41, radius * .10, radius * .05, '#F7FFFA')
        p.circle(x + radius * .48, y - radius * .50, radius * .07, mix(color, '#FFFFFF', .60))
        p.circle(x, y, radius + 2, outline=mix(floor, color, item['flash'] * 1.6), width=1)

    def frame(self, dt):
        self.update(dt)
        colors = PALETTES[self.palette]
        self.stage.light = self.palette == 1
        self.stage.accent = colors[3]
        self.draw_room(colors)
        p = self.paint
        p.begin()
        for item in self.balls:
            height = (item['y'] - BOUNDS[2]) / (BOUNDS[3] - BOUNDS[2])
            for layer in (2, 1, 0):
                p.oval(item['x'], -230, item['r'] * (1.1 + height * .6 + layer * .14),
                       1.6 + layer * 1.2, mix(colors[2], '#030A13', (1 - height) * (.15 - layer * .035)))
        for ripple in self.ripples:
            if ripple is None:
                for _ in range(2):
                    p.circle(0, 0, 0)
            else:
                x, y, started = ripple
                age = (self.time - started) / RIPPLE_SECONDS
                left, right, bottom, top = BOUNDS
                radius_limit = max(0., min(105., x - left, right - x, y - bottom, top - y) - 2)
                for layer in (0, 1):
                    p.circle(x, y, radius_limit * (.08 + age * .82 + layer * .085),
                             outline=mix(colors[2], colors[3], (1 - age) * (.6 - layer * .22)))
        for item in self.balls:
            self.draw_ball(item, colors)
        p.end()
        self.stage.hud(f"{colors[0]} · {'重力下落' if self.gravity else '自由漂浮'}  /  {self.speed:.2f}×  /  点击推开彩球")


if __name__ == '__main__':
    app = PrismBalls()
    app.stage.run(app.frame, app.reset)
