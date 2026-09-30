"""Pure heart geometry and motion shared by desktop drawing and browser fixtures."""
import math


THEMES = [
    ("玫瑰星尘", "#FF528E", "#FFCADC", "#957DFF"),
    ("冰蓝心跳", "#53DCEB", "#DCF9FF", "#8397FF"),
    ("香槟暮光", "#FFB66D", "#FFF0CF", "#E688AE"),
]


def heart_point(angle):
    return (16 * math.sin(angle) ** 3,
            13 * math.cos(angle) - 5 * math.cos(2 * angle)
            - 2 * math.cos(3 * angle) - math.cos(4 * angle))


def heartbeat(beat_time):
    phase = (beat_time % 1.55) / 1.55
    return (math.exp(-((phase - 0.18) / 0.06) ** 2)
            + 0.58 * math.exp(-((phase - 0.34) / 0.09) ** 2))


def spread_at(age):
    return 0.0 if age is None else math.sin(math.pi * age / 3.6) ** 2
