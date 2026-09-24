"""Optional Windows PNG snapshots; importing this module requires only Python."""
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import sys
import tempfile

INSTALL_COMMAND = "python -m pip install -r requirements-export.txt"


def export_support():
    """Report whether this system has the optional window-capture dependency."""
    if sys.platform != "win32":
        return False, "PNG 导出当前支持 Windows 桌面。"
    try:
        import PIL
        from PIL import ImageGrab
        version = tuple(int(part) for part in PIL.__version__.split(".")[:3])
        if version < (11, 2, 1):
            raise ImportError("Pillow version is too old")
    except (ImportError, AttributeError, ValueError):
        return False, "PNG 导出需要 Pillow 11.2.1 或更新版本，请运行：" + INSTALL_COMMAND
    return True, ""


def _user32():
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    for name in ("IsWindow", "IsIconic", "IsWindowVisible"):
        function = getattr(user32, name)
        function.argtypes = [wintypes.HWND]
        function.restype = wintypes.BOOL
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ClientToScreen.restype = wintypes.BOOL
    return user32


def _window_info(root, canvas):
    """Return root HWND, client size, and Canvas bounds in that client area."""
    user32 = _user32()
    hwnd = user32.GetAncestor(root.winfo_id(), 2)  # GA_ROOT, not the creator panel.
    if not hwnd or not user32.IsWindow(hwnd):
        raise RuntimeError("作品窗口已关闭，无法导出。")
    if user32.IsIconic(hwnd):
        raise RuntimeError("请先还原作品窗口，再导出 PNG。")
    if not user32.IsWindowVisible(hwnd):
        raise RuntimeError("作品窗口不可见，请显示窗口后再导出。")

    client, drawing = wintypes.RECT(), wintypes.RECT()
    origin, drawing_origin = wintypes.POINT(), wintypes.POINT()
    canvas_hwnd = canvas.winfo_id()
    if not (user32.GetClientRect(hwnd, ctypes.byref(client))
            and user32.GetClientRect(canvas_hwnd, ctypes.byref(drawing))
            and user32.ClientToScreen(hwnd, ctypes.byref(origin))
            and user32.ClientToScreen(canvas_hwnd, ctypes.byref(drawing_origin))):
        raise RuntimeError("无法读取作品窗口尺寸，请稍后重试。")
    size = (client.right - client.left, client.bottom - client.top)
    bounds = (drawing_origin.x - origin.x, drawing_origin.y - origin.y,
              drawing.right - drawing.left, drawing.bottom - drawing.top)
    if min(*size, *bounds[2:]) <= 0:
        raise RuntimeError("作品窗口的绘图区尺寸无效。")
    return hwnd, size, bounds


def _artwork_box(canvas, scale, image_size, client_size, canvas_bounds):
    """Map Turtle's y=+265..-285 scene to existing screenshot pixels."""
    image_width, image_height = image_size
    client_width, client_height = client_size
    x, y, width, height = canvas_bounds
    tk_width, tk_height = canvas.winfo_width(), canvas.winfo_height()
    if min(image_width, image_height, client_width, client_height,
           width, height, tk_width, tk_height) <= 0:
        raise RuntimeError("作品窗口的绘图区尺寸无效。")
    # Win32, Tk, and Pillow may report different units under desktop scaling.
    # Pillow's HWND capture returns the client area, without the title/border.
    pixel_x, pixel_y = image_width / client_width, image_height / client_height
    tk_x, tk_y = width / tk_width, height / tk_height
    border = sum(canvas.winfo_pixels(canvas.cget(option))
                 for option in ("borderwidth", "highlightthickness"))
    top = max(border, -265 * scale - canvas.canvasy(0))
    bottom = min(tk_height - border, 285 * scale - canvas.canvasy(0))
    left = max(0, math.ceil((x + border * tk_x) * pixel_x))
    right = min(image_width, math.floor((x + width - border * tk_x) * pixel_x))
    top = max(0, math.ceil((y + top * tk_y) * pixel_y))
    bottom = min(image_height, math.floor((y + bottom * tk_y) * pixel_y))
    if left >= right or top >= bottom:
        raise RuntimeError("作品窗口没有可导出的绘图区。")
    return left, top, right, bottom


def capture_artwork(stage):
    """Freeze the visible artwork as RGB pixels, excluding HUD and borders.

    Uses Pillow's Windows HWND capture (available since 11.2.1). The image is
    never enlarged, and no desktop capture is used as a fallback. This function
    neither advances animation timers nor changes the window or pause state.
    """
    available, reason = export_support()
    if not available:
        raise RuntimeError(reason)
    if stage.closed:
        raise RuntimeError("作品窗口已关闭，无法导出。")
    from PIL import ImageGrab

    stage.root.update_idletasks()
    canvas = getattr(stage.canvas, "_canvas", stage.canvas)
    hwnd, client_size, canvas_bounds = _window_info(stage.root, canvas)
    picture = ImageGrab.grab(window=hwnd)
    box = _artwork_box(canvas, stage.scale, picture.size, client_size, canvas_bounds)
    return picture.crop(box).convert("RGB")


def save_png(image, path, metadata=None):
    """Atomically write the frozen image; metadata describes only this snapshot."""
    pnginfo = None
    if metadata is not None:
        from PIL.PngImagePlugin import PngInfo
        pnginfo = PngInfo()
        pnginfo.add_text("turtle_gallery", json.dumps(metadata, ensure_ascii=False, allow_nan=False))
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=path.name + ".",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            image.save(stream, format="PNG", pnginfo=pnginfo)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return image.size
