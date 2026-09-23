"""Rebuild authentic gallery previews and README media (optional Pillow, Windows desktop).

    python tools/render_media.py --originals --gif --compose

The application itself has no Pillow dependency. Capture helpers execute one work
at a time in a separate process and write only project-owned image files.
"""
import argparse
import ast
import contextlib
import ctypes
import importlib.util
import io
import math
from pathlib import Path
import random
import runpy
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
ORIGINALS = ASSETS / "originals"
WORK = ROOT / ".work" / "media"


def font(size, bold=False, mono=False):
    candidates = ["C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    if mono:
        candidates.insert(0, "C:/Windows/Fonts/consola.ttf")
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def works():
    sys.path.insert(0, str(ROOT))
    from run import catalog
    return catalog().WORKS


def grab(root):
    if sys.platform != "win32":
        raise RuntimeError("Window capture requires a Windows desktop; --compose works from existing images.")
    root.update_idletasks()
    root.update()
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    user32.GetAncestor.restype = ctypes.c_void_p
    return ImageGrab.grab(window=user32.GetAncestor(root.winfo_id(), 2)).convert("RGB")


def rounded_image(destination, picture, box, radius=14):
    x, y, width, height = box
    picture = ImageOps.fit(picture.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (width, height))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    destination.paste(picture, (x, y), mask)


def load_scene(number):
    path = ROOT / "社团展示" / "previews" / f"{number:02}.png"
    with Image.open(path) as original:
        return original.crop((4, 101, original.width - 4, original.height - 65)).convert("RGB")


def compose():
    ASSETS.mkdir(parents=True, exist_ok=True)
    exhibits = ASSETS / "exhibits"
    exhibits.mkdir(exist_ok=True)
    for number in range(1, 11):
        ImageOps.fit(load_scene(number), (800, 464), method=Image.Resampling.LANCZOS).save(
            exhibits / f"{number:02}.png", optimize=True)
    hero = Image.new("RGB", (1440, 790), "#0A1423")
    draw = ImageDraw.Draw(hero)
    for x in range(-200, 1441, 45):
        draw.line((x, 0, x + 300, 790), fill="#102034", width=1)
    draw.text((64, 57), "PYTHON  ×  TURTLE", font=font(17, bold=True), fill="#8ED6C9")
    draw.text((58, 152), "TURTLE", font=font(78, bold=True), fill="#F4F4E9")
    draw.text((58, 239), "GALLERY", font=font(78, bold=True), fill="#C4EEE0")
    draw.text((66, 352), "海龟画廊", font=font(31), fill="#D8E5E6")
    draw.text((66, 410), "用代码，点亮一个小世界。", font=font(21), fill="#9EB3C6")
    for x, text in [(66, "10 款互动作品"), (251, "14 个原始创意")]:
        draw.rounded_rectangle((x, 480, x + 166, 525), radius=10, fill="#1D3541", outline="#365360")
        draw.text((x + 17, 490), text, font=font(17), fill="#BFE6DB")
    draw.text((66, 644), "标准库运行  ·  点击交互  ·  每一幅都能改", font=font(16), fill="#A6B7C6")
    draw.text((66, 681), "github.com/zjh-b/turtle-gallery", font=font(15, mono=True), fill="#6E8C9F")
    for number, title, x, y in [(1, "LIGHT UP THE NIGHT", 620, 80), (3, "SYMMETRY IN BLOOM", 1006, 80),
                                 (4, "A QUIET KOI POND", 620, 402), (7, "LET THE OCEAN GLOW", 1006, 402)]:
        draw.rounded_rectangle((x - 10, y - 10, x + 355, y + 279), radius=18, fill="#142437", outline="#2C4356")
        rounded_image(hero, load_scene(number), (x, y, 345, 231), 10)
        draw.text((x + 5, y + 246), title, font=font(12, bold=True), fill="#B9C6D1")
    hero.save(ASSETS / "hero.png", optimize=True)

    originals = [work for work in works() if work["collection"] == "original"]
    board = Image.new("RGB", (1440, 1200), "#101A2A")
    draw = ImageDraw.Draw(board)
    draw.text((40, 29), "从第一笔开始  /  ORIGINAL SKETCHBOOK", font=font(28, True), fill="#E7EBD9")
    draw.text((40, 78), "14 个原始创意：几何、角色、动画、小游戏与生活小工具", font=font(18), fill="#9DB6C6")
    for index, work in enumerate(originals):
        x, y = 40 + index % 4 * 350, 130 + index // 4 * 257
        source = ORIGINALS / f"{work['id']:02}.png"
        if not source.exists():
            continue
        draw.rounded_rectangle((x, y, x + 327, y + 235), radius=12, fill="#1C2B3E")
        with Image.open(source) as picture:
            # Keep the complete original composition visible in wider cards.
            picture = picture.convert("RGB")
            if work["id"] not in (20, 22):
                picture = picture.crop((5, 5, picture.width - 5, picture.height - 5))
            for suffix, size in (("thumb", (244, 154)), ("compact", (220, 126))):
                ImageOps.pad(picture, size, method=Image.Resampling.LANCZOS, color="#101A2A").save(
                    ORIGINALS / f"{work['id']:02}_{suffix}.png", optimize=True)
            contained = ImageOps.contain(picture, (307, 182), method=Image.Resampling.LANCZOS)
            padded = Image.new("RGB", (307, 182), picture.getpixel((10, 10)))
            padded.paste(contained, ((307 - contained.width) // 2, (182 - contained.height) // 2))
            rounded_image(board, padded, (x + 10, y + 10, 307, 182), 8)
        draw.text((x + 13, y + 203), f"{work['number']}  {work['title']}", font=font(16), fill="#DEE7E8")
    draw.text((744, 974), "每一个作品，都能找到源代码。", font=font(24, True), fill="#BEE1D3")
    draw.text((744, 1025), "在画廊中选择「原始创意」，继续你的下一笔。", font=font(17), fill="#92ACBD")
    draw.text((40, 1160), "便签为原作提示语排版预览；月饼计算展示真实终端输出。其余为原作运行画面。", font=font(14), fill="#7F98AD")
    board.save(ASSETS / "originals.png", optimize=True)
    print("Composed hero.png and originals.png")


def original_capture(number):
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    destination = ORIGINALS / f"{number:02}.png"
    if number == 20:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        messages = next(ast.literal_eval(node.value) for node in tree.body
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "messages" for t in node.targets))
        picture = Image.new("RGB", (900, 560), "#EEE9E4")
        d = ImageDraw.Draw(picture)
        d.text((52, 42), "温柔便签", font=font(32, True), fill="#665565")
        for i, message in enumerate((messages[1], messages[4], messages[9], messages[13])):
            x, y = 55 + i % 2 * 410, 128 + i // 2 * 175
            color = ["#FFCAD6", "#BBDEEE", "#E5D1F0", "#CDE6D9"][i]
            d.rounded_rectangle((x, y, x + 378, y + 143), radius=10, fill=color)
            d.text((x + 24, y + 18), "亲爱的你啊", font=font(16), fill="#75677B")
            d.text((x + 24, y + 67), message, font=font(24), fill="#54465B")
        d.text((55, 510), "原作提示语排版预览 · 运行后会在桌面生成随机便签", font=font(16), fill="#817588")
        picture.save(destination)
        return
    if number == 22:
        import builtins
        original_input = builtins.input
        values = iter(("", "26", "6", "q"))
        output = io.StringIO()
        def answer(prompt=""):
            value = next(values)
            print(prompt + value)
            return value
        try:
            builtins.input = answer
            with contextlib.redirect_stdout(output):
                runpy.run_path(str(path), run_name="__main__")
        finally:
            builtins.input = original_input
        picture = Image.new("RGB", (900, 560), "#102234")
        d = ImageDraw.Draw(picture)
        d.rounded_rectangle((35, 35, 865, 525), radius=14, fill="#152D40", outline="#3C5C6A")
        d.text((64, 54), "PYTHON  /  月饼装盒计算", font=font(22, True), fill="#8FDBC4")
        for index, line in enumerate(output.getvalue().splitlines()):
            d.text((65, 120 + index * 38), line, font=font(21), fill="#E4E9DD")
        picture.save(destination)
        return

    import turtle
    import tkinter
    random.seed(7)
    screen = turtle.Screen()
    screen.setup(1000, 740, 20, 20)
    screen.tracer(0)
    if number == 17:
        # Fit the tall original tree in the capture window without changing its source.
        width, height = screen._window_size()
        half_width = 600
        half_height = half_width * (height - 20) / (width - 20)
        screen.setworldcoordinates(-half_width, 150 - half_height, half_width, 150 + half_height)
    saved = False
    class Captured(BaseException):
        pass
    def capture(*args):
        nonlocal saved
        if not saved:
            saved = True
            sys.settrace(None)
            screen.update()
            grab(screen.getcanvas().winfo_toplevel()).save(destination)
        raise Captured()
    turtle.done = capture
    turtle.mainloop = capture
    turtle.TurtleScreen.mainloop = capture
    time.sleep = lambda seconds: None
    syntax = ast.parse(path.read_text(encoding="utf-8-sig"))
    loop = next((node.lineno for node in syntax.body if isinstance(node, ast.While)), None)
    if number in (19, 24):
        loop = next(node.lineno for node in syntax.body if isinstance(node, ast.For))
    visits = 0
    def trace(frame, event, arg):
        nonlocal visits
        if event == "line" and frame.f_code.co_filename == str(path) and frame.f_lineno == loop:
            visits += 1
            if number == 23 and visits == 1:
                needle = frame.f_globals["Needle"]
                for angle in range(0, 360, 45):
                    item = needle()
                    item.angle = angle
                    frame.f_globals["needles"].append(item)
            # Clock drawing happens inside the loop: capture its completed first frame.
            if visits >= (2 if number in (16, 21, 23) else 1):
                capture()
        return trace if frame.f_code.co_filename == str(path) else None
    try:
        if loop:
            sys.settrace(trace)
        runpy.run_path(str(path), run_name="__main__")
        capture()
    except Captured:
        pass
    finally:
        sys.settrace(None)
        try:
            screen.bye()
        except (turtle.Terminator, tkinter.TclError):
            pass


def animation_capture(number):
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("capture_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    classes = {1: "Fireworks", 3: "Kaleidoscope", 4: "Pond", 6: "SeasonTree", 7: "Jellyfish", 10: "Breakout"}
    random.seed(13)
    app = getattr(module, classes[number])()
    app.stage.root.geometry("960x700+20+20")
    app.stage.root.update()
    app.reset()
    if number == 4:
        app.feed(140 * app.stage.scale, 20 * app.stage.scale)
    if number == 10:
        app.autoplay = True
        for _ in range(22):
            app.update(0.05)
    for index in range(16):
        app.frame(0.12)
        app.stage.screen.update()
        picture = grab(app.stage.root)
        picture = picture.crop((4, 92, picture.width - 4, picture.height - 60))
        picture.save(WORK / f"{number:02}_{index:02}.png")
    app.stage.close()


def make_gif():
    WORK.mkdir(parents=True, exist_ok=True)
    selected = (1, 4, 6, 7, 3, 10)
    titles = {work["id"]: work["title"] for work in works()}
    for number in selected:
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-animation", str(number)], check=True, timeout=60)
    frames = []
    for sequence, number in enumerate(selected):
        for index in range(16):
            frame = Image.new("RGB", (720, 475), "#111D2C")
            d = ImageDraw.Draw(frame)
            d.text((22, 13), f"{number:02}  {titles[number]}", font=font(22, True), fill="#E2ECE3")
            d.text((507, 22), "TURTLE GALLERY", font=font(12, True), fill="#8DCABF")
            with Image.open(WORK / f"{number:02}_{index:02}.png") as picture:
                rounded_image(frame, picture, (16, 57, 688, 385), 9)
            for dot in range(len(selected)):
                x = 314 + dot * 18
                d.ellipse((x, 455, x + 5, 460), fill="#B6E5D1" if sequence == dot else "#3B5164")
            frames.append(frame)
    samples = Image.new("RGB", (192 * 6, 128))
    for i in range(6):
        samples.paste(frames[i * 16].resize((192, 128)), (i * 192, 0))
    palette = samples.quantize(colors=160)
    converted = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    converted[0].save(ASSETS / "showcase.gif", save_all=True, append_images=converted[1:], duration=120,
                      loop=0, optimize=True, disposal=1)
    print(f"Wrote showcase.gif ({(ASSETS / 'showcase.gif').stat().st_size / 1024 / 1024:.2f} MiB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originals", action="store_true")
    parser.add_argument("--compose", action="store_true")
    parser.add_argument("--gif", action="store_true")
    parser.add_argument("--capture-original", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--capture-animation", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    if args.capture_original:
        original_capture(args.capture_original)
        return
    if args.capture_animation:
        animation_capture(args.capture_animation)
        return
    if args.originals:
        for work in works():
            if work["collection"] == "original":
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-original", str(work["id"])],
                               check=True, timeout=60)
                print(f"Captured original {work['number']}", flush=True)
    if args.gif:
        make_gif()
    if args.compose:
        compose()


if __name__ == "__main__":
    main()
