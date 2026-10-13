"""Compose a silent, captioned rose rehearsal from actual Tk window frames.

    python tools/render_rose_preview.py --capture exports/rose-frames --output exports/rose-preview

Requires Pillow and FFmpeg with libx264. A new output directory is required.
The complete current 20-second story is accepted; this tool does not publish.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "社团展示"))
from tools.capture_rose_video import source_hashes, timeline
from tools.render_video import Encoder, _ffmpeg, _fonts

SIZE = (1280, 720)
BACKGROUND = "#111026"
CAPTIONS = ((0, 1.2, "送你一朵代码玫瑰"),
            (1.2, 3.2, "按 G，从一根花茎开始"),
            (3.2, 6.5, "花瓣一层层展开"),
            (6.5, 8.5, "把星河，赠予你"),
            (8.5, 11, "按 C，换成冰蓝回声"),
            (11, 13.5, "再按 C，换成香槟晨星"),
            (13.5, 18, "点击花旁，洒下一捧星尘"),
            (18, 20, "关注我，继续看代码画出的小世界"))


def sha(path, source=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if source else data).hexdigest()


def validate_report(report):
    if not isinstance(report, dict):
        raise ValueError("Invalid capture report")
    frames, events = timeline(report.get("fps"), 20)
    if (report.get("work") != 27 or type(report.get("frames")) is not int
            or report["frames"] != frames or report.get("duration") != 20
            or report.get("warmup_seconds") != 7 or report.get("events") != events):
        raise ValueError("Expected the complete 20-second rose story")
    size = report.get("size")
    if (not isinstance(size, list) or len(size) != 2
            or any(type(value) is not int or value <= 0 for value in size)):
        raise ValueError("Invalid captured artwork size")
    if report.get("source_sha256_lf") != source_hashes():
        raise ValueError("Capture sources changed or are incomplete; record again")


def fonts():
    from PIL import ImageFont
    regular, bold = _fonts(None, None)
    return {"label": ImageFont.truetype(regular, 20),
            "caption": ImageFont.truetype(bold, 28)}


def compose(source, seconds, face):
    from PIL import Image, ImageDraw, ImageOps
    picture = Image.new("RGB", SIZE, BACKGROUND)
    art = ImageOps.contain(source.convert("RGB"), (1216, 574), Image.Resampling.LANCZOS)
    picture.paste(art, ((SIZE[0]-art.width)//2, 60+(574-art.height)//2))
    draw = ImageDraw.Draw(picture)
    draw.text((32, 16), "PYTHON / 星河玫瑰", font=face["label"], fill="#DFCAD8")
    draw.text((1248, 16), "难安这余念 / 无声试片", font=face["label"], fill="#A996B4", anchor="ra")
    caption = next(text for start, end, text in CAPTIONS if start <= seconds < end)
    draw.line((48, 649, 1232, 649), fill="#403047")
    draw.text((640, 665), caption, font=face["caption"], fill="#F1DEE8", anchor="ma")
    return picture


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def produce(capture, output, ffmpeg=None):
    from PIL import Image
    capture, output = Path(capture).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    report = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
    validate_report(report)
    paths = [capture / f"frame-{index:05d}.png" for index in range(report["frames"])]
    if not all(path.is_file() for path in paths):
        raise ValueError("Capture has missing frames; record again")
    executable, face = _ffmpeg(ffmpeg), fonts()
    dependencies = (Path(__file__), ROOT / "tools/render_video.py", ROOT / "社团展示/高清导出.py")
    sources = {path.relative_to(ROOT).as_posix(): sha(path, True) for path in dependencies}
    output.mkdir(parents=True, exist_ok=False)
    media = ("preview.mp4", "storyboard.jpg", "captions.zh.srt")
    encoder = None
    try:
        encoder = Encoder(executable, output / "preview.mp4", SIZE, report["fps"])
        thumbnails, input_hashes = [], {}
        moments = {round(at * report["fps"]) for at in (0, 4, 7.5, 10, 12, 14.5)}
        for index, path in enumerate(paths):
            data = path.read_bytes()
            input_hashes[path.name] = hashlib.sha256(data).hexdigest()
            with Image.open(BytesIO(data)) as source:
                if list(source.size) != report["size"]:
                    raise ValueError(f"Artwork size changed at frame {index}")
                picture = compose(source, index/report["fps"], face)
            encoder.write(picture.tobytes())
            if index in moments:
                thumbnails.append(picture.resize((640, 360), Image.Resampling.LANCZOS))
        encoder.finish()
        encoder = None
        board = Image.new("RGB", (1280, 1080), BACKGROUND)
        for index, thumbnail in enumerate(thumbnails):
            board.paste(thumbnail, ((index % 2)*640, (index // 2)*360))
        board.save(output / "storyboard.jpg", quality=93)
        srt = "\n".join(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n"
                        for index, (start, end, text) in enumerate(CAPTIONS, 1))
        (output / "captions.zh.srt").write_bytes(srt.encode("utf-8"))
        validate_report(report)
        if any(sha(ROOT / name, True) != expected for name, expected in sources.items()):
            raise ValueError("Preview sources changed during rendering")
        manifest = {"status": "silent rehearsal; not submitted", "size": list(SIZE),
                    "frames": report["frames"], "fps": report["fps"], "duration": 20,
                    "audio": False, "capture": report, "source_sha256_lf": sources,
                    "input_frame_sha256": input_hashes,
                    "files": {name: sha(output / name) for name in media}}
        (output / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print(f"Saved silent 20-second rose preview and storyboard to {output}", flush=True)
        return manifest
    except BaseException:
        try:
            if encoder is not None:
                encoder.abort()
        finally:
            # Only this invocation's known files in its newly created directory.
            for name in (*media, "manifest.json"):
                (output / name).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    try:
        produce(args.capture, args.output, args.ffmpeg)
    except Exception as exc:
        parser.exit(1, f"Preview failed: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
