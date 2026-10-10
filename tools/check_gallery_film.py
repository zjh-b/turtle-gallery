#!/usr/bin/env python3
"""Optional local browser checks for the gallery film (requirements-browser.txt).

Uses a fresh headless browser, never an account profile or remote website.
Mobile checks emulate touch in Chromium; they do not represent physical phones.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import re
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.check_browser import ROOT, local_site, require, assert_no_overflow

FILM = "assets/social-immersive/video.mp4"
CAPTIONS = "captions/immersive.zh.vtt"
LINKS = ("https://www.bilibili.com/video/BV1VhpY66EsQ/",
         "https://space.bilibili.com/3546966168438889", FILM)
CASES = (("desktop", 1440, 1000, {}),
         ("mobile", 390, 844, {"is_mobile": True, "has_touch": True}),
         ("narrow", 320, 844, {"is_mobile": True, "has_touch": True}),
         ("no-js", 390, 844, {"java_script_enabled": False}),
         ("reduced-motion", 1440, 1000, {"reduced_motion": "reduce"}),
         ("blocked-media", 390, 844, {}))


def cue_seconds(value):
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def expected_cues():
    source = (ROOT / "docs/assets/social-immersive/captions.zh.srt").read_text(encoding="utf-8-sig")
    return [[cue_seconds(start), cue_seconds(end), text.strip()]
            for start, end, text in re.findall(
                r"\d+\n([\d:,]+) --> ([\d:,]+)\n(.*?)(?=\n\n|\Z)", source, re.S)]


def wait_native(page, expression):
    # Browser media still works with page JavaScript disabled. Poll from the
    # host rather than relying on a setInterval in that disabled page.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if page.evaluate(expression):
            return
        time.sleep(.05)
    raise AssertionError("Native media condition timed out: " + expression)


def check_case(browser, base, output, case):
    name, width, height, options = case
    with browser.new_context(viewport={"width": width, "height": height}, **options) as context:
        page = context.new_page()
        page.set_default_timeout(10000)
        requests, errors = [], []
        page.on("request", lambda request: requests.append(request.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        if name == "blocked-media":
            page.route("**/" + FILM, lambda route: route.abort())
        response = page.goto(base + "/index.html", wait_until="networkidle")
        require(response is not None and response.status == 200, "Gallery must load")
        section, video = page.locator("#immersive"), page.locator("#gallery-film")
        section.scroll_into_view_if_needed()
        require(video.is_visible(), "Film must be visible")
        state = video.evaluate("v => [v.controls, v.playsInline, v.preload, v.autoplay, v.loop, v.paused, v.currentTime]")
        require(state == [True, True, "none", False, False, True, 0], "Unexpected initial film state: " + str(state))
        require(not any(url.endswith(FILM) for url in requests), "MP4 requested before user playback")
        require(video.get_attribute("poster") == "assets/social-immersive/cover.png", "Poster missing")
        for href in LINKS:
            suffix = "[download]" if href == FILM else ""
            require(section.locator(f'a[href="{href}"]{suffix}').first.is_visible(), "Missing persistent link: " + href)
        require(section.locator('a[href$="/docs/IMMERSIVE_ART.md"]').first.is_visible(), "Desktop guide missing")
        assert_no_overflow(page)
        if name in ("desktop", "mobile", "narrow", "no-js"):
            section.screenshot(path=str(output / (name + ".png")))
        if name == "blocked-media":
            video.evaluate("v => {v.load(); v.play().catch(() => {});}")
            wait_native(page, "(() => {const v=document.querySelector('#gallery-film'); return v.error || v.networkState === v.NETWORK_NO_SOURCE;})()")
            require(any(url.endswith(FILM) for url in requests), "Blocked video was never requested")
            for href in LINKS:
                suffix = "[download]" if href == FILM else ""
                require(section.locator(f'a[href="{href}"]{suffix}').first.is_visible(), "Failed media hid fallback: " + href)
        else:
            video.focus()
            page.keyboard.press("Space")
            wait_native(page, "document.querySelector('#gallery-film').currentTime > 0.15")
            page.keyboard.press("Space")
            require(video.evaluate("v => v.paused"), "Native keyboard pause failed")
            paused = video.evaluate("v => v.currentTime")
            page.wait_for_timeout(160)
            require(video.evaluate("v => v.currentTime") == paused, "Paused film kept advancing")
            track = video.locator("track")
            require(track.count() == 1 and track.get_attribute("src") == CAPTIONS, "Chinese caption resource missing")
            require(track.get_attribute("default") is None and track.evaluate("t => t.track.mode") == "disabled", "Captions must initially be off")
            track.evaluate("t => {t.track.mode = 'hidden';}")
            wait_native(page, "document.querySelector('#gallery-film track').readyState === 2")
            cues = track.evaluate("t => [...t.track.cues].map(c => [c.startTime, c.endTime, c.text])")
            require(len(cues) == 5 and cues[-1][1] == 20 and cues == expected_cues(), "WebVTT differs from the film's SRT")
            require(abs(video.evaluate("v => v.duration") - 20) < 0.1, "Film duration differs from captions")
            for resource in (FILM, CAPTIONS, "assets/social-immersive/cover.png"):
                require(context.request.get(base + "/" + resource).status == 200, "Missing local resource: " + resource)
        require(not errors, "Browser errors: " + "; ".join(errors))
        return {"name": name, "status": "passed", "viewport": [width, height]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("msedge", "chromium"),
                        default="msedge" if platform.system() == "Windows" else "chromium")
    parser.add_argument("--output", type=Path, default=ROOT / ".work/gallery-film")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.exit(2, "Install optional requirements-browser.txt before running browser checks.\n")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"browser": args.browser, "scope": "Fresh local browser; mobile is touch emulation", "checks": []}
    with local_site() as base, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, **({"channel": "msedge"} if args.browser == "msedge" else {}))
        report["browser_version"] = browser.version
        try:
            for case in CASES:
                try:
                    result = check_case(browser, base, args.output, case)
                except Exception as error:
                    result = {"name": case[0], "status": "failed", "error": str(error)}
                report["checks"].append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
        finally:
            browser.close()
    (args.output / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(result["status"] != "passed" for result in report["checks"]))


if __name__ == "__main__":
    sys.exit(main())
