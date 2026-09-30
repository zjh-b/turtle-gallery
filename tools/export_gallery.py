"""Export the shared work catalog for the static website. Uses only the standard library."""
import json
import math
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
    # libm differs in its last bits across Windows and Linux. Only fixtures
    # are rounded; runtime geometry retains full precision. Error < 1e-9.
    fixtures = []
    for count in (3, 4, 10, 16):
        result = [[[round(value, 9) or 0.0 for value in point] for point in stroke]
                  for stroke in mirror_points(points, count)]
        fixtures.append(dict(points=points, count=count, result=result))
    data = dict(version=1, view=VIEW, radius=RADIUS, min_count=MIN_COUNT, max_count=MAX_COUNT,
                max_strokes=60, max_points=2400, max_stroke_points=400,
                fixtures=fixtures)
    destination = ROOT / "docs/play/kaleidoscope-config.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported shared kaleidoscope geometry to docs/play/kaleidoscope-config.json")


def export_heart():
    """Export bounded browser settings and portable shared-motion fixtures."""
    sys.path.insert(0, str(ROOT / "社团展示"))
    from 爱心参数 import THEMES, heart_point, heartbeat, spread_at
    def rounded(value):
        return round(value, 9) or 0.0
    fixtures = dict(
        heart=[dict(angle=angle, result=[rounded(value) for value in heart_point(angle)])
               for angle in (0, .4, math.pi/2, math.pi, math.pi*1.5, math.tau)],
        beat=[dict(time=time, result=rounded(heartbeat(time)))
              for time in (0, .15, .279, .527, 1.1625, 1.55, 1.829)],
        spread=[dict(age=age, result=rounded(spread_at(age)))
                for age in (None, 0, .45, .9, 1.8, 2.7, 3.6)])
    data = dict(version=1, view=[640, 640], themes=THEMES, densities=[420, 680, 1000],
                default_count=680, max_step=.05, burst_duration=3.6,
                rate_min=.45, rate_max=1.8, fixtures=fixtures)
    destination = ROOT / "docs/play/heart-config.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Exported shared heart geometry and motion to docs/play/heart-config.json")


def build_gallery(catalog_works):
    """Project catalog metadata into JSON-ready website data without writing files."""
    repository = "https://github.com/zjh-b/turtle-gallery"
    works = []
    for work in catalog_works:
        item = {key: work[key] for key in ("id", "number", "title", "subtitle", "collection", "category", "controls", "description", "featured", "tags", "creation", "autoplay")}
        item["tags"] = list(work["tags"])
        item["web_play"] = work.get("web_play")
        item["preview"] = (f"assets/exhibits/{work['number']}.png" if work["collection"] == "interactive" else
                           f"assets/originals/{work['number']}.png")
        item["source"] = f"{repository}/blob/main/{quote(work['filename'], safe='/')}"
        works.append(item)
    return {"project": "Turtle Gallery", "repository": repository, "works": works}


def main():
    sys.path.insert(0, str(ROOT))
    from run import catalog
    data = build_gallery(catalog().WORKS)
    destination = ROOT / "docs" / "gallery.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(data['works'])} works to docs/gallery.json")
    export_fireworks()
    export_kaleidoscope()
    export_heart()


if __name__ == "__main__":
    main()
