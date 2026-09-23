"""星光收集：织纹篮子、星星拖尾、接取粒子、连击和结算画面。"""
import math
import random

from 舞台 import Paint, Stage, mix, polar


class StarGame:
    def __init__(self):
        self.stage = Stage("把星光装进口袋", "← → 或 A D 移动    M 切换鼠标控制    接住 +1 分    漏接五颗结束", accent="#F7D78F")
        self.paint = Paint(self.stage, "game")
        rng = random.Random(18)
        self.sky = [(rng.uniform(-490, 490), rng.uniform(-130, 257), rng.uniform(0.6, 1.7)) for _ in range(80)]
        self.keys = set()
        self.items, self.sparks, self.popups = [], [], []
        self.best = 0
        self.score, self.lives, self.combo = 0, 5, 0
        self.x = self.time = self.timer = self.flash = self.catch = 0
        self.ended = False
        self.mouse_control = False
        self.mouse_x = 0
        for key in ("m", "M"):
            self.stage.screen.onkey(self.toggle_mouse, key)
        self.stage.canvas.bind("<Motion>", self.move_mouse, add="+")
        for key in ("Left", "Right", "a", "d", "A", "D"):
            self.stage.screen.onkeypress(lambda k=key: self.keys.add(k), key)
            self.stage.screen.onkeyrelease(lambda k=key: self.keys.discard(k), key)
        self.stage.canvas.bind("<FocusOut>", lambda event: self.keys.clear(), add="+")

    @property
    def basket_y(self):
        return -212

    def toggle_mouse(self):
        self.mouse_control = not self.mouse_control
        self.mouse_x = self.x
        self.keys.clear()

    def move_mouse(self, event):
        if not self.stage.paused:
            self.mouse_x = max(-425, min(425, self.stage.event_point(event)[0]))

    def reset(self):
        self.items = [[-160, 155, 110, 0.5], [85, 240, 120, 2]]
        self.sparks.clear()
        self.popups.clear()
        self.keys.clear()
        self.score, self.lives, self.combo = 0, 5, 0
        self.x = self.time = self.flash = self.catch = 0
        self.timer = 1
        self.ended = False
        self.mouse_x = 0

    def finish(self):
        self.ended = True
        self.best = max(self.best, self.score)

    def caught(self, x):
        self.score += 1
        self.combo += 1
        self.best = max(self.best, self.score)
        self.catch = 0.35
        self.popups.append([x, self.basket_y + 45, 0, f"+1  连接 {self.combo} 颗" if self.combo >= 3 else "+1"])
        for i in range(12):
            a = i * math.tau / 12
            self.sparks.append([x, self.basket_y + 8, math.cos(a) * 85, math.sin(a) * 85 + 35, 0])

    def update(self, dt):
        if self.ended:
            return
        self.time += dt
        self.flash, self.catch = max(0, self.flash - dt), max(0, self.catch - dt)
        left = bool(self.keys & {"Left", "a", "A"})
        right = bool(self.keys & {"Right", "d", "D"})
        if self.mouse_control:
            self.x += (self.mouse_x - self.x) * min(1, dt * 18)
        else:
            self.x = max(-425, min(425, self.x + (right - left) * 430 * dt))
        self.timer -= dt
        if self.timer <= 0:
            self.items.append([random.uniform(-415, 415), 235, random.uniform(95, 125) + min(self.score * 3, 150),
                               random.random() * math.tau])
            self.timer = max(0.35, 1.05 - self.score * 0.016)
        alive = []
        for item in self.items:
            old_y = item[1]
            item[1] -= item[2] * dt
            if old_y >= self.basket_y >= item[1] and abs(item[0] - self.x) <= 48:
                self.caught(item[0])
            elif item[1] < self.basket_y - 34:
                self.lives = max(0, self.lives - 1)
                self.combo, self.flash = 0, 0.45
            else:
                alive.append(item)
        self.items = alive
        for spark in self.sparks:
            spark[0] += spark[2] * dt
            spark[1] += spark[3] * dt
            spark[3] -= 110 * dt
            spark[4] += dt
        self.sparks = [s for s in self.sparks if s[4] < 0.65]
        for popup in self.popups:
            popup[1] += dt * 48
            popup[2] += dt
        self.popups = [p for p in self.popups if p[2] < 0.8]
        if self.lives == 0:
            self.finish()

    def basket(self, p):
        x, y = self.x, self.basket_y
        if self.flash:
            x += math.sin(self.flash * 80) * 5
        y += math.sin(self.catch * math.pi / 0.35) * 4
        p.oval(x + 2, y - 40, 52, 8, "#242544")
        p.line([(x - 32, y - 8), (x - 30, y + 35), (x, y + 49),
                (x + 30, y + 35), (x + 32, y - 8)], "#DEA971", 5, True)
        p.line([(x - 30, y - 8), (x - 28, y + 34), (x, y + 45),
                (x + 28, y + 34), (x + 30, y - 8)], "#F4D39C", 1, True)
        p.poly([(x - 47, y), (x + 47, y), (x + 34, y - 36), (x - 34, y - 36)],
               "#B87953", "#EBC58D", 2)
        for row in range(4):
            yy = y - 6 - row * 8
            width = 44 - row * 3
            p.line([(x - width, yy), (x + width, yy)], "#E0AB75", 3)
        for col in range(-3, 4):
            p.line([(x + col * 11, y - 3), (x + col * 8, y - 34)], "#916142", 2)
        p.oval(x, y, 48, 7, "#5C4350", "#FFE0A4", 3)
        p.star(x, y - 20, 10, "#FFE1A0")
        p.circle(x, y - 20, 3, "#B87953")

    def frame(self, dt):
        if dt > 0:
            self.update(dt)
        p = self.paint
        p.begin()
        edge = self.stage.view[0] / 2 + 10
        p.gradient("#151C3A", "#4B3C64")
        for x, y, r in self.sky:
            p.circle(x, y, r, mix("#73799A", "#F7E7CB", 0.55 + 0.4 * math.sin(self.time * 0.6 + x)))
        p.glow(349, 165, 71, "#BFB0C4", "#222642", 9)
        p.circle(349, 165, 29, "#F2DFB9")
        p.circle(360, 174, 27, "#282A49")
        # 远山、近丘和小树组成可辨识的夜景。
        p.poly([(-edge, -310), (-edge, -168), (-370, -105), (-228, -190), (-72, -131),
                (101, -196), (292, -94), (edge, -163), (edge, -310)], "#3C3A60")
        p.poly([(-edge, -310), (-edge, -211), (-380, -170), (-160, -237), (58, -183),
                (275, -235), (470, -166), (edge, -218), (edge, -310)], "#303052", smooth=True)
        for x, y, s in [(-432, -195, 0.8), (-402, -211, 0.55), (418, -202, 0.8), (455, -185, 1)]:
            p.line([(x, y - 34 * s), (x, y + 26 * s)], "#202B43", 3)
            for dy in (0, 13, 26):
                p.poly([(x, y + (dy + 18) * s), (x - (25 - dy * 0.4) * s, y + (dy - 14) * s),
                        (x + (25 - dy * 0.4) * s, y + (dy - 14) * s)], "#222D47")
        for x, y, speed, phase in self.items:
            for j in (3, 2, 1):
                p.circle(x, y + j * 10, 6 - j, mix("#35304D", "#D9B888", 0.42 - j * 0.09))
            p.glow(x, y, 24, "#EDC679", "#34304D", 4)
            angle = math.pi / 2 + math.sin(self.time * 2 + phase) * 0.18
            p.star(x, y, 16, "#FFE09A", angle, "#FFF0C7")
            p.circle(x - 3.5, y + 1, 1.2, "#A47F55")
            p.circle(x + 3.5, y + 1, 1.2, "#A47F55")
        self.basket(p)
        for x, y, vx, vy, age in self.sparks:
            p.star(x, y, max(1, 4 * (1 - age / 0.65)), mix("#443B5A", "#FFEAC0", 1 - age / 0.65))
        for x, y, age, label in self.popups:
            p.text(x, y, label, mix("#514363", "#FFE7A6", 1 - age / 0.8), 13, bold=True)
        p.text(-448, 231, "已收集", "#C2BBD7", 10, "w")
        p.text(-448, 195, f"{self.score:02d}", "#FFE5AB", 30, "w", True)
        p.text(445, 237, "剩余机会", "#C2BBD7", 10, "e")
        for i in range(5):
            p.star(344 + i * 24, 211, 8, "#F9D78F" if i < self.lives else "#55506A")
        if self.ended:
            p.rect(-257, 135, 257, -130, "#191F39", "#7D7593", 2)
            for i in range(3):
                p.star(-48 + i * 48, 82 + (14 if i == 1 else 0), 18 if i == 1 else 13, "#FFE0A0")
            p.text(0, 37, "今晚的星光，属于你", "#EDE5F3", 19, bold=True)
            p.text(0, -12, f"{self.score} 颗", "#FFE3A6", 32, bold=True)
            p.text(0, -56, f"本次打开的最高纪录：{self.best} 颗", "#ACA9C4", 11)
            p.text(0, -99, "按 R 再来一局  ·  邀请下一位同学挑战", "#E5D4B4", 11)
        p.end()
        self.stage.hud(("鼠标控制" if self.mouse_control else "键盘控制") + f"   ·   连续接住 {self.combo} 颗   ·   最高纪录 {self.best} 颗" + ("   ·   按 R 重来" if self.ended else ""))


if __name__ == "__main__":
    app = StarGame()
    app.stage.run(app.frame, app.reset)
