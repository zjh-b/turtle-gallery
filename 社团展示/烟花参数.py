"""Shared firework constants and pure formulas for Python and browser exports."""
import math

VIEW = (1020, 580)
PALETTES = [("#FFC976", "#FF7B87"), ("#7ADFFF", "#AF9BFF"),
            ("#FF91CB", "#FFD7F0"), ("#A1F2C9", "#FFE8A8")]
SHAPES = ("礼花", "星环", "爱心", "金柳")
PHYSICS = dict(particle_count=84, drag=0.65, gravity=46, willow_gravity=75,
               speed_min=95, speed_max=145, life_min=1.65, life_max=2.5,
               rocket_duration=0.85, bloom_life=2.5,
               particle_cap=600, rocket_cap=8, bloom_cap=8, max_step=0.05)


def initial_velocity(kind, index, speed):
    """Return one ray's velocity, keeping the original four flower formulas."""
    angle = index * math.tau / PHYSICS["particle_count"]
    vx, vy = math.cos(angle) * speed, math.sin(angle) * speed
    if kind == 1:
        vx *= 1.2
        vy *= 0.65
        if index % 3 == 0:
            vx *= 0.45
            vy *= 0.45
    elif kind == 2:
        vx = 9 * 16 * math.sin(angle) ** 3
        vy = 9 * (13 * math.cos(angle) - 5 * math.cos(2 * angle)
                  - 2 * math.cos(3 * angle) - math.cos(4 * angle))
    elif kind == 3:
        vy = abs(vy) * 1.2
    elif index % 4 == 0:
        vx *= 0.55
        vy *= 0.55
    return vx, vy


def location(particle, age):
    """Integrate drag and gravity without mutating the particle."""
    age = max(0, age)
    travel = (1 - math.exp(-PHYSICS["drag"] * age)) / PHYSICS["drag"]
    return (particle["x"] + particle["vx"] * travel,
            particle["y"] + particle["vy"] * travel - particle["gravity"] * age * age / 2)
