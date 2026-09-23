"""代码绘制的层叠山水：昼夜渐变、倒影、归鸟与行舟。"""
import math
import random

from 舞台 import Paint, Stage, mix


class Landscape:
    def __init__(self):
        self.stage = Stage("山水有回声", "D 切换昼夜    点击湖面 添一叶小舟    ↑↓ 调整风速",
                           "#E8E8D9", "#668D84", light=True)
        self.paint = Paint(self.stage, "landscape")
        rng = random.Random(82)
        self.stars = [(rng.uniform(-480, 480), rng.uniform(40, 260), rng.uniform(0.8, 1.6)) for _ in range(60)]
        self.mountains = []
        for layer in range(3):
            peaks = [(rng.uniform(-590, 590), rng.uniform(50, 170), rng.uniform(25, 75)) for _ in range(10)]
            profile = []
            for x in range(-680, 681, 14):
                height = max(height * math.exp(-((x - center) / width) ** 2) for center, height, width in peaks)
                profile.append((x, -28 - layer * 29 + height + math.sin(x * 0.03) * 5))
            self.mountains.append(profile)
        self.time, self.night, self.night_target, self.wind = 0, 0, 0, 1
        self.boats = []
        self.stage.screen.onclick(self.add_boat)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.toggle_day, key)
        self.stage.screen.onkey(lambda: self.change_wind(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_wind(-0.25), "Down")

    def reset(self):
        self.time, self.night, self.night_target, self.wind = 0, 0, 0, 1
        self.boats = [[-65, -160, 0.85, 1], [255, -226, 1.15, -1]]

    def toggle_day(self):
        self.night_target = 1 - self.night_target

    def change_wind(self, amount):
        self.wind = max(0.25, min(2.5, self.wind + amount))

    def add_boat(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if -275 < y < -115 and abs(x) < 450:
            self.boats.append([x, y, 0.65 + (-y - 115) / 200, random.choice((-1, 1))])
            self.boats = self.boats[-5:]

    def boat(self, p, x, y, scale, direction):
        def pt(a, b):
            return x + a * scale * direction, y + b * scale
        wood = mix("#495F59", "#89939D", self.night)
        sail = mix("#F3EACB", "#A8B9C5", self.night)
        for i in range(6):
            yy = y - 10 - i * 4
            p.line([(x - (25 - i * 2) * scale, yy), (x + (25 - i * 2) * scale, yy)],
                   mix("#A1C0B8", "#344C68", self.night), 1)
        p.poly([pt(-35, 0), pt(36, 0), pt(23, -9), pt(-22, -9)], wood, smooth=True)
        p.line([pt(0, -1), pt(0, 63)], wood, 2)
        p.poly([pt(2, 59), pt(29, 16), pt(2, 12)], sail, wood, 1, True)
        p.poly([pt(-2, 52), pt(-24, 16), pt(-2, 14)], mix(sail, wood, 0.15), wood, 1, True)
        p.line([pt(2, 28), pt(22, 28)], mix(sail, wood, 0.35))
        p.circle(*pt(-15, 7), 2.7 * scale, wood)
        p.line([pt(-15, 5), pt(-15, -1)], wood, 3)

    def pavilion(self, p):
        color = mix("#486E64", "#223E50", self.night)
        p.poly([(-520, -155), (-460, -110), (-380, -119), (-290, -141), (-239, -173), (-520, -204)], color, smooth=True)
        for x, y, height in [(-401, -123, 74), (-433, -119, 59)]:
            p.line([(x, y), (x + 4, y + height)], color, 6)
            for j in range(4):
                yy = y + height * (0.4 + j * 0.17)
                p.line([(x + 3, yy), (x - 25 + j * 4, yy + 8)], color, 3)
                p.oval(x - 9, yy + 7, 25 - j * 3, 5, color)
        p.rect(-341, -135, -305, -91, color)
        p.rect(-335, -128, -312, -98, mix("#D0D8BC", "#6B7880", self.night))
        p.poly([(-354, -97), (-323, -75), (-292, -97), (-307, -93), (-338, -93)], color, smooth=True)
        p.line([(-350, -137), (-296, -137)], color, 3)

    def frame(self, dt):
        self.time += dt * self.wind
        self.night += max(-dt * 0.42, min(dt * 0.42, self.night_target - self.night))
        self.stage.light = self.night < 0.5
        self.stage.accent = mix("#668D84", "#B1C8D9", self.night)
        for boat in self.boats:
            boat[0] += boat[3] * dt * 9 * self.wind
            if abs(boat[0]) > 510:
                boat[0] = -math.copysign(505, boat[0])
        sky = mix("#E8E7D9", "#172C47", self.night)
        water = mix("#BCD3C6", "#25465E", self.night)
        p = self.paint
        p.begin()
        p.gradient(sky, water)
        for x, y, radius in self.stars:
            if self.night > 0.1:
                p.circle(x, y, radius, mix(sky, "#DAE5DF", self.night * 0.85))
        p.circle(-239, 182, 35, mix("#DDAF81", "#E9E6CC", self.night))
        if self.night > 0:
            p.circle(-226, 190, 33, mix("#DDAF81", sky, self.night))
        for i, y in enumerate((199, 224, 154)):
            x = ((i * 235 + self.time * 5) % 1150) - 550
            p.oval(x, y, 78, 7, mix(sky, "#EDF0E4", 0.22 * (1 - self.night)))
        mountain_colors = [mix("#9FBEB3", "#31465E", self.night), mix("#729F94", "#27485A", self.night),
                           mix("#517F77", "#1C3A4B", self.night)]
        for profile, color in zip(self.mountains, mountain_colors):
            p.poly([(-680, -109)] + profile + [(680, -109)], color, smooth=True)
        p.rect(-self.stage.view[0] / 2, -104, self.stage.view[0] / 2, -310, water)
        for profile, color in zip(self.mountains, mountain_colors):
            reflection = [(x, -104 - (y + 104) * 0.55) for x, y in profile]
            p.poly([(-680, -104)] + reflection + [(680, -104)], mix(water, color, 0.30), smooth=True)
        for i in range(30):
            y = -113 - i * 6
            x = math.sin(i * 2.15 + self.time * 0.08) * 415
            p.line([(x, y), (x + 25 + i % 5 * 20, y)], mix(water, sky, 0.4), 1)
        self.pavilion(p)
        for i in range(5):
            x = (self.time * 19 + i * 24 + 30) % 1040 - 520
            y = 113 + i * 7 + math.sin(self.time * 0.45) * 7
            wing = math.sin(self.time * 3 + i * 0.6) * 5
            p.line([(x - 8, y + wing), (x, y), (x + 8, y + wing)], mix("#506A63", "#9AB0BE", self.night), 1.5, True)
        for x, y, scale, direction in sorted(self.boats, key=lambda b: -b[1]):
            self.boat(p, x, y + math.sin(self.time * 1.3 + x) * 1.4, scale, direction)
        p.text(391, 191, "远山", mix("#55796F", "#B8C7CB", self.night), 25, bold=True)
        p.text(391, 150, "近水", mix("#55796F", "#B8C7CB", self.night), 25, bold=True)
        p.rect(382, 119, 400, 100, "#AD675C")
        p.text(391, 110, "闲", "#F3E8D3", 9)
        p.end()
        self.stage.hud(("月色" if self.night_target else "晴昼") + f"   ·   风速 × {self.wind:.2f}   ·   一叶小舟，慢慢经过")


if __name__ == "__main__":
    app = Landscape()
    app.stage.run(app.frame, app.reset)
