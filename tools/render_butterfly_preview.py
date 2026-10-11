"""Compose a silent, captioned rehearsal from the butterfly's real PNG frames.

    python tools/render_butterfly_preview.py --capture exports/butterfly-frames --output exports/butterfly-preview

Requires Pillow and FFmpeg with libx264. This is a review draft, not a publisher.
The output must be new. manifest.json is written only after successful encoding.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "社团展示"))
from tools.capture_butterfly_video import source_hashes, timeline
from tools.render_video import Encoder, _ffmpeg, _fonts

SIZE = (1280, 720)
CAPTIONS = ((0, 4, "点一束光，看看蝶的回应"),
            (4, 8, "换一侧，它也轻轻跟过来"),
            (8, 10, "按 C，换成玫瑰月光"),
            (10, 12, "按 M，定住位置，蝶翼仍在呼吸"),
            (12, 14, "再按 C，换成翡翠流萤"),
            (14, 18, "恢复漫游，再追一束微光"),
            (18, 20, "关注我，继续看代码画出的小世界"))


def sha(path, source=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if source else data).hexdigest()


def validate_report(report):
    fps = report.get("fps")
    frames, events = timeline(fps, 20)
    if (report.get("work") != 28 or report.get("frames") != frames
            or report.get("duration") != 20 or report.get("events") != events):
        raise ValueError("Expected the complete 20-second butterfly story")
    size = report.get("size")
    if (not isinstance(size, list) or len(size) != 2
            or any(type(value) is not int or value <= 0 for value in size)):
        raise ValueError("Invalid captured artwork size")
    if report.get("source_sha256_lf") != source_hashes():
        raise ValueError("Capture sources changed or are incomplete; record again")


def produce(capture, output, ffmpeg=None):
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    capture, output = Path(capture).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    report = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
    validate_report(report)
    paths = [capture / f"frame-{index:05d}.png" for index in range(report["frames"])]
    if not all(path.is_file() for path in paths):
        raise ValueError("Capture has missing frames; record again")
    encoder_path = _ffmpeg(ffmpeg)
    regular, bold = _fonts(None, None)
    small, caption_font = ImageFont.truetype(regular, 20), ImageFont.truetype(bold, 28)
    own_sources = (Path(__file__), ROOT / "tools/render_video.py", ROOT / "社团展示/高清导出.py")
    sources = {path.relative_to(ROOT).as_posix(): sha(path, True) for path in own_sources}
    output.mkdir(parents=True, exist_ok=False)
    encoder = Encoder(encoder_path, output / "preview.mp4", SIZE, report["fps"])
    thumbnails, frame_hashes = [], {}
    moments = {round(at * report["fps"]) for at in (0, 3, 6, 9, 13, 16)}
    try:
        for index, path in enumerate(paths):
            frame_hashes[path.name] = sha(path)
            with Image.open(path) as source:
                if list(source.size) != report["size"]:
                    raise ValueError(f"Artwork size changed at frame {index}")
                art = ImageOps.contain(source.convert("RGB"), (1216, 568), Image.Resampling.LANCZOS)
            picture = Image.new("RGB", SIZE, "#080D23")
            draw = ImageDraw.Draw(picture)
            draw.text((32, 18), "PYTHON / 霓光蝶舞", font=small, fill="#C1C9EB")
            draw.text((1248, 18), "互动试录 · 无声", font=small, fill="#7F8AAE", anchor="ra")
            picture.paste(art, ((SIZE[0]-art.width)//2, 62+(568-art.height)//2))
            seconds = index / report["fps"]
            caption = next(text for start, end, text in CAPTIONS if start <= seconds < end)
            draw.line((32, 647, 1248, 647), fill="#303552")
            draw.text((640, 663), caption, font=caption_font, fill="#E8E6FC", anchor="ma")
            encoder.write(picture.tobytes())
            if index in moments:
                thumbnails.append(picture.resize((640, 360), Image.Resampling.LANCZOS))
        encoder.finish()
    except BaseException:
        encoder.abort()
        raise
    validate_report(report)
    if any(sha(ROOT / name, True) != expected for name, expected in sources.items()):
        raise ValueError("Compositor sources changed during rendering")
    board = Image.new("RGB", (1280, 1080), "#080D23")
    for index, thumbnail in enumerate(thumbnails):
        board.paste(thumbnail, ((index % 2)*640, (index // 2)*360))
    board.save(output / "storyboard.jpg", quality=93)
    srt = "\n".join(f"{index}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{text}\n"
                    for index, (start, end, text) in enumerate(CAPTIONS, 1))
    # .gitattributes requires LF; use bytes to avoid Windows newline conversion.
    (output / "captions.zh.srt").write_bytes(srt.encode("utf-8"))
    names = ("preview.mp4", "storyboard.jpg", "captions.zh.srt")
    manifest = {"status": "silent rehearsal; not submitted", "size": list(SIZE),
                "frames": report["frames"], "fps": report["fps"], "duration": 20,
                "audio": False, "capture": report, "source_sha256_lf": sources,
                "input_frame_sha256": frame_hashes,
                "files": {name: sha(output / name) for name in names}}
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(f"Saved silent 20-second preview and storyboard to {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
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
