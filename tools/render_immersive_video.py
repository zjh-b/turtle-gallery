"""Compose a 20-second landscape film from authentic Tk frame captures.

Run capture_immersive_video.py separately for works 29 (7s), 30 (5s), 31 (8s),
then pass their parent directory as --captures. Requires Pillow and FFmpeg.
The output directory must be new. No network or account access is performed.
"""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "社团展示"))
from tools.render_video import Encoder, _ffmpeg, _fonts

SHOTS = ((29, 0, 7), (30, 7, 12), (31, 12, 20))
CAPTIONS = (
    (0, 2, "点一下，极光回应你"),
    (2, 7, "天空亮起 · 湖面泛起涟漪"),
    (7, 12, "换个角度，看金属环转动"),
    (12, 17, "移动光源，水晶变了模样"),
    (17, 20, "关注我，继续看代码画出的小世界"),
)
LABELS = {29: "01 / 极光之境", 30: "02 / 机械星仪", 31: "03 / 水晶花园"}
SIZE = (1920, 1080)


def sha(path, source=False):
    data = path.read_bytes()
    return hashlib.sha256(data.replace(b"\r\n", b"\n") if source else data).hexdigest()


def read_captures(directory):
    """Reject partial/stale recordings before starting an encoder."""
    from run import catalog
    scene_paths = {item["id"]: item["filename"] for item in catalog().WORKS}
    reports, fps = {}, None
    for work, start, end in SHOTS:
        folder = directory / str(work)
        report = json.loads((folder / "capture.json").read_text(encoding="utf-8"))
        rate = report["fps"]
        if report["work"] != work or rate not in (24, 30) or fps not in (None, rate):
            raise ValueError(f"Incompatible capture: {work}")
        fps = rate
        if report["frames"] != (end - start) * fps:
            raise ValueError(f"Work {work} needs exactly {end - start} seconds")
        for number in range(report["frames"]):
            if not (folder / f"frame-{number:05d}.png").is_file():
                raise ValueError(f"Missing frame {work}/{number}")
        expected_sources = {scene_paths[work], "社团展示/舞台.py", "社团展示/作品导出.py",
                            "tools/capture_immersive_video.py"}
        if set(report["source_sha256_lf"]) != expected_sources:
            raise ValueError(f"Capture source record is incomplete: {work}")
        for name, expected in report["source_sha256_lf"].items():
            source = (ROOT / name).resolve()
            if not source.is_relative_to(ROOT) or sha(source, True) != expected:
                raise ValueError(f"Capture source changed: {name}")
        reports[work] = report
    return reports, fps


