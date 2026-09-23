"""Headless checks for the real animation, interaction and drawing code.

Run with ``python -m unittest discover -s tests -v``. Only the window and
Canvas are replaced; geometry, animation frames and game physics stay real.
"""

import copy
import importlib.util
import math
from pathlib import Path
import random
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


DEMO_DIR = Path(__file__).resolve().parents[1] / "社团展示"


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Some of the original files have a UTF-8 BOM (common on Windows).
    source = path.read_text(encoding="utf-8-sig")
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


STAGE = load_source("gallery_stage_tests", DEMO_DIR / "舞台.py")
DEMO_CLASSES = {
    "01_点击烟花.py": "Fireworks",
    "02_旋转星系.py": "Galaxy",
    "03_鼠标万花筒.py": "Kaleidoscope",
    "04_互动鱼塘.py": "Pond",
    "05_接住星星.py": "StarGame",
    "06_四季分形树.py": "SeasonTree",
    "07_深海水母.py": "Jellyfish",
    "08_山水画卷.py": "Landscape",
    "09_几何绘图仪.py": "Spirograph",
    "10_霓虹弹球.py": "Breakout",
    "25_星空彼岸花.py": "StarryLily",
    "26_怦然心动.py": "ParticleHeart",
    "27_星河玫瑰.py": "GalaxyRose",
    "28_霓光蝶舞.py": "NeonButterfly",
}
with patch.dict(sys.modules, {"舞台": STAGE}):
    DEMOS = {
        class_name: load_source("gallery_test_" + class_name, DEMO_DIR / filename)
        for filename, class_name in DEMO_CLASSES.items()
    }


class Canvas:
    """A tiny Canvas that records public drawing operations, without Tk."""

    def __init__(self):
        self.items = {}
        self.bindings = {}
        self.next_id = 1
        self.coordinate_updates = 0
        self.option_updates = 0
        self.root = SimpleNamespace(minsize=Mock(), protocol=Mock(), attributes=Mock())

    def _create(self, kind, *coords, **options):
        if len(coords) % 2 or not all(math.isfinite(v) for v in coords):
            raise ValueError("Canvas coordinates must be finite x/y pairs")
        if kind == "line" and len(coords) < 4:
            raise ValueError("A line needs at least two points")
        if kind == "polygon" and len(coords) < 6:
            raise ValueError("A polygon needs at least three points")
        item = self.next_id
        self.next_id += 1
        self.items[item] = dict(kind=kind, coords=coords, options=options)
        return item

    def create_rectangle(self, *args, **kwargs):
        return self._create("rectangle", *args, **kwargs)

    def create_oval(self, *args, **kwargs):
        return self._create("oval", *args, **kwargs)

    def create_line(self, *args, **kwargs):
        return self._create("line", *args, **kwargs)

    def create_polygon(self, *args, **kwargs):
        return self._create("polygon", *args, **kwargs)

    def create_text(self, *args, **kwargs):
        return self._create("text", *args, **kwargs)

    def matching(self, item_or_tag):
        return [key for key, item in self.items.items()
                if key == item_or_tag or item_or_tag == "all"
                or item_or_tag in item["options"].get("tags", ())]

    def coords(self, item, *coords):
        if not all(math.isfinite(v) for v in coords):
            raise ValueError("Canvas coordinates must be finite")
        self.items[item]["coords"] = coords
        self.coordinate_updates += 1

    def itemconfigure(self, item_or_tag, **options):
        for item in self.matching(item_or_tag):
            self.items[item]["options"].update(options)
        self.option_updates += 1

    def delete(self, item_or_tag):
        for item in self.matching(item_or_tag):
            del self.items[item]

    def tag_raise(self, item_or_tag):
        pass

    def bind(self, event, callback, add=None):
        self.bindings[event] = callback

    def canvasx(self, x):
        return x

    def canvasy(self, y):
        return y

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def winfo_toplevel(self):
        return self.root


class Screen:
    def __init__(self):
        self.canvas = Canvas()
        self.keys, self.keypresses, self.keyreleases = {}, {}, {}
        self.width, self.height = 1000, 720
        self.timers = []
        self.bye = Mock()
        self.update = Mock()

    def getcanvas(self):
        return self.canvas

    def setup(self, width, height):
        self.width, self.height = width, height

    def window_width(self):
        return self.width

    def window_height(self):
        return self.height

    def title(self, title):
        self.window_title = title

    def bgcolor(self, color):
        self.background = color

    def tracer(self, value):
        pass

    def listen(self):
        pass

    def onkey(self, callback, key):
        self.keys[key] = callback

    def onkeypress(self, callback, key):
        self.keypresses[key] = callback

    def onkeyrelease(self, callback, key):
        self.keyreleases[key] = callback

    def onclick(self, callback):
        self.click = callback

    def ontimer(self, callback, delay):
        self.timers.append((callback, delay))

    def mainloop(self):
        pass


