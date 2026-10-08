"""A single note board retains every original greeting and bounded interaction."""
import unittest
from unittest.mock import patch

from test_demos import HeadlessStage, state
from test_original_art import load_original


class OriginalNotesTests(unittest.TestCase):
    def app(self):
        module = load_original('弹窗.py')
        with patch.object(module, 'Stage', HeadlessStage):
            return module, module.KindNotes()

    def test_single_stage_entry_is_safe_to_import(self):
        with patch('tkinter.Tk', side_effect=AssertionError('Import opened a root')), \
                patch('tkinter.Toplevel', side_effect=AssertionError('Created a popup')):
            module = load_original('弹窗.py')
        self.assertTrue(hasattr(module, 'KindNotes'), 'Original notes need a single Stage entry')

    def test_every_original_message_remains_reachable(self):
        module, app = self.app()
        expected = {
            '今天天气怎么样', '今天的你也很辛苦', '期待我们下次见面', '在干吗', '别熬夜',
            '很高兴和你在一起', '愿所有梦想成真', '好好吃饭', '旦逢良辰，顺颂时宜',
            '见到你就很开心', '你笑起来真好看', '告诉你，我在想你', '时间都很珍贵',
            '你是今天的小幸运', '有好多事想对你说', '有你在就很安心', '你的努力很有用',
            '一切都会变好', '慢慢来', '今天也为你加油', '你已经很棒了', '小挫折而已',
            '累了就停下来', '你的坚持，终有所得', '每天进步一点点', '你值得温柔对待',
        }
        seen = {module.MESSAGES[i] for i in app.cards}
        for _ in range(13):
            app.next_group()
            app.frame(2)
            self.assertEqual(len(set(app.cards)), 6)
            seen.update(module.MESSAGES[i] for i in app.cards)
        self.assertEqual(seen, expected)
        for message in module.MESSAGES:
            lines = module.note_lines(message)
            self.assertEqual(''.join(lines), message)
            self.assertLessEqual(len(lines), 2)
            self.assertLessEqual(max(map(len, lines)), 7)

    def test_clicks_hit_visible_cards_after_resize_and_ignore_gaps(self):
        _, app = self.app()
        app.stage.screen.width, app.stage.screen.height = 760, 580
        app.frame(0)
        before = state(app)
        app.click(-150 * app.stage.scale, 100 * app.stage.scale)
        app.click(0, 270 * app.stage.scale)
        self.assertEqual(state(app), before)
        app.click(300 * app.stage.scale, -103 * app.stage.scale)
        self.assertEqual(app.selected, 5)
        self.assertEqual(app.ages[5], 0)
        self.assertTrue(all(age is None for age in app.ages[:5]))
        old = app.cards[:]
        app.frame(2)
        self.assertEqual(app.cards[:5], old[:5])
        self.assertNotEqual(app.cards[5], old[5])

    def test_pause_freezes_content_actions_and_zero_delta(self):
        _, app = self.app()
        app.next_group()
        app.frame(.2)
        app.stage.paused = True
        frozen = state(app)
        app.next_group()
        app.click(0, 112)
        app.change_selected()
        app.move_selection(1)
        app.frame(0)
        self.assertEqual(state(app), frozen)
        app.cycle_palette()
        self.assertEqual(app.palette, 1)
        self.assertEqual(app.cards, frozen['cards'])

    def test_animation_completes_and_keyboard_changes_only_selected_card(self):
        module, app = self.app()
        app.move_selection(-1)
        self.assertEqual(app.selected, 5)
        before = app.cards[:]
        app.change_selected()
        app.frame(module.TURN_SECONDS / 4)
        self.assertEqual(app.cards, before)
        self.assertGreater(app.card_lift(5), 0)
        app.frame(module.TURN_SECONDS)
        self.assertEqual(app.cards[:5], before[:5])
        self.assertNotEqual(app.cards[5], before[5])
        self.assertTrue(all(age is None for age in app.ages))
        self.assertEqual(app.card_lift(5), 0)
        self.assertTrue({'Left', 'Right', 'Return', 'c', 'n'} <= set(app.stage.screen.keys))

    def test_reset_restores_defaults_and_idle_cards_stay_cached(self):
        _, app = self.app()
        original = app.cards[:]
        app.next_group()
        app.frame(2)
        app.cycle_palette()
        app.reset()
        self.assertEqual(app.cards, original)
        self.assertEqual((app.palette, app.selected), (0, 0))
        app.frame(0)
        # A settled frame should not rewrite hundreds of Canvas coordinates.
        changes = app.stage.canvas.coordinate_updates, app.stage.canvas.option_updates
        ids = set(app.stage.canvas.items)
        for _ in range(20):
            app.frame(.05)
        self.assertEqual(set(app.stage.canvas.items), ids)
        self.assertEqual((app.stage.canvas.coordinate_updates, app.stage.canvas.option_updates), changes)

    def test_repeated_turns_palettes_and_resizes_keep_objects_bounded(self):
        _, app = self.app()
        counts = []
        for cycle in range(4):
            for _ in range(12):
                app.next_group()
                app.frame(.2)
                app.next_group()
                app.frame(2)
                app.move_selection(1)
                app.change_selected()
                app.frame(2)
            app.cycle_palette()
            app.stage.screen.width, app.stage.screen.height = ((760, 580) if cycle % 2 else (1100, 800))
            app.frame(0)
            counts.append(len(app.stage.canvas.items))
        self.assertLess(max(counts), 1100)
        self.assertLessEqual(counts[-1], counts[-2] + 6)


if __name__ == '__main__':
    unittest.main()
