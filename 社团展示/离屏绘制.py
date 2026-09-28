"""Optional Pillow rendering of artwork vectors, without Tk or screenshots."""
from functools import lru_cache
import math


class RenderCancelled(RuntimeError):
    """The caller cancelled an offscreen render."""


def _check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise RenderCancelled("已取消高清重绘。")


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _validate(commands, view, size, font_scale):
    if (len(view) != 2 or any(not _number(v) or not 1 <= v <= 1000000 for v in view)
            or len(size) != 2 or any(type(v) is not int or not 1 <= v <= 3840 for v in size)
            or size[0]*size[1] > 3840*2160
            or not math.isclose(size[0]/view[0], size[1]/view[1], rel_tol=1e-9)):
        raise ValueError("绘图尺寸无效或与画幅比例不一致。")
    if not _number(font_scale) or not 0 < font_scale <= 8:
        raise ValueError("字体缩放无效。")
    if len(commands) > 5000:
        raise ValueError("绘图指令过多。")
    coordinate_count = 0
    scale = size[0]/view[0]*2
    for kind, coords, options in commands:
        if kind not in ("rectangle", "oval", "line", "polygon", "text"):
            raise ValueError("不支持的绘图类型：" + str(kind))
        coordinate_count += len(coords)
        if (coordinate_count > 200000 or len(coords) % 2
                or any(not _number(v) or abs(v)*scale > 2**26 for v in coords)):
            raise ValueError("绘图坐标无效或过多。")
        expected = {"rectangle": 4, "oval": 4, "text": 2}.get(kind)
        if ((expected is not None and len(coords) != expected)
                or (kind == "line" and len(coords) < 4)
                or (kind == "polygon" and len(coords) < 6)):
            raise ValueError("绘图坐标不完整。")
        width = options.get("width", 1)
        if not _number(width) or not 0 <= width <= 1000:
            raise ValueError("线条宽度无效。")
        if options.get("dash") or (kind == "polygon" and options.get("smooth")):
            raise ValueError("高清重绘暂不支持虚线或平滑多边形。")
        if kind == "text":
            font = options.get("font", ())
            if (len(font) != 3 or not _number(font[1]) or not 0 < font[1] <= 512
                    or font[1]*font_scale*scale > 16384
                    or options.get("anchor", "center") not in ("center", "w", "e")):
                raise ValueError("字体大小或文字定位无效。")


def _smooth(points, steps=12):
    """Sample the quadratic B-spline used by Canvas smooth lines."""
    if len(points) < 3:
        return points
    def midpoint(a, b):
        return (a[0]+b[0])/2, (a[1]+b[1])/2
    closed = all(math.isclose(a, b, abs_tol=1e-9) for a, b in zip(points[0], points[-1]))
    if closed:
        points = points[:-1]
        start = midpoint(points[-1], points[0])
        segments = [(points[i], midpoint(points[i], points[(i+1) % len(points)]))
                    for i in range(len(points))]
    else:
        start = points[0]
        segments = [(points[i], points[-1] if i == len(points)-2 else midpoint(points[i], points[i+1]))
                    for i in range(1, len(points)-1)]
    result = [start]
    for control, end in segments:
        for index in range(1, steps+1):
            t = index/steps
            result.append(tuple((1-t)**2*start[k] + 2*(1-t)*t*control[k] + t*t*end[k]
                                for k in (0, 1)))
        start = end
    return result


@lru_cache(maxsize=32)
def _font(path, pixels):
    from PIL import ImageFont
    return ImageFont.truetype(path, pixels)


def render_commands(commands, view, size, *, font_paths, font_scale=4/3, cancel=None):
    """Draw ordered logical vectors at the requested size with 2x antialiasing.

    Input coordinates are Canvas x/y around the artwork centre (positive y is
    down). No live Canvas, scene object or image screenshot is read or changed.
    """
    _check_cancel(cancel)
    _validate(commands, view, size, font_scale)
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise RuntimeError("高清重绘需要 Pillow，请安装 requirements-export.txt 中的可选依赖。") from error
    scale = size[0]/view[0]*2
    origin = size[0], size[1]
    image = result = None
    try:
        image = Image.new("RGB", (size[0]*2, size[1]*2), "black")
        draw = ImageDraw.Draw(image)
        for index, (kind, coords, options) in enumerate(commands):
            if index % 32 == 0:
                _check_cancel(cancel)
            if options.get("state") == "hidden":
                continue
            points = [(coords[i]*scale+origin[0], coords[i+1]*scale+origin[1])
                      for i in range(0, len(coords), 2)]
            fill, outline = options.get("fill") or None, options.get("outline") or None
            width = max(1, round(options.get("width", 1)*scale))
            if kind in ("rectangle", "oval"):
                if fill is None and outline is None:
                    continue
                (x1, y1), (x2, y2) = points
                box = (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))
                method = draw.rectangle if kind == "rectangle" else draw.ellipse
                method(box, fill=fill, outline=outline, width=width)
            elif kind == "polygon":
                if fill is not None or outline is not None:
                    draw.polygon(points, fill=fill, outline=outline, width=width)
            elif kind == "line":
                if fill is None:
                    continue
                if options.get("smooth"):
                    points = _smooth(points)
                draw.line(points, fill=fill, width=width, joint="curve")
                if options.get("capstyle", "round") == "round":
                    radius = width/2
                    for x, y in (points[0], points[-1]):
                        draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=fill)
            else:
                _, font_size, weight = options["font"]
                regular, bold = font_paths
                path = (bold or regular) if weight == "bold" else regular
                if not path:
                    raise ValueError("高清重绘需要可用的 TrueType 字体。")
                font = _font(str(path), max(1, round(font_size*font_scale*scale)))
                anchor = {"center": "mm", "w": "lm", "e": "rm"}[options.get("anchor", "center")]
                draw.text(points[0], options.get("text", ""), font=font, fill=fill, anchor=anchor)
        _check_cancel(cancel)
        result = image.resize(size, Image.Resampling.LANCZOS)
        _check_cancel(cancel)
        return result
    except Exception:
        if result is not None:
            result.close()
        raise
    finally:
        if image is not None:
            image.close()
