"""Record deterministic PNG frames from one real Tk artwork window (Windows).

    python tools/capture_immersive_video.py --work 29 --output exports/aurora-frames

Each invocation owns one window and captures only that window's artwork area.
Animation uses fixed simulation steps; wall-clock recording speed may differ.
The output directory must be new. A capture.json is written only on success.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
EVENTS = {
    29: ((.7, "touch", 200, 100), (3.1, "touch", 100, -190)),
    30: ((.6, "select", -290, -90), (3., "select", 290, 80)),
    31: ((.7, "illuminate", 400, 150), (3., "illuminate", -50, 150)),
}


def duration(value):
    """Reject NaN/Infinity as well as invalid or excessive capture lengths."""
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seconds must be a number") from exc
    if not math.isfinite(seconds) or not 0 < seconds <= 30:
        raise argparse.ArgumentTypeError("seconds must be positive and at most 30")
    return seconds


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def capture(args):
    sys.path.insert(0, str(ROOT))
    from run import catalog
    from 社团展示.作品导出 import capture_artwork, export_support

    available, reason = export_support()
    if not available:
        raise RuntimeError(reason)
    work = next(item for item in catalog().WORKS if item["id"] == args.work)
    path = ROOT / work["filename"]
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("immersive_capture_scene", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    args.output.mkdir(parents=True, exist_ok=False)
    frames = max(1, math.ceil(args.seconds * args.fps))
    events = [{"frame": round(at * args.fps), "requested_time": at,
               "time": round(at * args.fps) / args.fps, "action": action,
               "logical_position": [x, y]}
              for at, action, x, y in EVENTS[args.work]
              if round(at * args.fps) < frames]
    app = None
    try:
        app = getattr(module, work["entry_class"])()
        app.stage.reset_action = app.reset
        # Keep the original scene aspect while fitting the available desktop.
        factor = min(1.5, (app.stage.root.winfo_screenwidth() - 80) / 1000,
                     (app.stage.root.winfo_screenheight() - 100) / 720)
        app.stage.root.geometry(f"{round(1000 * factor)}x{round(720 * factor)}+20+20")
        app.stage.root.update()
        app.stage.reset()
        for _ in range(args.fps):
            app.frame(1 / args.fps)
        app.stage.screen.update()
        size = None
        for index in range(frames):
            for event in events:
                if event["frame"] == index:
                    x, y = event["logical_position"]
                    getattr(app, event["action"])(x * app.stage.scale, y * app.stage.scale)
            app.frame(0 if index == 0 else 1 / args.fps)
            app.stage.screen.update()
            picture = capture_artwork(app.stage)
            if size is None:
                size = picture.size
            elif picture.size != size:
                raise RuntimeError("Artwork size changed during capture; keep the window unchanged.")
            picture.save(args.output / f"frame-{index:05d}.png")
            if (index + 1) % args.fps == 0:
                print(f"Work {args.work}: {index + 1}/{frames} frames", flush=True)
        sources = (path, path.parent / "舞台.py", path.parent / "作品导出.py", Path(__file__))
        report = {"work": args.work, "renderer": "actual Tk window artwork capture",
                  "frames": frames, "size": list(size), "fps": args.fps,
                  "duration": frames / args.fps, "requested_seconds": args.seconds,
                  "warmup_seconds": 1, "events": events,
                  "frame_pattern": "frame-%05d.png",
                  "source_sha256_lf": {source.relative_to(ROOT).as_posix(): digest(source)
                                       for source in sources}}
        (args.output / "capture.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {frames} frames ({size[0]}x{size[1]}) to {args.output}", flush=True)
    finally:
        if app is not None:
            app.stage.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--work", type=int, choices=(29, 30, 31), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=int, choices=(24, 30), default=30)
    parser.add_argument("--seconds", type=duration, default=7.)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.output.exists():
        parser.error("Output directory already exists; choose a new directory.")
    try:
        capture(args)
    except Exception as exc:
        parser.exit(1, f"Capture failed: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
