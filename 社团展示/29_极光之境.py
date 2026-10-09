"""极光之境：流动幕帘、雪山与冰湖，用有界矢量图形绘制北境夜色。"""
import math
import random

from 舞台 import Paint, Stage, mix

THEMES = (
    ("翡翠极夜", "#071528", "#111F32", "#69EBC1", "#7395EC", "#BBDFE0"),
    ("紫霞雪境", "#141128", "#272039", "#CB95F1", "#6FCEEB", "#DBD2E8"),
    ("琥珀黎明", "#201725", "#342831", "#F0C17B", "#DB8AA8", "#E8D3B8"),
)


class AuroraLandscape:
    def __init__(self):
        self.stage = Stage("极光之境", "点击天空 光涌 / 水面 涟漪    C 配色    ↑↓ 速度    W 风", accent="#8CDEC9")
        self.paint = Paint(self.stage, "aurora-landscape")
        rng = random.Random(2909)
        self.stars = [(rng.uniform(-470, 475), rng.uniform(-25, 244), rng.uniform(.6, 1.5),
                       rng.random()*math.tau) for _ in range(110)]
        self.stars = [s for s in self.stars if not (s[0] < -200 and s[1] > 113)]
        self.water = [(rng.uniform(-440, 440), -106-i*7.5, rng.uniform(24, 99), rng.random()*math.tau)
                      for i in range(19)]
        self.snow = [(rng.uniform(-470, 475), rng.uniform(-244, 242), rng.random()*math.tau)
                     for _ in range(28)]
        self.ridge = [(-505, -72), (-452, -27), (-391, -43), (-334, 1), (-274, -23),
                      (-180, 60), (-96, -25), (-28, 15), (42, -42), (116, -4),
                      (204, -52), (274, 31), (350, -23), (410, 8), (505, -67)]
        # Small, fixed crags break the clean triangular skyline without flicker.
        self.skyline = []
        for a, b in zip(self.ridge, self.ridge[1:]):
            for step in range(7):
                u = step/7
                self.skyline.append((a[0]+(b[0]-a[0])*u,
                                     a[1]+(b[1]-a[1])*u+rng.uniform(-5, 4)*math.sin(math.pi*u)))
        self.skyline.append(self.ridge[-1])
        self.reflections = [(rng.uniform(-158, 466), -156-i*1.85,
                             rng.uniform(28, 92), rng.random()*math.tau)
                            for i in range(45) for _ in range(5)]
        self.palettes = []
        for _, sky, floor, green, blue, ice in THEMES:
            self.palettes.append({
                "curtain": [[mix(sky, color, .025+.71*i/63) for i in range(64)] for color in (green, blue)],
                "reflection": [mix(floor, green, .005+.39*i/31) for i in range(32)],
                "stars": [mix(sky, ice, .18+.56*i/31) for i in range(32)],
                "ridge": mix(sky, ice, .14), "snow": mix(sky, ice, .46),
                "facet": mix(sky, ice, .19), "water": mix(floor, ice, .16),
                "bank": mix(sky, ice, .21), "bank_light": mix(sky, ice, .43),
                "trunk": mix(sky, floor, .4), "pine": mix(sky, green, .075),
                "pine_snow": mix(sky, ice, .31),
                "ripples": [mix(floor, ice, .06+.43*i/31) for i in range(32)],
            })
        self.reset()
        self.stage.screen.onclick(self.touch)
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_theme, key)
        for key in ("w", "W"):
            self.stage.screen.onkey(self.toggle_wind, key)
        self.stage.screen.onkey(lambda: self.change_speed(.25), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-.25), "Down")

    def reset(self):
        self.time = 0.0
        self.theme = 0
        self.speed = 1.0
        self.wind = True
        self.pulses = []
        self.ripples = []

    def change_theme(self):
        if not self.stage.paused:
            self.theme = (self.theme+1) % len(THEMES)

    def change_speed(self, amount):
        if not self.stage.paused:
            self.speed = max(.25, min(2, self.speed+amount))

    def toggle_wind(self):
        if not self.stage.paused:
            self.wind = not self.wind

    def touch(self, x, y):
        if self.stage.paused:
            return
        x, y = self.stage.point(x, y)
        if not self.stage.in_scene(x, y):
            return
        if y > -70:
            self.pulses = (self.pulses+[[x, y, 0.0]])[-6:]
        elif -237 < y < -101:
            self.ripples = (self.ripples+[[x, y, 0.0]])[-8:]

    def curtain(self, u, layer):
        phase = self.time*.25
        x = -172+u*650
        lower = 54+layer*31+33*math.sin(u*6.4+phase+layer*1.4)+15*math.sin(u*12.4-phase*.8)
        height = 82+24*math.sin(u*3.8+layer)+20*math.sin(u*7-phase*.4)**2
        pulse = sum(math.exp(-((x-px)/110)**2)*math.sin(math.pi*age/3)**2
                    for px, _, age in self.pulses)
        lower += min(22, pulse*14)
        upper = min(243, lower+height)
        intensity = (.63+.24*math.sin(u*18-phase*1.7)**2)*math.sin(math.pi*u)**.7
        return x, lower, upper, min(1, intensity+min(.25, pulse*.13))

    def draw_curtains(self, p, colors):
        for layer in (1, 0):
            points = [self.curtain(i/72, layer) for i in range(73)]
            palette = colors["curtain"][layer]
            # Continuous ribbons remove the checkerboard seams of column quads.
            # Many shallow tonal steps blend into a soft curtain at window size.
            for row in range(39, -1, -1):
                low, high = row/40, (row+1)/40
                lower = [(x, y+(top-y)*low) for x, y, top, _ in points]
                upper = [(x, y+(top-y)*high+.4) for x, y, top, _ in reversed(points)]
                strength = (1-low)**2.4 * (.42 if layer else .72)
                p.poly(lower+upper, palette[round(strength*63)])
            # Fine vertical rays give the folds structure without a tile grid.
            for i in range(1, 72, 3):
                x, y, top, glow = points[i]
                for segment in range(4):
                    a, b = segment/4, (segment+1)/4
                    strength = min(1, ((.42 if layer else .72)+glow*.16)*(1-a)**2.4)
                    p.line([(x, y+(top-y)*a), (x+1.6, y+(top-y)*b)],
                           palette[round(strength*63)], .5)
            p.line([(x, y+.8) for x, y, _, _ in points], palette[38 if layer else 52], 1)

    def pine(self, p, x, y, height, colors):
        lean = math.sin(self.time*.7+x)*2 if self.wind else 0
        p.line([(x, y), (x+lean, y+height)], colors["trunk"], 3)
        for row in range(9):
            fraction = .12+row*.092
            base = y+height*fraction
            span = height*(.25-.22*fraction)*(1+.11*math.sin(row*7+x))
            center = x+lean*fraction
            for side in (-1, 1):
                points = [(center, base+height*.17), (center+side*span*.54, base+height*.06),
                          (center+side*span*.46, base+height*.06), (center+side*span, base),
                          (center+side*span*.62, base+.5), (center, base+height*.025)]
                p.poly(points, colors["pine"])
                p.line(points[:4], colors["pine_snow"], 1.25)

    def frame(self, dt):
        if dt > 0 and math.isfinite(dt) and not self.stage.paused:
            self.time += dt*self.speed
            self.pulses = [[x, y, age+dt] for x, y, age in self.pulses if age+dt < 3]
            self.ripples = [[x, y, age+dt] for x, y, age in self.ripples if age+dt < 3.6]
        name, sky, floor, green, _, ice = THEMES[self.theme]
        colors = self.palettes[self.theme]
        p = self.paint
        p.begin()
        p.gradient(sky, sky)
        for x, y, radius, phase in self.stars:
            shade = round((.5+.5*math.sin(self.time*.6+phase))*31)
            p.circle(x, y, radius, colors["stars"][shade])
        for radius, shade in ((45, .015), (33, .04), (25, .07)):
            p.circle(-349, 66, radius, mix(sky, ice, shade))
        p.circle(-349, 66, 19, ice)
        p.circle(-342, 73, 18, sky)
        self.draw_curtains(p, colors)
        # A distant silhouette, a shaded near ridge and separate snow facets.
        distant = [(x, y*.65+13) for x, y in self.ridge]
        p.poly([(-505, -100)]+distant+[(505, -100)], mix(sky, ice, .07))
        p.poly([(-505, -105)]+self.skyline+[(505, -105)], colors["ridge"])
        for i in (3, 5, 7, 9, 11, 13):
            x, y = self.ridge[i]
            before, after = self.ridge[i-1], self.ridge[i+1]
            p.poly([(x, y), (x+13, y-33), (x+9, y-49), (x+24, y-69),
                    (after[0]+15, -99), (x-31, -99), (x-12, y-53)], colors["facet"])
            p.poly([(x, y), (x+(after[0]-x)*.52, y+(after[1]-y)*.52),
                    (x+17, y-23), (x+11, y-43), (x+3, y-26), (x-5, y-30),
                    (x-3, y-15), (x-18, y-25),
                    (x+(before[0]-x)*.58, y+(before[1]-y)*.58)], colors["snow"])
            for strand in range(3):
                end_x = x+(after[0]-x)*(.2+strand*.13)
                end_y = -78-strand*3
                p.line([(x+strand*2, y-strand*7), (x+13+strand*5, y-38-strand*4),
                        (end_x-8, end_y+13), (end_x, end_y)], colors["ridge"], .8)
        p.rect(-505, -98, 505, -289, floor)
        reflected = [(x, -98-(y+98)*.52) for x, y in self.ridge]
        p.poly([(-505, -98)]+reflected+[(505, -98)], mix(floor, ice, .065))
        for x, y, length, phase in self.reflections:
            u = max(0, min(1, (x+172)/650))
            _, bottom, top, glow = self.curtain(u, 0)
            center = -98-(bottom+98)*.51
            distance = abs(y-center)/max(12, (top-bottom)*.5)
            strength = glow*max(0, 1-distance)**1.6*(.78+.22*math.sin(phase+self.time))
            drift = math.sin(self.time*.7+phase)*6
            shade = colors["reflection"][round(strength*31)]
            p.line([(x-length/2+drift, y), (x+length/2+drift, y+.35)], shade, 1)
        p.line([(-493, -98), (493, -98)], colors["water"], 1)
        for x, y, length, phase in self.water:
            shift = math.sin(self.time*.5+phase)*8
            p.line([(x+shift-length/2, y), (x+shift+length/2, y)], colors["water"], 1)
        for x, y, age in self.ripples:
            radius = 5+age*28
            color = colors["ripples"][round((1-age/3.6)*31)]
            p.oval(x, y, radius, radius*.22, "", color, 1)
            p.oval(x, y, radius*.65, radius*.14, "", color, 1)
        p.poly([(-505, -206), (-360, -220), (-259, -249), (-137, -258),
                (-81, -288), (-505, -288)], colors["bank"])
        p.line([(-500, -205), (-360, -219), (-259, -248), (-137, -257)], colors["bank_light"], 2)
        p.poly([(330, -258), (414, -220), (505, -197), (505, -288), (289, -288)], colors["bank"])
        for x, y, height in ((-461, -224, 105), (-413, -236, 75), (-373, -243, 54),
                              (456, -231, 100), (416, -246, 66)):
            self.pine(p, x, y, height, colors)
        if self.wind:
            for x, y, phase in self.snow:
                xx = (x+math.sin(self.time*.4+phase)*12+475) % 950-475
                yy = (y-self.time*8+250) % 500-250
                p.circle(xx, yy, .65, colors["stars"][6])
        p.text(-434, 207, "极光之境", ice, 28, "w")
        p.text(-432, 173, "AURORA / THE QUIET NORTH", colors["stars"][18], 9, "w")
        p.line([(-432, 150), (-374, 150)], green, 1)
        p.text(-432, 128, "将夜色，轻轻拨亮。", colors["stars"][16], 11, "w")
        p.text(270, -258, "29 / LIGHT ABOVE THE FJORD", colors["stars"][12], 9)
        p.end()
        self.stage.hud(f"{name}   ·   极光速度 × {self.speed:.2f}   ·   {'雪风轻扬' if self.wind else '风停雪静'}")


if __name__ == "__main__":
    app = AuroraLandscape()
    app.stage.run(app.frame, app.reset)