class HeadlessStage(STAGE.Stage):
    def __init__(self, *args, **kwargs):
        with patch.object(STAGE.turtle, "Screen", return_value=Screen()):
            super().__init__(*args, **kwargs)


def make_app(name):
    module = DEMOS[name]
    with patch.object(module, "Stage", HeadlessStage):
        app = getattr(module, name)()
    app.reset()
    return app


def state(app):
    return copy.deepcopy({key: value.getstate() if isinstance(value, random.Random) else value
                          for key, value in vars(app).items()
                          if key not in {"stage", "paint"}})


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(2026)

    def tearDown(self):
        random.setstate(self.random_state)

    def test_all_interactive_demos_draw_and_freeze_at_zero_delta(self):
        for name in DEMOS:
            with self.subTest(demo=name):
                app = make_app(name)
                app.frame(0.025)
                self.assertGreater(len(app.stage.canvas.items), 20)
                app.stage.paused = True
                before = state(app)
                app.frame(0)
                self.assertEqual(state(app), before)
                app.stage.reset_action = app.reset
                app.stage.reset()
                self.assertFalse(app.stage.paused)
                app.frame(0.025)

    def test_paused_clicks_do_not_add_objects(self):
        cases = [("Fireworks", "click", (0, 100)),
                 ("Pond", "feed", (0, 0)),
                 ("Jellyfish", "light", (0, 100)),
                 ("Landscape", "add_boat", (0, -200)),
                 ("Breakout", "click", (0, -100)),
                 ("StarryLily", "meteor", (0, 100)),
                 ("ParticleHeart", "burst", (0, 100)),
                 ("GalaxyRose", "stardust", (0, 100)),
                 ("NeonButterfly", "attract", (0, 100))]
        for name, method, args in cases:
            with self.subTest(demo=name):
                app = make_app(name)
                app.stage.paused = True
                before = state(app)
                getattr(app, method)(*args)
                self.assertEqual(state(app), before)

    def test_flowers_complete_growth_and_replay_without_resetting_palette(self):
        for name, field in (("StarryLily", "bloom"), ("GalaxyRose", "growth")):
            with self.subTest(demo=name):
                app = make_app(name)
                app.frame(8)
                self.assertEqual(getattr(app, field), 7)
                app.change_theme()
                app.replay()
                self.assertEqual(getattr(app, field), 0)
                self.assertEqual(app.theme, 1)
                app.frame(1)
                app.stage.paused = True
                before = state(app)
                app.replay()
                app.frame(0)
                self.assertEqual(state(app), before)

    def test_lily_meteors_account_for_scale_stay_bounded_and_expire(self):
        app = make_app("StarryLily")
        scale = app.stage.scale
        for _ in range(30):
            app.meteor(230 * scale, 100 * scale)
        self.assertEqual(len(app.meteors), 5)
        self.assertAlmostEqual(app.meteors[-1][0], 230)
        self.assertAlmostEqual(app.meteors[-1][1], 100)
        before = copy.deepcopy(app.meteors)
        app.meteor(0, 400 * scale)
        self.assertEqual(app.meteors, before)
        app.frame(2)
        self.assertFalse(app.meteors)

    def test_rose_stardust_pool_is_bounded_and_expires(self):
        app = make_app("GalaxyRose")
        for _ in range(20):
            app.stardust(0, 0)
        self.assertEqual(len(app.particles), 144)
        app.frame(1)
        self.assertEqual(len(app.particles), 144)
        app.frame(1.5)
        self.assertFalse(app.particles)

    def test_particle_heart_reassembles_without_allocating_more_particles(self):
        app = make_app("ParticleHeart")
        original = copy.deepcopy(app.particles)
        for _ in range(30):
            app.burst(0, 0)
        self.assertEqual(app.burst_age, 0)
        app.frame(1.8)
        self.assertIsNotNone(app.burst_age)
        app.frame(2)
        self.assertIsNone(app.burst_age)
        self.assertEqual(app.particles, original)
        self.assertEqual(len(app.particles), app.PARTICLE_COUNT)
        app.change_rate(-100)
        self.assertGreater(app.rate, 0)
        app.change_rate(100)
        self.assertLessEqual(app.rate, 2)

    def test_butterfly_target_expires_and_hover_holds_position(self):
        app = make_app("NeonButterfly")
        scale = app.stage.scale
        app.attract(250 * scale, 100 * scale)
        self.assertAlmostEqual(app.target[0], 250)
        self.assertAlmostEqual(app.target[1], 100)
        app.frame(.5)
        self.assertGreater(app.offset[0], 0)
        app.toggle_motion()
        position = app.offset[:]
        app.frame(1)
        self.assertEqual(app.offset, position)
        app.frame(6)
        self.assertIsNone(app.target)

    def test_new_scenes_render_all_palettes_and_keep_canvas_pool_bounded(self):
        for name in ("StarryLily", "ParticleHeart", "GalaxyRose", "NeonButterfly"):
            with self.subTest(demo=name):
                app = make_app(name)
                app.frame(8)
                for _ in range(3):
                    app.change_theme()
                    app.frame(.05)
                self.assertEqual(app.theme, 0)
                count = len(app.stage.canvas.items)
                self.assertLess(count, 1600)
                app.frame(.05)
                self.assertLessEqual(len(app.stage.canvas.items), count + 10)

    def test_heart_curve_closes_and_is_symmetric(self):
        point = DEMOS["ParticleHeart"].heart_point
        self.assertAlmostEqual(point(0)[0], point(math.tau)[0])
        self.assertAlmostEqual(point(0)[1], point(math.tau)[1])
        for angle in (.2, 1.0, 2.4):
            left, right = point(angle), point(-angle)
            self.assertAlmostEqual(left[0], -right[0])
            self.assertAlmostEqual(left[1], right[1])

    def test_game_key_release_and_focus_loss_stop_movement(self):
        for name in ("StarGame", "Breakout"):
            with self.subTest(demo=name):
                app = make_app(name)
                app.stage.screen.keypresses["Right"]()
                self.assertIn("Right", app.keys)
                app.stage.screen.keyreleases["Right"]()
                self.assertFalse(app.keys)
                app.stage.screen.keypresses["Left"]()
                app.stage.canvas.bindings["<FocusOut>"](None)
                self.assertFalse(app.keys)

    def test_fireworks_stay_bounded_and_expire(self):
        app = make_app("Fireworks")
        app.auto = False
        for i in range(30):
            app.launch(0, 100, i % 4)
            app.burst(0, 100, i % 4)
        self.assertLessEqual(len(app.rockets), 8)
        self.assertLessEqual(len(app.particles), 600)
        self.assertLessEqual(len(app.blooms), 8)
        # Rockets become blooms, then every particle expires naturally.
        app.frame(0.9)
        self.assertFalse(app.rockets)
        app.frame(3)
        self.assertFalse(app.particles)
        self.assertFalse(app.blooms)

    def test_galaxy_selection_accounts_for_window_scale(self):
        app = make_app("Galaxy")
        for index, (orbit, radius, color, speed, phase, name) in enumerate(DEMOS["Galaxy"].PLANETS):
            with self.subTest(planet=name):
                x, y = app.orbit(orbit, phase)
                app.select(x * app.stage.scale, y * app.stage.scale)
                self.assertEqual(app.selected, index)
        app.select(0, 0)
        self.assertIsNone(app.selected)
        app.change_speed(-100)
        self.assertGreater(app.speed, 0)
        app.change_speed(100)
        self.assertLessEqual(app.speed, 4)

    def test_kaleidoscope_retains_bounded_strokes_and_rescales_ink(self):
        app = make_app("Kaleidoscope")
        app.clear()
        app.count = 3
        app.previous = (0, 0)
        for i in range(930):
            app.draw(20 if i % 2 else -20, 30)
        self.assertEqual(len(app.ink), app.strokes)
        self.assertLessEqual(app.strokes, 900)
        self.assertEqual(len(app.stage.canvas.matching("ink")), app.strokes * 6)
        original_paths = copy.deepcopy(app.paths)
        old_ids = set(app.stage.canvas.matching("ink"))
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.frame(0)
        self.assertEqual(app.paths, original_paths)
        self.assertTrue(old_ids.isdisjoint(app.stage.canvas.matching("ink")))
        self.assertEqual(len(app.stage.canvas.matching("ink")), app.strokes * 6)
        app.draw(400, 400)
        self.assertIsNone(app.previous)
        app.clear()
        self.assertFalse(app.paths)
        self.assertFalse(app.stage.canvas.matching("ink"))

    def test_pond_limits_objects_and_fish_eat_nearby_food(self):
        app = make_app("Pond")
        for _ in range(30):
            app.add_fish()
            app.feed(0, 0)
        self.assertLessEqual(len(app.fish), 14)
        self.assertLessEqual(len(app.food), 60)
        self.assertLessEqual(len(app.ripples), 12)
        app.fish = app.fish[:1]
        fish = app.fish[0]
        app.food = [[fish["x"], fish["y"], 10]]
        app.update(0.025)
        self.assertFalse(app.food)
        for _ in range(300):
            app.update(0.05)
        self.assertFalse(app.ripples)
        self.assertLessEqual(abs(fish["x"]), 435)
        self.assertGreaterEqual(fish["y"], -230)
        self.assertLessEqual(fish["y"], 220)

    def test_star_crossing_basket_is_caught_even_with_large_movement(self):
        app = make_app("StarGame")
        app.timer = 100
        app.items = [[app.x, app.basket_y + 20, 1000, 0]]
        app.update(0.05)
        self.assertEqual((app.score, app.combo, app.lives), (1, 1, 5))
        self.assertFalse(app.items)
        self.assertTrue(app.sparks)
        app.update(1)
        self.assertFalse(app.sparks)
        self.assertFalse(app.popups)

    def test_star_game_ends_after_five_misses_and_reset_keeps_best(self):
        app = make_app("StarGame")
        app.timer = 100
        app.caught(0)
        app.items = [[300, app.basket_y - 40, 10, 0] for _ in range(8)]
        app.update(0.025)
        self.assertTrue(app.ended)
        self.assertEqual(app.lives, 0)
        self.assertEqual(app.combo, 0)
        before = state(app)
        app.update(1)
        self.assertEqual(state(app), before)
        app.reset()
        self.assertEqual((app.best, app.score, app.lives), (1, 0, 5))
        self.assertFalse(app.ended)

    def test_tree_branches_form_a_connected_tapering_tree(self):
        app = make_app("SeasonTree")
        children = {i: [] for i in range(len(app.branches))}
        self.assertLessEqual(len(app.branches), 511)
        roots = 0
        for index, (parent, length, angle, level, seed) in enumerate(app.branches):
            self.assertGreater(length, 0)
            if parent == -1:
                roots += 1
                self.assertEqual(level, 0)
            else:
                self.assertLess(parent, index)
                children[parent].append(index)
                self.assertLess(length, app.branches[parent][1])
                self.assertEqual(level, app.branches[parent][3] + 1)
        self.assertEqual(roots, 1)
        self.assertTrue(all(len(nodes) in (0, 2) for nodes in children.values()))
        app.regrow()
        app.frame(0.5)
        self.assertGreater(app.growth, 0)
        self.assertLess(app.growth, 1)
        app.frame(10)
        self.assertGreaterEqual(app.growth, max(branch[3] for branch in app.branches) + 1)

    def test_jellyfish_light_expires_and_motion_returns_to_center(self):
        app = make_app("Jellyfish")
        app.light(200 * app.stage.scale, 100 * app.stage.scale)
        app.frame(1)
        self.assertGreater(app.offset[0], 0)
        self.assertGreater(app.offset[1], 0)
        app.frame(6)
        self.assertIsNone(app.target)
        self.assertEqual(app.offset, [0, 0])

    def test_landscape_boats_and_daylight_stay_in_bounds(self):
        app = make_app("Landscape")
        app.add_boat(0, 100)
        self.assertEqual(len(app.boats), 2)
        for _ in range(15):
            app.add_boat(0, -200 * app.stage.scale)
        self.assertLessEqual(len(app.boats), 5)
        app.boats = [[509, -200, 1, 1]]
        app.toggle_day()
        app.frame(3)
        self.assertEqual(app.night, 1)
        self.assertFalse(app.stage.light)
        self.assertGreaterEqual(app.boats[0][0], -510)
        self.assertLessEqual(app.boats[0][0], 510)
        app.toggle_day()
        app.frame(3)
        self.assertEqual(app.night, 0)
        self.assertTrue(app.stage.light)

    def test_all_spirograph_presets_close_and_redraw_finishes(self):
        app = make_app("Spirograph")
        for index in range(len(DEMOS["Spirograph"].PRESETS)):
            with self.subTest(preset=index):
                app.choose(index)
                self.assertLess(math.dist(app.points[0], app.points[-1]), 1e-8)
                self.assertTrue(all(math.isfinite(x) and math.isfinite(y) for x, y in app.points))
                self.assertGreater(max(math.dist(app.points[0], p) for p in app.points), 100)
                app.redraw()
                app.frame(app.period / 2.2 / 2)
                self.assertAlmostEqual(app.progress, 0.5)
                app.frame(app.period / 2.2)
                self.assertEqual(app.progress, 1)
                self.assertGreaterEqual(app.theta, 0)
                self.assertLess(app.theta, app.period)


