"""分秒之间：真实本机时间、金属指针与可切换的三款表盘。

直接运行 ``python 时钟.py``。C 换色，T 平滑／跳秒，D 真实／演示，
↑↓ 调整演示速度，点击表盘切换数字时间；空格暂停，R 重置。
表盘使用缓存的矢量图形，动画只更新指针，不清屏、不阻塞窗口。
"""
from datetime import datetime, timedelta
import math

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、背景、背景亮部、表盘、表盘亮部、金属暗部、金属亮部、文字、秒针。
PALETTES = (
    ("午夜黄铜", "#070F1B", "#142B3E", "#0D1C2D", "#203E52",
     "#665138", "#E9C989", "#EEE5CF", "#E58C72"),
    ("松石银光", "#081A1A", "#183F3D", "#102B2A", "#255A53",
     "#627E79", "#E1ECE3", "#E5EEE7", "#F5B767"),
    ("象牙玫瑰金", "#E9E0D1", "#F6EFE0", "#EEE5D2", "#FFF8E9",
     "#956B56", "#E8B89B", "#5A483C", "#A33F3C"),
)
CENTER = (0, -8)
DIAL_RADIUS = 218


def clock_angles(moment, smooth=True):
    """Return clockwise angles from twelve; jumping seconds also align the hands."""
    second = moment.second + (moment.microsecond / 1_000_000 if smooth else 0)
    minute = moment.minute + second / 60
    hour = moment.hour % 12 + minute / 60
    return hour * 30, minute * 6, second * 6


