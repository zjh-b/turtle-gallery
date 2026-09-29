#!/usr/bin/env python3
"""Optional real-browser regression checks for the static kaleidoscope page.

Install with ``python -m pip install -r requirements-browser.txt``. Windows
uses installed Edge by default; use ``--browser chromium`` after installing
Playwright Chromium elsewhere. Artifacts go to .work/kaleidoscope. Mobile
checks emulate Chromium touch and do not establish physical-device support.
"""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import struct
import sys
import time

from check_browser import (ROOT, assert_no_overflow, local_site, observed_page,
                           require, set_visibility, touch_points)


CANVAS = "#kaleidoscope-canvas"


def ready(page, base_url):
    response = page.goto(base_url + "/play/kaleidoscope.html", wait_until="networkidle")
    require(response is not None and response.ok, "Kaleidoscope page must return HTTP 200")
    page.wait_for_function("""() => {
      const canvas = document.querySelector('#kaleidoscope-canvas');
      const controls = document.querySelector('#play-controls');
      return canvas && !canvas.hidden && controls && !controls.disabled;
    }""", timeout=5000, polling=25)
    require(page.locator("#kaleidoscope-fallback").is_hidden(), "Ready page must replace the fallback with Canvas")
    require(page.locator("#play-status").inner_text().strip(), "Ready page must expose a readable status")


def canvas_hash(page):
    # Repeated getImageData calls can switch Chromium's raster backend and
    # change antialiasing during a pixel-equality check. Snapshot the PNG.
    return page.locator(CANVAS).evaluate("""async canvas => {
      const bytes = new TextEncoder().encode(canvas.toDataURL('image/png'));
      const hash = await crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
    }""")


def stroke_count(page):
    label = page.locator("#stroke-count").inner_text()
    match = re.search(r"\d+", label)
    require(match is not None, "Visible stroke count must contain a number")
    return int(match.group())


def assert_static(page, message):
    before = canvas_hash(page)
    frames = page.evaluate("window.__browserCheck.frames")
    page.wait_for_timeout(180)
    require(canvas_hash(page) == before, message + ": rendered pixels changed")
    require(page.evaluate("window.__browserCheck.frames") == frames, message + ": animation frames kept running")
    require(page.evaluate("window.__browserCheck.pending") == 0, message + ": a frame is still scheduled")


def assert_dpi_cap(page):
    dimensions = page.locator(CANVAS).evaluate("""canvas => {
      const rect = canvas.getBoundingClientRect();
      return {width: canvas.width, height: canvas.height, cssWidth: rect.width, cssHeight: rect.height};
    }""")
    require(dimensions["width"] > 0 and dimensions["height"] > 0, "Canvas needs a drawable backing store")
    require(dimensions["width"] <= dimensions["cssWidth"] * 2 + 2, "Canvas width exceeds DPR cap of 2")
    require(dimensions["height"] <= dimensions["cssHeight"] * 2 + 2, "Canvas height exceeds DPR cap of 2")
    require(abs(dimensions["cssWidth"] - dimensions["cssHeight"]) < 2, "Kaleidoscope canvas must remain square")


def coordinates(page, points):
    canvas = page.locator(CANVAS)
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    require(box is not None, "Canvas needs a visible input target")
    return [(box["x"] + x * box["width"], box["y"] + y * box["height"]) for x, y in points]


def start_stroke(page, points=((0.54, 0.47), (0.61, 0.40))):
    positions = coordinates(page, points)
    page.mouse.move(*positions[0])
    page.mouse.down()
    for point in positions[1:]:
        page.mouse.move(*point, steps=4)


def draw_stroke(page, points=((0.54, 0.47), (0.61, 0.40), (0.70, 0.36))):
    start_stroke(page, points)
    page.mouse.up()


def begin_drawing(page):
    page.locator("#draw-mode").click()
    require(page.locator("#draw-mode").get_attribute("aria-pressed") == "true", "Drawing mode must expose its pressed state")
    require(page.locator(CANVAS).evaluate("el => getComputedStyle(el).touchAction") == "none", "Drawing mode must reserve touch gestures for drawing")