class BreakoutTests(unittest.TestCase):
    def setUp(self):
        self.random_state = random.getstate()
        random.seed(2026)
        self.app = make_app("Breakout")

    def tearDown(self):
        random.setstate(self.random_state)

    def test_fast_ball_cannot_pass_through_a_brick(self):
        app = self.app
        app.bricks = [dict(x=0, y=100, color="#FFFFFF")]
        app.ready = False
        app.ball = [0, 60, 0, 1000]
        app.update(0.05)
        self.assertTrue(app.won)
        self.assertTrue(app.ended)
        self.assertEqual(app.score, 10)
        self.assertLess(app.ball[3], 0)

    def test_fast_ball_cannot_pass_through_paddle(self):
        app = self.app
        app.ready = False
        app.ball = [0, -180, 0, -1000]
        app.update(0.05)
        self.assertGreater(app.ball[3], 0)
        self.assertGreaterEqual(app.ball[1], app.PADDLE_Y + 8 + app.RADIUS)
        self.assertEqual(app.lives, 3)

    def test_paddle_edges_steer_ball_in_opposite_directions(self):
        for offset in (-40, 40):
            with self.subTest(offset=offset):
                app = self.app
                app.ball = [offset, -202, 0, -315]
                app.step(0.01)
                self.assertGreater(app.ball[2] * offset, 0)
                self.assertGreater(app.ball[3], 0)
                self.assertAlmostEqual(math.hypot(*app.ball[2:]), 315)

    def test_ball_reflects_from_wall_and_ceiling(self):
        app = self.app
        app.ball = [403, 216, 100, 100]
        app.step(0.025)
        self.assertLess(app.ball[2], 0)
        self.assertLess(app.ball[3], 0)
        self.assertLessEqual(app.ball[0], 411 - app.RADIUS)
        self.assertLessEqual(app.ball[1], 224 - app.RADIUS)

    def test_three_misses_end_game_and_reset_restores_bricks(self):
        app = self.app
        for expected_lives in (2, 1, 0):
            app.ready = False
            app.ball = [300, -268, 0, -300]
            app.update(0.025)
            self.assertEqual(app.lives, expected_lives)
            self.assertTrue(app.ready)
        self.assertTrue(app.ended)
        self.assertFalse(app.won)
        app.launch()
        self.assertTrue(app.ready)
        app.reset()
        self.assertFalse(app.ended)
        self.assertEqual((app.score, app.lives, len(app.bricks)), (0, 3, 40))

    def test_autoplay_completes_a_game_without_user_input(self):
        app = self.app
        app.toggle_auto()
        # Fixed simulated time, never a wall-clock benchmark or GUI timer.
        for _ in range(24000):
            app.update(0.025)
            if app.ended:
                break
        self.assertTrue(app.ended, "Autoplay did not finish in ten simulated minutes")
        self.assertTrue(app.won)
        self.assertEqual(app.score, 400)
        self.assertFalse(app.bricks)
        self.assertLessEqual(len(app.trail), 12)
        self.assertLessEqual(len(app.sparks), 160)


