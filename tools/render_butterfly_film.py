"""Make a 20-second butterfly candidate film, original score and two covers.

    python tools/render_butterfly_film.py --capture exports/butterfly-frames --output exports/butterfly-film

Requires Pillow and FFmpeg with libx264/AAC. Accepts the complete, current
butterfly capture only. Creates a new output directory; never publishes.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "社团展示"))
from tools.butterfly_audio import synthesize
from tools.render_butterfly_preview import CAPTIONS, sha, validate_report
from tools.render_video import Encoder, _ffmpeg, _fonts

SIZE = (1280, 720)
BACKGROUND = "#0B0D23"
COVER_CROP = (.31, .055, .83, .855)


def fonts():
    from PIL import ImageFont
    regular, bold = _fonts(None, None)
    return {"label": ImageFont.truetype(regular, 20),
            "caption": ImageFont.truetype(bold, 28),
            "small": ImageFont.truetype(regular, 18),
            "headline": ImageFont.truetype(bold, 90),
            "hero": ImageFont.truetype(bold, 116),
            "cover_small": ImageFont.truetype(regular, 28)}


def validate_capture(capture):
    from PIL import Image
    report = json.loads((capture / "capture.json").read_text(encoding="utf-8"))
    validate_report(report)
    paths = [capture / f"frame-{index:05d}.png" for index in range(report["frames"])]
    if not all(path.is_file() for path in paths):
        raise ValueError("Capture has missing frames; record again")
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            if list(source.size) != report["size"]:
                raise ValueError(f"Artwork size changed at frame {index}")
    return report, paths


def compose(source, seconds, face):
    from PIL import Image, ImageDraw, ImageOps
    picture = Image.new("RGB", SIZE, BACKGROUND)
    art = ImageOps.contain(source.convert("RGB"), (1216, 574), Image.Resampling.LANCZOS)
    picture.paste(art, ((1280-art.width)//2, 60+(574-art.height)//2))
    draw = ImageDraw.Draw(picture)
    draw.ellipse((32, 24, 40, 32), fill="#B8A4F3")
    draw.text((52, 16), "PYTHON / 霓光蝶舞", font=face["label"], fill="#D8D3ED")
    draw.text((1248, 16), "难安这余念", font=face["label"], fill="#969DBB", anchor="ra")
    caption = next(text for start, end, text in CAPTIONS if start <= seconds < end)
    draw.line((48, 649, 1232, 649), fill="#292D46")
    draw.text((640, 665), caption, font=face["caption"], fill="#F0EDF9", anchor="ma")
    draw.line((0, 718, round(1279*min(1, seconds/20)), 718), fill="#A799CE", width=2)
    return picture


def cover(source, portrait, face):
    """Independently lay out 16:9 and 4:3; retain the complete butterfly."""
    from PIL import Image, ImageDraw, ImageOps
    size = (1200, 900) if portrait else SIZE
    picture = Image.new("RGB", size, BACKGROUND)
    width, height = source.size
    crop = source.crop(tuple(round(value * (width if index % 2 == 0 else height))
                             for index, value in enumerate(COVER_CROP)))
    art = ImageOps.contain(crop.convert("RGB"), (800, 600) if portrait else (660, 580),
                           Image.Resampling.LANCZOS)
    # Feather only the empty outer margin, to join the real frame to the cover.
    mask = Image.new("L", art.size)
    mask.putdata([round(255 * min(1, min(x, y, art.width-1-x, art.height-1-y)/22))
                  for y in range(art.height) for x in range(art.width)])
    location = ((1200-art.width)//2, 260) if portrait else (584, (720-art.height)//2)
    picture.paste(art, location, mask)
    draw = ImageDraw.Draw(picture)
    draw.text((64, 38), "PYTHON / 霓光蝶舞", font=face["cover_small"], fill="#BDB1DD")
    if portrait:
        draw.text((64, 92), "会追光的蝴蝶", font=face["headline"], fill="#F1EDF9")
        draw.text((68, 213), "点击追光 · 三种配色", font=face["cover_small"], fill="#9CAFCB")
    else:
        draw.text((60, 191), "会追光的", font=face["headline"], fill="#F1EDF9")
        draw.text((55, 297), "蝴蝶", font=face["hero"], fill="#D4BDFA")
        draw.line((64, 463, 160, 463), fill="#8473B4", width=3)
        draw.text((64, 492), "点击追光 · 三种配色", font=face["cover_small"], fill="#9CAFCB")
    draw.text((size[0]-48, size[1]-42), "难安这余念", font=face["label"],
              fill="#969DBB", anchor="ra")
    return picture


def mux(ffmpeg, silent, score, output):
    result = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                             "-i", str(silent), "-i", str(score),
                             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                             "-c:a", "aac", "-b:a", "160k", "-t", "20",
                             "-movflags", "+faststart", str(output)],
                            capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Audio mux failed: " + result.stderr.decode("utf-8", "replace")[-2000:])


def produce(capture, output, ffmpeg=None):
    from PIL import Image
    capture, output = Path(capture).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    report, paths = validate_capture(capture)
    executable, face = _ffmpeg(ffmpeg), fonts()
    dependencies = (Path(__file__), ROOT / "tools/butterfly_audio.py",
                    ROOT / "tools/render_butterfly_preview.py", ROOT / "tools/render_video.py",
                    ROOT / "社团展示/高清导出.py")
    sources = {path.relative_to(ROOT).as_posix(): sha(path, True) for path in dependencies}
    output.mkdir(parents=True, exist_ok=False)
    silent, score = output / ".silent.mp4", output / ".score.wav"
    media = ("video.mp4", "cover.png", "cover-4x3.png", "storyboard.jpg", "captions.zh.srt")
    encoder = None
    try:
        encoder = Encoder(executable, silent, SIZE, report["fps"])
        thumbnails, input_hashes, cover_source = [], {}, None
        moments = {round(at * report["fps"]) for at in (0, 3, 6, 9, 13, 16)}
        for index, path in enumerate(paths):
            data = path.read_bytes()
            input_hashes[path.name] = hashlib.sha256(data).hexdigest()
            with Image.open(BytesIO(data)) as source:
                if list(source.size) != report["size"]:
                    raise ValueError(f"Artwork size changed at frame {index}")
                picture = compose(source, index/report["fps"], face)
                if index == 3*report["fps"]:
                    cover_source = source.copy()
            encoder.write(picture.tobytes())
            if index in moments:
                thumbnails.append(picture.resize((640, 360), Image.Resampling.LANCZOS))
        encoder.finish()
        encoder = None
        audio = synthesize(score)
        mux(executable, silent, score, output / "video.mp4")
        cover(cover_source, False, face).save(output / "cover.png")
        cover(cover_source, True, face).save(output / "cover-4x3.png")
        board = Image.new("RGB", (1280, 1080), BACKGROUND)
        for index, thumbnail in enumerate(thumbnails):
            board.paste(thumbnail, ((index % 2)*640, (index // 2)*360))
        board.save(output / "storyboard.jpg", quality=93)
        srt = "\n".join(f"{index}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{text}\n"
                        for index, (start, end, text) in enumerate(CAPTIONS, 1))
        (output / "captions.zh.srt").write_bytes(srt.encode("utf-8"))
        validate_report(report)
        if any(sha(ROOT / name, True) != expected for name, expected in sources.items()):
            raise ValueError("Film sources changed during rendering")
        manifest = {"status": "candidate; not submitted", "size": list(SIZE),
                    "frames": report["frames"], "fps": report["fps"], "duration": 20,
                    "audio": audio, "audio_note": "Original oscillators; measurements describe PCM before AAC encoding",
                    "capture": report, "source_sha256_lf": sources,
                    "input_frame_sha256": input_hashes,
                    "cover_frame": paths[3*report["fps"]].name,
                    "cover_crop_ratio": list(COVER_CROP),
                    "files": {name: sha(output / name) for name in media}}
        (output / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print(f"Saved 20-second candidate film and covers to {output}", flush=True)
        return manifest
    except BaseException:
        if encoder is not None:
            encoder.abort()
        # Only remove this invocation's known outputs from its new directory.
        for name in (*media, "manifest.json"):
            (output / name).unlink(missing_ok=True)
        raise
    finally:
        silent.unlink(missing_ok=True)
        score.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    try:
        produce(args.capture, args.output, args.ffmpeg)
    except Exception as exc:
        parser.exit(1, f"Film failed: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
