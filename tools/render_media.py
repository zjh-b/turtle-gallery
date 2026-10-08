"""Rebuild authentic gallery previews and README media (optional Pillow, Windows desktop).

    python tools/render_media.py --originals --gif --compose
    python tools/render_media.py --social --compose
    python tools/render_media.py --creator
    python tools/render_media.py --aspects
    python tools/render_media.py --hd
    python tools/render_media.py --exhibits 2 6 9
    python tools/render_media.py --original-ids 14 15 24 --compose-originals

The application itself has no Pillow dependency. Capture helpers execute one work
at a time in a separate process and write only project-owned image files.
"""
import argparse
import ctypes
import importlib.util
import math
from pathlib import Path
import random
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageGrab, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
ORIGINALS = ASSETS / "originals"
WORK = ROOT / ".work" / "media"
SOCIAL_IDS = (25, 26, 27, 28)
SOCIAL_FRAMES = 24


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


def rounded_image(destination, picture, box, radius=14, contain=False):
    x, y, width, height = box
    if contain:
        picture = ImageOps.pad(picture.convert("RGB"), (width, height),
                               method=Image.Resampling.LANCZOS, color="#111827")
    else:
        picture = ImageOps.fit(picture.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (width, height))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    destination.paste(picture, (x, y), mask)


def load_scene(number):
    path = ROOT / "社团展示" / "previews" / f"{number:02}.png"
    with Image.open(path) as original:
        if number in SOCIAL_IDS:
            return original.convert("RGB")
        return original.crop((4, 101, original.width - 4, original.height - 65)).convert("RGB")


def compose():
    ASSETS.mkdir(parents=True, exist_ok=True)
    exhibits = ASSETS / "exhibits"
    exhibits.mkdir(exist_ok=True)
    catalog = works()
    for number in (work["id"] for work in catalog if work["collection"] == "interactive"):
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
    interactive_count = sum(work["collection"] == "interactive" for work in catalog)
    original_count = len(catalog) - interactive_count
    for x, text in [(66, f"{interactive_count} 款互动作品"), (251, f"{original_count} 个原始创意")]:
        draw.rounded_rectangle((x, 480, x + 166, 525), radius=10, fill="#1D3541", outline="#365360")
        draw.text((x + 17, 490), text, font=font(17), fill="#BFE6DB")
    draw.text((66, 644), "标准库运行  ·  点击交互  ·  每一幅都能改", font=font(16), fill="#A6B7C6")
    draw.text((66, 681), "github.com/zjh-b/turtle-gallery", font=font(15, mono=True), fill="#6E8C9F")
    for number, title, x, y in [(25, "STARRY SPIDER LILY", 620, 80), (26, "A HEART MADE OF LIGHT", 1006, 80),
                                 (27, "A ROSE IN THE GALAXY", 620, 402), (28, "WINGS OF LIGHT", 1006, 402)]:
        draw.rounded_rectangle((x - 10, y - 10, x + 355, y + 279), radius=18, fill="#142437", outline="#2C4356")
        rounded_image(hero, load_scene(number), (x, y, 345, 231), 10, contain=True)
        draw.text((x + 5, y + 246), title, font=font(12, bold=True), fill="#B9C6D1")
    hero.save(ASSETS / "hero.png", optimize=True)

    compose_originals()
    print("Composed hero.png")


def compose_originals():
    """Update the original-work contact sheet without rewriting other collections."""
    ASSETS.mkdir(parents=True, exist_ok=True)

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
    print("Composed originals.png")


