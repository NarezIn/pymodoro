"""
Since our Pomodoro has a terminal-based user interface (TUI), 
this library has utility functions to display data in console/terminal.
Users should see the timer and session info (the progress bars, the ticking clock, the tables) 
appearing in the command line.

demo:
current sub-session: [2/4] # meaning the user is at the second sub-session of this study session
if it is studying time:
    current sub-session progress: [tomato...⬜️⬜️⬜️⬜️⬜️⬜️⬜️] (12min/25min)
else if it is rest time:
    curent sub-session rest progress: [sleepy.....⬜⬜⬜⬜] (3min/5min)
"""
import sys
import emoji
from pomodoro.storage import Storage



def render_ith_sub(current_sub_num: int, total_sub_num: int) -> str:
    """
    Display which sub-session the user is currently at.
    """
    if total_sub_num <= 0:
        raise ValueError("Total_sub_num must be greater than zero when rendering ith sub-session!")
    return f"current sub-session: [{current_sub_num}/{total_sub_num}]"

def render_sub_progress(current: int, total: int, is_resting: bool = False) -> str:
    """
    Render a sub-session progress bar with emojis.

    Args:
        current: Minutes completed
        total: Total minutes for the sub-session
        is_resting: Whether the session is a rest period

    Returns:
        str: Progress bar string with label and filled/empty icons
    """
    if total <= 0:
        raise ZeroDivisionError("Total duration must be greater than 0")

    # Bar settings
    bar_length = 10
    label = "resting" if is_resting else "studying"

    # Choose emoji
    filled_emoji = emoji.emojize(":sleepy_face:") if is_resting else emoji.emojize(":tomato:")
    empty_emoji = emoji.emojize(":white_medium_square:") + " " # append space for spacing test

    # Clamp current to [0, total]
    current = max(0, min(current, total))

    # Calculate number of filled icons
    filled_count = int(bar_length * (current / total))
    empty_count = bar_length - filled_count

    # Build progress bar string
    bar = filled_emoji * filled_count + empty_emoji * empty_count

    return f"{label}: {bar} {current}min/{total}min"

def render_full(current_sub_num: int, total_sub_num: int,
                current_mins: int, total_mins: int,
                is_resting = False):
    """
    Render the full TUI, including the timer, the session info, and the progress bars.
    """
    ith_sub = render_ith_sub(current_sub_num, total_sub_num)
    sub_progress = render_sub_progress(current_mins, total_mins, is_resting)
    full_output = f"\r\033[K\033[F{ith_sub}\n{sub_progress}"
    sys.stdout.write(full_output)
    sys.stdout.flush()

def show_timer_history(storage: Storage):
    """
    Print all timers in storage with their IDs and durations
    """
    timers = storage.list_timers()
    
    if not timers:
        print("No timers found.")
        return
    print("Timer History:")
    for timer_id, timer in timers.items():
        print(f"ID: {timer_id}, Duration: {timer.duration} minutes")

def finish_session():
    """Call this when the timer hits 100% so the next print starts on a new line."""
    print()
    sys.stdout.flush()


def render_from_state(state: dict) -> str:
    """
    Build a full terminal display string from a daemon state dict.

    Args:
        state (dict): the full state from session.json, with "session"
            and "config" keys.

    Returns:
        str: a multi-line string with sub-session info, progress bar,
             and time remaining.
    """
    session = state.get("session", state)
    phase = session.get("phase")
    if phase is None:
        completed = session.get("completed_cycles", 0)
        total = session.get("total_cycles", 0)
        return f"Session complete! {completed}/{total} cycles finished.\n"

    completed = session.get("completed_cycles", 0)
    total_cycles = session.get("total_cycles", 4)
    current_sub = min(completed + 1, total_cycles)
    remaining = session.get("remaining_seconds", 0)
    total_secs = session.get("total_seconds", 1)
    is_resting = (phase == "break")
    display_time = session.get("display_time", "00:00")

    sub_line = render_ith_sub(current_sub, total_cycles)
    elapsed = total_secs - remaining
    progress_line = render_sub_progress(elapsed, total_secs, is_resting)
    # Replace the "Xmin/Ymin" suffix with the display_time.
    progress_line = progress_line.rsplit(" ", 1)[0] + f" {display_time}"

    return f"{sub_line}\n{progress_line}"


def live_display_loop(state_file) -> None:
    """
    Foreground loop for --show. Polls the state file every second,
    renders a live progress bar with ANSI refresh, and handles Ctrl+C.

    Args:
        state_file: a pathlib.Path pointing to session.json.
    """
    import time
    from pomodoro.ipc import read_session, write_command, clear_command

    write_command("show_progress")
    shown_notification = False
    prev_line_count = 0

    try:
        while True:
            state = read_session()
            if state is None:
                sys.stdout.write("\r\033[KWaiting for daemon...\r\n")
                sys.stdout.flush()
                time.sleep(1)
                continue

            display = render_from_state(state)

            notification = state.get("notification")
            if notification and not shown_notification:
                display += f"\n  {notification['text']}"
                shown_notification = True

            display += "\n[Ctrl+C to return to quiet mode]"
            line_count = display.count("\n") + 1

            # Move up to the start of the previous render, clear below.
            if prev_line_count > 0:
                sys.stdout.write(f"\033[{prev_line_count - 1}F")
            sys.stdout.write("\033[J")
            sys.stdout.write(display + "\n")
            sys.stdout.flush()
            prev_line_count = line_count + 1  # +1 for the trailing newline

            if state.get("session", {}).get("phase") is None:
                sys.stdout.write("\033[JGood work!\r\n")
                sys.stdout.flush()
                break

            time.sleep(1)
    except KeyboardInterrupt:
        sys.stdout.write("\033[JReturning to quiet mode...\r\n")
        sys.stdout.flush()
    finally:
        clear_command()



