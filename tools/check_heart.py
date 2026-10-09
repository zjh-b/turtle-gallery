#!/usr/bin/env python3
"""Optional real-browser checks for the interactive particle-heart page.

Install ``requirements-browser.txt`` first. Windows uses installed Edge; use
``--browser chromium`` after installing Playwright Chromium elsewhere. Output
goes to .work/heart. Mobile tests use Chromium emulation, not a physical phone.
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
                           require, set_visibility, touch_points, wait_for_gallery)


CANVAS = "#heart-canvas"


def ready(page, base_url):
    response = page.goto(base_url + "/play/heart.html", wait_until="networkidle")
    require(response is not None and response.ok, "Heart page must return HTTP 200")
    page.wait_for_function("""() => {
      const canvas = document.querySelector('#heart-canvas');
      const controls = document.querySelector('#play-controls');
      return canvas && !canvas.hidden && controls && !controls.disabled;
    }""", timeout=5000, polling=25)
    require(page.locator("#heart-fallback").is_hidden(), "Ready page must replace fallback with Canvas")
    require(page.locator("#play-status").inner_text().strip(), "Ready page must expose a readable status")


def canvas_hash(page):
    # Reading the main context with getImageData may change Chromium's raster
    # backend. Hash a PNG snapshot so equality tests do not alter rendering.
    return page.locator(CANVAS).evaluate("""async canvas => {
      const bytes = new TextEncoder().encode(canvas.toDataURL('image/png'));
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
    page.wait_for_function("frames => window.__browserCheck.frames > frames + 2", arg=frames, polling=25)
    require(page.locator("#pause").get_attribute("aria-pressed") == "false", "Playing state must be announced")


def assert_dpi_cap(page):
    size = page.locator(CANVAS).evaluate("""canvas => {
      const rect = canvas.getBoundingClientRect();
      return {width: canvas.width, height: canvas.height, cssWidth: rect.width, cssHeight: rect.height};
    }""")
    require(size["width"] > 0 and size["height"] > 0, "Canvas needs a drawable backing store")
    require(size["width"] <= size["cssWidth"] * 2 + 2, "Canvas width exceeds DPR cap of 2")
    require(size["height"] <= size["cssHeight"] * 2 + 2, "Canvas height exceeds DPR cap of 2")
    require(abs(size["cssWidth"] - size["cssHeight"]) < 2, "Heart canvas must remain square")


def coordinates(page, x=0.5, y=0.5):
    canvas = page.locator(CANVAS)
    canvas.scroll_into_view_if_needed()
    box = canvas.bounding_box()
    require(box is not None, "Canvas needs a visible input target")
    return box["x"] + box["width"] * x, box["y"] + box["height"] * y


def count_label(page):
    match = re.search(r"\d+", page.locator("#particle-count").inner_text())
    require(match is not None, "Visible particle count must contain a number")
    return int(match.group())


def set_rate(page, value):
    page.locator("#rate").evaluate("""(input, value) => {
      input.value = String(value);
      input.dispatchEvent(new Event('input', {bubbles: true}));
      input.dispatchEvent(new Event('change', {bubbles: true}));
    }""", value)


def resume_without_catchup(page, action):
    frozen = page.locator(CANVAS).evaluate("canvas => canvas.toDataURL('image/png')")
    # Observe only the first application callback after resuming. Its rendered
    # frame must match the frozen scene, independent of subsequent frame speed.
    page.evaluate("""() => {
      const request = window.requestAnimationFrame;
      window.__resumedFrame = null;
      window.requestAnimationFrame = callback => request(time => {
        window.requestAnimationFrame = request;
        callback(time);
        window.__resumedFrame = document.querySelector('#heart-canvas').toDataURL('image/png');
      });
    }""")
    action()
    page.wait_for_function("window.__resumedFrame !== null", polling=25)
    require(page.evaluate("window.__resumedFrame") == frozen, "First resumed frame must not catch up hidden elapsed time")


def check_desktop(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(page.locator("#pause").get_attribute("aria-pressed") == "true", "Initial scene must be paused")
        require(page.locator(CANVAS).get_attribute("tabindex") == "0", "Canvas must be keyboard focusable")
        require(page.locator("#theme option").count() == 3, "Three themes must be available")
        require(page.locator("#density option").evaluate_all("nodes => nodes.map(node => Number(node.value))") == [420, 680, 1000], "Density choices must match shared configuration")
        require(float(page.locator("#rate").get_attribute("min")) == 0.45 and float(page.locator("#rate").get_attribute("max")) == 1.8, "Rate control must expose the configured limits")
        require(count_label(page) == 680, "Default scene must contain 680 particles")
        require(page.locator("#theme").input_value() == "0" and float(page.locator("#rate").input_value()) == 1, "Default scene must use rose and normal heartbeat speed")
        assert_static(page, "Initial scene")
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.screenshot(path=str(output / "desktop.png"), full_page=True)

        hashes = set()
        for theme in ("0", "1", "2"):
            page.locator("#theme").select_option(theme)
            hashes.add(canvas_hash(page))
            assert_static(page, "Theme change while paused")
        require(len(hashes) == 3, "All three themes must produce distinct artwork")
        for density in ("420", "1000", "680"):
            page.locator("#density").select_option(density)
            require(count_label(page) == int(density), "Particle count must follow density selection")
            assert_static(page, "Density change while paused")
        for rate in (0.45, 1.8, 1.25):
            set_rate(page, rate)
            require(str(rate) in page.locator("#rate-value").inner_text(), "Rate value must be visible")
        page.locator("#theme").select_option("1")
        page.locator("#density").select_option("1000")
        baseline = canvas_hash(page)
        page.locator("#burst").click()
        assert_playing(page)
        page.wait_for_timeout(200)
        require(canvas_hash(page) != baseline, "Burst must visibly animate the heart")
        page.locator("#pause").click()
        assert_static(page, "Paused burst")
        page.screenshot(path=str(output / "desktop-scattered.png"), full_page=True)
        page.locator("#reset").click()
        require(page.locator("#theme").input_value() == "1" and page.locator("#density").input_value() == "1000" and float(page.locator("#rate").input_value()) == 1.25, "Reset must preserve all chosen parameters")
        require(canvas_hash(page) == baseline, "Reset must restore the selected scene at time zero")
        assert_static(page, "Reset scene")

        page.locator("#rate").focus()
        page.keyboard.press("c")
        page.keyboard.press("r")
        require(page.locator("#theme").input_value() == "1", "Canvas shortcuts must ignore focused form controls")
        page.locator(CANVAS).focus()
        page.keyboard.press("Space")
        assert_playing(page)
        page.keyboard.press("Space")
        assert_static(page, "Keyboard pause")
        page.keyboard.press("Enter")
        assert_playing(page)
        page.keyboard.press("c")
        require(page.locator("#theme").input_value() == "2", "C must cycle theme")
        page.keyboard.press("r")
        assert_static(page, "Keyboard reset")
        before = canvas_hash(page)
        for key in ("Enter", " ", "c", "r"):
            page.locator(CANVAS).dispatch_event("keydown", {"key": key, "ctrlKey": True})
            page.locator(CANVAS).dispatch_event("keydown", {"key": key, "shiftKey": True})
        require(canvas_hash(page) == before and page.locator("#theme").input_value() == "2", "Modified keys must not trigger canvas shortcuts")
        assert_static(page, "Modified keyboard guards")
        page.set_viewport_size({"width": 800, "height": 900})
        assert_no_overflow(page)
        assert_dpi_cap(page)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_reduced_motion(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(page.locator("#reduced-motion").is_checked(), "System reduced-motion preference must initialize the checkbox")
        require(page.locator("#pause").is_disabled(), "Reduced motion must disable playback")
        before = canvas_hash(page)
        page.locator("#burst").click()
        require(canvas_hash(page) != before, "Reduced-motion burst must visibly scatter particles")
        assert_static(page, "Static scatter")
        page.screenshot(path=str(output / "reduced-motion.png"), full_page=True)
        page.locator(CANVAS).click()
        require(canvas_hash(page) == before, "Second reduced-motion tap must regroup the original heart")
        page.locator(CANVAS).focus()
        page.keyboard.press("Space")
        assert_static(page, "Reduced-motion playback shortcut")
        page.keyboard.press("Enter")
        require(canvas_hash(page) != before, "Enter must support a static scatter")
        assert_static(page, "Reduced-motion keyboard scatter")
        page.locator("#reduced-motion").uncheck()
        require(page.locator("#pause").is_enabled(), "Leaving reduced motion must restore playback control")
        assert_static(page, "Leaving reduced motion must remain paused")
        page.locator("#pause").click()
        assert_playing(page)
        page.locator("#reduced-motion").check()
        assert_static(page, "Enabling reduced motion while playing")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))

    with browser.new_context(reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        page.locator("#pause").click()
        assert_playing(page)
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_function("document.querySelector('#reduced-motion').checked", polling=25)
        assert_static(page, "New system reduced-motion preference must stop animation")
        page.emulate_media(reduced_motion="no-preference")
        page.wait_for_function("!document.querySelector('#reduced-motion').checked", polling=25)
        assert_static(page, "System preference returning to normal must remain paused")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_lifecycle(browser, base_url, output):
    with browser.new_context(reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        page.locator("#pause").click()
        assert_playing(page)
        set_visibility(page, "hidden")
        assert_static(page, "Hidden document")
        resume_without_catchup(page, lambda: set_visibility(page, "visible"))
        assert_playing(page)
        page.locator("#pause").click()
        set_visibility(page, "hidden")
        set_visibility(page, "visible")
        assert_static(page, "Visibility must preserve manual pause")
        page.locator("#pause").click()
        assert_playing(page)
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true}))")
        assert_static(page, "Pagehide")
        resume_without_catchup(page, lambda: page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))"))
        assert_playing(page)
        page.locator("#pause").click()
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true})); window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}));")
        assert_static(page, "Page restore must preserve manual pause")
        page.evaluate("for (let i = 0; i < 24; i++) document.querySelector('#pause').click()")
        assert_static(page, "Rapid playback toggles")
        require(page.evaluate("window.__browserCheck.peak") <= 1, "Lifecycle changes must not duplicate animation loops")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_inputs(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 1000}, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        before = canvas_hash(page)
        x, y = coordinates(page)
        page.mouse.move(x, y)
        page.mouse.down()
        require(canvas_hash(page) == before, "Scatter must wait for release")
        page.mouse.up()
        require(canvas_hash(page) != before, "A complete mouse click must scatter")
        page.locator("#reset").click()
        require(canvas_hash(page) == before, "Reset must restore static initial artwork")
        cancellations = {
            "pointercancel": lambda: page.locator(CANVAS).dispatch_event("pointercancel", {"pointerId": 1, "pointerType": "mouse"}),
            "blur": lambda: page.evaluate("window.dispatchEvent(new Event('blur'))"),
            "hidden": lambda: set_visibility(page, "hidden"),
            "pagehide": lambda: page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted: true}))"),
        }
        for name, cancel in cancellations.items():
            page.mouse.move(*coordinates(page))
            page.mouse.down()
            cancel()
            if name == "hidden":
                set_visibility(page, "visible")
            elif name == "pagehide":
                page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
            page.mouse.up()
            require(canvas_hash(page) == before, name + ": pending click must be cancelled")
        x, y = coordinates(page)
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 20, y)
        page.mouse.move(x, y)
        page.mouse.up()
        require(canvas_hash(page) == before, "Moving more than 12 px and returning must cancel the tap")
        page.mouse.down()
        page.wait_for_timeout(760)
        page.mouse.up()
        require(canvas_hash(page) == before, "Long press must not scatter")
        page.mouse.down()
        page.mouse.move(0, 0)
        page.mouse.move(x, y)
        page.mouse.up()
        require(canvas_hash(page) == before, "Leaving the canvas must cancel the tap even after returning")
        page.mouse.down()
        page.set_viewport_size({"width": 1000, "height": 950})
        page.wait_for_timeout(100)
        page.mouse.up()
        page.set_viewport_size({"width": 1200, "height": 1000})
        page.wait_for_timeout(100)
        require(canvas_hash(page) == before, "Resize must cancel pending input and preserve artwork")
        page.locator(CANVAS).click()
        require(canvas_hash(page) != before, "A fresh click must work after cancellation")
        assert_static(page, "Cancelled inputs must not schedule animation")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_mobile(browser, base_url, output):
    with browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                             is_mobile=True, has_touch=True, reduced_motion="reduce") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        action = page.locator(CANVAS).evaluate("el => getComputedStyle(el).touchAction")
        require("pan-y" in action and "pinch-zoom" in action, "Canvas must permit vertical scrolling and pinch zoom")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        x, y = coordinates(page)
        initial = canvas_hash(page)
        page.touchscreen.tap(x, y)
        require(canvas_hash(page) != initial, "Native emulated touch tap must scatter")
        page.touchscreen.tap(x, y)
        require(canvas_hash(page) == initial, "Second touch tap must regroup")
        client = context.new_cdp_session(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
        require(canvas_hash(page) == initial, "Cancelled touch must not scatter")
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x - 30, y), (x + 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": touch_points([(x - 30, y)])})
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(canvas_hash(page) == initial, "Second finger must cancel the tap for the whole gesture")
        scroll_before = page.evaluate("window.scrollY")
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        for distance in (20, 40, 65, 90):
            client.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": touch_points([(x, y - distance)])})
            page.wait_for_timeout(30)
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(200)
        require(page.evaluate("window.scrollY") > scroll_before, "Vertical touch drag must scroll the page")
        require(canvas_hash(page) == initial, "Touch scrolling must not scatter")
        x, y = coordinates(page)
        client.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": touch_points([(x, y)])})
        page.wait_for_timeout(760)
        client.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        require(canvas_hash(page) == initial, "Long touch must not scatter")
        page.touchscreen.tap(x, y)
        require(canvas_hash(page) != initial, "A fresh touch tap must work after cancelled gestures")
        page.screenshot(path=str(output / "mobile-scattered.png"), full_page=True)
        page.set_viewport_size({"width": 844, "height": 390})
        page.wait_for_timeout(100)
        assert_no_overflow(page)
        assert_dpi_cap(page)
        page.screenshot(path=str(output / "mobile-landscape.png"), full_page=True)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def save_png(page, output, name):
    with page.expect_download() as download_info:
        page.locator("#save-png").click()
    download = download_info.value
    require(download.suggested_filename.lower().endswith(".png"), "Export must suggest a PNG filename")
    target = output / name
    download.save_as(target)
    data = target.read_bytes()
    require(data[:8] == b"\x89PNG\r\n\x1a\n", "Downloaded image must be a real PNG")
    require(len(data) > 1000, "Downloaded PNG must contain image data")
    require(struct.unpack(">II", data[16:24]) == (1080, 1080), "Export dimensions must be exactly 1080 x 1080")
    encoded = base64.b64encode(data).decode("ascii")
    stats = page.evaluate("""async encoded => {
      const image = new Image();
      image.src = 'data:image/png;base64,' + encoded;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width; canvas.height = image.height;
      const context = canvas.getContext('2d'); context.drawImage(image, 0, 0);
      const bytes = context.getImageData(0, 0, canvas.width, canvas.height).data;
      const colors = new Set(); let opaque = 0;
      for (let i = 0; i < bytes.length; i += 4) {
        if (bytes[i + 3] === 255) opaque++;
        if (i % 64 === 0) colors.add((bytes[i] << 16) | (bytes[i + 1] << 8) | bytes[i + 2]);
      }
      return {opaque, colors: colors.size, pixels: canvas.width * canvas.height};
    }""", encoded)
    require(stats["opaque"] > stats["pixels"] * 0.9, "PNG must preserve the artwork background")
    require(stats["colors"] > 32, "PNG must contain varied visible artwork")
    return encoded


def check_export(browser, base_url, output):
    with browser.new_context(viewport={"width": 1200, "height": 950}, accept_downloads=True,
                             reduced_motion="no-preference") as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        before = canvas_hash(page)
        save_png(page, output, "heart.png")
        require(canvas_hash(page) == before, "Saving a paused scene must preserve it exactly")
        assert_static(page, "Saving must preserve pause")
        page.locator("#theme").select_option("2")
        page.locator("#density").select_option("1000")
        page.locator("#reduced-motion").check()
        page.locator("#burst").click()
        scattered = save_png(page, output, "heart-scattered.png")
        require(scattered != base64.b64encode((output / "heart.png").read_bytes()).decode("ascii"), "Different theme and spread must affect exported artwork")
        page.locator("#reduced-motion").uncheck()
        page.locator("#pause").click()
        assert_playing(page)
        page.evaluate("""() => {
          const original = HTMLCanvasElement.prototype.toBlob;
          window.__originalToBlob = original;
          HTMLCanvasElement.prototype.toBlob = function (callback, ...args) {
            window.__capturedExport = {width: this.width, height: this.height,
              sourceIsMain: this.id === 'heart-canvas', data: this.toDataURL('image/png').split(',')[1]};
            return original.call(this, blob => setTimeout(() => callback(blob), 120), ...args);
          };
        }""")
        encoded = save_png(page, output, "heart-playing.png")
        captured = page.evaluate("window.__capturedExport")
        (output / "heart-captured.png").write_bytes(base64.b64decode(captured["data"]))
        page.evaluate("() => { HTMLCanvasElement.prototype.toBlob = window.__originalToBlob; }")
        require(captured["width"] == 1080 and captured["height"] == 1080 and not captured["sourceIsMain"], "Export must use an independent high-resolution canvas")
        # toBlob and toDataURL may use different PNG compression. Compare the
        # decoded pixels, not encoder bytes, to detect an incorrectly late frame.
        matching = page.evaluate("""async pair => {
          const pixels = async encoded => {
            const image = new Image(); image.src = 'data:image/png;base64,' + encoded;
            await image.decode();
            const canvas = document.createElement('canvas');
            canvas.width = image.width; canvas.height = image.height;
            const context = canvas.getContext('2d'); context.drawImage(image,0,0);
            return context.getImageData(0,0,canvas.width,canvas.height).data;
          };
          const [saved, captured] = await Promise.all(pair.map(pixels));
          return saved.length === captured.length && saved.every((value,index) => value === captured[index]);
        }""", [encoded, captured["data"]])
        require(matching, "Async export must retain the exact captured pixels while playback continues")
        assert_playing(page)
        page.locator("#pause").click()
        page.evaluate("() => { HTMLCanvasElement.prototype.toBlob = function (callback) { setTimeout(() => callback(null), 0); }; }")
        page.locator("#save-png").click()
        page.wait_for_function("!document.querySelector('#save-png').disabled", polling=25)
        require(any(word in page.locator("#play-status").inner_text() for word in ("失败", "重试", "未成功")), "Failed export must explain the failure or offer a retry")
        page.evaluate("() => { HTMLCanvasElement.prototype.toBlob = window.__originalToBlob; }")
        save_png(page, output, "heart-retry.png")
        assert_static(page, "Export retry must preserve pause")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def assert_fallback(page):
    image = page.locator("#heart-fallback")
    require(image.is_visible(), "Fallback preview must remain visible")
    require(image.evaluate("img => img.complete && img.naturalWidth > 0"), "Fallback preview must load")
    require(page.locator(CANVAS).is_hidden(), "Unavailable Canvas must stay hidden")
    require(page.locator("#play-controls").evaluate("el => el.disabled && [...el.querySelectorAll('button, input, select')].every(control => control.matches(':disabled'))"), "Unavailable controls must remain disabled")
    require(page.locator("a[href*='github.com'][href*='blob/main']").count() > 0, "Fallback must retain the desktop source link")


def check_fallback(browser, base_url, output):
    with browser.new_context(java_script_enabled=False, viewport={"width": 1100, "height": 900}) as context:
        page = context.new_page()
        page.goto(base_url + "/play/heart.html", wait_until="networkidle")
        assert_fallback(page)
        require(page.locator("noscript").inner_text().strip(), "No-JavaScript visitors need an explanation")
        page.screenshot(path=str(output / "fallback-no-js.png"), full_page=True)
    for failure in ("config", "canvas"):
        with browser.new_context() as context:
            if failure == "canvas":
                context.add_init_script("HTMLCanvasElement.prototype.getContext = function () { return null; };")
            page = context.new_page()
            if failure == "config":
                page.route("**/heart-config.json", lambda route: route.abort())
            page.goto(base_url + "/play/heart.html", wait_until="networkidle")
            page.wait_for_function("document.querySelector('#play-status').textContent.includes('暂不可用')", polling=25)
            assert_fallback(page)
            page.screenshot(path=str(output / ("fallback-" + failure + ".png")), full_page=True)


def check_gallery(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1000}) as context:
        page = context.new_page()
        page.goto(base_url + "/index.html", wait_until="networkidle")
        wait_for_gallery(page)
        links = page.locator("a[href='play/heart.html']")
        require(links.count() >= 2, "Home and generated artwork card must both link to the heart")
        card = page.locator(".art-card").filter(has=page.locator("#art-title-26"))
        require(card.locator("a[href='play/heart.html']").count() == 1, "Artwork 26 needs exactly one playable entry")
        links.first.click()
        page.wait_for_url("**/play/heart.html")
        page.wait_for_function("!document.querySelector('#play-controls').disabled", polling=25)
        require(page.locator(CANVAS).is_visible(), "Gallery link must open a working heart page")
        for destination in ("fireworks", "kaleidoscope"):
            outgoing = page.locator(f"a[href='{destination}.html']")
            require(outgoing.count() > 0, "Heart page must link to " + destination)
            outgoing.first.click()
            page.wait_for_url(f"**/play/{destination}.html")
            returning = page.locator("a[href='heart.html']")
            require(returning.count() > 0, destination + " must link back to the heart")
            returning.first.click()
            page.wait_for_url("**/play/heart.html")
        page.goto(base_url + "/index.html", wait_until="networkidle")
        page.set_viewport_size({"width": 390, "height": 844})
        assert_no_overflow(page)


CHECKS = {"desktop": check_desktop, "reduced-motion": check_reduced_motion,
          "lifecycle": check_lifecycle, "inputs": check_inputs, "mobile": check_mobile,
          "export": check_export, "fallback": check_fallback, "gallery": check_gallery}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("msedge", "chromium"),
                        default="msedge" if platform.system() == "Windows" else "chromium")
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "heart")
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
