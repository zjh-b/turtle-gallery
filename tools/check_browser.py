#!/usr/bin/env python3
"""Optional real-browser regression checks for the static fireworks page.

Install with ``python -m pip install -r requirements-browser.txt``. Windows
uses installed Edge by default; CI can use ``--browser chromium`` after
``python -m playwright install chromium``. Screenshots and a JSON report go
to .work/browser. Mobile checks emulate Chromium touch, not a physical phone.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import platform
import sys
import threading
import time


ROOT = Path(__file__).resolve().parents[1]

# Observe the native scheduler without exposing test hooks in the application.
# The visibility override is limited to lifecycle checks in this test context.
SCHEDULER_PROBE = """(() => {
  const request = window.requestAnimationFrame.bind(window);
  const cancel = window.cancelAnimationFrame.bind(window);
  const pending = new Set();
  const probe = window.__browserCheck = {frames: 0, peak: 0, visibility: null};
  Object.defineProperty(probe, 'pending', {get: () => pending.size});
  window.requestAnimationFrame = callback => {
    let id = request(time => {pending.delete(id); probe.frames++; callback(time);});
    pending.add(id);
    probe.peak = Math.max(probe.peak, pending.size);
    return id;
  };
  window.cancelAnimationFrame = id => {pending.delete(id); cancel(id);};
  const hidden = Object.getOwnPropertyDescriptor(Document.prototype, 'hidden').get;
  const state = Object.getOwnPropertyDescriptor(Document.prototype, 'visibilityState').get;
  Object.defineProperties(document, {
    hidden: {get: () => probe.visibility === null ? hidden.call(document) : probe.visibility === 'hidden'},
    visibilityState: {get: () => probe.visibility === null ? state.call(document) : probe.visibility}
  });
})()"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *args):
        pass


