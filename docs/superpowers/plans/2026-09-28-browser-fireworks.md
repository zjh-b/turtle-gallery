# Browser Fireworks Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task by task. Shared workspace ownership is assigned per file.

**Goal:** Publish a usable, accessible browser version of artwork 01.

**Architecture:** Shared Python constants export to static JSON; a DOM-free JavaScript model feeds a Canvas renderer and a small page controller. Existing gallery links identify the one playable artwork.

**Tech Stack:** Python standard library, native browser modules / Canvas, Node built-in tests, optional Playwright verification.

**Spec:** [Browser fireworks design](../specs/2026-09-28-browser-fireworks-design.md)

## Global Constraints

- Desktop Python >= 3.9, no new desktop runtime dependency.
- Particle cap 600; rocket and bloom caps 8; backing-store DPI <= 2.
- Motion and automatic display are opt-in; reduced motion makes discrete static bursts.
- No claims of real-device validation from mobile emulation.
- Retain the 28-work catalog and existing desktop controls.

## Review Focus

- Touch scrolling / pointer cancellation must not emit accidental fireworks.
- Page visibility and rapid toggling must not create duplicate frame loops.
- Coordinates must follow resized / scaled Canvas bounds.
- Missing config / Canvas must retain the usable static preview and links.
- Exported constants and numerical fixtures must stay in sync with Python.

## Tasks

### 1. Shared physics and browser model

- [x] Extract constants / pure formulas into `社团展示/烟花参数.py`, keeping desktop results; extend `tools/export_gallery.py` to generate config and numerical fixtures.
- [x] Write `tests/web/fireworks-model.test.mjs`; observe missing implementation failure.
- [x] Implement `docs/play/fireworks-model.js` with the interface in the spec; run `node --test tests/web/*.test.mjs` and relevant Python tests.

### 2. Playable page

- [x] Add `docs/play/fireworks.html`, `fireworks.css`, `fireworks-view.js`, `fireworks.js` for scene rendering and accessible controls.
- [x] Add `tools/check_browser.py` covering input, scrolling/cancellation, lifecycle, reduced motion, fallback, responsive bounds and gallery entry.
- [x] Run the browser check on local HTTP with Edge, inspect screenshots, fix visible defects.

### 3. Integrate and publish

- [x] Add catalog-backed browser URL to work 01, home entry and per-card link; regenerate gallery data.
- [x] Update bilingual README, creation / contribution guidance, M3 progress, and a browser verification record with exact tested scope.
- [x] Add a CI job for Node model tests; enforce generated config consistency in existing checks.
- [x] Run Python, Node, browser and catalog checks; independent code review.
Release procedure: commit / push under existing authorization, then verify the exact commit in CI, Pages deployment and published assets.

## Execution notes

The user has already authorized gradual implementation and publishing of the roadmap. This plan uses that continuing authorization. Root implements the page and integrates; a parallel worker owns physics/model and its tests. Final review checks the whole change.

Verification: 150 Python tests (149 passed, one optional GUI font check skipped); 11 Node tests; 6 browser groups passed on Edge 154. The previous gallery smoke check also passed. Browser screenshots and limits are recorded in `docs/benchmarks/browser-m3.json`.

Ruling: use `.js` browser modules with a local `type: module` declaration so Windows Python HTTP preview serves the correct MIME type. QA polling uses timers to exclude Playwright?s own RAF from lifecycle counts; disabled controls are checked through the HTML disabled state and inherited `:disabled`.
