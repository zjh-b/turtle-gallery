"""Build a repeatable 22-second portrait film from the real 25/26 scenes.

Optional maintenance tool: Pillow + an installed FFmpeg with libx264.
No window, screen recording, network request or third-party image is used.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DURATION = 22
SHOTS = (
    (0, 2, 25, "hook"), (2, 8, 25, "bloom"),
    (8, 12, 25, "palette"), (12, 18, 26, "stardust"),
    (18, 22, 26, "follow"),
)
COPY = {
    "zh": (
        ("这朵花\n是 Python 画的", "代码开花 01 · 真实程序画面"),
        ("让星空里的彼岸花\n慢慢盛开", "按 G，重播一次绽放"),
        ("赤色 · 蓝紫 · 鎏金\n你更喜欢哪一色？", "按 C，换一种星空"),
        ("点一下\n星尘散开又相聚", "每一粒星光，都由代码绘制"),
        ("关注我\n下集用代码放烟花", "代码开花 · 把灵感写成画面"),
    ),
    "en": (
        ("This flower is\ndrawn with Python.", "CODE IN BLOOM 01 / REAL PROGRAM OUTPUT"),
        ("Watch a starry\nlily bloom.", "Press G to watch it bloom again"),
        ("Red, violet or gold\nWhich is yours?", "Press C to change the palette"),
        ("One click. Stardust\nfinds its way back.", "Every point of light is drawn with code"),
        ("Follow for the next\ncreative sketch.", "NEXT: FIREWORKS MADE WITH CODE"),
    ),
}


def schedule(fps):
    if type(fps) is not int or fps not in (24, 30):
        raise ValueError("视频帧率请选择 24 或 30。")
    return [dict(start_frame=start*fps, end_frame=end*fps, work_id=work, name=name)
            for start, end, work, name in SHOTS]


def subtitles(language):
    if language not in COPY:
        raise ValueError("字幕语言请选择 zh 或 en。")
    parts = []
    for index, ((start, end, _, _), (caption, _)) in enumerate(zip(SHOTS, COPY[language]), 1):
        # The English end card also states what the next episode contains.
        if language == "en" and index == 5:
            caption = "Follow for the next sketch:\nfireworks made with code."
        parts.append(f"{index}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{caption}\n")
    return "\n".join(parts)


def inputs(fps):
    """Actions fire before sampling their numbered frame; coordinates are logical."""
    schedule(fps)
    return [
        {"frame": 2*fps, "work_id": 25, "action": "replay"},
        {"frame": 8*fps, "work_id": 25, "action": "theme"},
        {"frame": round(8.2*fps), "work_id": 25, "action": "meteor", "x": 155, "y": 195},
        {"frame": 10*fps, "work_id": 25, "action": "theme"},
        {"frame": round(12.6*fps), "work_id": 26, "action": "burst", "x": 0, "y": 0},
        {"frame": 16*fps, "work_id": 26, "action": "theme"},
        {"frame": 16*fps, "work_id": 26, "action": "theme"},
    ]


class Encoder:
    """One streamed RGB -> H.264 encoder, with bounded stderr and cleanup."""
    def __init__(self, ffmpeg, path, size, fps):
        self.frame_bytes = size[0]*size[1]*3
        self.closed = False
        self.errors = tempfile.TemporaryFile()
        command = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin",
                   "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size",
                   f"{size[0]}x{size[1]}", "-framerate", str(fps), "-i", "pipe:0",
                   "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", str(path)]
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                            stdout=subprocess.DEVNULL, stderr=self.errors,
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except BaseException:
            self.errors.close()
            raise

    def write(self, pixels):
        if len(pixels) != self.frame_bytes:
            raise ValueError("RGB 帧大小与视频尺寸不一致。")
        try:
            self.process.stdin.write(pixels)
        except (BrokenPipeError, OSError) as error:
            raise RuntimeError("FFmpeg 写入失败；请检查 libx264 支持和剩余磁盘空间。") from error

    def finish(self):
        if self.closed:
            return
        try:
            try:
                self.process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            try:
                code = self.process.wait(timeout=60)
            except subprocess.TimeoutExpired as error:
                self.process.kill()
                self.process.wait()
                raise RuntimeError("FFmpeg 编码结束超时。") from error
            if code:
                self.errors.seek(0)
                detail = self.errors.read(8192).decode("utf-8", errors="replace").strip()
                raise RuntimeError(f"FFmpeg 编码失败 ({code})：{detail}")
        except BaseException:
            # This includes Ctrl+C during wait(), not just encoder errors.
            if self.process.poll() is None:
                self.process.kill()
                self.process.wait()
            raise
        finally:
            self.closed = True
            self.errors.close()

    def abort(self):
        if not self.closed:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            try:
                self.process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            self.errors.close()
            self.closed = True


def lettering(picture, shot_index, language, font_paths, account="", cover=False):
    """Place text away from the right interaction rail and the lower app chrome.

    Insets are editorial choices, not a promise about every platform UI.
    Artwork geometry is left intact; only scene lettering is replaced.
    """
    from PIL import ImageDraw, ImageFont
    result = picture.copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size
    unit = width/1080
    left, usable = round(width*.09), round(width*.73)

    def text_block(lines, y, size, color, bold=False):
        font = ImageFont.truetype(font_paths[1 if bold else 0], round(size*unit))
        while max(draw.textlength(line, font=font) for line in lines.split("\n")) > usable:
            if font.size <= max(1, round(18*unit)):
                raise ValueError("文字过长，请缩短账号名或字幕。")
            font = ImageFont.truetype(font_paths[1 if bold else 0], font.size-1)
        draw.multiline_text((left, round(y*height)), lines, font=font, fill=color,
                            spacing=round(font.size*.28), anchor="la")

    eyebrow = "CODE IN BLOOM  /  01" if language == "en" else "代码开花  /  01"
    text_block(eyebrow, .105, 26, "#C694A8")
    headline, foot = COPY[language][shot_index]
    if cover:
        headline = "代码，也能开花" if language == "zh" else "Code can bloom."
        foot = "Python 星空彼岸花" if language == "zh" else "STARRY LILY / MADE WITH PYTHON"
    text_block(headline, .151, 64 if language == "zh" else 62, "#FFF2E7", bold=True)
    draw.line((left, height*.723, left+56*unit, height*.723), fill="#EEA1BA", width=max(1, round(3*unit)))
    text_block(foot, .74, 31, "#D0C2D5")
    if account:
        text_block(account, .795, 27, "#AD9BAF")
    return result


def _fonts(regular, bold):
    if regular:
        paths = (Path(regular), Path(bold or regular))
        if not all(path.is_file() for path in paths):
            raise ValueError("指定的字体文件不存在。")
        return tuple(str(path.resolve()) for path in paths)
    if bold:
        raise ValueError("指定 --font-bold 时也请指定 --font。")
    from 高清导出 import _font_paths
    return _font_paths()


def _ffmpeg(executable):
    found = shutil.which(executable or "ffmpeg")
    if not found:
        raise RuntimeError("找不到 FFmpeg。请安装包含 libx264 的 FFmpeg，并加入 PATH；或使用 --ffmpeg 指定路径。")
    result = subprocess.run([found, "-hide_banner", "-encoders"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=20,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode or "libx264" not in result.stdout:
        raise RuntimeError("此 FFmpeg 未提供 libx264 编码器。")
    return found


def produce(output, *, width=1080, fps=30, language="zh", account="", ffmpeg=None,
            font=None, font_bold=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"输出目录已存在，文件保持不变。请换一个 --output：{output}")
    if type(width) is not int or width not in (720, 1080):
        raise ValueError("视频宽度请选择 720 或 1080。")
    shots = schedule(fps)
    if language not in COPY or len(account) > 24 or any(ord(c) < 32 for c in account):
        raise ValueError("语言请选择 zh/en；账号署名最多 24 字，不能含换行或控制字符。")
    from video_scene import SceneFrames
    from PIL import Image, ImageDraw, ImageFont
    encoder_path = _ffmpeg(ffmpeg)
    font_paths = _fonts(font, font_bold)
    # Resolve fonts before starting a potentially long render.
    for path in font_paths:
        ImageFont.truetype(path, 30)
    size = width, width*16//9
    parameters = {
        25: dict(aspect=2, theme=0, speed=1.1, star_count=145, curvature=1.15, wind=.6, seed=2506),
        26: dict(aspect=2, theme=0, rate=.9, particle_count=1000, size=1.1, seed=2606),
    }
    scenes = {work: SceneFrames(work, params, fps, hide_lettering=True)
              for work, params in parameters.items()}
    # The hook opens on a mature flower; warm-up also uses fixed steps.
    for _ in range(7*fps):
        scenes[25].commands(1/fps)
    events = inputs(fps)
    events_by_frame = {}
    for event in events:
        events_by_frame.setdefault(event["frame"], []).append(event)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix=".gallery-video-", dir=output.parent) as temporary:
        folder = Path(temporary) / "result"
        folder.mkdir()
        with ExitStack() as cleanup:
            edited = Encoder(encoder_path, folder / "video.mp4", size, fps)
            cleanup.callback(edited.abort)
            clean = Encoder(encoder_path, folder / "clean.mp4", size, fps)
            cleanup.callback(clean.abort)
            board = Image.new("RGB", (360*5, 640+66), "#0B0F1D")
            cleanup.callback(board.close)
            board_draw = ImageDraw.Draw(board)
            board_font = ImageFont.truetype(font_paths[0], 20)
            selected = {0: 0, 6*fps: 1, 9*fps: 2, round(13.8*fps): 3, 20*fps: 4}
            for frame in range(DURATION*fps):
                shot_index = next(i for i, shot in enumerate(shots)
                                  if shot["start_frame"] <= frame < shot["end_frame"])
                work_id = shots[shot_index]["work_id"]
                scene = scenes[work_id]
                for event in events_by_frame.get(frame, ()):
                    scenes[event["work_id"]].event(event["action"], event.get("x", 0), event.get("y", 0))
                dt = 0 if frame in (0, 12*fps) else 1/fps
                with scene.render(size, font_paths, dt) as art:
                    clean.write(art.tobytes())
                    with lettering(art, shot_index, language, font_paths, account) as picture:
                        edited.write(picture.tobytes())
                        if frame in selected:
                            index = selected[frame]
                            with picture.resize((360, 640), Image.Resampling.LANCZOS) as thumb:
                                board.paste(thumb, (index*360, 0))
                            start, end, _, name = SHOTS[index]
                            board_draw.text((index*360+22, 660), f"{start:02d}–{end:02d}s / {name.upper()}",
                                            font=board_font, fill="#D0C2D5")
                    if frame == 0:
                        with lettering(art, 0, language, font_paths, account, cover=True) as cover:
                            cover.save(folder / "cover.png")
                if frame % (fps*2) == 0:
                    print(f"Rendered {frame}/{DURATION*fps} frames", flush=True)
            edited.finish()
            clean.finish()
            board.save(folder / "storyboard.jpg", quality=92)
        for lang in COPY:
            # Stable LF bytes keep the recorded hashes valid after Git checkout.
            (folder / f"captions.{lang}.srt").write_bytes(subtitles(lang).encode("utf-8"))
        sources = [ROOT / "tools" / name for name in ("render_video.py", "video_scene.py")]
        sources += [ROOT / "社团展示" / name for name in
                    ("25_星空彼岸花.py", "26_怦然心动.py", "舞台.py", "创作配方.py",
                     "爱心参数.py", "高清导出.py", "离屏绘制.py")]
        manifest = dict(format="turtle-gallery/social-film", version=1, duration_seconds=DURATION,
                        size=list(size), fps=fps, frames=DURATION*fps, language=language, account=account,
                        renderer="Pillow vector redraw, 2x antialiasing", audio=False,
                        parameters=parameters, shots=shots, events=events,
                        warmup_frames={"25": 7*fps, "26": 0},
                        sampling="Events before frame step; dt=0 at frames 0 and 12*fps, otherwise 1/fps; only active scene advances.",
                        text_insets={"left": .09, "right": .18, "top": .105, "last_baseline_max": .83},
                        render_seconds=round(time.perf_counter()-started, 2),
                        python=sys.version.split()[0],
                        font_sha256=[hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in font_paths],
                        source_hash_normalization="CRLF to LF; all other source bytes preserved",
                        source_sha256={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                                       for p in sources},
                        files={p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                               for p in folder.iterdir()})
        (folder / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=2)+"\n").encode("utf-8"))
        # No destination is touched until every frame, encode and sidecar succeeded.
        if output.exists():
            raise FileExistsError(f"输出目录已出现，保留现有文件：{output}")
        folder.rename(output)
    print(f"Saved {output} ({size[0]}x{size[1]}, {fps} fps, {DURATION}s, silent)", flush=True)
    return output


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=ROOT / "exports" / "social-01")
    result.add_argument("--width", type=int, choices=(720, 1080), default=1080)
    result.add_argument("--fps", type=int, choices=(24, 30), default=30)
    result.add_argument("--language", choices=tuple(COPY), default="zh")
    result.add_argument("--account", default="", help="Optional account label, up to 24 characters")
    result.add_argument("--ffmpeg", help="Path to an installed FFmpeg executable with libx264")
    result.add_argument("--font", help="Regular CJK TrueType font (defaults to Windows Microsoft YaHei)")
    result.add_argument("--font-bold", help="Bold font, defaults to --font when supplied")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        produce(args.output, width=args.width, fps=args.fps, language=args.language,
                account=args.account, ffmpeg=args.ffmpeg, font=args.font, font_bold=args.font_bold)
    except KeyboardInterrupt:
        print("Cancelled; no completed output directory was replaced.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, ValueError, ImportError, subprocess.TimeoutExpired) as error:
        print(f"Video export: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
