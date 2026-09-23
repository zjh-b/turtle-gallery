"""清浅荷塘：带花纹和鱼鳍的锦鲤会追逐食物，点击产生水波。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar

KOI_COLORS = [("#F8F0D8", "#E5754C"), ("#F4E9D1", "#C9553E"),
              ("#ECA966", "#F8E9C6"), ("#E8E9DD", "#525E5C")]


class Pond:
    def __init__(self):
        self.stage = Stage("清浅荷塘", "点击水面 投喂锦鲤     F 添加锦鲤（最多 14 条）",
                           "#B9D8CE", "#548A73", light=True)
        self.paint = Paint(self.stage, "pond")
        self.fish, self.food, self.ripples = [], [], []
        self.time = 0
        self.stage.screen.onclick(self.feed)
        for key in ("f", "F"):
            self.stage.screen.onkey(self.add_fish, key)

    def add_fish(self):
        if len(self.fish) < 14 and not self.stage.paused:
            self.fish.append(dict(x=random.uniform(-265, 265), y=random.uniform(-170, 165),
                                  angle=random.random() * math.tau, size=random.uniform(29, 43),
                                  colors=random.choice(KOI_COLORS), phase=random.random() * math.tau))

    def reset(self):
        self.fish.clear()
        self.food.clear()
        self.ripples.clear()
        self.time = 0
        for _ in range(7):
            self.add_fish()

    def feed(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not -275 < y < 260:
            return
        x, y = max(-425, min(425, x)), max(-240, min(225, y))
        for _ in range(6):
            self.food.append([x + random.uniform(-15, 15), y + random.uniform(-15, 15), 10])
        self.food = self.food[-60:]
        self.ripples.append([x, y, 0])
        self.ripples = self.ripples[-12:]

    def lily(self, p, x, y, r, angle):
        p.oval(x + 5, y - 6, r, r * 0.7, "#98BCAE")
        # 荷叶缺口由扇形轮廓自然形成。
        points = [(x, y)] + [(x + r * math.cos(a), y + r * 0.73 * math.sin(a))
                             for a in [angle + 0.2 + i * (math.tau - 0.45) / 48 for i in range(49)]]
        p.poly(points, "#729E7D", "#5C8A70")
        for i in range(9):
            a = angle + 0.4 + i * (math.tau - 0.7) / 8
            p.line([(x, y), (x + r * 0.55 * math.cos(a), y + r * 0.4 * math.sin(a)),
                    (x + r * 0.91 * math.cos(a), y + r * 0.66 * math.sin(a))], "#8AB38D", 1, True)
        p.oval(x, y, 3, 2, "#B4CAA0")

    def flower(self, p, x, y):
        p.oval(x + 4, y - 4, 31, 20, "#7FAD99")
        for layer, radius, fill, outline in [(0, 31, "#EAB2B7", "#C78D9E"), (1, 22, "#F5D3D3", "#DEA7B8")]:
            for i in range(9):
                a = i * math.tau / 9 + layer * 0.32
                p.poly([polar(2, a, x, y), polar(radius * 0.72, a - 0.45, x, y),
                        polar(radius, a, x, y), polar(radius * 0.72, a + 0.45, x, y)],
                       fill, outline, smooth=True)
        p.circle(x, y, 7, "#E9C878")
        for i in range(7):
            p.circle(*polar(4, i * math.tau / 7, x, y), 1, "#FFF1B1")

    def draw_fish(self, p, fish):
        x, y, a, size = fish["x"], fish["y"], fish["angle"], fish["size"]
        c, s = math.cos(a), math.sin(a)
        wag = math.sin(self.time * 5.5 + fish["phase"]) * 0.16
        base, patch = fish["colors"]

        def point(px, py, shadow=False):
            py += wag * max(0, -px) ** 1.5
            return (x + size * (px * c - py * s) + (5 if shadow else 0),
                    y + size * (px * s + py * c) - (7 if shadow else 0))

        def shape(coords, fill, outline="", shadow=False):
            p.poly([point(px, py, shadow) for px, py in coords], fill, outline, 1, True)

        body = [(1, 0), (0.74, 0.3), (0.18, 0.37), (-0.5, 0.25), (-1, 0.06),
                (-1, -0.06), (-0.5, -0.25), (0.18, -0.37), (0.74, -0.3)]
        tail = [(-0.85, 0), (-1.15, 0.17), (-1.62, 0.48), (-1.4, 0),
                (-1.62, -0.48), (-1.15, -0.17)]
        shape(body, "#89B2A4", shadow=True)
        shape(tail, mix(base, "#B4CEB7", 0.3), "#95AF99")
        for side in (-1, 1):
            fin = [(0.44, side * 0.22), (0.13, side * 0.6), (-0.27, side * 0.69), (-0.02, side * 0.26)]
            shape(fin, mix(base, "#B7D5BD", 0.3), "#95AF99")
            p.line([point(0.3, side * 0.24), point(-0.12, side * 0.56)], "#A7B59C")
        shape(body, base, mix(base, "#586D62", 0.45))
        for coords in [[(0.72, 0.22), (0.32, 0.34), (0.16, 0.07), (0.46, -0.04), (0.78, 0.03)],
                       [(-0.05, -0.28), (-0.35, -0.23), (-0.53, 0.03), (-0.21, 0.22), (0.1, 0.12)],
                       [(-0.67, 0.16), (-0.88, 0.04), (-0.72, -0.13), (-0.48, -0.06)]]:
            shape(coords, patch)
        p.line([point(0.65, 0.17), point(0.2, 0.23), point(-0.34, 0.12)],
               mix(base, "#FFFFFF", 0.6), 2, True)
        p.line([point(-0.05, 0), point(-0.42, 0.03), point(-0.7, 0)],
               mix(patch, "#718F78", 0.4), 1, True)
        for side in (-1, 1):
            ex, ey = point(0.73, side * 0.17)
            p.circle(ex, ey, 2.2, "#3E4640")
            p.circle(ex - 0.5, ey + 0.5, 0.65, "#FFFFFF")
        p.line([point(0.9, -0.08), point(0.95, 0), point(0.9, 0.08)], "#B8AB8D", 1, True)

    def update(self, dt):
        self.time += dt
        for food in self.food:
            food[2] -= dt
        self.food = [f for f in self.food if f[2] > 0]
        for ripple in self.ripples:
            ripple[2] += dt
        self.ripples = [r for r in self.ripples if r[2] < 2.2]
        positions = [(other["x"], other["y"]) for other in self.fish]
        for index, fish in enumerate(self.fish):
            if self.food:
                target = min(self.food, key=lambda f: math.hypot(f[0] - fish["x"], f[1] - fish["y"]))
                tx, ty = target[:2]
                if math.hypot(tx - fish["x"], ty - fish["y"]) < 22:
                    self.food.remove(target)
                    self.ripples.append([tx, ty, 0.8])
            else:
                tx = math.sin(self.time * 0.19 + fish["phase"]) * 305
                ty = math.cos(self.time * 0.23 + fish["phase"] * 2) * 175
            steer_x, steer_y = tx - fish["x"], ty - fish["y"]
            for j, (ox, oy) in enumerate(positions):
                if index == j:
                    continue
                dx, dy = fish["x"] - ox, fish["y"] - oy
                distance = math.hypot(dx, dy)
                if 0.01 < distance < 55:
                    strength = (55 - distance) * 2.2 / distance
                    steer_x += dx * strength
                    steer_y += dy * strength
            desired = math.atan2(steer_y, steer_x)
            turn = (desired - fish["angle"] + math.pi) % math.tau - math.pi
            fish["angle"] += max(-dt * 2, min(dt * 2, turn))
            speed = 78 if self.food else 31
            fish["x"] = max(-435, min(435, fish["x"] + math.cos(fish["angle"]) * speed * dt))
            fish["y"] = max(-230, min(220, fish["y"] + math.sin(fish["angle"]) * speed * dt))
        self.ripples = self.ripples[-20:]

    def frame(self, dt):
        if dt > 0:
            self.update(dt)
        p = self.paint
        p.begin()
        p.gradient("#CAE0D4", "#9FCABD")
        for row in range(7):
            points = [(x, -240 + row * 74 + math.sin(x * 0.014 + self.time * 0.22 + row) * 11) for x in range(-530, 550, 30)]
            p.line(points, "#BDD9CB", 1, True)
        for x, y, r in [(-418, -222, 49), (-368, -250, 35), (415, 177, 40)]:
            p.oval(x, y, r, r * 0.55, "#96BEAC")
            p.oval(x - 6, y + 5, r * 0.75, r * 0.32, "#A7C6B2")
        for fish in sorted(self.fish, key=lambda f: f["size"]):
            self.draw_fish(p, fish)
        for x, y, life in self.food:
            p.circle(x + 1, y - 2, 2.5, "#819F89")
            p.circle(x, y, 2.2, "#AC7548")
            p.circle(x - 0.5, y + 0.5, 0.7, "#F4D39A")
        for x, y, age in self.ripples:
            for offset in (0, 10, 20):
                radius = age * 32 + offset
                p.oval(x, y, radius, radius * 0.72, outline=mix("#E9F1DC", "#ADD0C2", min(1, age / 2.2)))
        for args in [(-376, 174, 70, -0.6), (-307, 217, 43, 1.4), (-430, 115, 39, 0.8),
                     (380, -201, 61, 2.5), (431, -142, 36, 1)]:
            self.lily(p, *args)
        self.flower(p, -350, 191)
        self.flower(p, 397, -187)
        p.text(430, 216, "荷 风  ·  鱼 趣", "#537D6C", 13, "e")
        p.text(-445, -275, "一池清水，一点闲趣。", "#598672", 10, "w")
        p.end()
        self.stage.hud(f"锦鲤 {len(self.fish)} 尾   ·   点一点水面，等它们慢慢游来")


if __name__ == "__main__":
    app = Pond()
    app.stage.run(app.frame, app.reset)
