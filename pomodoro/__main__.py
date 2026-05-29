"""
Entry point for the pymodoro CLI.

Run without arguments to start an interactive Pomodoro session that runs
in the background, leaving your terminal free for other tasks.
"""
import argparse
import subprocess
import sys

# Ensure emoji characters in progress bars render correctly on Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

from pomodoro.ipc import (
    DATA_DIR,
    ensure_data_dir,
    read_session,
    write_command,
    is_daemon_running,
)
from pomodoro.storage import Storage
from pomodoro.tui import show_timer_history

VERSION = "1.1.0"

INTRO_TEXT = """
The Pomodoro Technique is a time management method that splits work into
focused sessions, each with a work period and a rest period. This tool
runs a Pomodoro timer in the background so you can keep using your
terminal while the timer counts down.

You can customize work/break durations when prompted. For more options,
type: pymodoro --help
"""


def interactive_mode() -> None:
    """Run the interactive setup flow and spawn a daemon."""
    print(INTRO_TEXT)

    # Check for existing daemon
    if is_daemon_running():
        state = read_session()
        if state and state["session"].get("phase") is not None:
            print("A Pomodoro session is already running!")
            print("  Use pymodoro --show to view it")
            print("  Use pymodoro --stop to stop it")
            return

    # Prompt for durations
    try:
        work_input = input("Work duration in seconds [default 25]: ").strip()
        work_duration = int(work_input) if work_input else 25

        break_input = input("Break duration in seconds [default 5]: ").strip()
        break_duration = int(break_input) if break_input else 5

        cycles_input = input("Number of cycles [default 4]: ").strip()
        cycles = int(cycles_input) if cycles_input else 4
    except ValueError:
        print("Invalid input. Please enter a number.")
        return
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if work_duration <= 0 or break_duration <= 0 or cycles <= 0:
        print("Durations and cycles must be positive numbers.")
        return

    print(f"\nStarting Pomodoro: {work_duration}s work / {break_duration}s break, {cycles} cycles")

    # Save timer preset
    storage = Storage()
    timer_id = storage.create_timer(work_duration)
    print(f"Timer preset saved with ID: {timer_id}")

    # Spawn daemon in its own process group so terminal signals
    # (e.g. Ctrl+C in --show) do not propagate to it.
    popen_kwargs: dict = {"stdin": subprocess.DEVNULL}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        popen_kwargs["start_new_session"] = True

    ensure_data_dir()
    subprocess.Popen(
        [sys.executable, "-m", "pomodoro.daemon",
         "--work", str(work_duration),
         "--break", str(break_duration),
         "--cycles", str(cycles)],
        **popen_kwargs  # type: ignore[arg-type]
    )

    print("\nYour study session begins!")
    print("Enter pymodoro --show to see the load bar.\n")


def show_progress_mode() -> None:
    """Run the foreground live progress bar display."""
    if not is_daemon_running():
        print("No Pomodoro session is running.")
        print("Start one with: pymodoro")
        return

    from pomodoro.tui import live_display_loop
    from pomodoro.ipc import SESSION_FILE
    live_display_loop(SESSION_FILE)


def stop_mode() -> None:
    """Send a stop command to the running daemon."""
    if not is_daemon_running():
        print("No Pomodoro session is running.")
        return

    write_command("stop")
    print("Stop command sent. The daemon will exit shortly.")


def status_mode() -> None:
    """Print the current daemon status with a progress bar."""
    if not is_daemon_running():
        print("No Pomodoro session is running.")
        print("Start one with: pymodoro")
        return

    state = read_session()
    if state is None:
        print("Unable to read session state.")
        return

    from pomodoro.tui import render_from_state

    print(render_from_state(state))


def check_notify_mode() -> None:
    """Print session progress and pending notifications. Designed for PROMPT_COMMAND."""
    if not is_daemon_running():
        return

    state = read_session()
    if state is None:
        return

    from pomodoro.tui import render_from_state

    # Always show the progress bar.
    print(render_from_state(state).rstrip())

    # Show notification if there's a new one.
    notification = state.get("notification")
    if notification:
        last_file = DATA_DIR / "last_notify.txt"
        try:
            last_text = last_file.read_text().strip()
        except FileNotFoundError:
            last_text = ""

        msg = notification["text"]
        if msg != last_text:
            print(f"  {msg}")
            last_file.write_text(msg)


def main() -> None:
    """Parse arguments and dispatch to the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Pomodoro Penguin — a background Pomodoro timer for your terminal."
    )
    parser.add_argument("--show", action="store_true", dest="show_progress",
                        help="Show a live progress bar for the current session")
    parser.add_argument("--stop", action="store_true",
                        help="Stop the running Pomodoro session")
    parser.add_argument("--status", action="store_true",
                        help="Show the current session status")
    parser.add_argument("--history", action="store_true",
                        help="Show saved timer presets and exit")
    parser.add_argument("--use-timer", type=str,
                        help="Reuse a saved timer's duration for the work period")
    parser.add_argument("--check-notify", action="store_true",
                        help="Print any pending notification (for shell prompt integration)")
    parser.add_argument("--version", "-v", action="version",
                        version=f"Pomodoro Penguin {VERSION}",
                        help="Show the version and exit")

    args = parser.parse_args()

    if args.check_notify:
        check_notify_mode()
    elif args.show_progress:
        show_progress_mode()
    elif args.stop:
        stop_mode()
    elif args.status:
        status_mode()
    elif args.history:
        storage = Storage()
        show_timer_history(storage)
    elif args.use_timer:
        storage = Storage()
        try:
            timer = storage.get_timer(args.use_timer)
            print(f"Timer {args.use_timer}: {timer.duration} min work duration")
        except ValueError as e:
            print(str(e))
            sys.exit(1)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
