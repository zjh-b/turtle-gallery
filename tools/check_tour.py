"""Run a real, visible Windows tour for at least ten minutes (standard library).

    python tools/check_tour.py --output .work/tour-check.json

Uses the actual launcher, artwork child processes, Tk windows and IPC. Keyboard
messages target only the owned artwork window. Keep the desktop unlocked and do
not close the windows during the check. This is an optional manual acceptance
tool, not a headless CI test or a frame-rate benchmark.
"""
import argparse
import ctypes
from datetime import datetime
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


class ArtworkWindow:
    def __init__(self):
        self.api = ctypes.windll.user32
        self.callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        for name in ("EnumWindows", "EnumChildWindows"):
            getattr(self.api, name).restype = ctypes.c_bool
        self.api.EnumWindows.argtypes = [self.callback, ctypes.c_void_p]
        self.api.EnumChildWindows.argtypes = [ctypes.c_void_p, self.callback, ctypes.c_void_p]
        self.api.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        self.api.GetClassNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        self.api.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        for name in ("IsWindowVisible", "IsIconic"):
            getattr(self.api, name).argtypes = [ctypes.c_void_p]

    def find(self, pid):
        windows = []

        @self.callback
        def visit(hwnd, _):
            owner = ctypes.c_ulong()
            self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            if owner.value == pid and self.api.IsWindowVisible(hwnd):
                windows.append(hwnd)
            return True

        self.api.EnumWindows(visit, None)
        if windows and self.api.IsIconic(windows[0]):
            raise RuntimeError("Artwork window is minimized")
        return windows[0] if windows else None

    def key(self, pid, code):
        children = []

        @self.callback
        def visit(hwnd, _):
            name = ctypes.create_unicode_buffer(128)
            self.api.GetClassNameW(hwnd, name, 128)
            if name.value == "TkChild":
                children.append(hwnd)
            return True

        window = self.find(pid)
        if window is None:
            raise RuntimeError("Artwork window was not ready for keyboard input")
        self.api.EnumChildWindows(window, visit, None)
        if not children:
            raise RuntimeError("Artwork Canvas was not found")
        # Stage contains a single Canvas; never send input to unrelated windows.
        for message, flags in ((0x100, 1), (0x101, 0xC0000001)):
            if not self.api.PostMessageW(children[-1], message, code, flags):
                raise RuntimeError("Could not deliver artwork key")


