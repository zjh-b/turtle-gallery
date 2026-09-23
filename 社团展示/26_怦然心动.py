"""一颗会呼吸的粒子心：固定星尘池、双拍心跳与散开后重新聚合。"""
import math
import random

from 舞台 import Paint, Stage, mix
from 创作配方 import default_parameters, validate_parameters


THEMES = [
    ("玫瑰星尘", "#FF528E", "#FFCADC", "#957DFF"),
    ("冰蓝心跳", "#53DCEB", "#DCF9FF", "#8397FF"),
    ("香槟暮光", "#FFB66D", "#FFF0CF", "#E688AE"),
]


def heart_point(angle):
    """The classic parametric heart, centred in the artwork's safe area."""
    return (16 * math.sin(angle) ** 3,
            13 * math.cos(angle) - 5 * math.cos(2 * angle)
            - 2 * math.cos(3 * angle) - math.cos(4 * angle))


class ParticleHeart:
    WORK_ID = 26
    PARTICLE_COUNT = 680

    def __init__(self):
        self.stage = Stage("怦然心动", "点击 散成星尘再相聚    C 切换色彩    ↑↓ 调整心跳    E 创作面板", accent="#FF91B5")
        self.paint = Paint(self.stage, "particle-heart")
        parameters = default_parameters(self.WORK_ID)
        self.seed = parameters["seed"]
        self.theme = parameters["theme"]
        self.rate = parameters["rate"]
        self.particle_count = parameters["particle_count"]
        self.size = parameters["size"]
        self._make_geometry()
        self.contour = [heart_point(index * math.tau / 160) for index in range(161)]
        self.orbit_back = [self.orbit(index * math.pi / 70) for index in range(71)]
        self.orbit_front = [self.orbit(math.pi + index * math.pi / 70) for index in range(71)]
        self.colors = []
        for _, core, light, accent in THEMES:
            self.colors.append({
                "dust": [mix("#28172F", core, index / 31) for index in range(32)],
                "light": [mix(core, light, index / 31) for index in range(32)],
                "star": [mix("#101329", accent, index / 31) for index in range(32)],
                "atmosphere": [mix("#100E22", core, 0.008 + index * 0.0022) for index in range(17)],
                "constellation": mix("#232438", accent, 0.55),
                "orbit_back": mix("#14122A", accent, 0.34),
                "orbit_front": mix("#15122A", accent, 0.37),
                "glow_outer": mix("#26162E", core, 0.10),
                "glow_inner": mix("#26162E", core, 0.24),
            })
        self.reset()
        self.stage.screen.onclick(self.burst)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        self.stage.screen.onkey(lambda: self.change_rate(0.15), "Up")
        self.stage.screen.onkey(lambda: self.change_rate(-0.15), "Down")
        self.stage.enable_creation(self)

    def _make_geometry(self):
        rng = random.Random(self.seed)
        # Geometry is generated once. The depth controls the density and brightness
        # of the shell; every frame reuses the same small set of Canvas items.
        self.particles = []
        for _ in range(self.particle_count):
            angle = rng.random() * math.tau
            radius = 1 - rng.random() ** 2.3 * 0.60
            x, y = heart_point(angle)
            depth = rng.uniform(-1, 1)
            phase = rng.random() * math.tau
            self.particles.append((x * 13.0 * radius, y * 13.0 * radius,
                                   depth, rng.uniform(0.85, 2.15), phase,
                                   rng.uniform(40, 180), angle))
        self.particles.sort(key=lambda item: item[2])
        # Scatter directions and phase components never change during animation.
        self._motion = [(math.sin(phase), math.cos(phase),
                         math.sin(angle) * velocity, math.cos(angle) * velocity * 0.65)
                        for _, _, _, _, phase, velocity, angle in self.particles]
        # A separate random stream keeps the background stable when density changes.
        star_rng = random.Random(self.seed ^ 0x5F3759DF)
        self.stars = [(star_rng.uniform(-475, 475), star_rng.uniform(-263, 248),
                       star_rng.uniform(0.6, 1.7), star_rng.random() * math.tau) for _ in range(78)]

    def get_parameters(self):
        return {"seed": self.seed, "theme": self.theme, "rate": self.rate,
                "particle_count": self.particle_count, "size": self.size}

    def apply_parameters(self, parameters):
        parameters = validate_parameters(self.WORK_ID, parameters)
        geometry_changed = (parameters["seed"] != self.seed
                            or parameters["particle_count"] != self.particle_count)
        self.seed = parameters["seed"]
        self.theme = parameters["theme"]
        self.rate = parameters["rate"]
        self.particle_count = parameters["particle_count"]
        self.size = parameters["size"]
        if geometry_changed:
            self._make_geometry()

    def reset(self):
        self.time = self.beat_time = 0.0
        self.burst_age = None

    @staticmethod
    def orbit(angle):
        return (310 * math.cos(angle),
                -28 + 60 * math.sin(angle) + 0.22 * 310 * math.cos(angle))

    def change_theme(self):
        if not self.stage.paused:
            self.theme = (self.theme + 1) % len(THEMES)

    def change_rate(self, amount):
        if not self.stage.paused:
            self.rate = max(0.45, min(1.8, self.rate + amount))

    def burst(self, x, y):
        if self.stage.paused:
            return
        if self.stage.in_scene(*self.stage.point(x, y)):
            self.burst_age = 0.0

    def frame(self, dt):
        self.time += dt
        self.beat_time += dt * self.rate
        if dt > 0 and self.burst_age is not None:
            self.burst_age += dt
            if self.burst_age >= 3.6:
                self.burst_age = None
        spread = 0.0 if self.burst_age is None else math.sin(math.pi * self.burst_age / 3.6) ** 2
        phase = (self.beat_time % 1.55) / 1.55
        beat = math.exp(-((phase - 0.18) / 0.06) ** 2) + 0.58 * math.exp(-((phase - 0.34) / 0.09) ** 2)
        pulse = 1 + beat * 0.055
        name, core, light, accent = THEMES[self.theme]
        colors = self.colors[self.theme]
        p = self.paint
        p.begin()
        p.gradient("#070D20", "#180C23")
        # The nested, low-contrast ovals form a soft coloured atmosphere.
        for index in range(17):
            radius = 298 - index * 11
            p.oval(0, 5, radius, radius * 0.75, colors["atmosphere"][index])
        for x, y, radius, star_phase in self.stars:
            twinkle = 0.55 + 0.3 * math.sin(self.time * 0.7 + star_phase)
            p.circle(x, y, radius, colors["star"][round(twinkle * 31)])
        for side in (-1, 1):
            dots = [(side * 396, 115), (side * 419, 53), (side * 364, 5), (side * 405, -75)]
            p.line(dots, "#28243E", 1)
            for x, y in dots:
                p.circle(x, y, 2.3, colors["constellation"])
                p.circle(x, y, 6, "", "#302B46")
        # An inclined ellipse passes behind the heart, then returns in front.
        orbit_angle = self.time * 0.27
        p.line(self.orbit_back, colors["orbit_back"], 1)
        # Faint concentric outlines help the thousands-of-stars illusion without
        # increasing the particle pool or covering the sculptural, hollow centre.
        shape_scale = pulse * self.size
        for scale, tint, width in ((1.025, 0.12, 4.5), (1, 0.30, 1.1), (0.965, 0.09, 1.0)):
            contour = [(x * 13 * shape_scale * scale, y * 13 * shape_scale * scale + 26)
                       for x, y in self.contour]
            p.line(contour, mix("#23162F", core, tint * (1 - spread * 0.85)), width, True)
        rotation = 0.08 * math.sin(self.time * 0.38)
        turn_cos, turn_sin = math.cos(rotation), math.sin(rotation)
        glow_outer, glow_inner = colors["glow_outer"], colors["glow_inner"]
        wave_sin, wave_cos = math.sin(self.time * 0.75), math.cos(self.time * 0.75)
        light_sin, light_cos = math.sin(self.time * 1.1), math.cos(self.time * 1.1)
        scatter_scale = spread * self.size
        point_scale = 1 + beat * 0.12
        for index, ((x, y, depth, radius, _, _, _), motion) in enumerate(zip(self.particles, self._motion)):
            phase_sin, phase_cos, scatter_x, scatter_y = motion
            xx = (x * turn_cos + depth * 17 * turn_sin) * shape_scale + scatter_x * scatter_scale
            yy = (y * shape_scale + 26 + (wave_sin * phase_cos + wave_cos * phase_sin) * 1.4
                  + scatter_y * scatter_scale)
            if depth > 0.55:
                color = colors["light"][min(31, round((depth - 0.55) * 50))]
            else:
                brightness = 0.48 + 0.28 * depth + 0.14 * (light_sin * phase_cos + light_cos * phase_sin)
                color = colors["dust"][max(0, min(31, round(brightness * 31)))]
            if index % 59 == 0:
                p.circle(xx, yy, radius * 3.0, glow_outer)
                p.circle(xx, yy, radius * 1.7, glow_inner)
            p.circle(xx, yy, radius * point_scale, color)
        p.line(self.orbit_front, colors["orbit_front"], 1)
        for shift in (0, math.pi):
            x, y = self.orbit(orbit_angle + shift)
            p.glow(x, y, 8, accent, "#15112A", 3)
            p.circle(x, y, 2, light)
        p.text(0, -250, "把一瞬的心动，写成漫长的星光。", "#A27D9F", 11)
        p.text(0, 233, "E V E R Y   B E A T   I S   A   L I T T L E   U N I V E R S E", "#77657F", 8)
        p.end()
        self.stage.hud(f"{name}   ·   心跳 × {self.rate:.2f}   ·   {len(self.particles)} 粒星尘 / 散开后会再次相聚")


if __name__ == "__main__":
    app = ParticleHeart()
    app.stage.run(app.frame, app.reset)