@contextmanager
def local_site():
    """Keep the ephemeral HTTP server alive only for this check invocation."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "docs")))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def ready(page, base_url):
    response = page.goto(base_url + "/play/fireworks.html", wait_until="networkidle")
    require(response is not None and response.ok, "Fireworks page must return HTTP 200")
    page.wait_for_function("""() => {
      const canvas = document.querySelector('#fireworks-canvas');
      const controls = document.querySelector('#play-controls');
      return canvas && !canvas.hidden && controls && !controls.disabled;
    }""", timeout=5000, polling=25)
    require(page.locator("#fireworks-fallback").is_hidden(), "Ready page must replace fallback with Canvas")
    require(page.locator("#play-status").inner_text().strip(), "Ready page must announce its status")


def observed_page(context):
    context.add_init_script(SCHEDULER_PROBE)
    page = context.new_page()
    page.set_default_timeout(5000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return page, errors


def canvas_hash(page):
    return page.locator("#fireworks-canvas").evaluate("""async canvas => {
      const bytes = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
      const hash = await crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
    }""")


def assert_static(page, message):
    before = canvas_hash(page)
    frames = page.evaluate("window.__browserCheck.frames")
    page.wait_for_timeout(180)
    require(canvas_hash(page) == before, message + ": rendered pixels changed")
    require(page.evaluate("window.__browserCheck.frames") == frames, message + ": animation frames kept running")
    require(page.evaluate("window.__browserCheck.pending") == 0, message + ": a frame is still scheduled")


def assert_playing(page):
    frames = page.evaluate("window.__browserCheck.frames")
    # Time-based polling keeps Playwright's own RAF callbacks out of the probe.
    page.wait_for_function("frames => window.__browserCheck.frames > frames + 2", arg=frames, polling=25)
    require(page.locator("#pause").get_attribute("aria-pressed") == "false", "Playing state must be exposed by pause button")


def assert_no_overflow(page):
    require(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "Layout must fit viewport without horizontal overflow")


def assert_dpi_cap(page):
    dimensions = page.locator("#fireworks-canvas").evaluate("""canvas => {
      const rect = canvas.getBoundingClientRect();
      return {width: canvas.width, height: canvas.height, cssWidth: rect.width, cssHeight: rect.height};
    }""")
    require(dimensions["width"] <= dimensions["cssWidth"] * 2 + 2, "Canvas width exceeds DPR cap of 2")
    require(dimensions["height"] <= dimensions["cssHeight"] * 2 + 2, "Canvas height exceeds DPR cap of 2")
    require(dimensions["width"] > 0 and dimensions["height"] > 0, "Canvas must have a drawable backing store")


def check_desktop(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "Automatic display must be opt-in")
        require(page.locator("#pause").get_attribute("aria-pressed") == "true", "Initial scene must be paused")
        require(page.locator("#fireworks-canvas").get_attribute("tabindex") == "0", "Keyboard users must be able to focus Canvas")
        assert_static(page, "Initial scene must remain static")
        assert_no_overflow(page)
        page.screenshot(path=str(output / "desktop.png"), full_page=True)

        page.locator("#shape").select_option("2")
        page.locator("#palette").select_option("1")
        page.locator("#shape").focus()
        page.keyboard.press("f")
        assert_static(page, "Canvas shortcuts must not run while a form control has focus")
        require(page.locator("#palette").input_value() == "1", "Palette choice must be retained")

        initial = canvas_hash(page)
        page.locator("#fireworks-canvas").click(position={"x": 190, "y": 110})
        assert_playing(page)
        page.wait_for_timeout(250)
        require(canvas_hash(page) != initial, "Clicking Canvas must produce a visible launch")
        page.locator("#pause").click()
        require(page.locator("#pause").get_attribute("aria-pressed") == "true", "Pause state must be announced")
        assert_static(page, "Paused scene must stop drawing")

        page.locator("#fireworks-canvas").focus()
        page.keyboard.press("Space")
        assert_playing(page)
        page.keyboard.press("Space")
        assert_static(page, "Keyboard pause must stop drawing")
        page.keyboard.press("Enter")
        assert_playing(page)
        page.keyboard.press("a")
        require(page.locator("#auto").get_attribute("aria-pressed") == "true", "A shortcut must enable automatic display")
        page.keyboard.press("a")
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "A shortcut must disable automatic display")
        page.keyboard.press("f")
        page.wait_for_timeout(1100)
        page.locator("#pause").click()
        page.screenshot(path=str(output / "desktop-finale.png"), full_page=True)
        page.locator("#fireworks-canvas").focus()
        page.keyboard.press("r")
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "Reset must stop automatic display")
        require(page.locator("#pause").get_attribute("aria-pressed") == "true", "Reset must restore a static scene")
        assert_static(page, "Keyboard reset must remain static")

        page.locator("#launch").click()
        assert_playing(page)
        page.locator("#finale").click()
        page.locator("#auto").click()
        require(page.locator("#auto").get_attribute("aria-pressed") == "true", "Automatic display button must enable the mode")
        page.locator("#reset").click()
        assert_static(page, "Reset button must stop motion")
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "Reset button must disable automatic display")
        page.set_viewport_size({"width": 800, "height": 900})
        assert_no_overflow(page)
        assert_dpi_cap(page)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_reduced_motion(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(page.locator("#reduced-motion").is_checked(), "System reduced-motion preference must be applied")
        require(page.locator("#pause").is_disabled() and page.locator("#auto").is_disabled(), "Reduced motion must disable playback and automatic display")
        assert_static(page, "Reduced-motion initial scene")

        hashes = set()
        for shape, palette in (("0", "0"), ("1", "1"), ("2", "2"), ("3", "3")):
            page.locator("#reset").click()
            page.locator("#shape").select_option(shape)
            page.locator("#palette").select_option(palette)
            before = canvas_hash(page)
            page.locator("#fireworks-canvas").click(position={"x": 230, "y": 90})
            after = canvas_hash(page)
            require(after != before, "Reduced-motion input must draw a visible static burst")
            hashes.add(after)
            assert_static(page, "Reduced-motion burst must stay static")
        require(len(hashes) == 4, "Different shape/palette selections must visibly affect fireworks")
        page.screenshot(path=str(output / "reduced-motion.png"), full_page=True)

        before = canvas_hash(page)
        page.locator("#finale").click()
        require(canvas_hash(page) != before, "Reduced-motion finale must draw static fireworks")
        assert_static(page, "Reduced-motion finale")
        page.locator("#fireworks-canvas").focus()
        page.keyboard.press("a")
        page.keyboard.press("Space")
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "Keyboard shortcuts must respect reduced motion")
        assert_static(page, "Reduced-motion keyboard guards")

        page.locator("#reduced-motion").uncheck()
        require(page.locator("#pause").is_enabled() and page.locator("#auto").is_enabled(), "Leaving reduced motion must restore controls")
        page.locator("#launch").click()
        assert_playing(page)
        page.locator("#reduced-motion").check()
        assert_static(page, "Enabling reduced motion while playing must stop animation")
        require(page.locator("#auto").get_attribute("aria-pressed") == "false", "Reduced motion must stop automatic display")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def set_visibility(page, state):
    page.evaluate("""state => {
      window.__browserCheck.visibility = state;
      document.dispatchEvent(new Event('visibilitychange'));
    }""", state)


def check_lifecycle(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}, reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        page.locator("#launch").click()
        assert_playing(page)
        set_visibility(page, "hidden")
        assert_static(page, "Hidden document must cancel its animation frame")
        set_visibility(page, "visible")
        assert_playing(page)
        page.locator("#pause").click()
        set_visibility(page, "hidden")
        set_visibility(page, "visible")
        assert_static(page, "Visibility changes must preserve a user's pause")
        page.locator("#pause").click()
        assert_playing(page)
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true}))")
        assert_static(page, "Pagehide must cancel animation")
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
        assert_playing(page)
        page.locator("#pause").click()
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true})); window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}));")
        assert_static(page, "Restoring a paused page must preserve its pause")
        page.evaluate("""() => {
          const pause = document.querySelector('#pause');
          for (let i = 0; i < 24; i++) pause.click();
        }""")
        assert_static(page, "Rapid playback toggles must leave no frame running")
        require(page.evaluate("window.__browserCheck.peak") <= 1, "Lifecycle changes must never create duplicate animation loops")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def touch_points(points):
    return [{"id": index + 1, "x": x, "y": y, "radiusX": 2, "radiusY": 2, "force": 1}
            for index, (x, y) in enumerate(points)]


def check_mobile(browser, base_url, output):
    with browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                             is_mobile=True, has_touch=True, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        action = page.locator("#fireworks-canvas").evaluate("el => getComputedStyle(el).touchAction")
        require("pan-y" in action and "pinch-zoom" in action, "Canvas must permit vertical scrolling and pinch zoom")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        canvas = page.locator("#fireworks-canvas")
        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        x, y = box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5
        before = canvas_hash(page)
        page.touchscreen.tap(x, y)
        require(canvas_hash(page) != before, "A real emulated touch tap must draw a burst")
        assert_static(page, "Reduced-motion touch tap")
        client = context.new_cdp_session(page)

        before = canvas_hash(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
        require(canvas_hash(page) == before, "A cancelled touch must not launch fireworks")

        before = canvas_hash(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 30, y), (x + 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(canvas_hash(page) == before, "A second touch must cancel the pending launch")

        before = canvas_hash(page)
        scroll_before = page.evaluate("window.scrollY")
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        for distance in (20, 40, 65, 90):
            client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x, y - distance)])})
            page.wait_for_timeout(30)
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(200)
        require(canvas_hash(page) == before, "Dragging across Canvas must not launch fireworks")
        require(page.evaluate("window.scrollY") > scroll_before, "Vertical touch dragging over Canvas must scroll the page")

        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        x, y = box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5
        before = canvas_hash(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        page.wait_for_timeout(760)
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(canvas_hash(page) == before, "Long touches must not count as taps")
        page.set_viewport_size({"width": 844, "height": 390})
        page.wait_for_timeout(100)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.screenshot(path=str(output / "mobile-landscape.png"), full_page=True)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def assert_fallback(page):
    image = page.locator("#fireworks-fallback")
    require(image.is_visible(), "Fallback preview must remain visible")
    require(image.evaluate("img => img.complete && img.naturalWidth > 0"), "Fallback preview must load successfully")
    require(page.locator("#fireworks-canvas").is_hidden(), "Unusable Canvas must remain hidden")
    require(page.locator("#play-controls").evaluate("el => el.disabled && [...el.querySelectorAll('button, input, select')].every(control => control.matches(':disabled'))"),
            "Unavailable interactive controls must remain disabled")
    require(page.locator("a[href*='github.com'][href*='blob/main']").count() > 0, "Fallback must retain a desktop source link")


def check_fallback(browser, base_url, output):
    with browser.new_context(java_script_enabled=False, viewport={"width": 1100, "height": 900}) as context:
        page = context.new_page()
        page.goto(base_url + "/play/fireworks.html", wait_until="networkidle")
        assert_fallback(page)
        require(page.locator("noscript").inner_text().strip(), "No-JavaScript visitors need a readable explanation")
        page.screenshot(path=str(output / "fallback-no-js.png"), full_page=True)

    with browser.new_context() as context:
        page = context.new_page()
        page.route("**/fireworks-config.json", lambda route: route.abort())
        page.goto(base_url + "/play/fireworks.html", wait_until="networkidle")
        page.wait_for_function("document.querySelector('#play-status').textContent.includes('暂不可用')", polling=25)
        assert_fallback(page)
        page.screenshot(path=str(output / "fallback-config.png"), full_page=True)

    with browser.new_context() as context:
        context.add_init_script("HTMLCanvasElement.prototype.getContext = function () { return null; };")
        page = context.new_page()
        page.goto(base_url + "/play/fireworks.html", wait_until="networkidle")
        page.wait_for_function("document.querySelector('#play-status').textContent.includes('暂不可用')", polling=25)
        assert_fallback(page)


def check_gallery(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1000}) as context:
        page = context.new_page()
        page.goto(base_url + "/index.html", wait_until="networkidle")
        page.wait_for_function("document.querySelectorAll('#gallery-grid .art-card').length === 28", polling=25)
        links = page.locator("a[href='play/fireworks.html']")
        require(links.count() >= 2, "Home and generated artwork card must both link to browser fireworks")
        card = page.locator(".art-card").filter(has=page.locator("#art-title-1"))
        require(card.locator("a[href='play/fireworks.html']").count() == 1, "Artwork 01 must have one playable entry")
        links.first.click()
        page.wait_for_url("**/play/fireworks.html")
        page.wait_for_function("!document.querySelector('#play-controls').disabled", polling=25)
        require(page.locator("#fireworks-canvas").is_visible(), "The gallery entry must open a working playable page")


CHECKS = {"desktop": check_desktop, "reduced-motion": check_reduced_motion,
          "lifecycle": check_lifecycle, "mobile": check_mobile,
          "fallback": check_fallback, "gallery": check_gallery}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("msedge", "chromium"),
                        default="msedge" if platform.system() == "Windows" else "chromium")
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "browser")
    parser.add_argument("--only", nargs="+", choices=tuple(CHECKS), help="Run selected check groups")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.exit(2, "Optional browser checks need: python -m pip install -r requirements-browser.txt\n")

    args.output.mkdir(parents=True, exist_ok=True)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "browser": args.browser,
              "mobile_scope": "Chromium device emulation; no physical-device claim", "checks": []}
    with local_site() as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, **({"channel": "msedge"} if args.browser == "msedge" else {}))
        report["browser_version"] = browser.version
        try:
            for name in args.only or CHECKS:
                started = time.monotonic()
                result = {"name": name}
                try:
                    CHECKS[name](browser, base_url, args.output)
                    result["status"] = "passed"
                    print(f"PASS {name}")
                except Exception as error:
                    result.update(status="failed", error=str(error))
                    print(f"FAIL {name}: {error}")
                result["seconds"] = round(time.monotonic() - started, 2)
                report["checks"].append(result)
        finally:
            browser.close()
    (args.output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = sum(item["status"] != "passed" for item in report["checks"])
    print(f"{len(report['checks']) - failures}/{len(report['checks'])} groups passed; artifacts: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
