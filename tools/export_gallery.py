"""Export the shared work catalog for the static website. Uses only the standard library."""
import json
from pathlib import Path
import sys
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


def export_fireworks():
    """Generate the browser configuration and cross-language numerical fixtures."""
    sys.path.insert(0, str(ROOT / "社团展示"))
    from 烟花参数 import PALETTES, PHYSICS, SHAPES, VIEW, initial_velocity, location
    velocities = [dict(kind=kind, index=index, speed=120,
                       result=initial_velocity(kind, index, 120))
                  for kind in range(4) for index in (0, 1, 21, 42, 63)]
    locations = []
    for particle in (dict(x=12, y=34, vx=115, vy=-70, gravity=46),
                     dict(x=-150, y=80, vx=-64, vy=112, gravity=75)):
        for age in (-0.2, 0, 0.35, 1.1, 2.4):
            locations.append(dict(particle=particle, age=age, result=location(particle, age)))
    data = dict(version=1, view=VIEW, palettes=PALETTES, shapes=SHAPES, physics=PHYSICS,
                fixtures=dict(velocities=velocities, locations=locations))
    destination = ROOT / "docs/play/fireworks-config.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported shared fireworks formulas to docs/play/fireworks-config.json")


def export_kaleidoscope():
    """Keep browser mirror geometry and its numerical fixtures in sync."""
    sys.path.insert(0, str(ROOT / "社团展示"))
    from 万花筒参数 import MAX_COUNT, MIN_COUNT, RADIUS, VIEW, mirror_points
    points = [(10, 20), (-30, 40), (122, -72)]
    data = dict(version=1, view=VIEW, radius=RADIUS, min_count=MIN_COUNT, max_count=MAX_COUNT,
                max_strokes=60, max_points=2400, max_stroke_points=400,
                fixtures=[dict(points=points, count=count, result=mirror_points(points, count))
                          for count in (3, 4, 10, 16)])
    destination = ROOT / "docs/play/kaleidoscope-config.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported shared kaleidoscope geometry to docs/play/kaleidoscope-config.json")


def main():
    sys.path.insert(0, str(ROOT))
    from run import catalog
    repository = "https://github.com/zjh-b/turtle-gallery"
    works = []
    for work in catalog().WORKS:
        item = {key: work[key] for key in ("id", "number", "title", "subtitle", "collection", "category", "controls", "description", "featured", "tags", "creation", "autoplay")}
        item["web_play"] = work.get("web_play")
        item["preview"] = (f"assets/exhibits/{work['number']}.png" if work["collection"] == "interactive" else
                           f"assets/originals/{work['number']}.png")
        item["source"] = f"{repository}/blob/main/{quote(work['filename'], safe='/')}"
        works.append(item)
    data = {"project": "Turtle Gallery", "repository": repository, "works": works}
    destination = ROOT / "docs" / "gallery.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(works)} works to docs/gallery.json")
    export_fireworks()
    export_kaleidoscope()


if __name__ == "__main__":
    main()
