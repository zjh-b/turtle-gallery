#!/usr/bin/env python3
"""Check catalog metadata, published data and local resources without opening a GUI.

Run ``python tools/check_catalog.py`` from any directory. This read-only check
uses the standard library; it never imports artwork modules or regenerates media.
PNG checks inspect the header, not the rendered image or screenshot freshness.
"""

import json
from pathlib import Path, PureWindowsPath
import re
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.export_gallery import build_gallery


def local_file(root, value, suffix, label, errors):
    """Check portable spelling as well as existence on case-insensitive systems."""
    if (not isinstance(value, str) or not value or "\\" in value
            or PureWindowsPath(value).drive or value.startswith("/")
            or any(part in ("", ".", "..") for part in value.split("/"))):
        errors.append(f"{label}: expected a relative path with forward slashes: {value!r}")
        return None
    if Path(value).suffix != suffix:
        errors.append(f"{label}: expected a {suffix} file: {value}")
        return None
    target = root / value
    try:
        if not target.resolve().is_relative_to(root):
            errors.append(f"{label}: path escapes its resource root: {value}")
            return None
        current = root
        for part in value.split("/"):
            names = {child.name for child in current.iterdir()}
            if part not in names:
                reason = "filename case mismatch" if any(name.casefold() == part.casefold() for name in names) else "missing file or directory"
                errors.append(f"{label}: {reason}: {value}")
                return None
            current = current / part
        if not target.is_file():
            errors.append(f"{label}: not a file: {value}")
            return None
    except (OSError, ValueError, RuntimeError) as error:
        errors.append(f"{label}: cannot access {value}: {error}")
        return None
    return target


def check_png(path, label, errors):
    if path is None:
        return
    try:
        with path.open("rb") as source:
            header = source.read(24)
        valid = (len(header) == 24 and header[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                 and all(struct.unpack(">II", header[16:24])))
        if not valid:
            errors.append(f"{label}: invalid PNG header or dimensions: {path.name}")
    except OSError as error:
        errors.append(f"{label}: cannot read {path.name}: {error}")


def validate_catalog(works, root=ROOT):
    """Return actionable errors; accept small fixture catalogs and future additions."""
    root = Path(root).resolve()
    errors = []
    if not isinstance(works, (list, tuple)) or not works:
        return ["Catalog WORKS must be a nonempty list or tuple."]
    seen = {field: set() for field in ("id", "number", "filename")}
    schema_valid = True
    for index, work in enumerate(works, 1):
        label = f"Work entry {index}"
        if not isinstance(work, dict):
            errors.append(f"{label}: expected a metadata dictionary")
            schema_valid = False
            continue
        label = f"Work {work.get('number', '?')} (entry {index})"
        before = len(errors)
        identifier = work.get("id")
        if type(identifier) is not int or not 1 <= identifier <= 99:
            errors.append(f"{label}: id must be an integer from 1 to 99 (two-digit website numbers)")
        elif work.get("number") != f"{identifier:02d}":
            errors.append(f"{label}: number must match id {identifier}: {identifier:02d}")
        for field in ("number", "title", "subtitle", "collection", "category", "controls", "description", "filename", "preview"):
            if not isinstance(work.get(field), str) or not work[field].strip():
                errors.append(f"{label}: {field} must be a nonempty string")
        if work.get("collection") not in ("interactive", "original"):
            errors.append(f"{label}: collection must be interactive or original")
        for field in ("featured", "creation", "autoplay"):
            if type(work.get(field)) is not bool:
                errors.append(f"{label}: {field} must be a boolean")
        tags = work.get("tags")
        if not isinstance(tags, (list, tuple)) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            errors.append(f"{label}: tags must be a list or tuple of nonempty strings")
        web_play = work.get("web_play")
        valid_web = web_play is None or isinstance(web_play, str) and re.fullmatch(r"play/[a-z0-9-]+\.html", web_play)
        if not valid_web:
            errors.append(f"{label}: web_play must be a local play/<page>.html path or null")
        schema_valid = schema_valid and len(errors) == before
        for field, values in seen.items():
            value = work.get(field)
            if isinstance(value, (str, int)):
                if value in values:
                    errors.append(f"{label}: duplicate {field}: {value}")
                values.add(value)
        local_file(root, work.get("filename"), ".py", label + " filename", errors)
        check_png(local_file(root, work.get("preview"), ".png", label + " desktop preview", errors), label + " desktop preview", errors)
        if isinstance(work.get("number"), str) and re.fullmatch(r"\d{2}", work["number"]):
            folder = "exhibits" if work.get("collection") == "interactive" else "originals"
            preview = f"assets/{folder}/{work['number']}.png"
            check_png(local_file(root / "docs", preview, ".png", label + " web preview", errors), label + " web preview", errors)
        if valid_web and web_play is not None:
            local_file(root / "docs", web_play, ".html", label + " web_play", errors)

    try:
        published = json.loads((root / "docs/gallery.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append(f"docs/gallery.json: cannot read valid JSON: {error}")
        return errors
    if not schema_valid:
        return errors
    try:
        expected = build_gallery(works)
    except UnicodeError as error:
        errors.append(f"Catalog filename cannot be encoded in a source URL: {error}")
        return errors
    if not isinstance(published, dict) or set(published) != set(expected):
        errors.append("docs/gallery.json: expected project, repository and works fields")
        return errors
    for field in ("project", "repository"):
        if published[field] != expected[field]:
            errors.append(f"docs/gallery.json: {field} differs from source")
    actual = published["works"]
    if not isinstance(actual, list):
        errors.append("docs/gallery.json: works must be a list")
        return errors
    if len(actual) != len(expected["works"]):
        errors.append(f"docs/gallery.json: expected {len(expected['works'])} works, found {len(actual)}")
    for index, (wanted, item) in enumerate(zip(expected["works"], actual), 1):
        label = f"docs/gallery.json work {wanted['number']} (entry {index})"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected a metadata object")
            continue
        different = [key for key in wanted if type(item.get(key)) is not type(wanted[key]) or item.get(key) != wanted[key]]
        # Missing null-valued fields must also be detected.
        different.extend(sorted(set(wanted) - set(item) - set(different)))
        different.extend(sorted(set(item) - set(wanted)))
        if different:
            errors.append(f"{label}: differs from source in {', '.join(different)}")
    return errors


def main():
    try:
        from run import catalog
        works = catalog().WORKS
        errors = validate_catalog(works, ROOT)
    except (OSError, ValueError, SyntaxError, AttributeError, TypeError, NameError) as error:
        print(f"ERROR: Cannot load catalog: {error}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("Fix catalog/resources; if published data is stale, run python tools/export_gallery.py.", file=sys.stderr)
        return 1
    online = sum(work.get("web_play") is not None for work in works)
    print(f"Catalog OK: {len(works)} works, desktop/web previews and {online} online pages; published JSON matches source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
