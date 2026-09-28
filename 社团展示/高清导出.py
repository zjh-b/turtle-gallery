"""Freeze scene geometry on the UI thread, then redraw and save without Tk."""
import copy
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import queue
import threading
from types import SimpleNamespace

from 舞台 import Artwork, FONT, Paint
from 创作配方 import make_recipe, validate_parameters
from 作品导出 import ExportCancelled, export_support, save_png


def target_size(aspect, resolution):
    if type(aspect) is not int or aspect not in (1, 2, 3):
        raise ValueError("高清重绘请先选择横屏 16:9、竖屏 9:16 或方形 1:1 画幅。")
    if type(resolution) is not int or resolution not in (1080, 2160):
        raise ValueError("请选择 1080 或 2160 高清重绘尺寸。")
    return {1: (resolution*16//9, resolution),
            2: (resolution, resolution*16//9),
            3: (resolution, resolution)}[aspect]


def _font_paths():
    folder = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    regular = next((folder/name for name in ("msyh.ttc", "msyh.ttf")
                    if (folder/name).is_file()), None)
    if regular is None:
        raise RuntimeError("高清重绘需要 Windows 微软雅黑字体（msyh.ttc）。仍可选择当前窗口像素导出。")
    bold = next((folder/name for name in ("msyhbd.ttc", "msyhbd.ttf")
                 if (folder/name).is_file()), regular)
    return str(regular), str(bold)


def redraw_support():
    available, reason = export_support()
    if not available:
        return available, reason
    try:
        _font_paths()
    except RuntimeError as error:
        return False, str(error)
    return True, ""


class _Recorder(Paint):
    """Use the shared primitives and transforms at logical, unrounded precision."""
    def __init__(self, view):
        super().__init__(SimpleNamespace(scale=1, offset=(0, 0), view=view, canvas=None), "artwork")
        self.commands = []

    def begin(self):
        self.commands.clear()
        self.transform()

    def _put(self, kind, points, **options):
        coords = tuple((value*self.scale + self.offset[i % 2]) * (1 if i % 2 == 0 else -1)
                       for i, value in enumerate(points))
        self.commands.append((kind, coords, options))
        return len(self.commands)

    def text(self, x, y, text, color, size=12, anchor="center", bold=False):
        return self._put("text", (x, y), text=text, fill=color, anchor=anchor,
                         font=(FONT, size*self.scale, "bold" if bold else "normal"))

    def end(self):
        pass


@dataclass(frozen=True)
class FrozenArtwork:
    work_id: int
    aspect: int
    view: tuple
    commands: tuple
    parameters: dict
    animation: dict
    font_scale: float


def freeze_artwork(app):
    """Copy a supported scene's present drawing, without a window or time step.

    The two registered scenes read shared geometry in frame(0); only their
    scalar time fields receive +=0. A shallow scene copy plus a fresh stage and
    recorder isolates those writes and prevents every live Canvas operation.
    """
    if app.stage.closed:
        raise RuntimeError("作品窗口已关闭，无法导出。")
    if app.WORK_ID not in (25, 26):
        raise ValueError("这件作品暂不支持高清重绘。")
    parameters = validate_parameters(app.WORK_ID, app.get_parameters())
    aspect = parameters["aspect"]
    target_size(aspect, 1080)
    view = Artwork.SIZES[aspect]
    recorder = _Recorder(view)
    clone = copy.copy(app)
    clone.stage = SimpleNamespace(artwork=SimpleNamespace(aspect=aspect, view=view),
                                  hud=lambda *args: None)
    clone.paint = recorder
    clone.frame(0)
    animation = {key: copy.deepcopy(getattr(app, key)) for key in
                 ("time", "bloom", "meteors", "beat_time", "burst_age") if hasattr(app, key)}
    interpreter = getattr(app.stage.root, "tk", None)
    font_scale = float(interpreter.call("tk", "scaling")) if interpreter is not None else 4/3
    if not math.isfinite(font_scale) or not 0 < font_scale <= 8:
        raise ValueError("无法读取当前窗口的字体缩放。")
    return FrozenArtwork(app.WORK_ID, aspect, view, tuple(recorder.commands),
                         parameters, animation, font_scale)


def render_snapshot(snapshot, resolution, cancel=None):
    size = target_size(snapshot.aspect, resolution)
    available, reason = redraw_support()
    if not available:
        raise RuntimeError(reason)
    from 离屏绘制 import render_commands
    return render_commands(snapshot.commands, snapshot.view, size,
                           font_paths=_font_paths(), font_scale=snapshot.font_scale, cancel=cancel)


class ExportJob:
    """One cancellable background export. The worker never calls Tk."""
    def __init__(self, snapshot, path, resolution):
        self.size = target_size(snapshot.aspect, resolution)
        self._cancel = threading.Event()
        self._results = queue.Queue()
        # A non-daemon thread gets to remove its temporary PNG on application
        # close. Both drawing and the atomic save observe the cancellation flag.
        self.thread = threading.Thread(target=self._run, args=(snapshot, Path(path), resolution),
                                       name="gallery-png-export", daemon=False)
        self.thread.start()

    def cancel(self):
        self._cancel.set()

    def poll(self):
        try:
            return self._results.get_nowait()
        except queue.Empty:
            return None

    def _run(self, snapshot, path, resolution):
        picture = None
        try:
            if self._cancel.is_set():
                raise ExportCancelled("已取消导出。")
            picture = render_snapshot(snapshot, resolution, cancel=self._cancel)
            if self._cancel.is_set():
                raise ExportCancelled("已取消导出。")
            metadata = {"Software": "Turtle Gallery", "Work": str(snapshot.work_id),
                        "Parameters": json.dumps(snapshot.parameters, ensure_ascii=False),
                        "Recipe": make_recipe(snapshot.work_id, snapshot.parameters),
                        "Animation": snapshot.animation, "Resolution": list(self.size),
                        "Renderer": "Pillow vector redraw, 2x antialiasing"}
            size = save_png(picture, path, metadata, cancel=self._cancel)
            result = {"state": "saved", "size": size, "path": str(path.resolve())}
        except Exception as error:
            result = ({"state": "cancelled", "message": "已取消导出，原文件保持不变。"}
                      if self._cancel.is_set() or isinstance(error, ExportCancelled)
                      else {"state": "error", "message": str(error)})
        finally:
            if picture is not None:
                picture.close()
        self._results.put(result)
