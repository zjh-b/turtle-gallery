"""以星云、日冕、受光球面和分层星环构成的微型轨道图鉴。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar

# 大小和轨道为艺术化示意；保留清楚的轮廓与足够的点击空间。
PLANETS = [(88, 10, "#D5A376", 0.65, 0.8, "水星"),
           (153, 20, "#559CDC", 0.42, 2.8, "地球"),
           (225, 16, "#E09473", 0.31, 4.5, "火星"),
           (320, 29, "#DDBD8F", 0.21, 5.9, "土星"),
           (419, 25, "#70CFDE", 0.14, 2.2, "海王星")]


class Galaxy:
    def __init__(self):
        self.stage = Stage("口袋里的宇宙", "点击星球 查看介绍     ↑↓ 调速     O 显示 / 隐藏轨道", accent="#AFBFFC")
        self.paint = Paint(self.stage, "galaxy")
        # Render-only caches stay with the painter, separate from scene state.
        self.paint.backdrop = Paint(self.stage, "galaxy-backdrop")
        self.paint.backdrop_signature = None
        self.paint.depth_order = None
        rng = random.Random(41)
        self.stars = [(rng.uniform(-510, 510), rng.uniform(-240, 257),
                       rng.uniform(0.35, 1.2), rng.random() * math.tau)
                      for _ in range(145)]
        # 固定的星尘池沿背景星云分布，不逐帧生成随机图形。
        self.dust = []
        for _ in range(260):
            x = rng.uniform(-520, 520)
            y = 125 * math.sin(x / 290) + rng.gauss(25, 36)
            if -233 < y < 253:
                self.dust.append((x, y, rng.uniform(0.3, 0.85),
                                  mix("#28334C", "#8197BA", rng.random() * 0.46)))
        self.bright_stars = [(-440, 170, 4.3), (-338, -154, 3.4),
                             (-172, 231, 3.1), (338, 210, 4.6),
                             (454, -102, 3.4), (189, -208, 3.3)]
        self.asteroids = [(rng.uniform(263, 282), rng.random() * math.tau,
                           rng.uniform(0.55, 1.35), mix("#344058", "#ABACBD", rng.random() * 0.5))
                          for _ in range(105)]
        self.nebula = self.make_nebula()
        colors = [planet[2] for planet in PLANETS] + ["#CBD2E3"]
        self.shades = {color: tuple(mix(mix(color, "#070D19", 0.78),
                                       mix(color, "#EEF8EB", 0.48), j / 24)
                                    for j in range(25)) for color in colors}
        self.ring_colors = tuple(mix("#6A6677", "#EBDFC3", value)
                                 for value in (0.35, 0.6, 0.88, 0.42, 0.04, 0.64, 0.9, 0.64, 0.22))
        self.trail_colors = [tuple(mix("#1A263D", planet[2], 0.12 + part * 0.035)
                                   for part in range(12)) for planet in PLANETS]
        self.sun_colors = tuple(mix("#ED7B38", "#FFF4C2", i / 31) for i in range(32))
        self.orbit_paths = [tuple(self.orbit(planet[0], j * math.tau / 150) for j in range(151))
                            for planet in PLANETS]
        self.time, self.speed = 0, 1
        self.selected = None
        self.show_orbits = True
        self.stage.screen.onclick(self.select)
        for key in ("o", "O"):
            self.stage.screen.onkey(self.toggle_orbits, key)
        self.stage.screen.onkey(lambda: self.change_speed(0.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-0.25), "Down")

    @staticmethod
    def make_nebula():
        """Low contrast, nested ribbons make haze without bitmap assets."""
        ribbons = []
        for branch in range(2):
            for layer in range(18):
                amount = layer / 17
                width = (78 if branch == 0 else 38) * (1 - amount * 0.86)
                upper, lower = [], []
                for i in range(45):
                    x = -550 + i * 25
                    center = 125 * math.sin(x / 290) + 25 + branch * 32
                    taper = 0.45 + 0.45 * math.sin(i / 44 * math.pi)
                    ripple = 6 * math.sin(x / 67 + branch)
                    upper.append((x, center + width * taper + ripple))
                    lower.append((x, center - width * taper + ripple))
                color = mix("#0B1327", "#192640" if branch == 0 else "#272340", amount * 0.52)
                ribbons.append((upper + list(reversed(lower)), color))
        return ribbons

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
        distance = max(1, math.hypot(x, y + 5))
        lx, ly = -x / distance, (-5 - y) / distance
        p.circle(x, y, r + 2, "#090F20")
        p.circle(x, y, r + 1, outline=mix(color, "#142037", 0.52))
        for j, shade in enumerate(self.shades[color]):
            t = j / 24
            p.circle(x + lx * r * 0.32 * t, y + ly * r * 0.32 * t,
                     r * (1 - t * 0.79), shade)
        angle = math.atan2(ly, lx)
        p.line([polar(r * 0.95, angle - 0.77 + k * 1.54 / 22, x, y)
                for k in range(23)], mix(color, "#E4F5FF", 0.3), 1.1, True)

    def ring(self, p, x, y, r, front):
        start = math.pi if front else 0
        for band, color in enumerate(self.ring_colors):
            factor = 1.42 + band * 0.067
            if not front:
                color = mix(color, "#101829", 0.38)
            points = []
            for i in range(48):
                angle = start + i * math.pi / 47
                xx, yy = math.cos(angle) * r * factor, math.sin(angle) * r * factor * 0.24
                points.append((x + xx * 0.96 - yy * 0.28, y + xx * 0.28 + yy * 0.96))
            p.line(points, color, 1.3, True)

    def draw_planet(self, p, data):
        y, x, i, radius, color, name = data
        if i == 3:
            self.ring(p, x, y, radius, False)
        self.sphere(p, x, y, radius, color)
        if i == 0:
            for dx, dy, size in [(-0.3, -0.15, 0.15), (0.27, 0.25, 0.1), (0.16, -0.45, 0.12)]:
                p.circle(x + dx * radius, y + dy * radius, radius * size, "#88705E", "#B39676")
        elif i == 1:
            for shape in [[(-0.67, 0.38), (-0.36, 0.67), (-0.12, 0.53), (0.12, 0.22),
                           (-0.12, 0.13), (-0.17, -0.12), (-0.43, 0.06)],
                          [(0.01, -0.06), (0.29, -0.05), (0.42, -0.28),
                           (0.19, -0.63), (-0.02, -0.43)]]:
                p.poly([(x + a * radius, y + b * radius) for a, b in shape], "#8AB49D", smooth=True)
            for offset in (0.43, -0.32):
                p.line([(x - radius * 0.65, y + radius * offset),
                        (x - radius * 0.2, y + radius * (offset + 0.13)),
                        (x + radius * 0.52, y + radius * (offset - 0.04))], "#B7D2DD", 1.1, True)
            moon_angle = self.time * 1.7
            mx, my = x + math.cos(moon_angle) * 35, y + math.sin(moon_angle) * 24
            p.oval(x, y, 35, 24, outline="#26364B")
            self.sphere(p, mx, my, 4, "#CBD2E3")
        elif i == 2:
            p.poly([(x - radius * 0.6, y + radius * 0.18), (x - 3, y + 6),
                    (x + radius * 0.64, y + 2), (x + 4, y - 5), (x - 6, y - 3)],
                   "#A56858", smooth=True)
            p.oval(x - 2, y + radius * 0.7, radius * 0.32, radius * 0.09, "#ECD0AA")
        elif i == 3:
            for band, offset in enumerate((-0.58, -0.28, 0.02, 0.32, 0.57)):
                half = radius * math.sqrt(1 - offset * offset) * 0.8
                p.line([(x - half, y + radius * offset), (x, y + radius * offset - 2),
                        (x + half, y + radius * offset)],
                       "#9C8876" if band % 2 else "#CBB494", 1.4, True)
            self.ring(p, x, y, radius, True)
        else:
            for offset, shade in ((-0.4, "#4C899F"), (0.09, "#79BECB"), (0.45, "#91CAD2")):
                p.line([(x - radius * 0.68, y + radius * offset),
                        (x, y + radius * (offset - 0.08)),
                        (x + radius * 0.64, y + radius * offset)], shade, 1.5, True)
            p.oval(x + 7, y - 8, 4, 1.6, "#426E8D")

    def draw_sun(self, p):
        for i in range(32):
            angle = i * math.tau / 32 + self.time * 0.025
            reach = 57 + 8 * math.sin(i * 2.17 + self.time * 0.55)
            points = [polar(42 + t * (reach - 42), angle + 0.13 * math.sin(t * math.pi), 0, -5)
                      for t in (0, 0.25, 0.5, 0.75, 1)]
            p.line(points, "#6B4333", 2.2, True)
            p.line(points[:3], "#B77945", 1.1, True)
        for i in range(32):
            t = i / 31
            p.circle(-7 * t, -5 + 8 * t, 42 * (1 - 0.8 * t), self.sun_colors[i])
        for i in range(12):
            angle = i * math.tau / 12 + self.time * 0.04
            radius = 29 + 5 * math.sin(i * 1.91)
            p.line([polar(radius, angle + j * 0.045, 0, -5) for j in range(6)],
                   "#F5BA69", 1, True)

    def labels(self, p, positions):
        for y, x, i, radius, color, name in positions:
            selected = self.selected == i
            # Inner labels point away from the Sun; near a window edge, only
            # their horizontal direction turns inward. Leave space for text.
            direction = 1 if x >= 0 else -1
            if abs(x) > 330:
                direction *= -1
            vertical = 1 if y >= -5 else -1
            label_y = max(-211, min(216, y + vertical * (radius + 17)))
            start_x = x + direction * radius * 0.7
            end_x = x + direction * (radius + 32)
            p.line([(start_x, y + vertical * radius * 0.6),
                    (end_x - direction * 16, label_y), (end_x, label_y)],
                   "#899BBC" if selected else "#45546D", 1)
            p.text(end_x, label_y + vertical * 12, name, "#EFF6FF" if selected else "#ADBED4",
                   10, "e" if direction < 0 else "w", selected)
            selection_radius = radius * (2.06 if i == 3 else 1) + 8
            p.circle(x, y, selection_radius + 4, outline="#344D73" if selected else "")
            p.circle(x, y, selection_radius, outline="#B8DFF4" if selected else "", width=1.3)
            p.poly([(x, y + selection_radius + 2), (x - 3, y + selection_radius + 7),
                    (x + 3, y + selection_radius + 7)], "#D6EEFF" if selected else "")

    def draw_backdrop(self):
        signature = (self.stage.width, self.stage.height, self.stage.scale)
        if self.paint.backdrop_signature == signature:
            return
        p = self.paint.backdrop
        p.begin()
        p.gradient("#070D1C", "#0B1226")
        for points, color in self.nebula:
            p.poly(points, color, smooth=True)
        for x, y, r, color in self.dust:
            p.circle(x, y, r, color)
        for x, y, radius in self.bright_stars:
            p.circle(x, y, radius, "#18263D")
            p.line([(x - radius * 1.4, y), (x + radius * 1.4, y)], "#59758F")
            p.line([(x, y - radius), (x, y + radius)], "#59758F")
            p.circle(x, y, 1.1, "#C6DFE9")
        p.end()
        self.paint.backdrop_signature = signature

    def frame(self, dt):
        self.time += dt * self.speed
        self.draw_backdrop()
        p = self.paint
        p.begin()
        for x, y, r, phase in self.stars:
            color = mix("#364764", "#D6E5F2", 0.32 + 0.27 * math.sin(self.time * 0.28 + phase))
            p.circle(x, y, r, color)
        p.glow(0, -5, 113 + 2 * math.sin(self.time * 0.7), "#D88844", "#11192A", 28)
        # Fixed slots preserve Canvas objects when the orbit switch changes.
        for i, (radius, _, color, speed, phase, _) in enumerate(PLANETS):
            orbit_color = "#4A5C7D" if self.selected == i else "#29364F"
            p.line(self.orbit_paths[i], orbit_color if self.show_orbits else "", 1)
            angle = self.time * speed + phase
            for part in range(12):
                a = angle - 0.75 + part * 0.75 / 12
                trail = [self.orbit(radius, a + j * 0.75 / 12 / 4) for j in range(5)]
                p.line(trail, self.trail_colors[i][part], 1.5)
        for radius, angle, size, color in self.asteroids:
            x, y = self.orbit(radius, angle + self.time * 0.075)
            p.circle(x, y, size, color)
        positions, planet_items = [], []
        # Draw in a fixed order for the item pool, then raise only the visible
        # foreground groups. Changing depth never reallocates their shapes.
        for i, (orbit, radius, color, speed, phase, name) in enumerate(PLANETS):
            x, y = self.orbit(orbit, self.time * speed + phase)
            data = (y, x, i, radius, color, name)
            positions.append(data)
            start = p.index
            self.draw_planet(p, data)
            planet_items.append((start, p.index))
        sun_start = p.index
        self.draw_sun(p)
        foreground_start = p.index
        self.labels(p, positions)
        p.line([(-445, -246), (445, -246)], "#26354C")
        descriptions = ["水星  /  岩石纹理 · 内侧的快速旅者", "地球  /  云层与海洋 · 月亮绕行",
                        "火星  /  赭红地貌 · 一抹明亮极冠", "土星  /  多层冰环 · 前后遮挡的光影",
                        "海王星  /  冰蓝大气 · 最外侧的慢舞"]
        p.text(-445, -268, descriptions[self.selected] if self.selected is not None else "微型星系  /  ORBITAL ATLAS",
               "#C4D0E6" if self.selected is not None else "#869BBB", 10, "w")
        p.text(445, -268, f"公转速度  × {self.speed:.2f}", "#A7B8DE", 10, "e")
        p.end()
        # Restore depth every frame: a planet that crossed behind the Sun must
        # not retain the foreground stacking order from its previous frame.
        ordered = sorted(positions, reverse=True)
        depth_order = tuple((data[2], data[0] <= -5) for data in ordered)
        if p.order_changed or p.depth_order != depth_order:
            for front in (False, True):
                if front:
                    for item in p.items[sun_start:foreground_start]:
                        p.canvas.tag_raise(item[1])
                for y, x, i, radius, color, name in ordered:
                    if (y <= -5) == front:
                        start, end = planet_items[i]
                        for item in p.items[start:end]:
                            p.canvas.tag_raise(item[1])
            for item in p.items[foreground_start:p.index]:
                p.canvas.tag_raise(item[1])
            p.depth_order = depth_order
        self.stage.hud("点击一颗星球，点亮它的轨道   ·   大小、轨道与速度为艺术化示意")


if __name__ == "__main__":
    app = Galaxy()
    app.stage.run(app.frame, app.reset)
