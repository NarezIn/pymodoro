import pytest
from pomodoro.session import PomodoroSession

# note that, like in test_timer, we use fake functions like fake_tick() 
# in order to circumvent using actual real time

def test_init_sets_up_work_break_phase_and_cycles():
    session = PomodoroSession(25, 5)

    assert session.work_timer.duration == 25
    assert session.work_timer.remaining == 25
    assert session.break_timer.duration == 5
    assert session.break_timer.remaining == 5
    assert session.current_phase == "work"
    assert session.completed_cycles == 0

def test_init_with_invalid_work_duration_raises():
    with pytest.raises(ValueError):
        PomodoroSession(0, 5)

    with pytest.raises(ValueError):
        PomodoroSession(-1, 5)

    with pytest.raises(TypeError):
        PomodoroSession("25", 5)

def test_init_with_invalid_break_duration_raises():
    with pytest.raises(ValueError):
        PomodoroSession(25, 0)

    with pytest.raises(ValueError):
        PomodoroSession(25, -5)

    with pytest.raises(TypeError):
        PomodoroSession(25, "5")

def test_start_starts_work_timer_when_in_work_phase():
    session = PomodoroSession(25, 5)

    session.start()

    assert session.current_phase == "work"
    assert session.work_timer.status == "running"
    assert session.break_timer.status == "stopped"

def test_start_starts_break_timer_when_in_break_phase():
    session = PomodoroSession(25, 5)
    session.current_phase = "break"

    session.start()

    assert session.current_phase == "break"
    assert session.break_timer.status == "running"
    assert session.work_timer.status == "stopped"

def test_start_when_phase_none_starts_break_timer_due_to_current_code_behavior():
    session = PomodoroSession(25, 5)
    session.current_phase = None

    session.start()

    assert session.current_phase is None
    assert session.break_timer.status == "running"
    assert session.work_timer.status == "stopped"

def test_pause_pauses_work_timer_when_in_work_phase():
    session = PomodoroSession(25, 5)
    session.work_timer.start()

    session.pause()

    assert session.current_phase == "work"
    assert session.work_timer.status == "paused"
    assert session.break_timer.status == "stopped"

def test_pause_pauses_break_timer_when_in_break_phase():
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    session.break_timer.start()

    session.pause()

    assert session.current_phase == "break"
    assert session.break_timer.status == "paused"
    assert session.work_timer.status == "stopped"

def test_pause_when_phase_none_pauses_break_timer_due_to_current_code_behavior():
    session = PomodoroSession(25, 5)
    session.break_timer.start()
    session.current_phase = None

    session.pause()

    assert session.current_phase is None
    assert session.break_timer.status == "paused"
    assert session.work_timer.status == "stopped"

def test_reset_restores_both_timers_and_session_state():
    session = PomodoroSession(25, 5)
    session.work_timer.start()
    session.work_timer.remaining = 10
    session.break_timer.remaining = 2
    session.break_timer.status = "paused"
    session.current_phase = "break"
    session.completed_cycles = 3

    session.reset()

    assert session.work_timer.remaining == 25
    assert session.break_timer.remaining == 5
    assert session.work_timer.status == "stopped"
    assert session.break_timer.status == "stopped"
    assert session.current_phase == "work"
    assert session.completed_cycles == 0

def test_tick_returns_immediately_when_phase_is_none():
    session = PomodoroSession(25, 5)
    session.current_phase = None
    session.work_timer.remaining = 12
    session.break_timer.remaining = 3

    result = session.tick()

    assert result is None
    assert session.current_phase is None
    assert session.work_timer.remaining == 12
    assert session.break_timer.remaining == 3

def test_tick_in_work_phase_calls_work_timer_tick(monkeypatch):
    session = PomodoroSession(25, 5)
    called = {"work_tick": 0}

    def fake_tick():
        called["work_tick"] += 1

    monkeypatch.setattr(session.work_timer, "tick", fake_tick)

    session.tick()

    assert called["work_tick"] == 1
    assert session.current_phase == "work"
    assert session.completed_cycles == 0

def test_tick_in_break_phase_calls_break_timer_tick(monkeypatch):
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    called = {"break_tick": 0}

    def fake_tick():
        called["break_tick"] += 1

    monkeypatch.setattr(session.break_timer, "tick", fake_tick)

    session.tick()

    assert called["break_tick"] == 1
    assert session.current_phase == "break"
    assert session.completed_cycles == 0

