"""Turtle Gallery entry point. Run from any working directory, without installing a package."""
import argparse
import importlib.util
from pathlib import Path
import runpy
import sys


ROOT = Path(__file__).resolve().parent
GALLERY = ROOT / "社团展示"


def catalog():
    """Read metadata without importing Tk or opening a window."""
    path = GALLERY / "作品目录.py"
    spec = importlib.util.spec_from_file_location("turtle_gallery_catalog", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def environment_check(works):
    failures = []
    print(f"Python {sys.version.split()[0]}")
    if sys.version_info < (3, 9):
        failures.append("Python 3.9 or newer is required.")
    try:
        import tkinter
        print(f"Tkinter {tkinter.TkVersion}: available (no window opened)")
    except ImportError:
        failures.append("Tkinter is missing. Install a Python distribution with Tk support.")
    for work in works:
        if not (ROOT / work["filename"]).is_file():
            failures.append(f"Missing source: {work['filename']}")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"{len(works)} works: all source files present.")
    print("Ready. Run python run.py to open the gallery. A desktop display is required.")
    return 0


def execute(path):
    sys.path.insert(0, str(path.parent))
    # Individual works should see their own argv, just as when run directly.
    sys.argv = [str(path)]
    try:
        runpy.run_path(str(path), run_name="__main__")
        return 0
    except KeyboardInterrupt:
        return 0
    except ImportError as exc:
        if exc.name in ("tkinter", "_tkinter", "turtle"):
            print("Tkinter/Turtle is unavailable. Install Python with Tk support; see README.md.", file=sys.stderr)
            return 1
        raise
    except Exception as exc:
        # Some original Turtle animation loops raise Terminator after their
        # window is closed. Closing a window is a successful exit.
        import turtle
        if isinstance(exc, turtle.Terminator):
            return 0
        import tkinter
        if isinstance(exc, tkinter.TclError) and any(marker in str(exc).lower()
                                                    for marker in ("no display name", "couldn't connect to display")):
            print("A desktop display is required. On a remote/headless machine, use --list or --check.", file=sys.stderr)
            return 1
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Turtle Gallery — 24 creative Python works.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List all works without opening a window")
    group.add_argument("--demo", metavar="ID", help="Run a specific work (01–24)")
    group.add_argument("--check", action="store_true", help="Check Python, Tkinter and source files without opening a window")
    args = parser.parse_args(argv)
    data = catalog()
    if args.list:
        for work in data.WORKS:
            print(f"{work['number']}  {work['title']}  [{work['collection']}]  {work['filename']}")
        return 0
    if args.check:
        return environment_check(data.WORKS)
    if args.demo:
        work = data.get_work(args.demo)
        if work is None:
            parser.error(f"Unknown work: {args.demo}. Use --list to see available IDs.")
        return execute(ROOT / work["filename"])
    return execute(GALLERY / "启动展示.py")


if __name__ == "__main__":
    raise SystemExit(main())
