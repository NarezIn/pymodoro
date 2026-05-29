"""
Background daemon that runs the Pomodoro timer.

Spawned by __main__.py, the daemon runs the session loop and writes state
to ~/.pymodoro/session.json. Notifications are delivered via the state
file and picked up by pymodoro --check-notify.
"""
import argparse
import os
import time

from pomodoro.session import PomodoroSession
from pomodoro.ipc import (
    write_session,
    read_command,
    clear_command,
    write_pid,
    remove_lock,
)


def run_daemon(
    work_duration: int,
    break_duration: int,
    total_cycles: int,
) -> None:
    """
    Run the Pomodoro daemon loop.

    Args:
        work_duration (int): work period duration in seconds.
        break_duration (int): break period duration in seconds.
        total_cycles (int): number of work/break cycles to complete.
    """
    session = PomodoroSession(work_duration, break_duration, total_cycles=total_cycles)
    write_pid(os.getpid())

    session.start()
    previous_phase = session.current_phase
    notification = None

    try:
        _run_loop(session, work_duration, break_duration, total_cycles, previous_phase, notification)
    except KeyboardInterrupt:
        pass
    finally:
        remove_lock()


def _run_loop(session, work_duration, break_duration, total_cycles, previous_phase, notification) -> None:
    while True:
        session.tick()
        status = session.get_status()
        current_phase = status["phase"]

        # Detect phase transitions and build notification for state file
        if current_phase != previous_phase:
            if previous_phase == "work" and current_phase == "break":
                cycle_num = status["completed_cycles"] + 1
                msg = f"Work session {cycle_num} complete! Time for a break."
                notification = {"text": msg, "type": "work_complete"}
            elif previous_phase == "break" and current_phase == "work":
                cycle_num = status["completed_cycles"]
                msg = f"Break session {cycle_num} complete! Back to work."
                notification = {"text": msg, "type": "break_complete"}
            elif current_phase is None:
                msg = "All cycles complete! Good work!"
                notification = {"text": msg, "type": "session_complete"}
            previous_phase = current_phase
        else:
            notification = None

        # Build and write state
        state = {
            "version": 1,
            "daemon_pid": os.getpid(),
            "config": {
                "work_duration_minutes": work_duration,
                "break_duration_minutes": break_duration,
                "total_cycles": total_cycles,
            },
            "session": status,
            "notification": notification,
        }
        write_session(state)

        # Check for commands
        command = read_command()
        if command:
            cmd = command.get("command", "")
            if cmd == "stop":
                clear_command()
                break
            clear_command()

        # Exit if session finished
        if current_phase is None:
            break

        try:
            time.sleep(1)
        except KeyboardInterrupt:
            # The daemon runs in the background; Ctrl+C from a different
            # foreground process (e.g. --show) must not kill it.
            pass


def main() -> None:
    """Parse arguments and launch the daemon."""
    parser = argparse.ArgumentParser(description="Run the Pomodoro daemon.")
    parser.add_argument("--work", type=int, required=True, help="Work duration in seconds")
    parser.add_argument("--break", type=int, required=True, dest="break_duration", help="Break duration in seconds")
    parser.add_argument("--cycles", type=int, required=True, help="Number of cycles")
    args = parser.parse_args()

    run_daemon(
        work_duration=args.work,
        break_duration=args.break_duration,
        total_cycles=args.cycles,
    )


if __name__ == "__main__":
    main()