def test_tick_in_work_phase_does_not_switch_if_remaining_above_zero(monkeypatch):
    session = PomodoroSession(25, 5)
    session.work_timer.remaining = 10

    def fake_tick():
        session.work_timer.remaining = 9

    monkeypatch.setattr(session.work_timer, "tick", fake_tick)

    session.tick()

    assert session.work_timer.remaining == 9
    assert session.current_phase == "work"
    assert session.completed_cycles == 0

def test_tick_in_work_phase_switches_to_break_if_remaining_reaches_zero(monkeypatch):
    session = PomodoroSession(25, 5)
    session.work_timer.remaining = 1

    def fake_tick():
        session.work_timer.remaining = 0

    monkeypatch.setattr(session.work_timer, "tick", fake_tick)

    session.tick()

    assert session.current_phase == "break"
    assert session.break_timer.status == "running"
    assert session.break_timer.remaining == session.break_timer.duration
    assert session.completed_cycles == 0

def test_tick_in_work_phase_switches_to_break_if_remaining_goes_negative(monkeypatch):
    session = PomodoroSession(25, 5)

    def fake_tick():
        session.work_timer.remaining = -1

    monkeypatch.setattr(session.work_timer, "tick", fake_tick)

    session.tick()

    assert session.current_phase == "break"
    assert session.break_timer.status == "running"
    assert session.completed_cycles == 0

def test_tick_in_break_phase_does_not_switch_if_remaining_above_zero(monkeypatch):
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    session.break_timer.remaining = 4

    def fake_tick():
        session.break_timer.remaining = 3

    monkeypatch.setattr(session.break_timer, "tick", fake_tick)

    session.tick()

    assert session.break_timer.remaining == 3
    assert session.current_phase == "break"
    assert session.completed_cycles == 0

def test_tick_in_break_phase_switches_to_work_if_remaining_reaches_zero(monkeypatch):
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    session.break_timer.remaining = 1

    def fake_tick():
        session.break_timer.remaining = 0

    monkeypatch.setattr(session.break_timer, "tick", fake_tick)

    session.tick()

    assert session.current_phase == "work"
    assert session.work_timer.status == "running"
    assert session.work_timer.remaining == session.work_timer.duration
    assert session.completed_cycles == 1

def test_tick_in_break_phase_switches_to_none_when_total_cycles_reached(monkeypatch):
    session = PomodoroSession(25, 5, total_cycles=2)
    session.current_phase = "break"
    session.completed_cycles = 1
    session.break_timer.remaining = 1

    def fake_tick():
        session.break_timer.remaining = 0

    monkeypatch.setattr(session.break_timer, "tick", fake_tick)

    session.tick()

    assert session.completed_cycles == 2
    assert session.current_phase is None
    assert session.work_timer.status == "stopped"

def test_tick_in_break_phase_switches_back_to_work_when_total_cycles_not_reached(monkeypatch):
    session = PomodoroSession(25, 5, total_cycles=2)
    session.current_phase = "break"
    session.completed_cycles = 0
    session.break_timer.remaining = 1

    def fake_tick():
        session.break_timer.remaining = 0

    monkeypatch.setattr(session.break_timer, "tick", fake_tick)

    session.tick()

    assert session.completed_cycles == 1
    assert session.current_phase == "work"
    assert session.work_timer.status == "running"

def test_switch_phase_from_work_goes_to_break_and_starts_break():
    session = PomodoroSession(25, 5)
    session.break_timer.remaining = 2
    session.break_timer.status = "paused"

    session.switch_phase()

    assert session.current_phase == "break"
    assert session.break_timer.remaining == 5
    assert session.break_timer.status == "running"
    assert session.completed_cycles == 0

def test_switch_phase_from_break_increments_cycles_and_goes_to_work():
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    session.completed_cycles = 0
    session.work_timer.remaining = 4
    session.work_timer.status = "paused"

    session.switch_phase()

    assert session.completed_cycles == 1
    assert session.current_phase == "work"
    assert session.work_timer.remaining == 25
    assert session.work_timer.status == "running"

def test_switch_phase_from_break_sets_phase_none_when_total_cycles_reached():
    session = PomodoroSession(25, 5, total_cycles=2)
    session.current_phase = "break"
    session.completed_cycles = 1

    session.switch_phase()

    assert session.completed_cycles == 2
    assert session.current_phase is None
    assert session.work_timer.status == "stopped"

