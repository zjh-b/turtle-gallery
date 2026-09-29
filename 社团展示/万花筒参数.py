"""Pure rotation / reflection geometry shared by desktop and browser fixtures."""
import math

VIEW = (560, 560)
RADIUS = 246
MIN_COUNT, MAX_COUNT = 3, 16


def mirror_points(points, count):
    result = []
    for index in range(count):
        angle = index * math.tau / count
        c, s = math.cos(angle), math.sin(angle)
        for mirror in (-1, 1):
            result.append([(x * c - y * mirror * s,
                            x * s + y * mirror * c) for x, y in points])
    return result
