"""Recipe round trips, validation, and reproducible scene state without a display."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_demos import CATALOG, DEMOS, make_app, state
import 创作配方 as recipes


class RecipeTests(unittest.TestCase):
    def test_presets_fit_schema_and_match_scene_theme_names(self):
        for work_id, name in ((25, "StarryLily"), (26, "ParticleHeart")):
            with self.subTest(work=work_id):
                theme = next(spec for spec in recipes.parameter_specs(work_id) if spec.key == "theme")
                self.assertEqual(theme.choices, tuple(item[0] for item in DEMOS[name].THEMES))
                for index in range(len(recipes.PRESETS[work_id])):
                    values = recipes.preset_parameters(work_id, index)
                    self.assertEqual(values, recipes.validate_parameters(work_id, values))

    def test_saved_recipe_round_trips_and_rejects_other_work(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "creation.json"
            for work_id in (25, 26):
                for aspect in range(4):
                    with self.subTest(work=work_id, aspect=aspect):
                        values = recipes.preset_parameters(work_id, 1)
                        values.update(seed=1234567, aspect=aspect)
                        saved = recipes.save_recipe(path, work_id, values)
                        self.assertEqual(saved["version"], 1)
                        self.assertEqual(saved["scene_version"], 2)
                        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), saved)
                        self.assertEqual(recipes.load_recipe(path, work_id)["parameters"], values)
                        with self.assertRaises(ValueError):
                            recipes.load_recipe(path, 26 if work_id == 25 else 25)

    def test_legacy_examples_migrate_to_original_aspect_and_save_as_version_two(self):
        examples = Path(__file__).resolve().parents[1] / "examples" / "recipes"
        with tempfile.TemporaryDirectory() as folder:
            saved_path = Path(folder) / "migrated.json"
            for filename in ("25-blue-night.json", "26-champagne.json"):
                with self.subTest(recipe=filename):
                    path = examples / filename
                    before = path.read_bytes()
                    legacy = json.loads(before)
                    self.assertEqual(legacy["scene_version"], 1)
                    self.assertNotIn("aspect", legacy["parameters"])
                    migrated = recipes.load_recipe(path, legacy["work_id"])
                    self.assertEqual(migrated["scene_version"], 2)
                    self.assertEqual(migrated["parameters"], {"aspect": 0, **legacy["parameters"]})
                    recipes.save_recipe(saved_path, migrated["work_id"], migrated["parameters"])
                    self.assertEqual(recipes.load_recipe(saved_path), migrated)
                    self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8")), migrated)
                    self.assertEqual(path.read_bytes(), before)

    def test_legacy_recipe_requires_exact_old_schema_and_valid_values(self):
        examples = Path(__file__).resolve().parents[1] / "examples" / "recipes"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.json"
            for filename in ("25-blue-night.json", "26-champagne.json"):
                legacy = json.loads((examples / filename).read_text(encoding="utf-8"))
                values = legacy["parameters"]
                invalid = (None, [], {}, {key: value for key, value in values.items() if key != "seed"},
                           dict(values, unknown=1), dict(values, aspect=0), dict(values, aspect=2),
                           dict(values, seed=True), dict(values, theme=4), dict(values, seed=-1))
                for parameters in invalid:
                    with self.subTest(recipe=filename, parameters=parameters):
                        path.write_text(json.dumps({**legacy, "parameters": parameters}), encoding="utf-8")
                        with self.assertRaises(ValueError):
                            recipes.load_recipe(path)

    def test_version_two_requires_aspect_and_rejects_invalid_choices(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "aspect.json"
            for work_id in (25, 26):
                valid = recipes.make_recipe(work_id, recipes.default_parameters(work_id))
                valid["scene_version"] = 2
                values = dict(valid["parameters"], aspect=0)
                invalid = [{key: value for key, value in values.items() if key != "aspect"},
                           dict(values, unknown=1)]
                invalid.extend(dict(values, aspect=value) for value in (-1, 4, True, 1.0, None, "1"))
                for parameters in invalid:
                    with self.subTest(work=work_id, parameters=parameters):
                        path.write_text(json.dumps({**valid, "parameters": parameters}), encoding="utf-8")
                        with self.assertRaises(ValueError):
                            recipes.load_recipe(path)

    def test_invalid_parameters_never_mutate_the_scene(self):
        for name in ("StarryLily", "ParticleHeart"):
            app = make_app(name)
            app.frame(.05)
            original = state(app)
            for field, value in (("seed", True), ("seed", -1), ("seed", 2**32),
                                 ("theme", 7), ("theme", 1.2), ("seed", "hello")):
                values = app.get_parameters()
                values[field] = value
                with self.subTest(scene=name, field=field, value=value):
                    with self.assertRaises(ValueError):
                        app.apply_parameters(values)
                    self.assertEqual(state(app), original)
            rate = "speed" if app.WORK_ID == 25 else "rate"
            for value in (float("nan"), float("inf"), True, 10**400, 100000, -1):
                values = app.get_parameters()
                values[rate] = value
                with self.assertRaises(ValueError):
                    app.apply_parameters(values)
                self.assertEqual(state(app), original)
            for values in ({}, {**app.get_parameters(), "unknown": 1}):
                with self.assertRaises(ValueError):
                    app.apply_parameters(values)

    def test_unknown_versions_malformed_and_oversized_files_are_rejected(self):
        valid = recipes.make_recipe(25, recipes.default_parameters(25))
        invalid = ["not json", "[]", "{}", '{"format":1,"format":2}', "[" * 2000 + "0" + "]" * 2000,
                   " " * (recipes.MAX_RECIPE_BYTES + 1)]
        for field, value in (("version", 2), ("version", True), ("scene_version", 3),
                             ("scene_version", True), ("scene_version", 1.0), ("scene_version", 0),
                             ("work_id", 27), ("work_id", True), ("parameters", None)):
            invalid.append(json.dumps({**valid, field: value}))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            for text in invalid:
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    recipes.load_recipe(path)

    def test_failed_atomic_replace_preserves_previous_file_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "saved.json"
            recipes.save_recipe(path, 25, recipes.default_parameters(25))
            before = path.read_bytes()
            with patch.object(recipes.os, "replace", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    recipes.save_recipe(path, 25, recipes.preset_parameters(25, 1))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_catalog_registers_only_supported_creators_and_all_scene_entries(self):
        self.assertEqual({w["id"] for w in CATALOG.WORKS if w["creation"]}, set(recipes.SPECIFICATIONS))
        for work in CATALOG.WORKS:
            if work["collection"] == "interactive":
                self.assertIn(work["entry_class"], DEMOS)
            else:
                self.assertIsNone(work["entry_class"])


class CreationSceneTests(unittest.TestCase):
    def test_example_recipe_reopens_in_a_new_instance_with_same_state(self):
        folder = Path(__file__).resolve().parents[1] / "examples" / "recipes"
        for name, filename in (("StarryLily", "25-blue-night.json"), ("ParticleHeart", "26-champagne.json"),
                               ("StarryLily", "25-portrait-night.json"), ("ParticleHeart", "26-square-heart.json")):
            values = recipes.load_recipe(folder / filename)["parameters"]
            first = make_app(name)
            first.apply_parameters(values)
            first.reset()
            first.frame(.05)
            first.frame(.05)
            expected = state(first)
            first.stage.close()
            second = make_app(name)
            second.apply_parameters(values)
            self.assertEqual(second.get_parameters(), values, filename)
            second.reset()
            second.frame(.05)
            second.frame(.05)
            self.assertEqual(state(second), expected)

    def test_restart_preserves_recipe_and_reproduces_state_with_same_inputs(self):
        for name in ("StarryLily", "ParticleHeart"):
            with self.subTest(scene=name):
                app = make_app(name)
                values = recipes.preset_parameters(app.WORK_ID, 1)
                values["seed"] = 98765
                app.apply_parameters(values)
                app.reset()
                interaction = app.meteor if app.WORK_ID == 25 else app.burst
                for _ in range(2):
                    app.frame(.05)
                interaction(80, 50)
                app.frame(.025)
                expected = state(app)
                changed = dict(values, seed=6543)
                app.apply_parameters(changed)
                app.frame(.2)
                app.apply_parameters(values)
                app.reset()
                self.assertEqual(app.get_parameters(), values)
                app.frame(.05)
                app.frame(.05)
                interaction(80, 50)
                app.frame(.025)
                self.assertEqual(state(app), expected)

    def test_density_does_not_shuffle_unrelated_geometry(self):
        lily = make_app("StarryLily")
        flowers = copy.deepcopy(lily.florets)
        lily.apply_parameters(dict(lily.get_parameters(), star_count=40))
        self.assertEqual(lily.florets, flowers)
        self.assertEqual(len(lily.stars), 40)
        heart = make_app("ParticleHeart")
        stars = copy.deepcopy(heart.stars)
        heart.apply_parameters(dict(heart.get_parameters(), particle_count=240))
        self.assertEqual(heart.stars, stars)
        self.assertEqual(len(heart.particles), 240)

    def test_keyboard_changes_are_saved_in_recipe_snapshot(self):
        for name in ("StarryLily", "ParticleHeart"):
            app = make_app(name)
            before = app.get_parameters()
            app.change_theme()
            (app.change_speed if app.WORK_ID == 25 else app.change_rate)(.1)
            after = app.get_parameters()
            self.assertNotEqual(after, before)
            self.assertEqual(after["theme"], 1)
            after["seed"] = -100
            self.assertEqual(app.get_parameters()["seed"], before["seed"])

    def test_parameter_extremes_render_and_pool_plateaus_after_repeated_changes(self):
        for name in ("StarryLily", "ParticleHeart"):
            app = make_app(name)
            high, low = app.get_parameters(), app.get_parameters()
            for spec in recipes.parameter_specs(app.WORK_ID):
                if spec.kind in ("int", "float"):
                    high[spec.key] = int(spec.high) if spec.kind == "int" else spec.high
                    low[spec.key] = int(spec.low) if spec.kind == "int" else spec.low
            count = 0
            for cycle in range(3):
                for values in (high, low):
                    app.apply_parameters(values)
                    app.reset()
                    app.frame(30)
                current = len(app.stage.canvas.items)
                self.assertLess(current, 1700)
                if cycle:
                    self.assertLessEqual(current, count)
                count = current


if __name__ == "__main__":
    unittest.main()