class StageAndPaintTests(unittest.TestCase):
    def setUp(self):
        self.stage = HeadlessStage("Test", "Controls")
        self.canvas = self.stage.canvas

    def test_unchanged_shapes_reuse_canvas_items_without_updates(self):
        painter = STAGE.Paint(self.stage, "test")
        for _ in range(3):
            painter.begin()
            painter.circle(10, 20, 3, "#FFFFFF")
            painter.end()
        self.assertEqual(len(self.canvas.items), 1)
        self.assertEqual(self.canvas.coordinate_updates, 0)
        self.assertEqual(self.canvas.option_updates, 0)

    def test_unused_items_hide_and_reappear_without_allocation(self):
        painter = STAGE.Paint(self.stage, "test")
        painter.begin()
        painter.circle(0, 0, 3, "#FFFFFF")
        painter.circle(10, 10, 4, "#FF0000")
        painter.end()
        ids = list(self.canvas.items)
        painter.begin()
        painter.circle(0, 0, 3, "#FFFFFF")
        painter.end()
        self.assertEqual(self.canvas.items[ids[1]]["options"]["state"], "hidden")
        painter.begin()
        painter.circle(0, 0, 3, "#FFFFFF")
        painter.circle(10, 10, 4, "#FF0000")
        painter.end()
        self.assertEqual(list(self.canvas.items), ids)
        self.assertEqual(self.canvas.items[ids[1]]["options"]["state"], "normal")

    def test_changing_shape_type_removes_the_old_item(self):
        painter = STAGE.Paint(self.stage, "test")
        painter.begin()
        painter.circle(0, 0, 3, "#FFFFFF")
        painter.end()
        original_id = next(iter(self.canvas.items))
        painter.begin()
        painter.text(0, 0, "Hello", "#FFFFFF")
        painter.end()
        self.assertNotIn(original_id, self.canvas.items)
        self.assertEqual(len(self.canvas.items), 1)
        self.assertEqual(next(iter(self.canvas.items.values()))["kind"], "text")

    def test_scaling_preserves_logical_coordinates_and_flips_canvas_y(self):
        painter = STAGE.Paint(self.stage, "test")
        self.stage.screen.width, self.stage.screen.height = 1000, 720
        painter.begin()
        painter.line([(10, 20), (30, -40)], "#FFFFFF", width=2)
        painter.end()
        item = next(iter(self.canvas.items.values()))
        self.assertEqual(item["coords"], (10, -20, 30, 40))
        self.stage.screen.width, self.stage.screen.height = 800, 576
        painter.begin()
        painter.line([(10, 20), (30, -40)], "#FFFFFF", width=2)
        painter.end()
        self.assertEqual(item["coords"], (8, -16, 24, 32))
        self.assertEqual(self.stage.event_point(SimpleNamespace(x=8, y=-16)), (10, 20))

    def test_hud_can_be_hidden_and_restored_with_cached_shapes(self):
        self.stage.hud("Running")
        ids = set(self.canvas.matching("hud"))
        self.stage.toggle_hud()
        self.stage.hud("Running")
        self.assertTrue(all(self.canvas.items[item]["options"]["state"] == "hidden" for item in ids))
        self.stage.toggle_hud()
        self.stage.hud("Running")
        self.assertEqual(set(self.canvas.matching("hud")), ids)
        self.assertTrue(all(self.canvas.items[item]["options"]["state"] == "normal" for item in ids))

    def test_tick_caps_elapsed_time_and_pause_still_renders(self):
        self.stage.frame = Mock()
        self.stage._last_time = 1
        with patch.object(STAGE.time, "perf_counter", side_effect=[3, 3.01]):
            self.stage.tick()
        self.stage.frame.assert_called_once_with(0.05)
        self.assertEqual(len(self.stage.screen.timers), 1)
        self.stage.toggle_pause()
        with patch.object(STAGE.time, "perf_counter", side_effect=[3.03, 3.04]):
            self.stage.tick()
        self.stage.frame.assert_called_with(0)
        self.assertEqual(self.stage.screen.update.call_count, 2)

    def test_close_is_idempotent_and_stops_scheduling(self):
        self.stage.frame = Mock()
        self.stage.close()
        self.stage.close()
        self.stage.tick()
        self.stage.screen.bye.assert_called_once()
        self.stage.frame.assert_not_called()
        self.assertFalse(self.stage.screen.timers)

    def test_color_interpolation_clamps_and_hue_wraps(self):
        self.assertEqual(STAGE.mix("#000000", "#FFFFFF", -1), "#000000")
        self.assertEqual(STAGE.mix("#000000", "#FFFFFF", 2), "#ffffff")
        self.assertEqual(STAGE.mix("#000000", "#FFFFFF", 0.5), "#808080")
        self.assertEqual(STAGE.hsv(0), STAGE.hsv(1))
        self.assertEqual(STAGE.hsv(-0.25), STAGE.hsv(0.75))


if __name__ == "__main__":
    unittest.main()
