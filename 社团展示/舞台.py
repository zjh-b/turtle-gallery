"""共用画布：Turtle 窗口、定时动画、可复用的矢量图形。只用标准库。"""
import colorsys
import math
import time
import tkinter as tk
import turtle

FONT = "Microsoft YaHei"


def mix(a, b, amount):
    amount = max(0, min(1, amount))
    aa = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
    bb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(aa, bb))


def hsv(h, s=0.6, v=1):
    return "#" + "".join(f"{round(c * 255):02x}" for c in colorsys.hsv_to_rgb(h % 1, s, v))


def polar(radius, angle, x=0, y=0):
    return x + radius * math.cos(angle), y + radius * math.sin(angle)


def star_points(x, y, radius, angle=math.pi / 2):
    return [polar(radius if i % 2 == 0 else radius * 0.46,
                  angle + i * math.pi / 5, x, y) for i in range(10)]


class Paint:
    """更新已有 Canvas 图形，不在每一帧删除再创建所有对象。坐标与 Turtle 一致。"""
    def __init__(self, stage, tag):
        self.stage, self.canvas, self.tag = stage, stage.canvas, tag
        self.items = []
        self.index = 0
        self.order_changed = False
        self.scale = stage.scale

    def begin(self):
        self.index = 0
        self.order_changed = False
        self.scale = self.stage.scale

    def _put(self, kind, points, **options):
        scale = self.scale
        coords = tuple(round(value * scale * (1 if i % 2 == 0 else -1), 2)
                       for i, value in enumerate(points))
        options["state"] = "normal"
        if self.index == len(self.items):
            self.items.append(None)
        old = self.items[self.index]
        if old is None or old[0] != kind:
            if old:
                self.canvas.delete(old[1])
            item = getattr(self.canvas, "create_" + kind)(*coords, tags=(self.tag,), **options)
            self.items[self.index] = [kind, item, coords, options]
            self.order_changed = True
        else:
            _, item, previous_coords, previous_options = old
            if previous_coords != coords:
                self.canvas.coords(item, *coords)
            if previous_options != options:
                self.canvas.itemconfigure(item, **options)
            old[2], old[3] = coords, options
        self.index += 1

    def end(self):
        for old in self.items[self.index:]:
            if old and old[3].get("state") != "hidden":
                self.canvas.itemconfigure(old[1], state="hidden")
                old[3]["state"] = "hidden"
        if self.order_changed:
            for old in self.items[:self.index]:
                self.canvas.tag_raise(old[1])
        self.canvas.tag_raise(self.tag)

    def rect(self, x1, y1, x2, y2, fill, outline="", width=1):
        self._put("rectangle", (x1, y1, x2, y2), fill=fill, outline=outline,
                  width=max(1, width * self.scale))

    def oval(self, x, y, rx, ry, fill="", outline="", width=1):
        self._put("oval", (x - rx, y + ry, x + rx, y - ry), fill=fill, outline=outline,
                  width=max(1, width * self.scale))

    def circle(self, x, y, r, fill="", outline="", width=1):
        self.oval(x, y, r, r, fill, outline, width)

    def line(self, points, color, width=1, smooth=False, dash=None):
        opts = dict(fill=color, width=max(1, width * self.scale),
                    smooth=smooth, capstyle="round", joinstyle="round", dash=dash or ())
        self._put("line", tuple(v for point in points for v in point), **opts)

    def poly(self, points, fill, outline="", width=1, smooth=False):
        self._put("polygon", tuple(v for point in points for v in point),
                  fill=fill, outline=outline, width=max(1, width * self.scale),
                  smooth=smooth, splinesteps=16)

    def text(self, x, y, text, color, size=12, anchor="center", bold=False):
        self._put("text", (x, y), text=text, fill=color, anchor=anchor,
                  font=(FONT, max(8, round(size * self.scale)), "bold" if bold else "normal"))

    def star(self, x, y, r, color, angle=math.pi / 2, outline=""):
        self.poly(star_points(x, y, r, angle), color, outline)

    def glow(self, x, y, r, color, background, rings=7):
        for i in range(rings, 0, -1):
            self.circle(x, y, r * i / rings, mix(background, color, (1 - i / (rings + 1)) ** 2 * 0.65))

    def gradient(self, top, bottom):
        w, h = self.stage.view
        for i in range(32):
            self.rect(-w / 2 - 2, h / 2 - i * h / 32 + 1,
                      w / 2 + 2, h / 2 - (i + 1) * h / 32 - 1, mix(top, bottom, i / 31))


