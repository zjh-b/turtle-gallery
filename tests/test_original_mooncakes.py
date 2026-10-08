"""Mooncake arithmetic is shared by the bounded gallery and text interface."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class MooncakePackingTests(unittest.TestCase):
    def app(self):
        module = load_original('测试.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return module, module.MooncakePacking()

    def test_integer_packing_handles_empty_large_and_exact_batches(self):
        module, _ = self.app()
        for total, capacity, expected in ((26, 6, (4, 2)), (0, 6, (0, 0)),
                                         (18, 6, (3, 0)), (5, 99, (0, 5)),
                                         (999999, 99, (10101, 0)),
                                         (999999, 1, (999999, 0))):
            with self.subTest(total=total, capacity=capacity):
                self.assertEqual(module.packing(total, capacity), expected)
        for total, capacity in ((-1, 6), (1000000, 6), (3, 0), (3, 100),
                                (2.5, 6), (True, 6), (3, False)):
            with self.subTest(total=total, capacity=capacity):
                with self.assertRaises(ValueError):
                    module.packing(total, capacity)
        for text in ('9' * 5000, '1_000', '+3', '3.0'):
            with self.assertRaises(ValueError):
                module.parse_number(text, 'total')
        self.assertEqual(module.parse_number('0' * 5000, 'total'), 0)

    def test_cancel_and_invalid_modal_input_preserve_numbers_and_restore_keys(self):
        _, app = self.app()
        app.stage.screen.textinput = Mock(return_value=None)
        app.stage.screen.listen = Mock()
        before = state(app)
        app.edit('total')
        self.assertEqual(state(app), before)
        self.assertEqual(app.stage.screen.listen.call_count, 1)
        for value in ('bad', '-1', '1000000', '2.5'):
            app.stage.screen.textinput.return_value = value
            app.edit('total')
            self.assertEqual((app.total, app.capacity), (26, 6))
            self.assertTrue(app.message)
        app.stage.screen.textinput.return_value = '0'
        app.edit('capacity')
        self.assertEqual(app.capacity, 6)
        app.stage.screen.textinput.return_value = '999999'
        app.edit('total')
        self.assertEqual(app.total, 999999)
        app.stage.screen.textinput.side_effect = KeyboardInterrupt
        app.edit('capacity')
        self.assertEqual(app.capacity, 6)
        self.assertEqual(app.stage.screen.listen.call_count, 8)

    def test_closing_the_parent_during_input_does_not_focus_a_destroyed_window(self):
        _, app = self.app()

        def close_parent(*args):
            app.stage.closed = True
            return None

        app.stage.screen.textinput = Mock(side_effect=close_parent)
        app.stage.screen.listen = Mock(side_effect=AssertionError('Focused a destroyed window'))
        app.edit('total')
        self.assertEqual((app.total, app.capacity), (26, 6))
        app.stage.screen.listen.assert_not_called()

    def test_animation_completes_and_paused_actions_leave_the_model_unchanged(self):
        _, app = self.app()
        app.replay()
        self.assertEqual(app.progress, 0)
        app.frame(0)
        initial = sum(item['options'].get('state') != 'hidden' for item in app.stage.canvas.items.values())
        app.frame(.5)
        self.assertTrue(0 < app.progress < 1)
        app.stage.paused = True
        before = state(app)
        app.replay()
        app.next_example()
        app.adjust('total', 1)
        app.edit('capacity')
        app.click(-70, 190)
        app.frame(0)
        self.assertEqual(state(app), before)
        app.stage.paused = False
        app.frame(30)
        self.assertEqual(app.progress, 1)
        complete = sum(item['options'].get('state') != 'hidden' for item in app.stage.canvas.items.values())
        self.assertGreater(complete, initial)

    def test_scaled_parameter_click_changes_the_visible_number(self):
        _, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.stage.screen.textinput = Mock(side_effect=['30', '7'])
        app.click(-70 * app.stage.scale, 190 * app.stage.scale)
        app.click(200 * app.stage.scale, 190 * app.stage.scale)
        self.assertEqual((app.total, app.capacity), (30, 7))

    def test_large_batches_only_draw_a_bounded_explicit_sample(self):
        _, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        for total, capacity in ((26, 6), (999999, 1), (999998, 99), (0, 1), (98, 99)):
            app.set_values(total, capacity)
            app.frame(.1)
            self.assertLess(len(app.stage.canvas.items), 1100)
            text = ' '.join(item['options'].get('text', '') for item in app.stage.canvas.items.values()
                            if item['options'].get('state') != 'hidden')
            self.assertIn('示意', text)
            self.assertIn(f'{total:,}', text)
            for _ in range(3):
                app.cycle_palette()
                app.frame(.1)
        app.set_values(999999, 99)
        app.adjust('total', 1)
        app.adjust('capacity', 1)
        self.assertEqual((app.total, app.capacity), (999999, 99))
        app.set_values(0, 1)
        app.adjust('total', -1)
        app.adjust('capacity', -1)
        self.assertEqual((app.total, app.capacity), (0, 1))

    def console(self, input_text):
        path = Path(__file__).resolve().parents[1] / '测试.py'
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        return subprocess.run([sys.executable, str(path), '--console'], input=input_text,
                              capture_output=True, text=True, encoding='utf-8', env=env, timeout=10)

    def test_console_reprompts_invalid_fields_and_reuses_exact_math(self):
        result = self.console('\nno\n-2\n26\n0\n6\nq\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('4个包装盒', result.stdout)
        self.assertIn('还有2个', result.stdout)
        self.assertIn('整数', result.stdout)
        self.assertFalse(result.stderr)

    def test_console_quit_or_eof_at_every_prompt_exits_cleanly(self):
        for data in ('q\n', '\nq\n', '\n26\nq\n', '', '\n', '\n26\n'):
            with self.subTest(data=data):
                result = self.console(data)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(result.stderr)

    def test_console_interrupt_at_any_prompt_is_a_clean_exit(self):
        module, _ = self.app()
        for inputs in ([KeyboardInterrupt], ['', KeyboardInterrupt], ['', '26', KeyboardInterrupt]):
            with patch('builtins.input', side_effect=inputs), redirect_stdout(io.StringIO()):
                self.assertEqual(module.console_main(), 0)


if __name__ == '__main__':
    unittest.main()
