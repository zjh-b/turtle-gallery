"""巡展的计时、窗口操作与父子进程协议；导入时不会创建窗口。"""
import json
import math
import os
import queue
import sys
import threading
import time

PREFIX = "TG_TOUR:"
ENVIRONMENT = "TURTLE_GALLERY_TOUR"
DEFAULT_ORDER = "25,26,27"
DEFAULT_SECONDS = 30


def validate_seconds(value):
    try:
        seconds = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("单件停留时间须为 10–600 秒的整数。") from None
    if isinstance(value, bool) or str(seconds) != str(value).strip() or not 10 <= seconds <= 600:
        raise ValueError("单件停留时间须为 10–600 秒的整数。")
    return seconds


def parse_playlist(value, works):
    eligible = {str(work["id"]): work for work in works if work.get("autoplay", False)}
    parts = [part.strip() for part in str(value).split(",")]
    if not parts or any(part not in eligible for part in parts):
        raise ValueError("巡展顺序请填写支持自动演示的编号，用逗号分隔：25,26,27。")
    if len(set(parts)) != len(parts):
        raise ValueError("巡展列表中每件作品只需填写一次。")
    return [eligible[part] for part in parts]


class TourClock:
    """互动只暂停切换；继续时给当前作品完整的展示时间。"""
    def __init__(self, duration, now=time.monotonic):
        self.duration = validate_seconds(duration)
        self.now = now
        self.paused = False
        self.deadline = now() + self.duration

    @property
    def remaining(self):
        return self.duration if self.paused else max(0, math.ceil(self.deadline - self.now()))

    @property
    def expired(self):
        return not self.paused and self.now() >= self.deadline

    def pause(self):
        self.paused = True

    def resume(self):
        self.deadline = self.now() + self.duration
        self.paused = False


class TourSession:
    def __init__(self, stage, settings, input_stream=sys.stdin, output_stream=sys.stdout):
        self.stage = stage
        self.clock = TourClock(settings["duration"])
        self.index, self.count = int(settings["index"]), int(settings["count"])
        if not 1 <= self.index <= self.count:
            raise ValueError("巡展位置无效。")
        self.output_stream = output_stream
        self.closed = False
        self.reason = "closed"
        self.commands = queue.Queue()
        self.paint = None
        self.reader = None
        self._control_serial = None
        self._bound_items = set()
        self._bindings = []
        # The all tag also receives events from the separate creation window.
        for sequence, callback in (("<ButtonPress>", self.activity), ("<MouseWheel>", self.activity),
                                   ("<KeyPress>", self.key)):
            funcid = stage.root.bind_all(sequence, callback, add="+")
            self._bindings.append((sequence, funcid))
        if input_stream is not None:
            self.reader = threading.Thread(target=self.read_commands,
                                           args=(input_stream, self.commands), daemon=True)
            self.reader.start()
        self.emit("ready")

    @staticmethod
    def read_commands(stream, commands):
        try:
            for line in stream:
                try:
                    value = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    commands.put(value.get("command"))
        except (OSError, ValueError):
            pass
        finally:
            commands.put("parent_closed")

    def emit(self, state, **fields):
        try:
            self.output_stream.write(PREFIX + json.dumps({"state": state, **fields}) + "\n")
            self.output_stream.flush()
        except (BrokenPipeError, OSError, ValueError):
            self.commands.put("parent_closed")

    def pause(self):
        if not self.closed and not self.clock.paused:
            self.clock.pause()
            self.emit("paused")

    def resume(self):
        if not self.closed:
            self.clock.resume()
            self.emit("running")

    def toggle(self):
        self.resume() if self.clock.paused else self.pause()

    def activity(self, event):
        if event.serial != self._control_serial:
            self.pause()

    def key(self, event):
        if self.closed:
            return
        if event.widget.winfo_toplevel() != self.stage.root:
            self.pause()
            return
        key = event.keysym.lower()
        if key == "escape":
            self.stage.close()
            return "break"
        editing = event.widget.winfo_class() in ("Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox")
        if not editing and key in ("p", "next"):
            self.toggle() if key == "p" else self.next()
            return "break"
        self.pause()

    def next(self):
        if not self.closed:
            self.reason = "next"
            self.emit("next")
            self.stage.close()

    def tick(self):
        if self.closed:
            return
        while True:
            try:
                command = self.commands.get_nowait()
            except queue.Empty:
                break
            if command in ("stop", "parent_closed"):
                self.reason = command
                self.stage.close()
                return
            if command == "next":
                self.next()
                return
            if command == "pause":
                self.pause()
            elif command == "resume":
                self.resume()
            elif command == "toggle":
                self.toggle()
        if self.clock.expired:
            self.next()

    def draw(self):
        if self.closed:
            return
        if self.paint is None:
            from 舞台 import Paint
            self.paint = Paint(self.stage, "tour")
        p = self.paint
        w, h = self.stage.view
        y = -h / 2 + 17
        p.begin()
        p.rect(-w / 2, -h / 2 + 31, w / 2, -h / 2, "#122737")
        state = "已接管 · 切换已暂停" if self.clock.paused else f"{self.clock.remaining} 秒后切换"
        p.text(-w / 2 + 26, y, f"巡展 {self.index}/{self.count}  ·  {state}", "#A8E1CC", 10, "w")
        for x, label, action in ((w / 2 - 340, "P  继续巡展" if self.clock.paused else "P  暂停巡展", self.toggle),
                                 (w / 2 - 190, "PgDn  下一件", self.next),
                                 (w / 2 - 26, "Esc  结束", self.stage.close)):
            item = p.text(x, y, label, "#ECF1F5", 9, "e")
            if item not in self._bound_items:
                def click(event, callback=action):
                    self._control_serial = event.serial
                    # Tk must finish dispatching the Canvas item event before
                    # a callback can destroy the window and its bindings.
                    self.stage.root.after_idle(callback)
                    return "break"
                self.stage.canvas.tag_bind(item, "<Button-1>", click)
                self._bound_items.add(item)
        p.end()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.emit("closed", reason=self.reason)
        # Remove only our callbacks, preserving unrelated application bindings.
        for sequence, funcid in self._bindings:
            self.stage.root._unbind(("bind", "all", sequence), funcid)
        self._bindings.clear()


def attach_tour(stage):
    raw = os.environ.get(ENVIRONMENT)
    if not raw:
        return None
    settings = json.loads(raw)
    if not isinstance(settings, dict):
        raise ValueError("巡展配置应为 JSON 对象。")
    return TourSession(stage, settings)