def save_png(page, output, name):
    with page.expect_download() as download_info:
        page.locator("#save-png").click()
    download = download_info.value
    require(download.suggested_filename.lower().endswith(".png"), "Export must suggest a PNG filename")
    target = output / name
    download.save_as(target)
    data = target.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "Downloaded file must be a real PNG")
    require(len(data) > 1000, "PNG must contain image data")
    require(struct.unpack(">II", data[16:24]) == (1080, 1080), "PNG dimensions must be exactly 1080 x 1080")
    stats = page.evaluate("""async encoded => {
      const image = new Image();
      image.src = 'data:image/png;base64,' + encoded;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width; canvas.height = image.height;
      const context = canvas.getContext('2d');
      context.drawImage(image, 0, 0);
      const bytes = context.getImageData(0, 0, canvas.width, canvas.height).data;
      const colors = new Set();
      let opaque = 0;
      for (let i = 0; i < bytes.length; i += 4) {
        if (bytes[i + 3] === 255) opaque++;
        if (i % 64 === 0) colors.add((bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2]);
      }
      return {opaque, colors: colors.size, pixels: canvas.width * canvas.height};
    }""", base64.b64encode(data).decode("ascii"))
    require(stats["opaque"] > stats["pixels"] * 0.9, "PNG must retain the artwork background")
    require(stats["colors"] > 32, "PNG must contain visible artwork rather than a solid blank image")


