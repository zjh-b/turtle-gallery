"""打砖块：细分时间步防止穿透，击球位置决定反弹方向。"""
from collections import deque
import math
import random

from 舞台 import Paint, Stage, mix


COLORS = ["#E79CBF", "#C4A4EE", "#8BAFE8", "#7FCFCB", "#E1C786"]


class Breakout:
    RADIUS = 7
    HALF_PADDLE = 52
    PADDLE_Y = -218

    def __init__(self):
        self.stage = Stage("霓虹弹球", "鼠标或 ←→ 移动    Enter / 点击 发球    A 自动演示", accent="#8DE4DC")
        self.paint = Paint(self.stage, "breakout")
        self.keys = set()
        self.trail = deque(maxlen=12)
        self.sparks = []
        self.bricks = []
        self.time, self.paddle, self.mouse_x = 0, 0, 0
        self.mouse_control, self.autoplay = True, False
        self.ready, self.ended, self.won = True, False, False
        self.score, self.lives, self.combo = 0, 3, 0
        self.ball = [0, -200, 135, 285]
        for key in ("Left", "Right"):
            self.stage.screen.onkeypress(lambda key=key: self.press(key), key)
            self.stage.screen.onkeyrelease(lambda key=key: self.keys.discard(key), key)
        self.stage.screen.onkey(self.launch, "Return")
        for key in ("a", "A"):
            self.stage.screen.onkey(self.toggle_auto, key)
        self.stage.screen.onclick(self.click)
        self.stage.canvas.bind("<Motion>", self.motion, add="+")
        self.stage.canvas.bind("<FocusOut>", lambda event: self.keys.clear(), add="+")

    def reset(self):
        self.keys.clear()
        self.trail.clear()
        self.sparks.clear()
        self.time, self.paddle, self.mouse_x = 0, 0, 0
        self.mouse_control, self.autoplay = True, False
        self.ready, self.ended, self.won = True, False, False
        self.score, self.lives, self.combo = 0, 3, 0
        self.ball = [0, -200, 135, 285]
        self.bricks = [dict(x=-332.5 + col * 95, y=169 - row * 31, color=COLORS[row])
                       for row in range(5) for col in range(8)]

    def press(self, key):
        self.mouse_control = False
        self.keys.add(key)

    def motion(self, event):
        if not self.stage.paused:
            self.mouse_x = max(-360, min(360, self.stage.event_point(event)[0]))
            self.mouse_control = True

    def click(self, x, y):
        x, y = self.stage.point(x, y)
        if self.stage.in_scene(x, y):
            self.launch()

    def launch(self):
        if self.ready and not self.ended and not self.stage.paused:
            self.ready = False
            self.ball[2:] = [135 if self.paddle <= 0 else -135, 285]

    def toggle_auto(self):
        self.autoplay = not self.autoplay
        self.keys.clear()

    def lose_ball(self):
        self.lives -= 1
        self.combo = 0
        self.trail.clear()
        self.ready = True
        self.ball[:2] = [self.paddle, self.PADDLE_Y + 18]
        if self.lives <= 0:
            self.ended = True

    def burst(self, x, y, color):
        for i in range(8):
            a = i * math.tau / 8
            speed = random.uniform(45, 105)
            self.sparks.append([x, y, math.cos(a) * speed, math.sin(a) * speed, 0, color])
        self.sparks = self.sparks[-160:]

    def step(self, dt):
        """每一步位移小于球半径，反弹后将球移出碰撞体。"""
        x, y, vx, vy = self.ball
        old_y = y
        x, y = x + vx * dt, y + vy * dt
        if x < -411 + self.RADIUS:
            x, vx = -411 + self.RADIUS, abs(vx)
        elif x > 411 - self.RADIUS:
            x, vx = 411 - self.RADIUS, -abs(vx)
        if y > 224 - self.RADIUS:
            y, vy = 224 - self.RADIUS, -abs(vy)
        paddle_top = self.PADDLE_Y + 8
        if vy < 0 and old_y >= paddle_top + self.RADIUS >= y and abs(x - self.paddle) <= self.HALF_PADDLE + 5:
            offset = max(-1, min(1, (x - self.paddle) / self.HALF_PADDLE))
            speed = max(315, math.hypot(vx, vy))
            vx = speed * 0.83 * offset
            if abs(vx) < 35:
                vx = 35 if offset >= 0 else -35
            vy = math.sqrt(max(1, speed * speed - vx * vx))
            y = paddle_top + self.RADIUS
            self.combo = 0
        for brick in self.bricks[:]:
            left, right = brick["x"] - 42, brick["x"] + 42
            bottom, top = brick["y"] - 10, brick["y"] + 10
            near_x, near_y = max(left, min(right, x)), max(bottom, min(top, y))
            if (x - near_x) ** 2 + (y - near_y) ** 2 > self.RADIUS ** 2:
                continue
            distances = [(abs(x - (left - self.RADIUS)), "left"), (abs(x - (right + self.RADIUS)), "right"),
                         (abs(y - (bottom - self.RADIUS)), "bottom"), (abs(y - (top + self.RADIUS)), "top")]
            side = min(distances)[1]
            if side == "left":
                x, vx = left - self.RADIUS, -abs(vx)
            elif side == "right":
                x, vx = right + self.RADIUS, abs(vx)
            elif side == "bottom":
                y, vy = bottom - self.RADIUS, -abs(vy)
            else:
                y, vy = top + self.RADIUS, abs(vy)
            self.bricks.remove(brick)
            self.score += 10
            self.combo += 1
            self.burst(brick["x"], brick["y"], brick["color"])
            speed = math.hypot(vx, vy)
            factor = min(480, speed + 3) / speed
            vx, vy = vx * factor, vy * factor
            break
        self.ball = [x, y, vx, vy]
        if not self.bricks:
            self.ended = self.won = True
        elif y < -269:
            self.lose_ball()

    def update(self, dt):
        self.time += dt
        for spark in self.sparks:
            spark[0] += spark[2] * dt
            spark[1] += spark[3] * dt
            spark[3] -= 90 * dt
            spark[4] += dt
        self.sparks = [s for s in self.sparks if s[4] < 0.65]
        if self.ended:
            return
        if self.autoplay:
            target = self.ball[0]
            if self.ball[3] < 0:
                # 预测反弹后的落点，再用球拍的偏心位置瞄准剩余砖块。
                remaining = max(0, (self.ball[1] - self.PADDLE_Y - 15) / -self.ball[3])
                projected = self.ball[0] + self.ball[2] * remaining
                folded = (projected + 404) % 1616
                impact = -404 + folded if folded <= 808 else 1212 - folded
                brick = min(self.bricks, key=lambda b: abs(b["x"] - impact) + b["y"] * 0.15)
                dx, dy = brick["x"] - impact, brick["y"] - self.PADDLE_Y
                offset = dx / math.hypot(dx, dy) * self.HALF_PADDLE / 0.83
                target = impact - offset
            self.paddle += max(-dt * 590, min(dt * 590, target - self.paddle))
            if self.ready:
                self.launch()
        elif self.mouse_control:
            self.paddle += (self.mouse_x - self.paddle) * min(1, dt * 23)
        else:
            self.paddle += (int("Right" in self.keys) - int("Left" in self.keys)) * dt * 520
        self.paddle = max(-360, min(360, self.paddle))
        if self.ready:
            self.ball[:2] = [self.paddle, self.PADDLE_Y + 18]
            return
        steps = max(1, math.ceil(math.hypot(*self.ball[2:]) * dt / 5))
        for _ in range(steps):
            self.step(dt / steps)
            if self.ready or self.ended:
                break
        if not self.ready:
            self.trail.append(tuple(self.ball[:2]))

    def frame(self, dt):
        if dt > 0:
            self.update(dt)
        p = self.paint
        p.begin()
        p.gradient("#0A1325", "#18253B")
        p.rect(-424, 235, 424, -278, "#0D1C30", "#365367", 1.5)
        for x in range(-400, 401, 40):
            p.line([(x, -263), (x, 220)], "#152A3E")
        for y in range(-260, 221, 40):
            p.line([(-407, y), (407, y)], "#152A3E")
        p.line([(-413, -259), (-413, 226), (413, 226), (413, -259)], "#477987", 2)
        for brick in self.bricks:
            x, y, color = brick["x"], brick["y"], brick["color"]
            p.rect(x - 43, y + 11, x + 43, y - 11, mix("#122438", color, 0.25), mix(color, "#263A4B", 0.3))
            p.rect(x - 39, y + 7, x + 39, y - 6, mix("#1A2C3F", color, 0.75))
            p.line([(x - 37, y + 6), (x + 37, y + 6)], mix(color, "#FFFFFF", 0.4), 1.2)
        for i, (x, y) in enumerate(self.trail):
            p.circle(x, y, 2 + i * 0.22, mix("#13283C", "#92E1D5", (i + 1) / 20))
        for x, y, vx, vy, age, color in self.sparks:
            p.line([(x - vx * 0.035, y - vy * 0.035), (x, y)], mix("#15273B", color, 1 - age / 0.65), 2)
        x = self.paddle
        p.line([(x - self.HALF_PADDLE, self.PADDLE_Y), (x + self.HALF_PADDLE, self.PADDLE_Y)], "#2D6171", 17)
        p.line([(x - self.HALF_PADDLE + 2, self.PADDLE_Y + 1), (x + self.HALF_PADDLE - 2, self.PADDLE_Y + 1)], "#80D6D0", 10)
        p.line([(x - 25, self.PADDLE_Y + 3), (x + 25, self.PADDLE_Y + 3)], "#C0F4DF", 2)
        bx, by = self.ball[:2]
        p.glow(bx, by, 16, "#A7F1DB", "#11253A", 4)
        p.circle(bx, by, self.RADIUS, "#DAFAE8")
        p.circle(bx - 2, by + 2, 2, "#FFFFFF")
        p.text(-418, 254, f"得分  {self.score:03d}", "#C6E9E6", 13, "w", True)
        p.text(418, 254, f"剩余球数  {self.lives}     砖块  {len(self.bricks):02d}", "#A7BACD", 11, "e")
        if self.ready and not self.ended:
            p.text(0, -106, "点击或按 Enter 发球", "#CADBE4", 16)
            p.text(0, -140, "击中球拍的不同位置，试试反弹方向", "#7795AF", 10)
        if self.ended:
            p.rect(-235, 56, 235, -154, "#13243A", "#67959C", 2)
            p.text(0, 9, "全部点亮，挑战成功！" if self.won else "这一局，打得不错", "#D6EEE4", 21, bold=True)
            p.text(0, -44, f"{self.score} 分", "#F4D9A7", 29, bold=True)
            p.text(0, -104, "按 R 重新挑战    ·    Esc 返回菜单", "#A8BDD0", 11)
        p.end()
        self.stage.hud(("自动演示中，A 键接管" if self.autoplay else "鼠标和键盘都能玩") +
                       f"   ·   连续击碎 {self.combo} 块   ·   清空全部砖块即获胜")


if __name__ == "__main__":
    app = Breakout()
    app.stage.run(app.frame, app.reset)