class Stage:
    def __init__(self, title, hint, background="#081122", accent="#8FE1DA", light=False):
        self.screen = turtle.Screen()
        display = self.screen.getcanvas()
        self.screen.setup(min(1100, max(760, display.winfo_screenwidth() - 80)),
                          min(800, max(580, display.winfo_screenheight() - 100)))
        self.screen.title(title + " · Turtle Gallery")
        self.screen.bgcolor(background)
        self.screen.tracer(0)
        self.canvas = self.screen.getcanvas()
        self.root = self.canvas.winfo_toplevel()
        self.root.minsize(760, 580)
        self.title, self.hint, self.accent, self.light = title, hint, accent, light
        self.background = background
        self.paused = self.closed = self.fullscreen = False
        self.show_hud = True
        self.frame = self.reset_action = None
        self._last_time = time.perf_counter()
        self.header = Paint(self, "hud")
        self.screen.onkey(self.toggle_pause, "space")
        for key in ("r", "R"):
            self.screen.onkey(self.reset, key)
        self.screen.onkey(self.close, "Escape")
        self.screen.onkey(self.toggle_fullscreen, "F11")
        for key in ("h", "H"):
            self.screen.onkey(self.toggle_hud, key)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.screen.listen()

    @property
    def width(self):
        return self.screen.window_width()

    @property
    def height(self):
        return self.screen.window_height()

    @property
    def scale(self):
        return max(0.4, min(self.width / 1000, self.height / 720))

    @property
    def view(self):
        return self.width / self.scale, self.height / self.scale

    def point(self, x, y):
        return x / self.scale, y / self.scale

    def event_point(self, event):
        return self.point(self.canvas.canvasx(event.x), -self.canvas.canvasy(event.y))

    def in_scene(self, x, y):
        return abs(x) < self.view[0] / 2 and -295 < y < 265

    def toggle_hud(self):
        self.show_hud = not self.show_hud

    def hud(self, status=""):
        if not self.show_hud:
            self.canvas.itemconfigure("hud", state="hidden")
            # 同步缓存，恢复说明时才能重新显示原有图形。
            for item in self.header.items:
                if item:
                    item[3]["state"] = "hidden"
            return
        p = self.header
        p.begin()
        w, h = self.view
        fg = "#234C4B" if self.light else "#F2F4FC"
        muted = "#537E76" if self.light else "#96A7C1"
        panel = "#D5E7DB" if self.light else "#10172A"
        p.rect(-w / 2, h / 2, w / 2, h / 2 - 88, panel)
        p.rect(-w / 2 + 30, h / 2 - 25, -w / 2 + 34, h / 2 - 55, self.accent)
        p.text(-w / 2 + 47, h / 2 - 38, self.title, fg, 21, "w", True)
        p.text(-w / 2 + 47, h / 2 - 68, ("已暂停  ·  " if self.paused else "") + status, muted, 10, "w")
        p.text(w / 2 - 30, h / 2 - 35, "TURTLE GALLERY", self.accent, 10, "e")
        p.text(w / 2 - 30, h / 2 - 57, "PYTHON  /  TURTLE", muted, 8, "e")
        p.rect(-w / 2, -h / 2 + 62, w / 2, -h / 2, panel)
        p.line([(-w / 2 + 30, -h / 2 + 62), (w / 2 - 30, -h / 2 + 62)],
               mix(panel, self.accent, 0.23))
        p.text(0, -h / 2 + 40, self.hint, fg, 10)
        p.text(0, -h / 2 + 17, "空格 暂停 / 继续    R 重来    H 隐藏 / 显示说明    F11 全屏    Esc 返回", muted, 9)
        p.end()

    def toggle_pause(self):
        self.paused = not self.paused

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def reset(self):
        self.paused = False
        if self.reset_action:
            self.reset_action()

    def close(self):
        if not self.closed:
            self.closed = True
            self.screen.bye()

    def tick(self):
        if self.closed:
            return
        started = time.perf_counter()
        dt = min(started - self._last_time, 0.05)
        self._last_time = started
        try:
            if self.frame:
                self.frame(0 if self.paused else dt)
            self.screen.update()
            if not self.closed:
                delay = max(1, round(1000 / 40 - (time.perf_counter() - started) * 1000))
                self.screen.ontimer(self.tick, delay)
        except (turtle.Terminator, tk.TclError):
            if not self.closed:
                raise

    def run(self, frame, reset):
        self.frame, self.reset_action = frame, reset
        self.reset()
        self.tick()
        self.screen.mainloop()
