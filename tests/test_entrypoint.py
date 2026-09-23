"""Check the public launcher and catalog without starting a desktop window."""

import builtins
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gallery_entrypoint_tests", ROOT / "run.py")
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.module_patch = patch.dict(sys.modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.catalog = ENTRY.catalog()

    def test_catalog_covers_twenty_four_distinct_existing_sources(self):
        works = self.catalog.WORKS
        self.assertEqual(len(works), 24)
        self.assertEqual({work["id"] for work in works}, set(range(1, 25)))
        self.assertEqual({int(work["number"]) for work in works}, set(range(1, 25)))
        self.assertEqual(len({work["filename"] for work in works}), 24)
        for work in works:
            with self.subTest(work=work["id"]):
                path = Path(work["filename"])
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertNotIn("\\", work["filename"], "Use portable forward slashes")
                self.assertTrue((ROOT / path).resolve().is_relative_to(ROOT))
                self.assertTrue((ROOT / path).is_file())
                self.assertEqual(path.suffix, ".py")
                for field in ("title", "collection"):
                    self.assertTrue(work[field].strip())

    def test_all_fourteen_original_creations_are_preserved_in_catalog(self):
        originals = {"2.py", "import turtle.py", "xin.py", "yeizi.py", "yusan.py",
                     "分形树.py", "哆啦A梦.py", "太极.py", "时钟.py", "风车.py",
                     "见缝插针.py", "下落的小球.py", "弹窗.py", "测试.py"}
        sources = {work["filename"] for work in self.catalog.WORKS}
        self.assertEqual(originals & sources, originals)
        gallery_sources = {name for name in sources if name.startswith("社团展示/")}
        self.assertEqual(len(gallery_sources), 10)

    def test_every_number_and_integer_id_resolves_to_its_work(self):
        for work in self.catalog.WORKS:
            for identifier in (str(work["number"]), str(int(work["number"])), work["id"]):
                with self.subTest(identifier=identifier):
                    self.assertEqual(self.catalog.get_work(identifier), work)

    def test_console_calculator_is_marked_for_terminal_execution(self):
        console_works = [work for work in self.catalog.WORKS if work["console"]]
        self.assertEqual(len(console_works), 1)
        self.assertEqual(console_works[0]["id"], 22)
        self.assertEqual(console_works[0]["filename"], "测试.py")
        self.assertEqual(console_works[0]["collection"], "original")

    def test_unknown_ids_and_paths_do_not_resolve(self):
        for identifier in ("", "00", "25", "-1", "no-such-work", "../舞台.py", "/tmp/demo.py"):
            with self.subTest(identifier=identifier):
                self.assertIsNone(self.catalog.get_work(identifier))


class EntrypointTests(unittest.TestCase):
    def setUp(self):
        # catalog() registers its import; restore global modules after every test.
        self.module_patch = patch.dict(sys.modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def test_list_prints_all_works_without_importing_graphics_or_executing(self):
        original_import = builtins.__import__

        def no_graphics(name, *args, **kwargs):
            if name in ("tkinter", "_tkinter", "turtle"):
                self.fail("--list should not import graphics modules")
            return original_import(name, *args, **kwargs)

        output = io.StringIO()
        with patch("builtins.__import__", side_effect=no_graphics), \
                patch.object(ENTRY, "execute") as execute, contextlib.redirect_stdout(output):
            result = ENTRY.main(["--list"])
        self.assertEqual(result, 0)
        execute.assert_not_called()
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 24)
        self.assertEqual({int(line.split()[0]) for line in lines}, set(range(1, 25)))
        self.assertIn("01_点击烟花.py", output.getvalue())
        self.assertIn("测试.py", output.getvalue())

    def test_demo_number_selects_its_source_and_returns_exit_status(self):
        with patch.object(ENTRY, "execute", return_value=7) as execute:
            result = ENTRY.main(["--demo", "01"])
        execute.assert_called_once_with(ROOT / "社团展示" / "01_点击烟花.py")
        self.assertEqual(result, 7)

    def test_no_arguments_selects_gallery(self):
        with patch.object(ENTRY, "execute", return_value=0) as execute:
            self.assertEqual(ENTRY.main([]), 0)
        execute.assert_called_once_with(ROOT / "社团展示" / "启动展示.py")

    def test_unknown_demo_has_actionable_parser_error(self):
        output = io.StringIO()
        with patch.object(ENTRY, "execute") as execute, contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit) as failure:
                ENTRY.main(["--demo", "does-not-exist"])
        self.assertEqual(failure.exception.code, 2)
        execute.assert_not_called()
        self.assertIn("Unknown work", output.getvalue())
        self.assertIn("--list", output.getvalue())

    def test_check_checks_sources_without_opening_a_window(self):
        output = io.StringIO()
        with patch("tkinter.Tk", side_effect=AssertionError("--check opened a Tk window")), \
                patch.object(ENTRY, "execute") as execute, contextlib.redirect_stdout(output):
            result = ENTRY.main(["--check"])
        self.assertEqual(result, 0)
        execute.assert_not_called()
        self.assertIn("24 works", output.getvalue())
        self.assertIn("Python", output.getvalue())

    def test_check_reports_missing_source_with_failure_exit_status(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = ENTRY.environment_check([{"filename": "missing-work-for-test.py"}])
        self.assertEqual(result, 1)
        self.assertIn("Missing source", stderr.getvalue())
        self.assertIn("missing-work-for-test.py", stderr.getvalue())

    def test_check_reports_missing_tk_without_a_traceback(self):
        original_import = builtins.__import__

        def missing_tk(name, *args, **kwargs):
            if name == "tkinter":
                raise ModuleNotFoundError("No module named 'tkinter'", name="tkinter")
            return original_import(name, *args, **kwargs)

        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("builtins.__import__", side_effect=missing_tk), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = ENTRY.environment_check([])
        self.assertEqual(result, 1)
        self.assertIn("Tkinter is missing", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
