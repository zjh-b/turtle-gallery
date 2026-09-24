"""Tour timing and process handover without opening desktop windows."""
import importlib
import io
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import unittest
from unittest.mock import Mock, patch

GALLERY = Path(__file__).resolve().parents[1] / "社团展示"
sys.path.insert(0, str(GALLERY))


class TourTests(unittest.TestCase):
    def setUp(self):
        self.tour = importlib.import_module("巡展")

    def test_timer_pauses_on_activity_and_resume_grants_full_duration(self):
        now = [100.0]
        clock = self.tour.TourClock(30, now=lambda: now[0])
        now[0] = 120
        self.assertEqual(clock.remaining, 10)
        clock.pause()
        now[0] = 999
        self.assertFalse(clock.expired)
        clock.resume()
        self.assertEqual(clock.remaining, 30)
        now[0] = 1028.99
        self.assertFalse(clock.expired)
        now[0] = 1029
        self.assertTrue(clock.expired)

    def test_playlist_preserves_order_and_rejects_unsupported_works(self):
        catalog = importlib.import_module("作品目录")
        self.assertEqual([w["id"] for w in self.tour.parse_playlist("27,25,26", catalog.WORKS)], [27, 25, 26])
        for value in ("", "25,", "25,28", "1", "unknown", "25,25"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.tour.parse_playlist(value, catalog.WORKS)
        for seconds in (0, 9, 601, "bad", 10.5, True):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.tour.validate_seconds(seconds)

    def session(self):
        stage = Mock()
        stage.closed = False
        stage.paused = False
        stage.creator_panel = None
        output = io.StringIO()
        session = self.tour.TourSession(stage, {"duration": 30, "index": 1, "count": 3},
                                        input_stream=None, output_stream=output)
        stage.close.side_effect = session.close
        return session, stage, output

    def test_next_and_user_close_have_distinct_protocol_events(self):
        session, stage, output = self.session()
        session.next()
        messages = [json.loads(line.removeprefix(self.tour.PREFIX)) for line in output.getvalue().splitlines()]
        self.assertEqual([event["state"] for event in messages], ["ready", "next", "closed"])
        self.assertEqual(messages[-1]["reason"], "next")
        session, stage, output = self.session()
        session.close()
        self.assertNotIn('"state": "next"', output.getvalue())
        self.assertIn('"reason": "closed"', output.getvalue())
        stage.close.assert_not_called()

    def test_keyboard_input_pauses_tour_without_pausing_animation(self):
        session, stage, output = self.session()
        event = Mock(keysym="c", serial=20)
        event.widget.winfo_class.return_value = "Canvas"
        event.widget.winfo_toplevel.return_value = stage.root
        session.key(event)
        self.assertTrue(session.clock.paused)
        self.assertFalse(stage.paused)
        event.keysym = "p"
        session.key(event)
        self.assertFalse(session.clock.paused)
        event.widget.winfo_class.return_value = "Entry"
        session.key(event)
        self.assertTrue(session.clock.paused)

    def test_creation_window_shortcuts_only_pause_switching(self):
        session, stage, output = self.session()
        event = Mock(keysym="Escape", serial=30)
        event.widget.winfo_class.return_value = "Entry"
        event.widget.winfo_toplevel.return_value = Mock()
        session.key(event)
        self.assertTrue(session.clock.paused)
        stage.close.assert_not_called()

    def test_canvas_end_button_defers_destroy_until_item_event_finishes(self):
        session, stage, output = self.session()
        stage.view = (1000, 720)
        session.paint = Mock()
        session.paint.text.side_effect = range(4)
        deferred = []
        stage.root.after_idle.side_effect = deferred.append
        session.draw()
        end_handler = stage.canvas.tag_bind.call_args_list[-1].args[2]
        self.assertEqual(end_handler(Mock(serial=100)), "break")
        self.assertFalse(session.closed, "Destroying during Canvas item dispatch crashes Windows Tk")
        self.assertEqual(len(deferred), 1)
        deferred[0]()
        self.assertTrue(session.closed)

    def test_parent_commands_and_eof_are_processed_only_by_tick(self):
        session, stage, output = self.session()
        self.tour.TourSession.read_commands(io.StringIO('{"command":"pause"}\n'), session.commands)
        stage.close.assert_not_called()
        session.tick()
        self.assertTrue(session.clock.paused)
        self.assertTrue(session.closed)
        self.assertIn('"reason": "parent_closed"', output.getvalue())


class LauncherTourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module("启动展示")

    def launcher(self, code=0, reader_alive=False):
        launcher = self.module.Launcher.__new__(self.module.Launcher)
        launcher.root = Mock()
        launcher.status = Mock()
        launcher.stop_button = Mock()
        launcher.tour_pause_button = Mock()
        launcher.tour_next_button = Mock()
        launcher.tour_start_button = Mock()
        launcher.tour_order = Mock()
        launcher.tour_seconds = Mock()
        launcher.console = None
        launcher.watch_job = None
        launcher.resize_job = None
        launcher.output = queue.Queue()
        launcher.output_tail = ""
        launcher.protocol_buffer = ""
        launcher.stopping = False
        launcher.stop_deadline = None
        launcher.closing = False
        launcher.tour_works = [self.module.get_work(25), self.module.get_work(26), self.module.get_work(27)]
        launcher.tour_active = True
        launcher.tour_index = 0
        launcher.tour_duration = 30
        launcher.tour_paused = False
        launcher.tour_ready = True
        launcher.tour_next_requested = False
        launcher.start_deadline = None
        launcher.active_work = launcher.tour_works[0]
        launcher.child = Mock(returncode=code)
        launcher.child.poll.return_value = code
        launcher.reader = Mock()
        launcher.reader.is_alive.return_value = reader_alive
        launcher.launch = Mock()
        return launcher

    def test_split_protocol_line_does_not_advance_until_exit_and_reader_finish(self):
        launcher = self.launcher(code=None)
        launcher.output.put('TG_TOUR:{"state": "ne')
        launcher.watch()
        self.assertFalse(launcher.tour_next_requested)
        launcher.output.put('xt"}\n')
        launcher.watch()
        self.assertTrue(launcher.tour_next_requested)
        launcher.launch.assert_not_called()
        launcher.child.poll.return_value = 0
        launcher.child.returncode = 0
        launcher.reader.is_alive.return_value = True
        launcher.watch()
        launcher.launch.assert_not_called()
        launcher.reader.is_alive.return_value = False
        launcher.watch()
        self.assertIsNone(launcher.child)
        self.assertEqual(launcher.tour_index, 1)
        launcher.launch.assert_called_once_with(launcher.tour_works[1], touring=True)

    def test_window_close_and_crash_stop_tour_even_after_next_message(self):
        for code, protocol in ((0, ''), (1, 'TG_TOUR:{"state":"next"}\n')):
            with self.subTest(code=code):
                launcher = self.launcher(code)
                launcher.output.put(protocol)
                with patch.object(self.module.messagebox, "showerror"):
                    launcher.watch()
                self.assertFalse(launcher.tour_active)
                launcher.launch.assert_not_called()

    def test_last_work_loops_to_first(self):
        launcher = self.launcher()
        launcher.tour_index = 2
        launcher.output.put('TG_TOUR:{"state":"next"}\n')
        launcher.watch()
        self.assertEqual(launcher.tour_index, 0)
        launcher.launch.assert_called_once_with(launcher.tour_works[0], touring=True)

    def test_exit_during_watch_keeps_process_until_final_reader_messages_arrive(self):
        launcher = self.launcher(code=None, reader_alive=True)
        child = launcher.child
        child.poll.side_effect = [None, 0, 0]
        child.returncode = 0
        launcher.watch()
        self.assertIs(launcher.child, child)
        launcher.launch.assert_not_called()
        launcher.output.put('TG_TOUR:{"state":"next"}\nTG_TOUR:{"state":"closed","reason":"next"}\n')
        launcher.watch()
        self.assertIs(launcher.child, child)
        launcher.reader.is_alive.return_value = False
        launcher.watch()
        self.assertEqual(launcher.tour_index, 1)
        launcher.launch.assert_called_once_with(launcher.tour_works[1], touring=True)

    def test_spinbox_typing_does_not_launch_work_or_change_page(self):
        launcher = self.launcher()
        launcher.displayed = launcher.tour_works
        launcher.change_page = Mock()
        # isinstance needs only the widget identity; no Tcl window is required.
        event = Mock(widget=self.module.tk.Spinbox.__new__(self.module.tk.Spinbox))
        launcher.shortcut(event, 0)
        launcher.page_shortcut(event, 1)
        launcher.launch.assert_not_called()
        launcher.change_page.assert_not_called()

    def test_read_output_closes_stream_even_on_failure(self):
        stream = io.StringIO("final output")
        output = queue.Queue()
        self.module.Launcher.read_output(stream, output)
        self.assertTrue(stream.closed)
        self.assertEqual("".join(output.queue), "final output")

    def test_launch_failure_stops_tour_and_allows_retry(self):
        launcher = self.launcher()
        launcher.child = launcher.active_work = None
        del launcher.launch
        with patch.object(self.module.subprocess, "Popen", side_effect=OSError("cannot start")), \
                patch.object(self.module.messagebox, "showerror"):
            launcher.launch(launcher.tour_works[0], touring=True)
        self.assertFalse(launcher.tour_active)
        self.assertIsNone(launcher.child)

    def test_launcher_never_opens_second_process_while_first_runs(self):
        launcher = self.launcher(code=None)
        first = launcher.child
        del launcher.launch
        with patch.object(self.module.subprocess, "Popen") as open_child:
            launcher.launch(launcher.tour_works[1], touring=True)
        self.assertIs(launcher.child, first)
        open_child.assert_not_called()

    def test_shutdown_kills_unresponsive_process_and_tolerates_closed_pipe(self):
        launcher = self.launcher(code=None)
        child = launcher.child
        child.wait.side_effect = [subprocess.TimeoutExpired("work", 2), 0]
        child.stdin.close.side_effect = BrokenPipeError()
        launcher.reap_child()
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_count, 2)
        launcher.reader.join.assert_called_once()

    def test_close_reaps_real_subprocess_and_reader(self):
        launcher = self.launcher()
        launcher.child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          text=True, encoding="utf-8")
        child = launcher.child
        launcher.reader = threading.Thread(target=launcher.read_output, args=(child.stdout, launcher.output))
        reader = launcher.reader
        reader.start()
        try:
            launcher.close()
            self.assertIsNotNone(child.poll())
            self.assertFalse(reader.is_alive())
            self.assertTrue(child.stdin.closed)
            self.assertTrue(child.stdout.closed)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