def check_desktop(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1050}, accept_downloads=True) as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(page.locator("#draw-mode").get_attribute("aria-pressed") == "false", "Drawing must be an explicit opt-in")
        require(page.locator("#symmetry option").evaluate_all("nodes => nodes.map(node => Number(node.value))") == list(range(3, 17)), "Symmetry choices must cover 3 through 16")
        require(page.locator("#palette option").count() == 3, "Three palettes must be available")
        assert_static(page, "Initial example must stay static")
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.screenshot(path=str(output / "desktop.png"), full_page=True)

        initial = canvas_hash(page)
        page.locator("#symmetry").select_option("3")
        three = canvas_hash(page)
        page.locator("#symmetry").select_option("16")
        sixteen = canvas_hash(page)
        require(len({initial, three, sixteen}) == 3, "Symmetry choices must visibly redraw the example")
        page.locator("#palette").select_option("1")
        palette_one = canvas_hash(page)
        page.locator("#palette").select_option("2")
        require(len({sixteen, palette_one, canvas_hash(page)}) == 3, "Every palette must visibly redraw the example")

        page.locator("#draw-mode").focus()
        page.keyboard.press("Enter")
        require(page.locator("#draw-mode").get_attribute("aria-pressed") == "true", "Keyboard must activate drawing mode")
        require(stroke_count(page) == 0 and page.locator("#undo").is_disabled(), "Starting hand drawing must clear the example")
        blank = canvas_hash(page)
        draw_stroke(page)
        first = canvas_hash(page)
        require(first != blank and stroke_count(page) == 1, "Dragging must commit a visible stroke")
        draw_stroke(page, ((0.49, 0.46), (0.40, 0.34), (0.33, 0.27)))
        require(stroke_count(page) == 2 and canvas_hash(page) != first, "Each drag must add one whole stroke")
        page.locator("#undo").focus()
        page.keyboard.press("Enter")
        require(stroke_count(page) == 1 and canvas_hash(page) == first, "Undo must remove exactly the most recent whole stroke")
        page.locator("#draw-mode").click()
        page.locator("#draw-mode").click()
        require(stroke_count(page) == 1 and canvas_hash(page) == first, "Reentering drawing mode must keep existing hand drawing")
        save_png(page, output, "drawing.png")
        page.screenshot(path=str(output / "desktop-drawing.png"), full_page=True)

        page.locator("#symmetry").select_option("7")
        require(stroke_count(page) == 1 and canvas_hash(page) != first, "Changing symmetry must redraw and preserve committed strokes")
        changed = canvas_hash(page)
        page.locator("#palette").select_option("0")
        require(stroke_count(page) == 1 and canvas_hash(page) != changed, "Changing palette must redraw and preserve committed strokes")
        page.locator("#clear").click()
        require(stroke_count(page) == 0 and page.locator("#undo").is_disabled(), "Clear must remove all strokes and disable Undo")
        require(page.locator("#draw-mode").get_attribute("aria-pressed") == "true", "Clear must preserve drawing mode")
        page.locator("#example").focus()
        page.keyboard.press("Enter")
        require(page.locator("#draw-mode").get_attribute("aria-pressed") == "false", "Example must exit drawing mode")
        require(canvas_hash(page) != blank and page.locator("#undo").is_disabled(),
                "Keyboard-accessible example must restore a visible template")
        assert_static(page, "Selected example must stay static")
        save_png(page, output, "example.png")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_lifecycle(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}) as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        begin_drawing(page)
        draw_stroke(page)
        baseline = canvas_hash(page)
        cancellations = {
            "pointercancel": lambda: page.locator(CANVAS).dispatch_event("pointercancel", {"pointerId": 1, "pointerType": "mouse"}),
            "blur": lambda: page.evaluate("window.dispatchEvent(new Event('blur'))"),
            "hidden": lambda: set_visibility(page, "hidden"),
            "pagehide": lambda: page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true}))"),
        }
        for name, cancel in cancellations.items():
            start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
            require(canvas_hash(page) != baseline, name + ": unfinished stroke must be visible before cancellation")
            cancel()
            if name == "hidden":
                set_visibility(page, "visible")
            elif name == "pagehide":
                page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
            page.mouse.move(*coordinates(page, [(0.34, 0.68)])[0])
            page.mouse.up()
            require(stroke_count(page) == 1 and canvas_hash(page) == baseline, name + ": cancellation must preserve committed strokes without reconnecting")

        start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
        page.mouse.move(*coordinates(page, [(0.99, 0.5)])[0])
        page.mouse.move(*coordinates(page, [(0.40, 0.66)])[0])
        page.mouse.up()
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "Leaving the circle must cancel the whole unfinished stroke")

        start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
        page.set_viewport_size({"width": 800, "height": 900})
        page.wait_for_timeout(100)
        page.mouse.up()
        require(stroke_count(page) == 1, "Resize must cancel unfinished drawing")
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.set_viewport_size({"width": 1200, "height": 950})
        page.wait_for_timeout(100)
        require(canvas_hash(page) == baseline, "Resize must keep completed drawing intact")

        start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
        page.locator("#draw-mode").evaluate("button => button.click()")
        page.mouse.up()
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "Ending drawing mode must cancel the unfinished stroke")
        page.locator("#draw-mode").click()
        start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
        page.locator("#symmetry").select_option("8")
        page.mouse.up()
        require(stroke_count(page) == 1, "Changing symmetry must cancel the unfinished stroke")
        page.locator("#symmetry").select_option("10")
        require(canvas_hash(page) == baseline, "Changing symmetry must not commit a partial stroke")
        start_stroke(page, ((0.47, 0.52), (0.39, 0.64)))
        page.locator("#palette").select_option("1")
        page.mouse.up()
        page.locator("#palette").select_option("0")
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "Changing palette must cancel the unfinished stroke")
        assert_static(page, "Idle hand drawing must have no animation loop")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_render_cache(browser, base_url, output):
    with browser.new_context() as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        result = page.evaluate("""async () => {
          const {KaleidoscopeModel} = await import('./kaleidoscope-model.js');
          const {drawKaleidoscope} = await import('./kaleidoscope-view.js');
          const config = await fetch('kaleidoscope-config.json').then(r => r.json());
          const model = new KaleidoscopeModel(config);
          const canvas = document.createElement('canvas');
          canvas.width = canvas.height = 352;
          const failures = [];
          function compare(name) {
            drawKaleidoscope(canvas, model, config);
            const fresh = document.createElement('canvas');
            fresh.width = canvas.width; fresh.height = canvas.height;
            drawKaleidoscope(fresh, model, config);
            if (canvas.toDataURL() !== fresh.toDataURL()) failures.push(name);
          }
          function stroke(offset) {
            model.begin(20, offset);
            for (let i = 1; i < 100; i++) model.move(20+i, offset+Math.sin(i/8)*15);
            model.end();
          }
          compare('example');
          model.setCount(16); compare('count');
          model.setPalette(2); compare('palette');
          model.clear(); compare('clear');
          stroke(30); compare('first stroke');
          stroke(60); compare('second stroke');
          model.undo(); stroke(-30); compare('replacement with same stroke count');
          model.begin(-30,-20); model.move(0,0); model.move(30,20);
          compare('current stroke');
          const original = CanvasRenderingContext2D.prototype.lineTo;
          let lines = 0, warmLines = 0, freshLines = 0;
          CanvasRenderingContext2D.prototype.lineTo = function (...args) {
            lines++; return original.apply(this, args);
          };
          try {
            drawKaleidoscope(canvas, model, config); warmLines = lines;
            const fresh = document.createElement('canvas');
            fresh.width = fresh.height = 352;
            lines = 0; drawKaleidoscope(fresh, model, config); freshLines = lines;
          } finally { CanvasRenderingContext2D.prototype.lineTo = original; }
          model.cancel(); compare('cancel');
          model.undo(); compare('undo');
          canvas.width = canvas.height = 704; compare('resize');
          model.example(); compare('restore example');
          return {failures, warmLines, freshLines};
        }""")
        require(not result["failures"], "Cached rendering differs from a fresh canvas: " + ", ".join(result["failures"]))
        require(result["warmLines"] < result["freshLines"] / 2,
                "Drawing a new segment must reuse completed strokes instead of tracing all history")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_mobile(browser, base_url, output):
    with browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                             is_mobile=True, has_touch=True, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        action = page.locator(CANVAS).evaluate("el => getComputedStyle(el).touchAction")
        require("pan-y" in action and "pinch-zoom" in action, "Canvas must allow normal scrolling and zoom before drawing")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        client = context.new_cdp_session(page)
        x, y = coordinates(page, [(0.5, 0.5)])[0]
        before = canvas_hash(page)
        page.touchscreen.tap(x, y)
        require(canvas_hash(page) == before, "Touching the initial example must not start drawing")
        scroll_before = page.evaluate("window.scrollY")
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        for distance in (20, 40, 65, 90):
            client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x, y - distance)])})
            page.wait_for_timeout(30)
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(200)
        require(page.evaluate("window.scrollY") > scroll_before, "Vertical touch dragging must scroll before drawing is enabled")
        require(canvas_hash(page) == before, "Scrolling must preserve the example")

        begin_drawing(page)
        x, y = coordinates(page, [(0.55, 0.44)])[0]
        empty = canvas_hash(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x + 30, y - 30)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(stroke_count(page) == 1 and canvas_hash(page) != empty, "A touch drag must commit a visible stroke")
        baseline = canvas_hash(page)

        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 20, y + 20)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x - 40, y + 45)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "Touch cancellation must discard only the unfinished stroke")

        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 20, y + 20)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x - 35, y + 35)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 35, y + 35), (x + 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": touch_points([(x - 35, y + 35)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x - 50, y + 45)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "A second finger must cancel the stroke and suppress the rest of that gesture")
        page.touchscreen.tap(x - 25, y + 20)
        require(stroke_count(page) == 1 and canvas_hash(page) == baseline, "A tap without movement must not create a stroke")
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 25, y + 20)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x - 55, y + 45)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(stroke_count(page) == 2 and canvas_hash(page) != baseline, "A fresh touch drag must draw again after cancellation")
        page.screenshot(path=str(output / "mobile-drawing.png"), full_page=True)

        page.locator("#draw-mode").click()
        action = page.locator(CANVAS).evaluate("el => getComputedStyle(el).touchAction")
        require("pan-y" in action and "pinch-zoom" in action, "Ending drawing must restore scrolling and zoom")
        page.set_viewport_size({"width": 844, "height": 390})
        page.wait_for_timeout(100)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.screenshot(path=str(output / "mobile-landscape.png"), full_page=True)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_limits(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}) as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        begin_drawing(page)
        points = coordinates(page, [(0.53, 0.45), (0.57, 0.41)])
        for _ in range(60):
            page.mouse.move(*points[0])
            page.mouse.down()
            page.mouse.move(*points[1])
            page.mouse.up()
        require(stroke_count(page) == 60, "Sixty complete strokes must fit within the configured limit")
        before = canvas_hash(page)
        draw_stroke(page, ((0.42, 0.56), (0.36, 0.62)))
        require(stroke_count(page) == 60 and canvas_hash(page) == before, "Exceeding the stroke limit must not drop old drawing")
        status = page.locator("#play-status").inner_text()
        require("撤销" in status or "清空" in status, "Limit status must explain how to continue drawing")
        page.locator("#undo").click()
        require(stroke_count(page) == 59, "Undo must free a stroke at the limit")
        draw_stroke(page, ((0.42, 0.56), (0.36, 0.62)))
        require(stroke_count(page) == 60, "Drawing must recover after Undo frees capacity")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def assert_fallback(page):
    image = page.locator("#kaleidoscope-fallback")
    require(image.is_visible(), "Fallback preview must remain visible")
    require(image.evaluate("img => img.complete && img.naturalWidth > 0"), "Fallback preview must load successfully")
    require(page.locator(CANVAS).is_hidden(), "Unusable Canvas must stay hidden")
    require(page.locator("#play-controls").evaluate("el => el.disabled && [...el.querySelectorAll('button, input, select')].every(control => control.matches(':disabled'))"), "Unavailable interactive controls must remain disabled")
    require(page.locator("a[href*='github.com'][href*='blob/main']").count() > 0, "Fallback must retain the desktop source link")


