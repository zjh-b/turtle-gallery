"""见缝插针：带精确到达判定的机械转盘小游戏。直接运行即可游玩。"""
import math

from 社团展示.舞台 import Paint, Stage, mix, polar


# 名称、底色、盘面、刻线、强调、文字、碰撞提示。
PALETTES = (
    ("深海铜仪", "#101D26", "#172C35", "#47646A", "#E6BD7D", "#E7EFE7", "#FF8E80"),
    ("瓷白青针", "#ECEBE0", "#DEDCCD", "#8AABA1", "#32766C", "#273F40", "#B7564D"),
    ("星夜紫晶", "#211E36", "#302942", "#65577C", "#CAB0ED", "#F1E9F5", "#F19B9D"),
)


def angular_distance(a, b):
    """两角的最短圆周距离，包括跨越 0/360° 的情况。"""
    return abs((a - b + 180) % 360 - 180)


class NeedleGame:
    CENTER = (80, 0)
    HUB = 57
    TIP = 185
    FLIGHT_SECONDS = .28
    CLEARANCE = 8
    TARGET = 18

    def __init__(self):
        self.stage = Stage("见缝插针 · 时机练习", "点击画面 / Enter 发针    C 配色    R 重新挑战",
                           PALETTES[0][1], PALETTES[0][4])
        self.paint = Paint(self.stage, "needle-game")
        self.paint.backdrop = Paint(self.stage, "needle-game-dial")
        self.paint.signature = None
        self.best = self.palette = 0
        self.reset()
        self.stage.screen.onclick(self.click)
        self.stage.screen.onkey(self.fire, "Return")
        for key in ("c", "C"):
            self.stage.screen.onkey(self.change_palette, key)

    @property
    def speed(self):
        return 62 + min(self.score, self.TARGET) * 2.2

    def reset(self):
        self.angle = self.time = 0.0
        self.needles = [45.0, 135.0, 225.0, 315.0]
        self.score = 0
        self.phase = "playing"
        self.flight = self.failed_angle = None
        self.feedback = 0.0
        self.sync_stage()

    def sync_stage(self):
        self.stage.accent = PALETTES[self.palette][4]
        self.stage.light = self.palette == 1

    def change_palette(self):
        self.palette = (self.palette + 1) % len(PALETTES)
        self.sync_stage()

    def click(self, x, y):
        x, y = self.stage.point(x, y)
        if -500 < x < 500 and -285 < y < 265 and self.stage.in_scene(x, y):
            self.fire()

    def fire(self):
        if self.stage.paused or self.phase != "playing" or self.flight is not None:
            return
        self.flight = 0.0

    def arrive(self):
        local = (180 - self.angle) % 360
        self.flight = None
        self.feedback = 1.0
        if any(angular_distance(local, other) < self.CLEARANCE for other in self.needles):
            self.failed_angle = local
            self.phase = "lost"
            return
        self.needles.append(local)
        self.score += 1
        self.best = max(self.best, self.score)
        if self.score >= self.TARGET:
            self.phase = "won"

    def advance(self, dt):
        """先积分到针抵达的时刻，再用新的速度积分余下时间。"""
        self.time += dt
        if self.phase != "playing":
            self.feedback = max(0.0, self.feedback - dt * 1.8)
            return
        remaining = dt
        if self.flight is not None:
            step = min(remaining, max(0, self.FLIGHT_SECONDS - self.flight))
            self.angle = (self.angle + self.speed * step) % 360
            self.flight += step
            remaining = max(0, remaining - step)
            self.feedback = max(0.0, self.feedback - step * 1.8)
            if self.flight >= self.FLIGHT_SECONDS - 1e-10:
                self.arrive()
        if self.phase == "playing":
            self.angle = (self.angle + self.speed * remaining) % 360
        self.feedback = max(0.0, self.feedback - remaining * 1.8)

    def backdrop(self, colors):
        signature = (self.palette, self.stage.scale, self.stage.view)
        if signature == self.paint.signature:
            return
        _, bg, surface, line, accent, text, _ = colors
        p = self.paint.backdrop
        p.begin()
        p.gradient(bg, mix(bg, surface, .75))
        # 细密的仪器网格只留在底层，发射区保持清楚。
        for x in range(-470, 490, 28):
            for y in range(-252, 255, 28):
                if math.hypot(x - 80, y) > 244:
                    p.circle(x, y, .65, mix(bg, line, .24))
        p.line([(-442, 209), (-408, 209)], accent, 2)
        p.text(-442, 179, "见缝插针", text, 25, "w", True)
        p.text(-440, 148, "THE ART OF TIMING", line, 9, "w")
        p.text(-440, 113, "等一道空隙，让下一针落定。", mix(line, text, .35), 10, "w")
        p.line([(-440, 84), (-288, 84)], mix(bg, line, .65))
        cx, cy = self.CENTER
        p.circle(cx + 3, cy - 4, 229, mix(bg, "#000000", .2))
        p.circle(cx, cy, 227, mix(surface, line, .3))
        p.circle(cx, cy, 225, bg)
        p.circle(cx, cy, 222, outline=mix(accent, bg, .48))
        p.circle(cx, cy, 213, surface)
        p.circle(cx, cy, 199, outline=mix(surface, line, .5))
        p.circle(cx, cy, 190, outline=mix(surface, line, .25))
        for i in range(120):
            a = i * math.tau / 120
            major = i % 10 == 0
            p.line([polar(204 if major else 211, a, cx, cy), polar(219, a, cx, cy)],
                   mix(line, accent, .7) if major else line, 1.5 if major else .65)
        for i in range(12):
            a = i * math.tau / 12
            x, y = polar(240, a, cx, cy)
            if i != 6:
                p.text(x, y, f"{i * 30:03}", mix(line, text, .23), 7)
        for radius in (76, 94, 112, 130, 148, 166):
            p.circle(cx, cy, radius, outline=mix(surface, line, .10))
        # 左侧供针槽；虚线指向中心，提示固定入针方向。
        p.line([(-298, 0), (17, 0)], mix(line, accent, .25), .8, dash=(3, 6))
        p.rect(-445, 16, -298, -16, mix(bg, surface, .8), outline=mix(bg, line, .55))
        p.line([(-435, 21), (-306, 21)], mix(bg, accent, .4))
        p.poly([(-283, 0), (-292, 4), (-292, -4)], accent)
        p.text(-440, -52, "点击 / ENTER", accent, 11, "w", True)
        p.text(-440, -77, "一针落定，再发下一针", mix(line, text, .28), 9, "w")
        p.line([(-440, -113), (-291, -113)], mix(bg, line, .5))
        p.text(-440, -146, "本轮成功", line, 9, "w")
        p.text(-440, -226, "目标 18 针 · 转速逐渐增加", line, 9, "w")
        p.text(429, 197, "01 / PLAY", accent, 9, "e")
        p.text(429, -206, "C · 三种配色", line, 9, "e")
        p.text(429, -230, "R · 重新开始", line, 9, "e")
        p.end()
        self.paint.signature = signature

    def draw_pin(self, angle, color, highlight):
        p = self.paint
        a = math.radians(angle)
        cx, cy = self.CENTER
        inner = polar(self.HUB - 3, a, cx, cy)
        outer = polar(self.TIP, a, cx, cy)
        p.line([inner, outer], color, 2.3)
        p.line([polar(self.HUB + 9, a, cx, cy), polar(self.TIP - 9, a, cx, cy)], highlight, .8)
        p.circle(*outer, 5.2, color)
        p.circle(outer[0] - 1, outer[1] + 1, 1.7, highlight)

    def draw(self):
        colors = PALETTES[self.palette]
        _, bg, surface, line, accent, text, danger = colors
        self.backdrop(colors)
        p = self.paint
        p.begin()
        for i, angle in enumerate(self.needles):
            color = mix(line, accent, .55) if i < 4 else accent
            self.draw_pin(angle + self.angle, color, mix(color, text, .75))
        if self.failed_angle is not None:
            self.draw_pin(180, danger, mix(danger, text, .7))
        # 发射针在到达前始终游离；抵达时才进入随盘旋转的集合。
        if self.phase == "playing":
            progress = 0 if self.flight is None else self.flight / self.FLIGHT_SECONDS
            tip_x = -307 + (self.CENTER[0] - self.HUB + 307) * progress
            p.line([(tip_x - 128, 0), (tip_x, 0)], accent, 2.4)
            p.line([(tip_x - 121, 1), (tip_x - 7, 1)], text, .7)
            p.circle(tip_x - 128, 0, 5.5, accent)
            p.circle(tip_x - 129.2, 1.2, 1.8, text)
        cx, cy = self.CENTER
        p.circle(cx + 1, cy - 2, self.HUB + 4, mix(bg, "#000000", .2))
        p.circle(cx, cy, self.HUB + 2, accent)
        p.circle(cx, cy, self.HUB, surface)
        for radius in range(54, 2, -3):
            p.circle(cx, cy, radius, mix(surface, bg, .55 * (1 - radius / 57)))
        p.circle(cx, cy, 50, outline=mix(surface, accent, .38))
        for i in range(24):
            a = math.radians(self.angle + i * 15)
            p.line([polar(44, a, cx, cy), polar(47, a, cx, cy)], mix(line, accent, .3), .7)
        p.text(cx, cy + 5, f"{self.TARGET - self.score:02}", text, 26, bold=True)
        p.text(cx, cy - 22, "待落定" if self.phase == "playing" else "已结束", line, 8)
        p.text(-440, -181, f"{self.score:02}", text, 31, "w", True)
        p.text(-368, -188, f"/ {self.TARGET:02}", line, 13, "w")
        p.text(429, 157, "本次运行最佳", line, 9, "e")
        p.text(429, 125, f"{self.best:02}", text, 24, "e", True)
        for i in range(self.TARGET):
            p.rect(-154 + i * 26, -267, -138 + i * 26, -263,
                   accent if i < self.score else mix(bg, line, .35))
        if self.feedback > 0:
            color = danger if self.phase == "lost" else accent
            radius = 59 + 17 * (1 - self.feedback)
            p.circle(cx, cy, radius, outline=mix(surface, color, self.feedback), width=1.6)
        if self.phase != "playing":
            p.rect(-131, -118, 291, -189, bg, outline=mix(line, accent, .4))
            p.text(cx, -140, "碰到上一针了" if self.phase == "lost" else "十八针，全部落定！",
                   danger if self.phase == "lost" else accent, 17, bold=True)
            p.text(cx, -169, "按 R 再来一局 · 最高成绩会保留", text, 10)
        p.end()
        self.stage.hud(f"{colors[0]} · 成功 {self.score}/{self.TARGET} · " +
                       ("寻找空隙" if self.phase == "playing" else "按 R 重新挑战"))

    def frame(self, dt):
        if dt > 0:
            self.advance(dt)
        self.draw()

    def run(self):
        self.stage.run(self.frame, self.reset)


if __name__ == "__main__":
    NeedleGame().run()
