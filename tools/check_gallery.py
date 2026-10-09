#!/usr/bin/env python3
"""Optional real-browser checks for gallery discovery and shareable filters.

Install ``requirements-browser.txt`` first. Windows uses installed Edge; use
``--browser chromium`` after installing Playwright Chromium elsewhere. Output
goes to .work/gallery. Mobile checks emulate Chromium, not a physical phone.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from check_browser import ROOT, assert_no_overflow, gallery_works, local_site, observed_page, require


WORKS = gallery_works()
ALL_IDS = [work["id"] for work in WORKS]
COLLECTION_IDS = {
    "all": ALL_IDS,
    "romantic": [work["id"] for work in WORKS if work["featured"]],
    "online": [work["id"] for work in WORKS if work["web_play"]],
    **{name: [work["id"] for work in WORKS if work["collection"] == name]
       for name in ("interactive", "original")},
}


def ready(page, base_url, query="", fragment="gallery"):
    url = base_url + "/index.html" + ("?" + query if query else "") + ("#" + fragment if fragment else "")
    response = page.goto(url, wait_until="networkidle")
    require(response is not None and response.ok, "Gallery must return HTTP 200")
    page.wait_for_function("!document.querySelector('#gallery-tools').hidden && document.querySelector('#gallery-grid').getAttribute('aria-busy') === 'false'", polling=25)


def visible_ids(page):
    return page.locator("#gallery-grid .art-card h3").evaluate_all("nodes => nodes.map(node => Number(node.id.replace('art-title-', '')))")


def collection_button(page, value):
    return page.locator(f"button[data-collection='{value}']")


def assert_collection(page, value):
    require(collection_button(page, value).get_attribute("aria-pressed") == "true", "Selected collection must be announced: " + value)
    require(page.locator("[data-collection][aria-pressed='true']").count() == 1, "Exactly one collection must be active")


def assert_url(page, collection="all", query="", marker=None, fragment=None):
    url = urlsplit(page.url)
    params = parse_qs(url.query)
    require(params.get("collection", ["all"]) == [collection], "URL must retain collection " + collection)
    require(params.get("q", [""]) == [query], "URL must retain the current search")
    if marker is not None:
        require(params.get("campaign") == [marker], "Unrelated URL parameters must survive gallery updates")
    if fragment is not None:
        require(url.fragment == fragment, "Unrelated URL fragments must survive gallery updates")


def check_discovery(browser, base_url, output):
    with browser.new_context(viewport={"width": 1440, "height": 1050}) as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        require(collection_button(page, "online").count() == 1, "Gallery needs a dedicated online collection")
        require(visible_ids(page) == ALL_IDS, "Default gallery must retain every catalog artwork")
        for value, expected_ids in COLLECTION_IDS.items():
            collection_button(page, value).click()
            assert_collection(page, value)
            require(visible_ids(page) == expected_ids, "Collection contents changed: " + value)
            require(collection_button(page, value).locator("span").inner_text() == str(len(expected_ids)), "Filter count must describe its collection")
        collection_button(page, "online").click()
        require(visible_ids(page) == [1, 3, 26], "Online collection must contain fireworks, kaleidoscope, and heart")
        require(page.locator("#gallery-grid .browser-play-link").count() == 3, "Every online artwork must have a playable link")
        assert_no_overflow(page)
        page.screenshot(path=str(output / "desktop-online.png"), full_page=True)
        page.locator("#art-title-26").locator("..").locator("a.browser-play-link").click()
        page.wait_for_url("**/play/heart.html")
        page.wait_for_function("!document.querySelector('#play-controls').disabled", polling=25)
        page.go_back(wait_until="networkidle")
        assert_collection(page, "online")
        require(visible_ids(page) == [1, 3, 26], "Returning from artwork must restore the online collection")
        ready(page, base_url, urlencode({"q": "沉浸艺术"}))
        require(visible_ids(page) == [29, 30, 31], "Immersive collection must discover all three desktop works")
        require(page.locator("#gallery-grid .browser-play-link").count() == 0,
                "Desktop artworks must not advertise browser playback")
        page.screenshot(path=str(output / "desktop-immersive.png"), full_page=True)
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_history(browser, base_url, output):
    with browser.new_context(viewport={"width": 1280, "height": 900}) as context:
        page, errors = observed_page(context)
        ready(page, base_url, urlencode({"collection": "online", "q": "怦然心动", "campaign": "club demo"}), "discover")
        assert_collection(page, "online")
        require(page.locator("#gallery-search").input_value() == "怦然心动", "Chinese deep-link search must be restored")
        require(visible_ids(page) == [26], "Deep link must open the matching particle heart")
        page.reload(wait_until="networkidle")
        assert_collection(page, "online")
        require(visible_ids(page) == [26], "Reload must retain the selected artwork")

        ready(page, base_url, "campaign=club", "discover")
        initial_length = page.evaluate("history.length")
        collection_button(page, "online").click()
        require(page.evaluate("history.length") == initial_length + 1, "Choosing a collection must create one history entry")
        page.locator("#gallery-search").fill("2")
        page.locator("#gallery-search").fill("26")
        require(page.evaluate("history.length") == initial_length + 1, "Typing must replace the current entry without flooding history")
        assert_url(page, "online", "26", "club", "discover")
        collection_button(page, "original").click()
        require(page.evaluate("history.length") == initial_length + 2, "Next collection must create one more history entry")
        page.go_back(wait_until="networkidle")
        assert_collection(page, "online")
        require(visible_ids(page) == [26] and page.locator("#gallery-search").input_value() == "26", "Back must restore both filters")
        page.go_back(wait_until="networkidle")
        assert_collection(page, "all")
        require(visible_ids(page) == ALL_IDS and page.locator("#gallery-search").input_value() == "", "Back to the initial entry must clear the search")
        page.go_forward(wait_until="networkidle")
        assert_collection(page, "online")
        require(visible_ids(page) == [26], "Forward must restore the filtered artwork")
        page.reload(wait_until="networkidle")
        assert_url(page, "online", "26", "club", "discover")
        require(visible_ids(page) == [26], "Reload after history navigation must retain results")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_search(browser, base_url, output):
    with browser.new_context() as context:
        page, errors = observed_page(context)
        ready(page, base_url, "collection=unknown&campaign=club", "discover")
        assert_collection(page, "all")
        require(visible_ids(page) == ALL_IDS, "Unknown collections must fall back to all artworks")
        collection_button(page, "online").click()
        page.locator("#gallery-search").fill("no-such-artwork-2026")
        require(not visible_ids(page), "Unmatched query must produce an empty result")
        require(page.locator("#gallery-message").is_visible(), "Empty search must offer a readable recovery action")
        page.locator("#message-action").click()
        assert_collection(page, "all")
        require(visible_ids(page) == ALL_IDS and page.locator("#gallery-search").input_value() == "", "Recovery must clear search and collection")
        require(page.locator("#gallery-search").evaluate("node => node === document.activeElement"), "Recovery must return keyboard focus to search")
        assert_url(page, "all", "", "club", "discover")
        require("collection=" not in urlsplit(page.url).query and "q=" not in urlsplit(page.url).query, "Default URL must omit empty gallery parameters")
        ready(page, base_url, urlencode({"q": "x" * 140, "collection": "online"}))
        require(page.locator("#gallery-search").input_value() == "x" * 100, "URL search must respect the 100-character limit")
        ready(page, base_url, "collection=online")
        search = page.locator("#gallery-search")
        search.dispatch_event("compositionstart")
        search.evaluate("node => { node.value = '26'; node.dispatchEvent(new InputEvent('input', {bubbles: true, isComposing: true})); }")
        require(visible_ids(page) == [1, 3, 26], "Unfinished IME input must not replace results")
        search.dispatch_event("compositionend")
        require(visible_ids(page) == [26], "Completed IME input must filter results")
        assert_url(page, "online", "26")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_recovery(browser, base_url, output):
    with browser.new_context(viewport={"width": 1280, "height": 900}) as context:
        page, errors = observed_page(context)
        page.route("**/gallery.json", lambda route: route.fulfill(status=503, body="Unavailable"))
        page.goto(base_url + "/index.html?collection=online&q=26#gallery", wait_until="networkidle")
        require(page.locator("#gallery-message").is_visible(), "Failed catalog must offer a retry")
        require(page.locator("#result-count").is_visible(), "Loading failure status must remain visible")
        require(page.locator("#gallery-tools").is_hidden() and page.locator("#share-gallery").is_hidden(), "Unloaded gallery must not offer empty filters or sharing")
        page.unroute("**/gallery.json")
        page.locator("#message-action").click()
        page.wait_for_function("!document.querySelector('#gallery-tools').hidden", polling=25)
        require(visible_ids(page) == [26], "Catalog retry must recover the original deep link")
        require(page.locator("#share-gallery").is_visible(), "Successful retry must enable sharing")

        before = page.evaluate("history.length")
        featured = page.locator(".featured-card").first
        link = featured.get_attribute("href")
        require(parse_qs(urlsplit(link).query) == {"collection": ["romantic"], "q": ["25"]}, "Featured card must expose a real deep link for opening a new tab")
        featured.focus()
        page.keyboard.press("Enter")
        require(visible_ids(page) == [25], "Keyboard activation must open the featured artwork")
        require(page.evaluate("history.length") == before + 1, "Featured navigation must create exactly one history entry")
        require(page.locator("#gallery").evaluate("node => node === document.activeElement"), "Featured navigation must move keyboard focus to the gallery")
        page.go_back(wait_until="networkidle")
        require(visible_ids(page) == [26], "One Back must undo featured navigation")
        page.locator("[data-show-featured]").click()
        require(visible_ids(page) == [25, 26, 27, 28], "Featured collection link must clear the previous query")
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_share(browser, base_url, output):
    for denied in (False, True):
        with browser.new_context(viewport={"width": 1280, "height": 900}) as context:
            context.add_init_script("""(() => {
              window.__copiedGallery = [];
              Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {
                writeText: async value => {
                  if (DENIED) throw new DOMException('Clipboard denied', 'NotAllowedError');
                  window.__copiedGallery.push(value);
                }
              }});
            })()""".replace("DENIED", "true" if denied else "false"))
            page, errors = observed_page(context)
            ready(page, base_url, "collection=online&q=26&campaign=club", "discover")
            page.locator("#share-gallery").click()
            if denied:
                field = page.locator(".manual-link")
                field.wait_for(state="visible")
                copied = field.input_value()
                require(field.get_attribute("readonly") is not None, "Manual link must be read-only")
                require(field.evaluate("node => node === document.activeElement && node.selectionStart === 0 && node.selectionEnd === node.value.length"), "Manual link must receive focus and be fully selected")
                page.screenshot(path=str(output / "share-fallback.png"), full_page=True)
            else:
                page.wait_for_function("window.__copiedGallery.length === 1", polling=25)
                copied = page.evaluate("window.__copiedGallery[0]")
                require(page.locator("#copy-status").is_visible(), "Successful sharing must announce feedback")
            shared = urlsplit(copied)
            require(shared.fragment == "gallery", "Shared links must open directly at the gallery")
            require(parse_qs(shared.query) == {"collection": ["online"], "q": ["26"], "campaign": ["club"]}, "Shared links must retain current filters and unrelated parameters")
            require(shared.scheme in ("http", "https") and shared.netloc == urlsplit(base_url).netloc, "Shared links must use the current deployment origin")
            assert_url(page, "online", "26", "club", "discover")
            page.locator("#gallery-search").fill("03")
            require(page.locator(".manual-link").is_hidden(), "Changing filters must hide a stale manual link")
            page.goto(copied, wait_until="networkidle")
            assert_collection(page, "online")
            require(visible_ids(page) == [26], "Opening the shared link must reproduce the selected artwork")
            require(not errors, "Uncaught browser errors: " + "; ".join(errors))


def check_mobile(browser, base_url, output):
    with browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3,
                             is_mobile=True, has_touch=True) as context:
        page, errors = observed_page(context)
        ready(page, base_url)
        collection_button(page, "online").tap()
        assert_collection(page, "online")
        require(visible_ids(page) == [1, 3, 26], "Mobile online filter must respond to touch")
        assert_no_overflow(page)
        for selector in ("#gallery-search", "#share-gallery", "[data-collection='online']"):
            target = page.locator(selector)
            target.focus()
            require(target.evaluate("node => node === document.activeElement"), "Control must be keyboard focusable: " + selector)
        collection_button(page, "all").focus()
        page.keyboard.press("Enter")
        assert_collection(page, "all")
        collection_button(page, "online").focus()
        page.keyboard.press("Space")
        assert_collection(page, "online")
        page.locator("#gallery-search").focus()
        page.keyboard.type("26")
        require(visible_ids(page) == [26], "Keyboard search must narrow the mobile gallery")
        page.locator("#gallery-tools").scroll_into_view_if_needed()
        assert_no_overflow(page)
        page.screenshot(path=str(output / "mobile-filtered.png"), full_page=True)
        for width in (320, 560, 850, 1024):
            page.set_viewport_size({"width": width, "height": 844})
            assert_no_overflow(page)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#gallery").screenshot(path=str(output / "mobile-gallery.png"))
        require(not errors, "Uncaught browser errors: " + "; ".join(errors))


CHECKS = {"discovery": check_discovery, "history": check_history, "search": check_search,
          "share": check_share, "mobile": check_mobile, "recovery": check_recovery}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", choices=("msedge", "chromium"),
                        default="msedge" if platform.system() == "Windows" else "chromium")
    parser.add_argument("--output", type=Path, default=ROOT / ".work" / "gallery")
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
