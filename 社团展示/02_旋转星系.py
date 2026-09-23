"""有立体明暗、星环、卫星和小行星带的微型星系。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar

# 轨道半径、星球半径、颜色、公转速度、起始角度、名称。
PLANETS = [(88, 9, "#D8A573", 0.65, 0.8, "水星"),
           (153, 18, "#67B7E6", 0.42, 2.8, "地球"),
           (225, 14, "#D9806F", 0.31, 4.5, "火星"),
           (320, 28, "#DAB98B", 0.21, 5.9, "土星"),
           (419, 23, "#75CFD2", 0.14, 2.2, "海王星")]


class Galaxy:
    def __init__(self):
        self.stage = Stage("口袋里的宇宙", "点击星球 查看介绍     ↑↓ 调速     O 显示 / 隐藏轨道", accent="#AFBFFC")
        self.paint = Paint(self.stage, "galaxy")
        rng = random.Random(41)
        self.stars = [(rng.uniform(-520, 520), rng.uniform(-300, 275), rng.uniform(0.5, 1.6),
                       rng.random() * 6) for _ in range(190)]
        self.asteroids = [(rng.uniform(261, 284), rng.random() * math.tau, rng.uniform(0.7, 1.7)) for _ in range(90)]
        self.time, self.speed = 0, 1
        self.selected = None
        self.show_orbits = True
        self.stage.screen.onclick(self.select)
        for key in ("o", "O"):
            self.stage.screen.onkey(self.toggle_orbits, key)
        self.stage.screen.onkey(lambda: self.change_speed(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-0.25), "Down")

    def reset(self):
        self.time, self.speed = 0, 1
        self.selected = None
        self.show_orbits = True

    def toggle_orbits(self):
        self.show_orbits = not self.show_orbits

    def select(self, x, y):
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        hits = []
        for i, (orbit, radius, color, speed, phase, name) in enumerate(PLANETS):
            px, py = self.orbit(orbit, self.time * speed + phase)
            distance = math.hypot(x - px, y - py)
            if distance <= radius + 14:
                hits.append((distance, i))
        self.selected = min(hits)[1] if hits else None

    def change_speed(self, amount):
        self.speed = min(4, max(0.25, self.speed + amount))

    def orbit(self, radius, angle):
        x, y = math.cos(angle) * radius, math.sin(angle) * radius * 0.51
        tilt = 0.15
        return x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt) - 5

    def sphere(self, p, x, y, r, color):
        p.circle(x + 2, y - 3, r + 3, "#0B1021")
        for j in range(16):
            t = j / 16
            p.circle(x - r * 0.25 * t, y + r * 0.23 * t, r * (1 - t * 0.78),
                     mix(mix(color, "#111629", 0.72), mix(color, "#F5F1D7", 0.32), t))
        p.circle(x - r * 0.35, y + r * 0.38, max(1, r * 0.1), mix(color, "#FFFFFF", 0.55))

    def ring(self, p, x, y, r, front):
        start = math.pi if front else 0
        for factor, color, width in [(1.85, "#96889C", 3), (1.64, "#E1D1B2", 3), (1.45, "#BAA8A5", 2)]:
            points = []
            for i in range(36):
                angle = start + i * math.pi / 35
                xx, yy = math.cos(angle) * r * factor, math.sin(angle) * r * 0.48
                points.append((x + xx * 0.96 - yy * 0.28, y + xx * 0.28 + yy * 0.96))
            p.line(points, color, width, True)

    def draw_planet(self, p, data):
        y, x, i, radius, color, name = data
        if i == 3:
            self.ring(p, x, y, radius, False)
        self.sphere(p, x, y, radius, color)
        if i == 1:
            # 几块不规则陆地让蓝色行星具有辨识度。
            for shape in [[(-0.6, 0.42), (-0.1, 0.55), (0.1, 0.22), (-0.17, -0.05), (-0.42, 0.07)],
                          [(0.02, -0.03), (0.35, -0.17), (0.14, -0.63), (-0.06, -0.4)]]:
                p.poly([(x + a * radius, y + b * radius) for a, b in shape], "#A0CBAE", smooth=True)
            moon_angle = self.time * 1.7
            mx, my = x + math.cos(moon_angle) * 34, y + math.sin(moon_angle) * 22
            p.oval(x, y, 34, 22, outline="#304258")
            self.sphere(p, mx, my, 4, "#D2D7E5")
        if i == 3:
            for offset in (-0.35, 0, 0.32):
                half = radius * math.sqrt(1 - offset * offset) * 0.8
                p.line([(x - half, y + radius * offset), (x, y + radius * offset - 2),
                        (x + half, y + radius * offset)], "#B19983", 2, True)
            self.ring(p, x, y, radius, True)
        if i == 4:
            p.line([(x - 14, y - 4), (x, y - 6), (x + 13, y - 4)], "#76B5BD", 2, True)
        p.line([(x + radius * 0.7, y - radius * 0.7), (x + radius + 12, y - radius - 10),
                (x + radius + 36, y - radius - 10)], "#526078")
        p.text(x + radius + 15, y - radius - 21, name, "#C0C9DE", 9, "w")
        if self.selected == i:
            p.circle(x, y, radius + 7, outline="#D0DFFF", width=1.5)

    def frame(self, dt):
        self.time += dt * self.speed
        p = self.paint
        p.begin()
        p.gradient("#080D21", "#13172F")
        for x, y, r, phase in self.stars:
            color = mix("#4A536F", "#EAF0FF", 0.45 + 0.4 * math.sin(self.time * 0.35 + phase))
            p.circle(x, y, r, color)
            if r > 1.5:
                p.line([(x - 3, y), (x + 3, y)], "#536380")
                p.line([(x, y - 3), (x, y + 3)], "#536380")
        p.glow(0, -5, 85 + 3 * math.sin(self.time), "#ED8C47", "#10142A", 13)
        if self.show_orbits:
            for radius, _, _, _, _, _ in PLANETS:
                points = [self.orbit(radius, i * math.tau / 120) for i in range(121)]
                p.line(points, "#2D3550")
        for radius, angle, size in self.asteroids:
            x, y = self.orbit(radius, angle + self.time * 0.1)
            p.circle(x, y, size, "#5B5771")
        positions = []
        for i, (orbit, radius, color, speed, phase, name) in enumerate(PLANETS):
            x, y = self.orbit(orbit, self.time * speed + phase)
            positions.append((y, x, i, radius, color, name))
        for data in sorted(positions, reverse=True):
            if data[0] > -5:
                self.draw_planet(p, data)
        for i in range(24):
            a = i * math.tau / 24 + self.time * 0.035
            inner, outer = 41, 48 + 4 * math.sin(i * 2 + self.time)
            p.line([polar(inner, a, 0, -5), polar(outer, a, 0, -5)], "#A06641", 2)
        for i in range(18):
            t = i / 18
            p.circle(-5 * t, -5 + 6 * t, 37 * (1 - 0.78 * t), mix("#EE8E42", "#FFF1B5", t))
        for data in sorted(positions, reverse=True):
            if data[0] <= -5:
                self.draw_planet(p, data)
        descriptions = ["水星：这幅作品里公转最快的行星", "地球：蓝色海洋、绿色陆地与一颗绕行的月亮",
                        "火星：暖红色球面，与蓝色行星形成对比", "土星：星环分前后两层，表现遮挡关系",
                        "海王星：位于最外侧的青蓝色行星"]
        p.text(-445, -261, descriptions[self.selected] if self.selected is not None else "微型星系  /  ORBITAL STUDY",
               "#C4D0E6" if self.selected is not None else "#6F819F", 10, "w")
        p.text(447, -261, f"公转速度  × {self.speed:.2f}", "#A7B8DE", 10, "e")
        p.end()
        self.stage.hud("点击一颗星球，观察它的造型   ·   大小、轨道与速度为艺术化示意")


if __name__ == "__main__":
    app = Galaxy()
    app.stage.run(app.frame, app.reset)
