"""Export the shared work catalog for the static website. Uses only the standard library."""
import json
from pathlib import Path
import sys
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(ROOT))
    from run import catalog
    repository = "https://github.com/zjh-b/turtle-gallery"
    works = []
    for work in catalog().WORKS:
        item = {key: work[key] for key in ("id", "number", "title", "subtitle", "collection", "category", "controls", "description", "featured", "tags", "creation")}
        item["preview"] = (f"assets/exhibits/{work['number']}.png" if work["collection"] == "interactive" else
                           f"assets/originals/{work['number']}.png")
        item["source"] = f"{repository}/blob/main/{quote(work['filename'], safe='/')}"
        works.append(item)
    data = {"project": "Turtle Gallery", "repository": repository, "works": works}
    destination = ROOT / "docs" / "gallery.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(works)} works to docs/gallery.json")


if __name__ == "__main__":
    main()