def run(args):
    sys.path.insert(0, str(ROOT / "社团展示"))
    app = importlib.import_module("启动展示").Launcher()
    app.root.geometry("1060x850+15+15")
    windows = ArtworkWindow()
    began = time.monotonic()
    started_at = datetime.now().astimezone().isoformat()
    children, scenes, actions, failures, window_gaps = [], [], [], [], []
    state, changed, heartbeat = "start", began, -1
    continuous_start = continuous_end = None
    missing_since = None
    passed = False

    def elapsed():
        return round(time.monotonic() - began, 3)

    def transition(value):
        nonlocal state, changed
        actions.append({"seconds": elapsed(), "action": value})
        state, changed = value, time.monotonic()
        print(f"{elapsed():.1f}s {value}", flush=True)

    def fail(message):
        failures.append(f"{message}; phase={state}; active={app.tour_active}; "
                        f"paused={app.tour_paused}; status={app.status.get()}")
        app.close()

    def callback_error(kind, value, traceback):
        fail(f"Tk callback: {kind.__name__}: {value}")

    append_output = app.console_append
    child_output = ""

    def capture_output(text):
        nonlocal child_output
        child_output = (child_output + text)[-8000:]
        if "Traceback (most recent call last)" in child_output or "Exception in Tkinter callback" in child_output:
            raise RuntimeError("Artwork reported an exception: " + child_output[-2000:])
        append_output(text)

    app.console_append = capture_output

    def watch():
        nonlocal heartbeat, continuous_start, continuous_end, passed, missing_since
        now = time.monotonic()
        if now - began > args.duration + 90:
            raise RuntimeError("Acceptance exceeded its overall time limit")
        if app.child is not None and app.child not in children:
            children.append(app.child)
        ready = app.child is not None and app.tour_ready and app.child.poll() is None
        if ready:
            # Tk destroys its window before its process exits and before the
            # launcher's next IPC poll. Allow only this bounded transition gap.
            if windows.find(app.child.pid) is None:
                if missing_since is None:
                    missing_since = now
                    window_gaps.append({"seconds": elapsed(), "pid": app.child.pid,
                                        "next_received": app.tour_next_requested})
                if now - missing_since > 2:
                    raise RuntimeError("Artwork window missing for more than two seconds")
                ready = False
            else:
                missing_since = None
        else:
            missing_since = None
        if ready:
            if not scenes or scenes[-1]["pid"] != app.child.pid:
                scenes.append({"seconds": elapsed(), "id": app.active_work["id"],
                               "pid": app.child.pid, "phase": state})
                print(f"Scene {scenes[-1]}", flush=True)
        if int((now - began) // 30) != heartbeat:
            heartbeat = int((now - began) // 30)
            print(f"{elapsed():.1f}s heartbeat: {state}, scenes={len(scenes)}", flush=True)
        if any(child.poll() not in (None, 0) for child in children):
            raise RuntimeError("Artwork exited with a nonzero code")
        if state == "start" and ready:
            windows.key(app.child.pid, ord("C"))
            transition("keyboard_takeover_sent")
        elif state == "keyboard_takeover_sent" and app.tour_paused:
            app.pause_tour()
            transition("launcher_resume_sent")
        elif state == "launcher_resume_sent" and not app.tour_paused:
            app.pause_tour()
            transition("launcher_pause_sent")
        elif state == "launcher_pause_sent" and app.tour_paused:
            transition("pause_confirmed")
        elif state == "pause_confirmed" and now - changed >= 2:
            if not app.tour_paused:
                raise RuntimeError("Paused tour resumed unexpectedly")
            windows.key(app.child.pid, ord("P"))
            transition("keyboard_resume_sent")
        elif state == "keyboard_resume_sent" and not app.tour_paused:
            app.next_tour()
            transition("manual_next_sent")
        elif state == "manual_next_sent" and ready and len(scenes) >= 2:
            if app.active_work["id"] != 26:
                raise RuntimeError("Manual next did not reach work 26")
            continuous_start = now
            transition("continuous_loop")
        elif state == "continuous_loop":
            if not app.tour_active or app.tour_paused:
                raise RuntimeError("Continuous tour stopped or paused unexpectedly")
            if now - began - scenes[-1]["seconds"] > 40:
                raise RuntimeError("Tour made no scene progress for more than forty seconds")
            if now - continuous_start >= args.duration and ready:
                continuous_end = now
                if len(scenes) < max(18, args.duration // 30 - 2) or {scene["id"] for scene in scenes} != {25, 26, 27}:
                    raise RuntimeError("Insufficient real scene transitions")
                expected = [25, 26, 27]
                if any(scene["id"] != expected[i % 3] for i, scene in enumerate(scenes)):
                    raise RuntimeError("Tour order changed")
                windows.key(app.child.pid, 0x1B)
                transition("escape_sent")
        elif state == "escape_sent" and app.child is None and not app.tour_active:
            if any(child.poll() != 0 for child in children):
                raise RuntimeError("Escape left an active or failed artwork")
            transition("escape_and_cleanup_confirmed")
            app.start_tour("25,26,27", 30)
            transition("restart_for_launcher_close")
        elif state == "restart_for_launcher_close" and ready:
            transition("launcher_close_sent")
            app.close()
            passed = True
            return
        if state != "continuous_loop" and now - changed > 35:
            raise RuntimeError(f"Timed out waiting for {state}")
        app.root.after(100, watch)

    app.root.report_callback_exception = callback_error
    app.root.protocol("WM_DELETE_WINDOW", lambda: fail("Acceptance interrupted by window close"))
    try:
        app.start_tour("25,26,27", 30)
        app.root.after(100, watch)
        app.root.mainloop()
    except KeyboardInterrupt:
        failures.append("Acceptance interrupted by keyboard")
    finally:
        if not app.closing:
            app.close()
        orphans = [child for child in children if child.poll() is None]
        if orphans:
            failures.append(f"Launcher left {len(orphans)} artwork processes alive")
            for child in orphans:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
        if not passed and not failures:
            failures.append("Acceptance ended before all checks finished")
        sources = ["run.py", "tools/check_tour.py", "社团展示/启动展示.py", "社团展示/巡展.py", "社团展示/舞台.py"]
        sources += [str(path.relative_to(ROOT)).replace("\\", "/")
                    for number in (25, 26, 27) for path in (ROOT / "社团展示").glob(f"{number}_*.py")]
        report = {
            "status": "passed" if passed and not failures else "failed",
            "host_started_at": started_at, "host_finished_at": datetime.now().astimezone().isoformat(),
            "platform": platform.platform(), "python": platform.python_version(),
            "tk": app.root.tk.call("info", "patchlevel"),
            "requested_seconds": args.duration, "seconds_per_work": 30,
            "continuous_seconds": round(continuous_end - continuous_start, 3) if continuous_end else None,
            "continuous_start_seconds": round(continuous_start - began, 3) if continuous_start else None,
            "elapsed_seconds": elapsed(), "visible_windows_checked": True,
            "scenes": scenes, "actions": actions, "window_transition_gaps": window_gaps,
            "failures": failures,
            "recent_child_output": child_output,
            "orphan_processes_before_fallback_cleanup": len(orphans),
            "child_exit_codes": [child.poll() for child in children],
            "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                              for name in sources},
            "limitations": ["Single Windows desktop; not a performance benchmark.",
                            "No lock screen, remote desktop or mixed-DPI multiple monitors tested.",
                            "Host timestamps are recorded verbatim; not a client calendar assertion."]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {args.output}", flush=True)
    return 0 if report["status"] == "passed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=600, help="continuous session seconds (600–3600)")
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "tour-check.json")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This real-window check requires Windows.")
    if not 600 <= args.duration <= 3600:
        parser.error("--duration must be between 600 and 3600 seconds")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
