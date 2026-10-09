"""Small window-free adapter for the two existing recipe-enabled artworks."""
import importlib.util
import math
from pathlib import Path
import sys
from types import SimpleNamespace

DEMO_DIR = Path(__file__).resolve().parents[1] / "社团展示"
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from 舞台 import Artwork
from 创作配方 import default_parameters, validate_parameters
from 高清导出 import _Recorder

WORKS = {25: ("25_星空彼岸花.py", "StarryLily"),
         26: ("26_怦然心动.py", "ParticleHeart")}


class _Viewport:
    aspect = 2
    scale = 1
    offset = (0, 0)
    canvas = None

    @property
    def view(self):
        return Artwork.SIZES.get(self.aspect, (1000, 720))

    def point(self, x, y):
        return x, y

    def in_scene(self, x, y):
        width, height = self.view
        return -width/2 < x < width/2 and -height/2 < y < height/2


def _ignore(*args, **kwargs):
    pass


class _Stage:
    def __init__(self, *args, **kwargs):
        self.artwork = _Viewport()
        self.paused = self.closed = False
        self.root = None
        self.screen = SimpleNamespace(onclick=_ignore, onkey=_ignore)

    hud = staticmethod(_ignore)
    enable_creation = staticmethod(_ignore)


class SceneFrames:
    """Run real scene initialization, frame updates and interactions without Tk.

    Only the freshly loaded scene module gets replacement Stage/Paint names.
    Existing desktop modules and instances are not patched. The caller chooses
    whether a sample advances exactly one fixed step or holds the current state.
    """
    def __init__(self, work_id, parameters=None, fps=30, *, hide_lettering=False):
        if type(work_id) is not int or work_id not in WORKS:
            raise ValueError("离屏动画当前支持作品 25 和 26。")
        if type(fps) is not int or fps not in (24, 30):
            raise ValueError("固定帧率请选择 24 或 30。")
        params = dict(default_parameters(work_id), aspect=2)
        if parameters is not None:
            params.update(parameters)
        params = validate_parameters(work_id, params)
        if params["aspect"] not in Artwork.SIZES:
            raise ValueError("离屏动画需要固定画幅。")
        filename, class_name = WORKS[work_id]
        path = DEMO_DIR / filename
        spec = importlib.util.spec_from_file_location(f"video_scene_{work_id}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.Stage = _Stage
        module.Paint = lambda artwork, tag: _Recorder(artwork.view)
        self.app = getattr(module, class_name)()
        self.app.apply_parameters(params)
        self.app.reset()
        self.view = Artwork.SIZES[params["aspect"]]
        self.app.paint = _Recorder(self.view)
        self.work_id, self.fps = work_id, fps
        self.hide_lettering = hide_lettering

    def commands(self, dt=0):
        if (type(dt) not in (int, float) or not math.isfinite(dt)
                or dt not in (0, 1/self.fps)):
            raise ValueError("每次采样只能保持当前帧或推进一个固定时间步。")
        self.app.frame(dt)
        return tuple((kind, coords, dict(options)) for kind, coords, options in self.app.paint.commands
                     if not (self.hide_lettering and kind == "text"))

    def render(self, size, font_paths, dt=0):
        from 离屏绘制 import render_commands
        return render_commands(self.commands(dt), self.view, size, font_paths=font_paths)

    def event(self, action, x=0, y=0):
        allowed = {25: {"replay", "meteor", "theme"}, 26: {"burst", "theme"}}
        if not isinstance(action, str) or action not in allowed[self.work_id]:
            raise ValueError("此作品不支持该录制操作。")
        if (type(x) not in (int, float) or type(y) not in (int, float)
                or not math.isfinite(x) or not math.isfinite(y)):
            raise ValueError("输入坐标必须是有限数值。")
        method = getattr(self.app, "change_theme" if action == "theme" else action)
        if action in ("meteor", "burst"):
            method(x, y)
        else:
            method()
