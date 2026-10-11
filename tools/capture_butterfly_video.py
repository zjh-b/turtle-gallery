"""Record the butterfly's 20-second interaction story from its real Tk window.

    python tools/capture_butterfly_video.py --output exports/butterfly-frames

Windows + Pillow 11.2.1 or newer. Only this process's artwork window is captured.
Fixed simulation steps are used, not real-time screen recording. The output
must be new; capture.json is written only after all frames and source checks.
Shorter --seconds captures are allowed for rehearsals; later events are omitted.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / "社团展示/28_霓光蝶舞.py"
SOURCES = (SCENE, ROOT / "社团展示/舞台.py", ROOT / "社团展示/作品导出.py",
           Path(__file__))
STORY = ((.8, "click", (280, 150)), (4., "click", (-280, 110)),
         (8., "C", None), (10.5, "M", None), (12., "C", None),
         (14., "M", None), (14.2, "click", (230, 145)))


def timeline(fps, seconds):
    if type(fps) is not int or fps not in (24, 30):
        raise ValueError("fps must be 24 or 30")
    if not math.isfinite(seconds) or not 0 < seconds <= 20:
        raise ValueError("seconds must be finite, positive and at most 20")
    frames = max(1, math.ceil(seconds * fps))
    events = []
    for at, action, position in STORY:
        frame = round(at * fps)
        if frame >= frames:
            continue
        event = {"frame": frame, "requested_time": at, "time": frame / fps,
                 "action": action}
        if position is not None:
            event["logical_position"] = list(position)
        events.append(event)
    return frames, events


def apply_event(app, event):
    """Use the same callbacks as clicks/C/M; these are not OS input events."""
    action = event["action"]
    if action == "click":
        x, y = event["logical_position"]
        app.attract(x * app.stage.scale, y * app.stage.scale)
    elif action == "C":
        app.change_theme()
    elif action == "M":
        app.toggle_motion()
    else:
        raise ValueError(f"Unsupported story action: {action}")


def render_frame(app, index, fps, events):
    for event in events:
        if event["frame"] == index:
            apply_event(app, event)
    app.frame(0 if index == 0 else 1 / fps)


def source_hashes():
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() for path in SOURCES}


def state(app, frame, fps):
    return {"frame": frame, "time": frame / fps, "scene_time": app.time,
            "theme": app.theme, "motion": app.motion, "offset": app.offset[:],
            "target": app.target[:] if app.target else None}


def capture(output, fps=30, seconds=20):
    frames, events = timeline(fps, seconds)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    sys.path.insert(0, str(ROOT))
    from 社团展示.作品导出 import capture_artwork, export_support
    available, reason = export_support()
    if not available:
        raise RuntimeError(reason)
    before = source_hashes()
    sys.path.insert(0, str(SCENE.parent))
    spec = importlib.util.spec_from_file_location("butterfly_recording_scene", SCENE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output.mkdir(parents=True, exist_ok=False)
    app = None
    try:
        app = module.NeonButterfly()
        app.stage.reset_action = app.reset
        factor = min(1.5, (app.stage.root.winfo_screenwidth() - 80) / 1000,
                     (app.stage.root.winfo_screenheight() - 100) / 720)
        app.stage.root.geometry(f"{round(1000*factor)}x{round(720*factor)}+20+20")
        app.stage.root.update()
        app.stage.reset()
        # Prevent unrelated keyboard/mouse input from altering this fixed story.
        # The window close button remains available for cancellation.
        app.stage.screen.onclick(None)
        for key in ("c", "C", "m", "M", "space", "r", "R", "F11", "h", "H"):
            app.stage.screen.onkey(None, key)
        for _ in range(fps):
            app.frame(1 / fps)
        samples = {0, frames - 1}
        for event in events:
            samples.update((max(0, event["frame"]-1), event["frame"]))
        records, size = [], None
        for index in range(frames):
            render_frame(app, index, fps, events)
            app.stage.screen.update()
            picture = capture_artwork(app.stage)
            if size is None:
                size = picture.size
            elif picture.size != size:
                raise RuntimeError("Artwork size changed; keep the window unchanged")
            picture.save(output / f"frame-{index:05d}.png")
            if index in samples:
                records.append(state(app, index, fps))
            if (index+1) % fps == 0:
                print(f"Butterfly: {index+1}/{frames} frames", flush=True)
        if source_hashes() != before:
            raise RuntimeError("Sources changed during capture; record again")
        report = {"work": 28, "renderer": "actual Tk window artwork capture",
                  "input": "scripted scene callbacks, not OS mouse/keyboard events",
                  "timing": "fixed simulation steps, not a real-time FPS measurement",
                  "frames": frames, "size": list(size), "fps": fps,
                  "duration": frames / fps, "requested_seconds": seconds,
                  "warmup_seconds": 1, "events": events, "state_samples": records,
                  "frame_pattern": "frame-%05d.png", "source_sha256_lf": before}
    finally:
        if app is not None:
            app.stage.close()
    (output / "capture.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    print(f"Saved {frames} frames ({size[0]}x{size[1]}) to {output}", flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fps", type=int, choices=(24, 30), default=30)
    parser.add_argument("--seconds", type=float, default=20)
    args = parser.parse_args()
    try:
        timeline(args.fps, args.seconds)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        capture(args.output, args.fps, args.seconds)
    except Exception as exc:
        parser.exit(1, f"Capture failed: {type(exc).__name__}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