class Layout:
    def __init__(self):
        from PIL import ImageFont
        regular, bold = _fonts(None, None)
        self.fonts = {"small": ImageFont.truetype(regular, 26),
                      "label": ImageFont.truetype(regular, 30),
                      "caption": ImageFont.truetype(bold, 45),
                      "cover": ImageFont.truetype(bold, 92)}

    def frame(self, source, work, seconds):
        from PIL import Image, ImageDraw, ImageOps
        picture = Image.new("RGB", SIZE, "#0B1018")
        draw = ImageDraw.Draw(picture)
        draw.text((70, 34), "PYTHON  /  代码造景", font=self.fonts["label"], fill="#E3E8EB")
        draw.text((1848, 38), LABELS[work], font=self.fonts["small"],
                  fill="#A4BDBB", anchor="ra")
        art = ImageOps.contain(source, (1792, 854), Image.Resampling.LANCZOS)
        picture.paste(art, ((1920 - art.width) // 2, 102 + (854 - art.height) // 2))
        draw.line((64, 980, 1856, 980), fill="#2A3643", width=2)
        draw.line((64, 980, 64 + round(1792 * min(1, seconds / 20)), 980),
                  fill="#8BC8BA", width=3)
        caption = next(text for start, end, text in CAPTIONS if start <= seconds < end)
        draw.text((960, 1000), caption, font=self.fonts["caption"], fill="#F1F0E7", anchor="ma")
        return picture

    def cover(self, sources):
        from PIL import Image, ImageDraw, ImageOps
        picture = Image.new("RGB", SIZE, "#0B1018")
        draw = ImageDraw.Draw(picture)
        draw.text((80, 60), "PYTHON  /  互动绘画", font=self.fonts["label"], fill="#A4BDBB")
        draw.text((75, 125), "代码里的三个小世界", font=self.fonts["cover"], fill="#F1F0E7")
        draw.text((82, 264), "极光 · 星仪 · 水晶     每一幅，都能回应你的操作",
                  font=self.fonts["label"], fill="#C2CBD1")
        # The aurora's whole scene anchors the cover; two real detail crops sit beside it.
        picture.paste(ImageOps.fit(sources[29], (1090, 605), Image.Resampling.LANCZOS), (80, 380))
        for work, y in ((30, 380), (31, 696)):
            source = sources[work]
            detail = source.crop((round(source.width * .40), 0, source.width, source.height))
            picture.paste(ImageOps.fit(detail, (625, 289), Image.Resampling.LANCZOS), (1200, y))
        return picture


def ambient(path):
    """Synthesize a quiet original pad: no samples, voice, or licensed recording."""
    rate, duration = 48000, 20
    chords = ((164.81, 196, 246.94), (130.81, 164.81, 196),
              (146.83, 196, 246.94), (146.83, 185, 220))
    samples = array("h")
    for index in range(rate * duration):
        t = index / rate
        total = 0.0
        for part, notes in enumerate(chords):
            elapsed = t - part * 5
            if not 0 <= elapsed < 6:
                continue
            envelope = min(1, elapsed / 1.2, (6 - elapsed) / 1.5)
            total += envelope * sum(math.sin(math.tau * hz * t)
                                    + .16 * math.sin(math.tau * hz * 2 * t)
                                    for hz in notes) / 3
        fade = min(1, t / .4, (duration - t) / 1.2)
        samples.append(round(3800 * total * max(0, fade)))
    if sys.byteorder != "little":
        samples.byteswap()
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        output.writeframes(samples.tobytes())


def produce(captures, output, ffmpeg):
    from PIL import Image, ImageDraw, ImageOps
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    reports, fps = read_captures(captures)
    encoder_path = _ffmpeg(ffmpeg)
    output.parent.mkdir(parents=True, exist_ok=True)
    layout = Layout()
    with tempfile.TemporaryDirectory(prefix=".immersive-video-", dir=output.parent) as temp:
        temp = Path(temp)
        result = temp / "result"
        result.mkdir()
        encoder = Encoder(encoder_path, temp / "silent.mp4", SIZE, fps)
        previews, sources = [], {}
        try:
            for work, start, end in SHOTS:
                for index in range((end - start) * fps):
                    with Image.open(captures / str(work) / f"frame-{index:05d}.png") as source:
                        if list(source.size) != reports[work]["size"]:
                            raise ValueError(f"Frame size changed: {work}/{index}")
                        picture = layout.frame(source.convert("RGB"), work, start + index / fps)
                        if index == 2 * fps:
                            sources[work] = source.convert("RGB")
                    encoder.write(picture.tobytes())
                    if start * fps + index in (fps, 4 * fps, 9 * fps, 14 * fps, 18 * fps):
                        previews.append(picture.resize((640, 360), Image.Resampling.LANCZOS))
                print(f"Composed work {work}", flush=True)
            encoder.finish()
        finally:
            encoder.abort()
        ambient(temp / "ambient.wav")
        subprocess.run([encoder_path, "-hide_banner", "-loglevel", "error", "-nostdin",
                        "-i", str(temp / "silent.mp4"), "-i", str(temp / "ambient.wav"),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-t", "20", "-movflags", "+faststart",
                        str(result / "video.mp4")], check=True, timeout=120,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        cover = layout.cover(sources)
        cover.save(result / "cover.png")
        # Bilibili also requires a 4:3 cover. Keep the headline and all three
        # scenes intact instead of accepting the platform's center crop.
        ImageOps.pad(cover, (1440, 1080), Image.Resampling.LANCZOS,
                     color="#0B1018").save(result / "cover-4x3.png")
        board = Image.new("RGB", (1280, 1080), "#0B1018")
        for index, picture in enumerate(previews):
            board.paste(picture, ((index % 2) * 640, (index // 2) * 360))
        draw = ImageDraw.Draw(board)
        draw.text((700, 795), "20 秒 / 真实程序画面", font=layout.fonts["label"], fill="#E3E8EB")
        draw.text((700, 850), "极光 → 星仪 → 水晶", font=layout.fonts["small"], fill="#A4BDBB")
        board.save(result / "storyboard.jpg", quality=94)
        lines = [f"{n}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{text}\n"
                 for n, (start, end, text) in enumerate(CAPTIONS, 1)]
        (result / "captions.zh.srt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
        manifest = {"duration": 20, "fps": fps, "frames": 20 * fps, "size": list(SIZE),
                    "renderer": "actual Tk artwork captures, fitted without distortion",
                    "audio": "original procedural ambient tones; no voiceover or external samples",
                    "shots": [{"work": w, "start": s, "end": e} for w, s, e in SHOTS],
                    "captures": list(reports.values()),
                    "source_sha256_lf": {"tools/render_immersive_video.py": sha(Path(__file__), True),
                                          "tools/render_video.py": sha(ROOT / "tools/render_video.py", True)},
                    "files": {path.name: sha(path) for path in sorted(result.iterdir())}}
        (result / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)
                                               + "\n", encoding="utf-8")
        result.rename(output)
    print(f"Saved 20 seconds / {20 * fps} frames to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg")
    args = parser.parse_args()
    try:
        produce(args.captures.resolve(), args.output.resolve(), args.ffmpeg)
    except Exception as exc:
        parser.exit(1, f"Render failed: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