def check_fallback(browser, base_url, output):
    with browser.new_context(java_script_enabled=False, viewport={"width": 1100, "height": 900}) as context:
        page = context.new_page()
        page.goto(base_url + "/play/kaleidoscope.html", wait_until="networkidle")
        assert_fallback(page)
        require(page.locator("noscript").inner_text().strip(), "No-JavaScript visitors need a readable explanation")
        page.screenshot(path=str(output / "fallback-no-js.png"), full_page=True)

    with browser.new_context() as context:
        page = context.new_page()
        page.route("**/kaleidoscope-config.json", lambda route: route.abort())
        page.goto(base_url + "/play/kaleidoscope.html", wait_until="networkidle")
        page.wait_for_function("document.querySelector('#play-status').textContent.includes('暂不可用')", polling=25)
        assert_fallback(page)
        page.screenshot(path=str(output / "fallback-config.png"), full_page=True)

    with browser.new_context() as context:
        context.add_init_script("HTMLCanvasElement.prototype.getContext = function () { return null; };")
        page = context.new_page()
        page.goto(base_url + "/play/kaleidoscope.html", wait_until="networkidle")
        page.wait_for_function("document.querySelector('#play-status').textContent.includes('暂不可用')", polling=25)
        assert_fallback(page)


def check_gallery(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1000}) as context:
        page = context.new_page()
        page.goto(base_url + "/index.html", wait_until="networkidle")
        page.wait_for_function("document.querySelectorAll('#gallery-grid .art-card').length === 28", polling=25)
        links = page.locator("a[href='play/kaleidoscope.html']")
        require(links.count() >= 2, "Home and generated artwork card must both link to the kaleidoscope")
        card = page.locator(".art-card").filter(has=page.locator("#art-title-3"))
        require(card.locator("a[href='play/kaleidoscope.html']").count() == 1, "Artwork 03 must have one playable entry")
        links.first.click()
        page.wait_for_url("**/play/kaleidoscope.html")
        page.wait_for_function("!document.querySelector('#play-controls').disabled", polling=25)
        require(page.locator(CANVAS).is_visible(), "Gallery link must open a working kaleidoscope")
        fireworks = page.locator("a[href='fireworks.html']")
        require(fireworks.count() > 0, "Kaleidoscope page must link to fireworks")
        fireworks.first.click()
        page.wait_for_url("**/play/fireworks.html")
        kaleidoscope = page.locator("a[href='kaleidoscope.html']")
        require(kaleidoscope.count() > 0, "Fireworks page must link to kaleidoscope")
        kaleidoscope.first.click()
        page.wait_for_url("**/play/kaleidoscope.html")


CHECKS = {"desktop": check_desktop, "lifecycle": check_lifecycle, "render-cache": check_render_cache, "mobile": check_mobile,
          "limits": check_limits, "fallback": check_fallback, "gallery": check_gallery}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("msedge", "chromium"),
                        default="msedge" if platform.system() == "Windows" else "chromium")
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "kaleidoscope")
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
