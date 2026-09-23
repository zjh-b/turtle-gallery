"""夜空烟花：升空、绽放、拖尾与水面倒影。"""
import math
import random

from 舞台 import Paint, Stage, hsv, mix

PALETTES = [("#FFC976", "#FF7B87"), ("#7ADFFF", "#AF9BFF"),
            ("#FF91CB", "#FFD7F0"), ("#A1F2C9", "#FFE8A8")]
SHAPES = ("礼花", "星环", "爱心", "金柳")


class Fireworks:
    def __init__(self):
        self.stage = Stage("把夜空点亮", "点击 发射烟花     A 自动表演     C 切换花型     F 烟花齐放", accent="#FFD391")
        self.paint = Paint(self.stage, "fireworks")
        rng = random.Random(22)
        self.stars = [(rng.uniform(-490, 490), rng.uniform(-85, 260), rng.uniform(0.6, 1.5)) for _ in range(85)]
        self.buildings = [(x, rng.randint(18, 73), rng.randint(17, 33), rng.random()) for x in range(-520, 530, 27)]
        self.particles, self.rockets, self.blooms = [], [], []
        self.time = 0
        self.timer = 0
        self.auto = True
        self.kind = 0
        self.stage.screen.onclick(self.click)
        for key in ("a", "A"):
            self.stage.screen.onkey(self.toggle_auto, key)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.next_kind, key)
        for key in ("f", "F"):
            self.stage.screen.onkey(self.finale, key)

    def finale(self):
        if not self.stage.paused:
            for i in range(5):
                self.launch(-320 + i * 160, 95 + (i % 2) * 70, i % 4)

    def reset(self):
        self.particles.clear()
        self.rockets.clear()
        self.blooms.clear()
        self.time, self.timer, self.auto, self.kind = 0, 0.7, True, 0
        for x, y, age, kind in [(-210, 90, 0.72, 0), (95, 145, 0.55, 1), (295, 30, 0.48, 2)]:
            self.burst(x, y, kind, age)

    def toggle_auto(self):
        self.auto = not self.auto

    def next_kind(self):
        self.kind = (self.kind + 1) % len(SHAPES)

    def click(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        self.launch(max(-420, min(420, x)), max(-50, min(205, y)), self.kind)

    def launch(self, x, y, kind):
        self.rockets.append(dict(x=x * 0.7, target=(x, y), age=0, kind=kind))
        self.rockets = self.rockets[-8:]

    def burst(self, x, y, kind=None, age=0):
        kind = self.kind if kind is None else kind
        colors = PALETTES[kind]
        self.blooms.append(dict(x=x, y=y, age=age, color=colors[0]))
        for i in range(84):
            a = i * math.tau / 84
            speed = random.uniform(95, 145)
            vx, vy = math.cos(a) * speed, math.sin(a) * speed
            if kind == 1:
                vx *= 1.2
                vy *= 0.65
                if i % 3 == 0:
                    vx *= 0.45
                    vy *= 0.45
            elif kind == 2:
                vx = 9 * 16 * math.sin(a) ** 3
                vy = 9 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
            elif kind == 3:
                vy = abs(vy) * 1.2
            elif i % 4 == 0:
                vx *= 0.55
                vy *= 0.55
            self.particles.append(dict(x=x, y=y, vx=vx, vy=vy, age=age, life=random.uniform(1.65, 2.5),
                                       color=colors[i % 2], gravity=75 if kind == 3 else 46, phase=a))
        self.particles = self.particles[-600:]
        self.blooms = self.blooms[-8:]

    def location(self, particle, age):
        age = max(0, age)
        travel = (1 - math.exp(-0.65 * age)) / 0.65
        return (particle["x"] + particle["vx"] * travel,
                particle["y"] + particle["vy"] * travel - particle["gravity"] * age * age / 2)

    def background(self, p):
        w, h = self.stage.view
        p.gradient("#070E24", "#24304E")
        for x, y, r in self.stars:
            p.circle(x, y, r, mix("#455270", "#D5E0FA", 0.5 + 0.35 * math.sin(self.time * 0.7 + x)))
        p.glow(355, 198, 48, "#7186B3", "#0E162D")
        p.circle(355, 198, 21, "#F6E7C4")
        p.circle(365, 204, 20, "#0E172D")
        for x, height, width, lit in self.buildings:
            p.rect(x, -153, x + width, -153 + height, "#10182C")
            if lit > 0.3:
                for dy in range(8, height - 4, 13):
                    p.rect(x + 5, -153 + dy, x + 8, -150 + dy, "#AD997D")
                    if lit > 0.6:
                        p.rect(x + 14, -153 + dy, x + 17, -150 + dy, "#607B9D")
        p.rect(-w / 2 - 2, -153, w / 2 + 2, -h / 2, "#0D1C32")
        p.line([(-w / 2, -152), (w / 2, -152)], "#48617A", 1)
        for i in range(30):
            y = -161 - i * 4.8
            x = math.sin(i * 2.1) * 440
            p.line([(x, y), (x + 35 + i % 4 * 14, y)], "#22354D")

    def frame(self, dt):
        self.time += dt
        if dt > 0:
            self.timer -= dt
            if self.auto and self.timer <= 0:
                self.launch(random.uniform(-350, 350), random.uniform(55, 190), random.randrange(4))
                self.timer = random.uniform(0.75, 1.1)
            for rocket in self.rockets[:]:
                rocket["age"] += dt
                if rocket["age"] >= 0.85:
                    self.burst(*rocket["target"], rocket["kind"])
                    self.rockets.remove(rocket)
            for particle in self.particles:
                particle["age"] += dt
            for bloom in self.blooms:
                bloom["age"] += dt
            self.particles = [p for p in self.particles if p["age"] < p["life"]]
            self.blooms = [b for b in self.blooms if b["age"] < 2.5]
        p = self.paint
        p.begin()
        self.background(p)
        for bloom in self.blooms:
            fade = max(0, 1 - bloom["age"] / 2.5)
            for i in range(15):
                y = -161 - i * 8
                width = (12 + i * 2.8) * fade
                x = bloom["x"] + math.sin(i * 1.8 + self.time * 2) * (4 + i)
                p.line([(x - width, y), (x + width, y)], mix("#0D1C32", bloom["color"], fade * (0.35 - i * 0.015)), 2)
            if bloom["age"] < 0.3:
                p.glow(bloom["x"], bloom["y"], 38 * (1 - bloom["age"] / 0.3), bloom["color"], "#10182D", 5)
        for rocket in self.rockets:
            t = min(1, rocket["age"] / 0.85)
            x = rocket["x"] + (rocket["target"][0] - rocket["x"]) * t
            y = -150 + (rocket["target"][1] + 150) * (1 - (1 - t) ** 1.5)
            p.line([(x - 5, y - 42), (x - 2, y - 17), (x, y)], "#786256", 3, True)
            p.line([(x - 2, y - 18), (x, y)], "#FFDFA0", 2)
            p.circle(x, y, 2, "#FFF5DB")
        for particle in self.particles:
            age = particle["age"]
            x, y = self.location(particle, age)
            if y <= -148:
                continue
            fade = min(1, max(0, (particle["life"] - age) / 0.8))
            for j in (3, 2, 1):
                a = self.location(particle, age - 0.065 * j)
                b = self.location(particle, age - 0.065 * (j - 1))
                color = mix("#14213A", particle["color"], fade * (1 - j * 0.22))
                p.line([a, b], color, 2 if j == 1 else 1)
            x, y = self.location(particle, age)
            if y > -150:
                p.circle(x, y, 1.5, mix("#14213A", "#FFF4DF", fade))
        p.end()
        self.stage.hud(f"花型：{SHAPES[self.kind]}   ·   自动表演{'开启' if self.auto else '关闭'}   ·   为夜空添一束光")


if __name__ == "__main__":
    app = Fireworks()
    app.stage.run(app.frame, app.reset)