class GalleryClock:
    def __init__(self):
        self.stage = Stage("分秒之间", "C 配色    T 平滑 / 跳秒    D 真实 / 演示    ↑↓ 演示速度    点击表盘 数字时间",
                           PALETTES[0][1], PALETTES[0][6])
        self.paint = Paint(self.stage, "clock-hands")
        self.paint.backdrop = Paint(self.stage, "clock-dial")
        self.paint.readout = Paint(self.stage, "clock-readout")
        self.paint.signature = None
        self.reset()
        for key in ("c", "C"):
            self.stage.screen.onkey(self.cycle_palette, key)
        for key in ("t", "T"):
            self.stage.screen.onkey(self.toggle_tick, key)
        for key in ("d", "D"):
            self.stage.screen.onkey(self.toggle_demo, key)
        self.stage.screen.onkey(lambda: self.change_speed(30), "Up")
        self.stage.screen.onkey(lambda: self.change_speed(-30), "Down")
        self.stage.screen.onclick(self.click_dial)

    def reset(self):
        self.palette = 0
        self.smooth, self.demo, self.digital = True, False, True
        self.speed = 60
        self.moment = datetime.now()

    def cycle_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)

    def toggle_tick(self):
        self.smooth = not self.smooth

    def toggle_demo(self):
        self.demo = not self.demo
        if not self.demo:
            # Return immediately to the computer clock, without retaining demo drift.
            self.moment = datetime.now()

    def change_speed(self, amount):
        if self.demo:
            self.speed = max(1, min(600, self.speed + amount))

    def click_dial(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.paused or not self.stage.in_scene(x, y):
            return
        if math.hypot(x - CENTER[0], y - CENTER[1]) <= DIAL_RADIUS:
            self.digital = not self.digital

    def draw_dial(self, colors):
        signature = (self.palette, self.stage.scale, self.stage.view)
        if self.paint.signature == signature:
            return
        self.paint.signature = signature
        _, background, ground, face, face_light, metal_dark, metal, ink, accent = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(background, ground)
        # Quiet stitched rays frame the dial while leaving the numerals prominent.
        etched = mix(background, metal, .14)
        for side in (-1, 1):
            for height in (-190, -120, -50, 20, 90, 160):
                x = side * (285 + abs(height) * .14)
                p.line([(x, height), (side * 448, height)], mix(background, ground, .7), .8)
            p.line([(side * 274, -8), (side * 380, -8)], etched)
            p.circle(side * 389, -8, 2, metal_dark)
            p.text(side * 355, 26, "CHRONO" if side < 0 else "ATELIER", mix(ground, metal, .55), 11)
            p.text(side * 355, -42, "分  秒" if side < 0 else "之  间", mix(ground, ink, .65), 17)
        p.text(0, -273, "T U R T L E   /   T I M E P I E C E", mix(ground, metal, .50), 9)
        # The shadow and bevel are independent circles so the rim has real depth.
        for radius, dx, dy, amount in ((250, 3, -5, .12), (247, 3, -6, .28), (244, 2, -6, .47)):
            p.circle(dx, CENTER[1] + dy, radius, mix(ground, background, amount))
        p.circle(*CENTER, 242, metal_dark)
        p.circle(*CENTER, 240, metal)
        p.circle(*CENTER, 238, mix(metal_dark, face, .4))
        # Fine radial segments imitate brushed metal. Fixed and cached after drawing.
        for index in range(144):
            angle = math.tau * index / 144
            next_angle = angle + math.tau / 144 + .001
            shine = .48 + .30 * math.cos(angle - 2.1) + .16 * math.cos(2 * angle + .4)
            color = mix(metal_dark, metal, shine)
            p.poly([polar(237, angle, *CENTER), polar(237, next_angle, *CENTER),
                    polar(221, next_angle, *CENTER), polar(221, angle, *CENTER)], color)
        p.circle(*CENTER, 220, mix(metal_dark, face, .55))
        p.circle(*CENTER, DIAL_RADIUS, face)
        for index in range(1, 25):
            p.circle(-index * .25, CENTER[1] + index * .4, 218 - index * 5.4,
                     mix(face, face_light, index / 31))
        p.circle(*CENTER, 216, outline=mix(face, metal, .46), width=.9)
        p.circle(*CENTER, 211, outline=mix(face, metal, .16), width=.8)
        p.circle(*CENTER, 184, outline=mix(face, metal, .13), width=.8)
        for minute in range(60):
            angle = math.pi / 2 - minute * math.tau / 60
            major = minute % 5 == 0
            inner = 191 if major else 201
            p.line([polar(inner, angle, *CENTER), polar(208, angle, *CENTER)],
                   metal if major else mix(face, metal, .72), 3.6 if major else 1.2)
            if major:
                p.line([polar(inner + 2, angle, *CENTER), polar(206, angle, *CENTER)],
                       mix(metal, "#FFFFFF", .37), 1)
        for hour in range(1, 13):
            angle = math.pi / 2 - hour * math.tau / 12
            x, y = polar(166, angle, *CENTER)
            p.text(x, y - 1, str(hour), mix(face, ink, .18), 24)
            p.text(x, y + 1, str(hour), ink, 23)
        p.text(0, 96, "分 秒 之 间", ink, 14)
        p.text(0, 75, "T U R T L E   A T E L I E R", mix(face, metal, .9), 8)
        p.line([(-23, 59), (23, 59)], mix(face, metal, .48), .8)
        p.circle(0, 59, 2, metal)
        # Recessed date window; its contents are drawn by a separate small painter.
        p.rect(-67, -105, 67, -78, mix(face, metal_dark, .6), outline=metal_dark)
        p.rect(-64, -102, 64, -80, mix(face, background, .45))
        p.end()

    @staticmethod
    def hand_points(points, degrees, dx=0, dy=0):
        angle = math.radians(90 - degrees)
        co, si = math.cos(angle), math.sin(angle)
        return [(CENTER[0] + u * co - v * si + dx,
                 CENTER[1] + u * si + v * co + dy) for u, v in points]

    def draw_hands(self, colors):
        _, background, _, face, _, metal_dark, metal, ink, accent = colors
        p = self.paint
        p.begin()
        hour, minute, second = clock_angles(self.moment, self.smooth)
        for degrees, length, width in ((hour, 107, 8), (minute, 153, 5.5)):
            silhouette = ((-19, -width * .55), (12, -width), (length - 16, -width * .6),
                          (length, 0), (length - 16, width * .6), (12, width), (-19, width * .55))
            p.poly(self.hand_points(silhouette, degrees, 3, -4), mix(face, background, .8))
            p.poly(self.hand_points(silhouette, degrees), metal_dark, outline=metal)
            p.poly(self.hand_points(((-17, 0), (12, 0), (length, 0),
                                    (length - 16, width * .6), (12, width), (-17, width * .55)), degrees),
                   mix(metal, "#FFFFFF", .25))
            p.poly(self.hand_points(((25, -width * .20), (length - 22, -width * .16),
                                    (length - 14, 0), (length - 22, width * .16), (25, width * .20)), degrees),
                   ink)
        needle = ((-39, -1.8), (184, -1), (199, 0), (184, 1), (-39, 1.8))
        p.poly(self.hand_points(needle, second, 2, -3), mix(face, background, .8))
        p.poly(self.hand_points(needle, second), accent)
        tail = self.hand_points(((-30, 0),), second)[0]
        p.circle(*tail, 5, face, outline=accent, width=2)
        p.circle(*CENTER, 10, metal_dark)
        p.circle(*CENTER, 8, metal)
        p.circle(-1.7, CENTER[1] + 1.7, 5, mix(metal, ink, .6))
        p.circle(*CENTER, 2.2, accent)
        p.end()

    def frame(self, dt):
        if dt > 0:
            self.moment = (self.moment + timedelta(seconds=dt * self.speed)
                           if self.demo else datetime.now())
        colors = PALETTES[self.palette]
        _, _, _, face, _, _, metal, ink, _ = colors
        self.stage.light = self.palette == 2
        self.stage.accent = metal if not self.stage.light else colors[5]
        self.draw_dial(colors)
        # Cached painters only need their group raised, not every static item.
        self.stage.canvas.tag_raise(self.paint.backdrop.tag)
        p = self.paint.readout
        p.begin()
        weekday = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")[self.moment.weekday()]
        p.text(0, -91, self.moment.strftime("%m.%d") + "  /  " + weekday, ink, 12)
        if self.digital:
            p.text(0, -128, self.moment.strftime("%H : %M : %S"), mix(face, ink, .85), 18)
        p.end()
        self.draw_hands(colors)
        mode = f"演示 {self.speed}×" if self.demo else "本机时间"
        motion = "平滑扫秒" if self.smooth else "逐秒跳动"
        self.stage.hud(f"{colors[0]}  ·  {mode}  ·  {motion}  ·  {self.moment:%Y.%m.%d}")

    def run(self):
        self.stage.run(self.frame, self.reset)


if __name__ == "__main__":
    GalleryClock().run()