def social_capture(number):
    """Capture genuine program frames, using a deterministic simulation clock."""
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("capture_social", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    random.seed(2026)
    app = getattr(module, work["entry_class"])()
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        app.stage.root.geometry("1000x720+20+20")
        app.stage.root.update()
        app.reset()

        def picture():
            app.stage.screen.update()
            raw = grab(app.stage.root)
            # Frame the artwork within the shared HUD's top and bottom panels.
            width, height, scale = app.stage.width, app.stage.height, app.stage.scale
            left = max(0, (raw.width - width) // 2)
            top = max(0, raw.height - height - left)
            return raw.crop((left, top + round(height / 2 - 265 * scale),
                             left + width, top + round(height / 2 + 285 * scale)))

        for index in range(SOCIAL_FRAMES):
            # Smaller simulation steps match the application's interactive clock.
            for _ in range(3):
                app.frame(0.05)
            picture().save(WORK / f"social_{number:02}_{index:02}.png")
        for _ in range(80):
            app.frame(0.05)
        still = picture()
        previews = ROOT / "社团展示" / "previews"
        previews.mkdir(exist_ok=True)
        still.save(previews / f"{number:02}.png", optimize=True)
        for suffix, size in (("thumb", (244, 154)), ("compact", (220, 126))):
            ImageOps.pad(still, size, method=Image.Resampling.LANCZOS, color="#101A2A").save(
                previews / f"{number:02}_{suffix}.png", optimize=True)
        destination = ASSETS / "exhibits"
        destination.mkdir(exist_ok=True)
        ImageOps.fit(still, (800, 464), method=Image.Resampling.LANCZOS).save(
            destination / f"{number:02}.png", optimize=True)
        print(f"Captured new work {number}", flush=True)
    finally:
        app.stage.close()


def exhibit_capture(number):
    """Refresh one registered interactive work at a fixed two-second pose."""
    work = next(work for work in works() if work["id"] == number)
    if work["collection"] != "interactive" or not work.get("entry_class"):
        raise ValueError("--exhibits requires registered interactive work IDs")
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    from 作品导出 import capture_artwork
    spec = importlib.util.spec_from_file_location("capture_exhibit", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    random.seed(2026)
    app = getattr(module, work["entry_class"])()
    try:
        app.stage.root.geometry("1000x720+20+20")
        app.stage.root.update()
        app.reset()
        for _ in range(50):
            app.frame(.04)
        app.stage.screen.update()
        artwork = capture_artwork(app.stage)
        previews = ROOT / "社团展示" / "previews"
        previews.mkdir(exist_ok=True)
        # Legacy previews include the window; the newer romantic series uses
        # artwork-only previews. Keep load_scene()'s existing framing contract.
        (artwork if number in SOCIAL_IDS else grab(app.stage.root)).save(
            previews / f"{number:02}.png", optimize=True)
        for suffix, size in (("thumb", (244, 154)), ("compact", (220, 126))):
            ImageOps.pad(artwork, size, method=Image.Resampling.LANCZOS, color="#101A2A").save(
                previews / f"{number:02}_{suffix}.png", optimize=True)
        destination = ASSETS / "exhibits"
        destination.mkdir(exist_ok=True)
        ImageOps.fit(artwork, (800, 464), method=Image.Resampling.LANCZOS).save(
            destination / f"{number:02}.png", optimize=True)
        print(f"Captured exhibit {number:02} at t=2s", flush=True)
    finally:
        app.stage.close()


def creator_capture():
    """Capture the actual artwork and parameter window for the creation guide."""
    work = next(work for work in works() if work["id"] == 25)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    from 创作配方 import preset_parameters
    spec = importlib.util.spec_from_file_location("capture_creator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, work["entry_class"])()
    try:
        app.stage.root.geometry("1000x720+20+20")
        app.stage.root.update()
        app.stage.reset_action = app.reset
        app.apply_parameters(preset_parameters(25, 1))
        app.reset()
        app.frame(8)
        app.stage.screen.update()
        app.stage.open_creation()
        panel = app.stage.creator_panel
        panel.status.set("参数随手可调，保存配方留住这一幅。")
        app.stage.root.update()
        artwork, controls = grab(app.stage.root), grab(panel.window)
        board = Image.new("RGB", (1440, 930), "#0B1424")
        draw = ImageDraw.Draw(board)
        draw.text((40, 25), "创作工坊 / MAKE IT YOURS", font=font(34, True), fill="#EAF1F5")
        draw.text((42, 79), "调一缕微风，换一片星河，把喜欢的参数保存下来。", font=font(19), fill="#A7BACB")
        rounded_image(board, artwork, (30, 150, 950, 684), 12, contain=True)
        rounded_image(board, controls, (1005, 118, 405, 771), 12, contain=True)
        draw.text((42, 868), "25 星空彼岸花  /  26 怦然心动    ·    按 E 或点击右上角打开", font=font(18), fill="#A8E1CC")
        board.save(ASSETS / "creator.png", optimize=True)
        print("Captured creator.png from the artwork and live parameter panel", flush=True)
    finally:
        app.stage.close()


def social_capture_is_current(work):
    """Reuse a capture only when all its artifacts include current scene code."""
    number = work["id"]
    scene_directory = ROOT / "社团展示"
    dependencies = [Path(__file__).resolve(), ROOT / work["filename"]]
    dependencies.extend(scene_directory / name for name in
                        ("舞台.py", "创作配方.py", "创作工坊.py", "作品目录.py"))
    modified = max(path.stat().st_mtime_ns for path in dependencies)
    previews = scene_directory / "previews"
    outputs = [previews / f"{number:02}{suffix}.png" for suffix in ("", "_thumb", "_compact")]
    outputs.append(ASSETS / "exhibits" / f"{number:02}.png")
    outputs.extend(WORK / f"social_{number:02}_{index:02}.png" for index in range(SOCIAL_FRAMES))
    return all(path.is_file() and path.stat().st_mtime_ns >= modified for path in outputs)


def aspect_capture(number):
    """Capture the same frozen scene in each composition, using public export."""
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    from 创作配方 import preset_parameters
    from 作品导出 import capture_artwork
    spec = importlib.util.spec_from_file_location("capture_aspect", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, work["entry_class"])()
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        app.stage.root.geometry("1100x900+20+20")
        app.stage.root.update()
        parameters = preset_parameters(number, 1 if number == 25 else 2)
        app.apply_parameters(parameters)
        app.frame(8)
        for aspect in (1, 2, 3):
            parameters["aspect"] = aspect
            app.apply_parameters(parameters)
            app.frame(0)
            app.stage.screen.update()
            picture = capture_artwork(app.stage)
            rw, rh = app.stage.artwork.ratio
            assert picture.width*rh == picture.height*rw, picture.size
            picture.save(WORK / f"aspect-{number}-{aspect}.png")
            print(f"Captured {number} / {rw}:{rh}: {picture.width} x {picture.height}", flush=True)
    finally:
        app.stage.close()


def make_aspects():
    for number in (25, 26):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-aspect", str(number)],
                       check=True, timeout=45)
    board = Image.new("RGB", (1320, 990), "#0B1424")
    draw = ImageDraw.Draw(board)
    draw.text((40, 28), "一幅心意，三种构图", font=font(34, True), fill="#EDF1F5")
    draw.text((42, 83), "横屏展示 · 竖屏分享 · 方形收藏   /   实际运行画面", font=font(19), fill="#A7BACB")
    for x, text in ((42, "16:9 / 横屏"), (650, "9:16 / 竖屏"), (906, "1:1 / 方形")):
        draw.text((x, 128), text, font=font(16), fill="#A8E1CC")
    for row, (number, title) in enumerate(((25, "星空彼岸花"), (26, "怦然心动"))):
        y = 170 + row*400
        for aspect, x, width, height in ((1, 40, 560, 315), (2, 650, 180, 320), (3, 906, 320, 320)):
            with Image.open(WORK / f"aspect-{number}-{aspect}.png") as picture:
                board.paste(picture.resize((width, height), Image.Resampling.LANCZOS), (x, y))
        draw.text((42, y+338), f"{number} / {title}", font=font(18), fill="#B9C6D5")
    draw.text((42, 944), "按 E 选择画幅  ·  配方保存构图  ·  PNG 按所选比例导出", font=font(17), fill="#A8E1CC")
    board.save(ASSETS / "aspect-compositions.png", optimize=True)


def make_hd():
    """Compare a small-window snapshot with the same frame redrawn at 4K."""
    work = next(work for work in works() if work["id"] == 25)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    from 创作配方 import preset_parameters
    from 作品导出 import capture_artwork
    from 高清导出 import ExportJob, freeze_artwork
    spec = importlib.util.spec_from_file_location("capture_hd", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, work["entry_class"])()
    try:
        app.stage.root.geometry("760x580+20+20")
        app.stage.root.update()
        app.apply_parameters(dict(preset_parameters(25, 1), aspect=1))
        app.frame(8)
        app.stage.screen.update()
        window = capture_artwork(app.stage)
        destination = ASSETS / "export-lily-4k.png"
        job = ExportJob(freeze_artwork(app), destination, 2160)
        job.thread.join(15)
        if job.thread.is_alive():
            job.cancel()
            job.thread.join()
            raise RuntimeError("HD sample export timed out")
        result = job.poll()
        if result["state"] != "saved":
            raise RuntimeError(result["message"])
        with Image.open(destination) as source:
            hd = source.convert("RGB")
        board = Image.new("RGB", (1400, 1000), "#0B1424")
        draw = ImageDraw.Draw(board)
        draw.text((40, 28), "从小窗口，导出大作品", font=font(34, True), fill="#EDF1F5")
        draw.text((42, 84), "同一构图 · 同一动画瞬间 · 按目标分辨率重新绘制", font=font(19), fill="#A7BACB")
        board.paste(hd.resize((780, 439), Image.Resampling.LANCZOS), (40, 140))
        region = (.38, .14, .69, .365)
        x1,y1,x2,y2 = region
        draw.rectangle((40+x1*780,140+y1*439,40+x2*780,140+y2*439), outline="#A8E1CC", width=2)
        for y, title, detail in ((158,"预览窗口","760 × 580"),
                                (280,"当前窗口 PNG",f"{window.width} × {window.height}"),
                                (402,"2160 高清重绘",f"{hd.width} × {hd.height}")):
            draw.text((870,y),title,font=font(20),fill="#A7BACB")
            draw.text((870,y+37),detail,font=font(30,True),fill="#ECF1F5")
        draw.text((42,610),"窗口图局部放大（双三次）",font=font(20),fill="#A7BACB")
        draw.text((722,610),"高清重绘图 · 同一区域",font=font(20),fill="#A8E1CC")
        for picture,x,method in ((window,40,Image.Resampling.BICUBIC),(hd,720,Image.Resampling.LANCZOS)):
            crop=picture.crop((round(x1*picture.width),round(y1*picture.height),
                               round(x2*picture.width),round(y2*picture.height)))
            board.paste(crop.resize((640,260),method),(x,656))
        draw.text((42,954),"按 E → 选择固定画幅 → PNG 导出尺寸 → 高清重绘",font=font(18),fill="#A8E1CC")
        board.save(ASSETS / "hd-export-comparison.png", optimize=True)
        print("Created 3840x2160 PNG and authentic detail comparison", flush=True)
    finally:
        app.stage.close()


def make_social():
    catalog = {work["id"]: work for work in works()}
    titles = {number: work["title"] for number, work in catalog.items()}
    for number in SOCIAL_IDS:
        if social_capture_is_current(catalog[number]):
            print(f"Using existing capture {number}", flush=True)
            continue
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-social", str(number)],
                       check=True, timeout=120)
    frames = []
    for number in SOCIAL_IDS:
        for index in range(SOCIAL_FRAMES):
            frame = Image.new("RGB", (720, 460), "#0B1424")
            draw = ImageDraw.Draw(frame)
            draw.text((22, 13), f"{number}  {titles[number]}", font=font(22, True), fill="#EDF1EF")
            draw.text((528, 24), "TURTLE GALLERY", font=font(11, True), fill="#98D6C5")
            with Image.open(WORK / f"social_{number:02}_{index:02}.png") as scene:
                rounded_image(frame, scene, (16, 57, 688, 378), 8)
            frames.append(frame)
    samples = Image.new("RGB", (192 * len(SOCIAL_IDS), 128))
    for index in range(len(SOCIAL_IDS)):
        samples.paste(frames[index * SOCIAL_FRAMES + SOCIAL_FRAMES - 1].resize((192, 128)), (index * 192, 0))
    palette = samples.quantize(colors=192)
    converted = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    converted[0].save(ASSETS / "romantic.gif", save_all=True, append_images=converted[1:],
                      duration=150, loop=0, optimize=True, disposal=1)
    board = Image.new("RGB", (1400, 940), "#0B1424")
    draw = ImageDraw.Draw(board)
    draw.text((42, 25), "浪漫光影 / FOUR WORLDS MADE OF LIGHT", font=font(30, True), fill="#DFE9F1")
    draw.text((44, 76), "星空彼岸花 · 怦然心动 · 星河玫瑰 · 霓光蝶舞", font=font(18), fill="#B3BCD4")
    for index, number in enumerate(SOCIAL_IDS):
        x, y = 40 + index % 2 * 680, 120 + index // 2 * 402
        draw.rounded_rectangle((x, y, x + 640, y + 377), radius=14, fill="#17243B", outline="#2B3B57")
        rounded_image(board, load_scene(number), (x + 10, y + 10, 620, 320), 9)
        draw.text((x + 18, y + 340), f"{number}  {titles[number]}", font=font(21, True), fill="#E0E8F5")
    board.save(ASSETS / "romantic.png", optimize=True)
    print(f"Composed romantic.png and romantic.gif ({(ASSETS / 'romantic.gif').stat().st_size / 1048576:.2f} MiB)")


def original_capture(number):
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    destination = ORIGINALS / f"{number:02}.png"
    if not work.get("entry_class"):
        raise ValueError("Original work must register an import-safe entry_class")
    # All originals expose a scene class; preview the same drawing as the app.
    sys.path.insert(0, str(ROOT))
    from 社团展示.作品导出 import capture_artwork
    spec = importlib.util.spec_from_file_location("capture_original_scene", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, work["entry_class"])()
    try:
        app.stage.root.geometry("1000x720+20+20")
        app.stage.root.update()
        app.reset()
        for _ in range(50):
            app.frame(.04)
        app.stage.screen.update()
        picture = capture_artwork(app.stage)
        picture.save(destination, optimize=True)
        for suffix, size in (("thumb", (244, 154)), ("compact", (220, 126))):
            ImageOps.pad(picture, size, method=Image.Resampling.LANCZOS, color="#101A2A").save(
                ORIGINALS / f"{number:02}_{suffix}.png", optimize=True)
    finally:
        app.stage.close()
    print(f"Captured refined original {number:02} at t=2s", flush=True)


def animation_capture(number):
    work = next(work for work in works() if work["id"] == number)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("capture_demo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    random.seed(13)
    app = getattr(module, work["entry_class"])()
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
    converted = []
    for sequence in range(len(selected)):
        # A shared palette across six unrelated scenes shifted the pale tree's
        # bark toward blue. Keep a stable local palette for each 16-frame clip,
        # sampled throughout its motion so colors remain consistent in time.
        clip = frames[sequence * 16:(sequence + 1) * 16]
        samples = Image.new("RGB", (360 * 4, 238))
        for index, sample in enumerate((0, 5, 10, 15)):
            samples.paste(clip[sample].resize((360, 238), Image.Resampling.LANCZOS),
                          (index * 360, 0))
        palette = samples.quantize(colors=256)
        converted.extend(frame.quantize(palette=palette, dither=Image.Dither.NONE)
                         for frame in clip)
    converted[0].save(ASSETS / "showcase.gif", save_all=True, append_images=converted[1:], duration=120,
                      loop=0, optimize=True, disposal=1)
    print(f"Wrote showcase.gif ({(ASSETS / 'showcase.gif').stat().st_size / 1024 / 1024:.2f} MiB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    interactive_ids = tuple(work["id"] for work in works() if work["collection"] == "interactive")
    original_ids = tuple(work["id"] for work in works() if work["collection"] == "original")
    parser.add_argument("--originals", action="store_true")
    parser.add_argument("--original-ids", nargs="+", type=int, choices=original_ids,
                        help="Refresh selected original works without recapturing the whole collection")
    parser.add_argument("--compose", action="store_true")
    parser.add_argument("--compose-originals", action="store_true",
                        help="Rebuild the original-work contact sheet from existing previews")
    parser.add_argument("--gif", action="store_true")
    parser.add_argument("--exhibits", nargs="+", type=int, choices=interactive_ids,
                        help="Refresh selected interactive previews at a fixed two-second pose")
    parser.add_argument("--social", action="store_true", help="Capture the four romantic light artworks and their animation")
    parser.add_argument("--creator", action="store_true", help="Capture the live creation panel and artwork")
    parser.add_argument("--aspects", action="store_true", help="Capture the six aspect compositions and comparison board")
    parser.add_argument("--hd", action="store_true", help="Export a 4K sample and compare actual detail with a window PNG")
    parser.add_argument("--capture-aspect", type=int, choices=(25, 26), help=argparse.SUPPRESS)
    parser.add_argument("--capture-original", type=int, choices=original_ids, help=argparse.SUPPRESS)
    parser.add_argument("--capture-animation", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--capture-social", type=int, choices=SOCIAL_IDS, help=argparse.SUPPRESS)
    parser.add_argument("--capture-exhibit", type=int, choices=interactive_ids, help=argparse.SUPPRESS)
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    if args.capture_exhibit:
        exhibit_capture(args.capture_exhibit)
        return
    if args.capture_aspect:
        aspect_capture(args.capture_aspect)
        return
    if args.capture_social:
        social_capture(args.capture_social)
        return
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
    elif args.original_ids:
        for number in dict.fromkeys(args.original_ids):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-original", str(number)],
                           check=True, timeout=90)
    if args.exhibits:
        for number in dict.fromkeys(args.exhibits):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--capture-exhibit", str(number)],
                           check=True, timeout=90)
    if args.gif:
        make_gif()
    if args.social:
        make_social()
    if args.creator:
        creator_capture()
    if args.hd:
        make_hd()
    if args.aspects:
        make_aspects()
    if args.compose:
        compose()
    elif args.compose_originals:
        compose_originals()


if __name__ == "__main__":
    main()