def test_switch_phase_from_break_goes_to_work_when_total_cycles_not_reached():
    session = PomodoroSession(25, 5, total_cycles=3)
    session.current_phase = "break"
    session.completed_cycles = 1

    session.switch_phase()

    assert session.completed_cycles == 2
    assert session.current_phase == "work"
    assert session.work_timer.status == "running"

def test_switch_phase_from_break_with_total_cycles_zero_ends_immediately():
    session = PomodoroSession(25, 5, total_cycles=0)
    session.current_phase = "break"
    session.completed_cycles = 0

    session.switch_phase()

    assert session.completed_cycles == 1
    assert session.current_phase is None
    assert session.work_timer.status == "stopped"

def test_get_status_in_work_phase_returns_correct_dictionary():
    session = PomodoroSession(25, 5)
    session.work_timer.remaining = 17
    session.work_timer.status = "running"

    status = session.get_status()

    assert isinstance(status, dict)
    assert status["phase"] == "work"
    assert status["remaining_seconds"] == 17
    assert status["status"] == "running"
    assert status["total_seconds"] == 25
    assert status["completed_cycles"] == 0
    assert status["total_cycles"] == 4

def test_get_status_in_break_phase_returns_correct_dictionary():
    session = PomodoroSession(25, 5)
    session.current_phase = "break"
    session.break_timer.remaining = 3
    session.break_timer.status = "paused"

    status = session.get_status()

    assert isinstance(status, dict)
    assert status["phase"] == "break"
    assert status["remaining_seconds"] == 3
    assert status["status"] == "paused"
    assert status["total_seconds"] == 5
    assert status["completed_cycles"] == 0
    assert status["total_cycles"] == 4

def test_get_status_when_phase_none_returns_finished_state():
    session = PomodoroSession(25, 5)
    session.current_phase = None
    session.completed_cycles = 4

    status = session.get_status()

    assert isinstance(status, dict)
    assert status["phase"] is None
    assert status["remaining_seconds"] == 0
    assert status["status"] == "finished"
    assert status["completed_cycles"] == 4
    assert status["total_cycles"] == 4

def test_full_cycle_work_then_break_increments_completed_cycles_once(monkeypatch):
    session = PomodoroSession(25, 5)

    def fake_work_tick():
        session.work_timer.remaining = 0

    monkeypatch.setattr(session.work_timer, "tick", fake_work_tick)
    session.tick()

    assert session.current_phase == "break"
    assert session.completed_cycles == 0
    assert session.break_timer.status == "running"

    def fake_break_tick():
        session.break_timer.remaining = 0

    monkeypatch.setattr(session.break_timer, "tick", fake_break_tick)
    session.tick()

    assert session.current_phase == "work"
    assert session.completed_cycles == 1
    assert session.work_timer.status == "running"

def test_multiple_full_cycles_with_total_cycles_stops_session(monkeypatch):
    session = PomodoroSession(25, 5, total_cycles=2)

    def fake_work_done():
        session.work_timer.remaining = 0

    def fake_break_done():
        session.break_timer.remaining = 0

    monkeypatch.setattr(session.work_timer, "tick", fake_work_done)
    session.tick()

    assert session.current_phase == "break"
    assert session.completed_cycles == 0

    monkeypatch.setattr(session.break_timer, "tick", fake_break_done)
    session.tick()

    assert session.current_phase == "work"
    assert session.completed_cycles == 1

    monkeypatch.setattr(session.work_timer, "tick", fake_work_done)
    session.tick()

    assert session.current_phase == "break"
    assert session.completed_cycles == 1

    monkeypatch.setattr(session.break_timer, "tick", fake_break_done)
    session.tick()

    assert session.completed_cycles == 2
    assert session.current_phase is None

def test_reset_after_session_end_restores_initial_state():
    session = PomodoroSession(25, 5)
    session.current_phase = None
    session.completed_cycles = 4
    session.work_timer.remaining = 0
    session.break_timer.remaining = 0

    session.reset()

    assert session.current_phase == "work"
    assert session.completed_cycles == 0
    assert session.work_timer.remaining == 25
    assert session.break_timer.remaining == 5
    assert session.work_timer.status == "stopped"
    assert session.break_timer.status == "stopped"