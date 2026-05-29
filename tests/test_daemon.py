"""
Tests for the daemon module — core loop logic and notification generation.
"""
import time
from pathlib import Path

import pytest

from pomodoro.daemon import run_daemon


class FakeTimer:
    """A controllable fake timer for testing the daemon loop."""

    def __init__(self, duration: int):
        self.duration = duration
        self.remaining = duration
        self.status = "stopped"

    def start(self):
        self.status = "running"

    def tick(self):
        if self.status == "running" and self.remaining > 0:
            self.remaining -= 1
        return self.remaining

    def reset(self):
        self.remaining = self.duration
        self.status = "stopped"

    def get_display_time(self):
        mins, secs = divmod(self.remaining, 60)
        return f"{mins:02d}:{secs:02d}"


class FakeSession:
    """
    A controllable session that simulates exact phase transitions.
    It cycles work→break→work→break... and sets phase=None after
    total_cycles completions.
    """

    def __init__(self, work_duration: int, break_duration: int, total_cycles: int = 4):
        self.work_timer = FakeTimer(work_duration)
        self.break_timer = FakeTimer(break_duration)
        self.current_phase = "work"
        self.completed_cycles = 0
        self.total_cycles = total_cycles

    def start(self):
        self.work_timer.start()

    def tick(self):
        if self.current_phase is None:
            return

        active = self.work_timer if self.current_phase == "work" else self.break_timer
        active.tick()

        if active.remaining <= 0:
            self._switch_phase()

    def _switch_phase(self):
        if self.current_phase == "work":
            self.current_phase = "break"
            self.break_timer.reset()
            self.break_timer.start()
        else:
            self.completed_cycles += 1
            if self.completed_cycles >= self.total_cycles:
                self.current_phase = None
            else:
                self.current_phase = "work"
                self.work_timer.reset()
                self.work_timer.start()

    def get_status(self):
        if self.current_phase is None:
            return {
                "phase": None,
                "remaining_seconds": 0,
                "total_seconds": 0,
                "display_time": "00:00",
                "status": "finished",
                "completed_cycles": self.completed_cycles,
                "total_cycles": self.total_cycles,
            }
        active = self.work_timer if self.current_phase == "work" else self.break_timer
        return {
            "phase": self.current_phase,
            "remaining_seconds": active.remaining,
            "total_seconds": active.duration,
            "display_time": active.get_display_time(),
            "status": active.status,
            "completed_cycles": self.completed_cycles,
            "total_cycles": self.total_cycles,
        }


