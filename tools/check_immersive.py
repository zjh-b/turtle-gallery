"""Capture real immersive scenes and measure local rendering work (Windows/Pillow).

    python tools/check_immersive.py --works 29 30 31 --samples 120
    python tools/check_immersive.py --works 30 --baseline-ref HEAD~1

Each scene/revision runs sequentially in a fresh Python process. Timing measures
manual frame calls plus Tk updates, without Stage.tick scheduling or recording;
it is not a promised display frame rate. Baselines replace ONLY the scene source:
the catalog, Stage, capture helper, interpreter and environment remain current.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SIZES = ((1000, 720), (760, 580))
SCOPE = ("Manual deterministic dt=0.025 s; geometry/Canvas submission and Tk update "
         "measured separately; no timer scheduling, recording or FPS guarantee. "
         "Baseline swaps only the scene source; shared Stage and helpers are current.")


def digest(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summary(values):
    return {"median_ms": round(statistics.median(values), 3),
            "p95_ms": round(sorted(values)[math.ceil(.95 * len(values)) - 1], 3)}


def click(app, number):
    scale = app.stage.scale
    if number == 29:
        app.touch(200 * scale, 100 * scale)
        app.touch(100 * scale, -190 * scale)
    elif number == 30:
        app.select(-290 * scale, -90 * scale)
        app.reverse()
    else:
        app.illuminate(400 * scale, 150 * scale)


def check_work(args):
    sys.path.insert(0, str(ROOT))
    from run import catalog
    from tools.render_media import grab
    from 社团展示.作品导出 import capture_artwork
    import PIL

    work = next(work for work in catalog().WORKS if work["id"] == args.child)
    path = ROOT / work["filename"]
    source = (subprocess.check_output(["git", "show", f"{args.source_ref}:{work['filename']}"],
                                      cwd=ROOT) if args.source_ref else path.read_bytes())
    sys.path.insert(0, str(path.parent))
    module = types.ModuleType("immersive_check_scene")
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    app = getattr(module, work["entry_class"])()
    report = {"id": args.child, "source_ref": args.source_ref or "working-tree", "scope": SCOPE,
              "source_sha256_lf": {work["filename"]: digest(source),
                                     "社团展示/舞台.py": digest((path.parent / "舞台.py").read_bytes())},
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "tk": app.stage.root.tk.call("info", "patchlevel"),
                              "pillow": PIL.__version__}, "sizes": [], "passed": False}
    try:
        app.stage.reset_action = app.reset
        for width, height in SIZES:
            app.stage.root.geometry(f"{width}x{height}+20+20")
            app.stage.root.update()
            app.stage.reset()
            app.frame(0)
            app.stage.screen.update()
            initial = capture_artwork(app.stage)
            for _ in range(50):
                app.frame(.04)
            captures = []
            for palette in range(3):
                app.frame(0)
                app.stage.screen.update()
                stem = f"{args.child}-{width}-{palette}"
                capture_artwork(app.stage).save(args.output / f"{stem}.png")
                captures.append(f"{stem}.png")
                if width == 760:
                    grab(app.stage.root).save(args.output / f"{stem}-window.png")
                    captures.append(f"{stem}-window.png")
                app.change_theme()
            click(app, args.child)
            for _ in range(25):
                app.frame(.04)
            app.stage.screen.update()
            interaction = capture_artwork(app.stage)
            interaction_name = f"{args.child}-{width}-interaction.png"
            interaction.save(args.output / interaction_name)
            captures.append(interaction_name)
            app.stage.paused = True
            for _ in range(5):
                app.frame(0)
            app.stage.screen.update()
            paused = capture_artwork(app.stage)
            freeze_ok = (paused.size, paused.mode, paused.tobytes()) == (
                interaction.size, interaction.mode, interaction.tobytes())
            app.stage.reset()  # The public handler used by R also clears pause.
            app.frame(0)
            app.stage.screen.update()
            reset = capture_artwork(app.stage)
            reset_ok = not app.stage.paused and (reset.size, reset.mode, reset.tobytes()) == (
                initial.size, initial.mode, initial.tobytes())
            for _ in range(20):
                app.frame(.025)
                app.stage.screen.update()
            count = len(app.stage.canvas.find_all())
            timings = {key: [] for key in ("frame_ms", "frame_cpu_ms", "tk_update_ms", "total_ms")}
            peak = count
            for _ in range(args.samples):
                started, cpu_start = time.perf_counter(), time.process_time()
                app.frame(.025)
                cpu_end, boundary = time.process_time(), time.perf_counter()
                app.stage.screen.update()
                finished = time.perf_counter()
                values = ((boundary - started), (cpu_end - cpu_start),
                          (finished - boundary), (finished - started))
                for key, value in zip(timings, values):
                    timings[key].append(1000 * value)
                peak = max(peak, len(app.stage.canvas.find_all()))
            checks = {"paused_pixels_unchanged": freeze_ok, "reset_pixels_restored": reset_ok,
                      "canvas_pool_stable": peak == count}
            record = {"requested_window": [width, height],
                      "actual_window": [app.stage.root.winfo_width(), app.stage.root.winfo_height()],
                      "samples": args.samples, "canvas_items": count, "peak_canvas_items": peak,
                      "checks": checks, "captures": captures,
                      **{key: summary(values) for key, values in timings.items()}}
            report["sizes"].append(record)
            print(f"{args.child} {width}x{height}: {record['total_ms']}; checks={checks}", flush=True)
        report["passed"] = all(all(item["checks"].values()) for item in report["sizes"])
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        try:
            write_json(args.output / f"{args.child}-report.json", report)
        finally:
            app.stage.close()
    return 0 if report["passed"] else 1


def sample_count(value):
    value = int(value)
    if not 10 <= value <= 600:
        raise argparse.ArgumentTypeError("samples must be between 10 and 600")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--works", nargs="+", type=int, choices=(29, 30, 31), default=[29, 30, 31])
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "immersive-check")
    parser.add_argument("--samples", type=sample_count, default=120)
    parser.add_argument("--baseline-ref", help="Compare scene source from a trusted local Git commit/ref")
    parser.add_argument("--child", type=int, choices=(29, 30, 31), help=argparse.SUPPRESS)
    parser.add_argument("--source-ref", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Real window capture requires a Windows desktop.")
    try:
        import PIL
        if tuple(int(n) for n in PIL.__version__.split(".")[:3]) < (11, 2, 1):
            raise ImportError("Pillow is too old")
    except (ImportError, ValueError):
        parser.error("Install Pillow 11.2.1+: python -m pip install -r requirements-export.txt")
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.child:
        return check_work(args)
    baseline = None
    if args.baseline_ref:
        baseline = subprocess.check_output(["git", "rev-parse", "--verify", "--end-of-options",
                                            args.baseline_ref + "^{commit}"], cwd=ROOT, text=True).strip()
    report = {"scope": SCOPE, "baseline_ref": baseline, "samples": args.samples,
              "metric_notes": {"frame_ms": "Elapsed geometry and Canvas command submission",
                               "frame_cpu_ms": "Process CPU during frame; OS timer granularity applies",
                               "tk_update_ms": "Elapsed explicit screen.update",
                               "total_ms": "Elapsed frame plus Tk update; capture excluded"},
              "runs": {}, "comparisons": [], "passed": True}
    variants = [("baseline", baseline), ("current", None)] if baseline else [("current", None)]
    for label, ref in variants:
        folder = args.output / label
        folder.mkdir(exist_ok=True)
        report["runs"][label] = []
        for number in dict.fromkeys(args.works):
            saved = folder / f"{number}-report.json"
            saved.unlink(missing_ok=True)
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--child", str(number),
                       "--output", str(folder), "--samples", str(args.samples)]
            if ref:
                command.extend(["--source-ref", ref])
            result = subprocess.run(command, cwd=ROOT)
            # A failed load must not reuse a report left by an earlier invocation.
            item = (json.loads(saved.read_text(encoding="utf-8")) if saved.is_file() else
                    {"id": number, "passed": False, "error": f"Child exited {result.returncode}"})
            item["passed"] = item["passed"] and result.returncode == 0
            report["runs"][label].append(item)
            report["passed"] &= item["passed"]
    if baseline:
        for before, after in zip(report["runs"]["baseline"], report["runs"]["current"]):
            if before["passed"] and after["passed"]:
                for old, new in zip(before["sizes"], after["sizes"]):
                    report["comparisons"].append({"id": after["id"], "window": new["requested_window"],
                        "current_minus_baseline_ms": {
                            key: {stat: round(new[key][stat] - old[key][stat], 3)
                                  for stat in ("median_ms", "p95_ms")}
                            for key in ("frame_ms", "frame_cpu_ms", "tk_update_ms", "total_ms")}})
    write_json(args.output / "report.json", report)
    print(f"Report: {args.output / 'report.json'}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