class TestDaemonLoop:
    """Tests for the daemon core loop using a fake session."""

    @pytest.fixture
    def tmp_ipc(self, monkeypatch, tmp_path):
        """Redirect IPC paths to tmp_path."""
        monkeypatch.setattr("pomodoro.daemon.write_session", lambda s: None)
        monkeypatch.setattr("pomodoro.daemon.write_pid", lambda p: None)
        monkeypatch.setattr("pomodoro.daemon.remove_lock", lambda: None)
        monkeypatch.setattr("pomodoro.ipc.write_session", lambda s: None)
        monkeypatch.setattr("pomodoro.ipc.write_pid", lambda p: None)
        monkeypatch.setattr("pomodoro.ipc.remove_lock", lambda: None)
        monkeypatch.setattr("pomodoro.ipc.DATA_DIR", Path(tmp_path))
        monkeypatch.setattr("pomodoro.ipc.SESSION_FILE", Path(tmp_path) / "session.json")
        monkeypatch.setattr("pomodoro.ipc.COMMAND_FILE", Path(tmp_path) / "command.json")
        monkeypatch.setattr("pomodoro.ipc.LOCK_FILE", Path(tmp_path) / "daemon.lock")
        return tmp_path

    def test_run_daemon_writes_initial_state(self, monkeypatch, tmp_ipc):
        """The daemon should write state immediately on first iteration."""
        captured_states = []

        def capture_write(state):
            captured_states.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", capture_write)

        class InstantSession(FakeSession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.current_phase = None  # Already finished

        monkeypatch.setattr("pomodoro.daemon.PomodoroSession", lambda w, b, total_cycles: InstantSession(w, b, total_cycles))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        assert len(captured_states) >= 1
        final_state = captured_states[-1]
        assert final_state["session"]["phase"] is None
        assert final_state["config"]["work_duration_minutes"] == 25

    def test_run_daemon_detects_work_to_break_transition(self, monkeypatch, tmp_ipc):
        """Notification is written to state file when work phase transitions to break."""
        captured_states = []

        def capture_write(state):
            captured_states.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", capture_write)

        class TransitionSession(FakeSession):
            call_count = 0
            def tick(self):
                TransitionSession.call_count += 1
                if TransitionSession.call_count == 1:
                    self.work_timer.remaining = 0
                    self._switch_phase()  # work → break
                elif TransitionSession.call_count == 2:
                    self.current_phase = None  # finish after one cycle

        monkeypatch.setattr("pomodoro.daemon.PomodoroSession", lambda w, b, total_cycles: TransitionSession(w, b, total_cycles))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        notifications = [s["notification"] for s in captured_states if s.get("notification")]
        assert len(notifications) >= 1
        assert "Work" in notifications[0]["text"]

    def test_run_daemon_session_completion_notification(self, monkeypatch, tmp_ipc):
        """Completion notification is written to state file when session finishes."""
        captured_states = []

        def capture_write(state):
            captured_states.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", capture_write)

        class CompletionSession(FakeSession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.current_phase = "break"  # transition from break → None triggers notification
                self.completed_cycles = self.total_cycles - 1

            def tick(self):
                self.current_phase = None

        monkeypatch.setattr("pomodoro.daemon.PomodoroSession", lambda w, b, total_cycles: CompletionSession(w, b, total_cycles))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        notifications = [s["notification"] for s in captured_states if s.get("notification")]
        assert any("Good work" in n["text"] for n in notifications)

    def test_run_daemon_processes_stop_command(self, monkeypatch, tmp_ipc):
        """Daemon exits when it reads a stop command."""
        iterations = []

        def record_iteration(state):
            iterations.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", record_iteration)

        call_count = [0]

        def command_sequence():
            call_count[0] += 1
            if call_count[0] >= 2:
                return {"command": "stop"}
            return None

        monkeypatch.setattr("pomodoro.daemon.read_command", command_sequence)
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        assert len(iterations) <= 3, f"Expected <= 3 iterations before stop, got {len(iterations)}"


class TestNotifications:
    """Tests for notification text generation in the state file."""

    def test_notification_text_work_to_break(self, monkeypatch):
        """Work→break transition generates correct notification in state."""
        captured_states = []

        def capture_write(state):
            captured_states.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", capture_write)

        class SingleTransitionSession(FakeSession):
            call_count = 0
            def tick(self):
                SingleTransitionSession.call_count += 1
                if SingleTransitionSession.call_count == 1:
                    self.work_timer.remaining = 0
                    self._switch_phase()
                elif SingleTransitionSession.call_count == 2:
                    self.current_phase = None

        monkeypatch.setattr("pomodoro.daemon.PomodoroSession", lambda w, b, total_cycles: SingleTransitionSession(w, b, total_cycles))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        notifications = [s["notification"] for s in captured_states if s.get("notification")]
        assert len(notifications) >= 1
        assert "Work session 1 complete" in notifications[0]["text"]
        assert "break" in notifications[0]["text"].lower()

    def test_notification_text_break_to_work(self, monkeypatch):
        """Break→work transition generates correct notification in state."""
        captured_states = []

        def capture_write(state):
            captured_states.append(state)

        monkeypatch.setattr("pomodoro.daemon.write_session", capture_write)

        class BreakToWorkSession(FakeSession):
            call_count = 0
            def tick(self):
                BreakToWorkSession.call_count += 1
                if BreakToWorkSession.call_count == 1:
                    self.work_timer.remaining = 0
                    self._switch_phase()  # work→break
                elif BreakToWorkSession.call_count == 2:
                    self.break_timer.remaining = 0
                    self._switch_phase()  # break→work
                elif BreakToWorkSession.call_count == 3:
                    self.current_phase = None  # done

        monkeypatch.setattr("pomodoro.daemon.PomodoroSession", lambda w, b, total_cycles: BreakToWorkSession(w, b, total_cycles))
        monkeypatch.setattr(time, "sleep", lambda s: None)

        run_daemon(25, 5, 4)

        notifications = [s["notification"] for s in captured_states if s.get("notification")]
        break_msgs = [n for n in notifications if "Break" in n["text"]]
        assert len(break_msgs) >= 1
        assert "back to work" in break_msgs[0]["text"].lower()
