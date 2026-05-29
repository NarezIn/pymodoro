"""
This is an example file to demo the Pomodoro timer in terminal.
"""
import time
from pomodoro.storage import Storage
from pomodoro.session import PomodoroSession
from pomodoro.tui import finish_session, render_full, render_ith_sub, render_sub_progress, show_timer_history

def main():
    print("Welcome to the Pomodoro Timer Demo!")
    print("This demo will show you how the Pomodoro timer works in the terminal.")

    #1. Create a Storage instance and add timers
    storage = Storage("demo_timers.json")
    print("\nCreating timers...")
    timer1_id = storage.create_timer(25)
    timer2_id = storage.create_timer(15)
    print(f"Created timer with IDs: {timer1_id}, {timer2_id}")

    #2. Show timer history
    print("\nShowing timer history:")
    show_timer_history(storage)
    print()

    #3. Retrieve a timer and start a Pomodoro session
    timer = storage.get_timer(timer1_id)
    print(f"Retrieved timer with duration: {timer.duration} minutes")

    #4. Update a timer
    storage.update_timer(timer1_id, duration=30)
    print(f"Updated timer {timer1_id} to {storage.get_timer(timer1_id).duration} minutes")
    print("new!")
    show_timer_history(storage)
    print()

    #5. Delete a timer
    storage.delete_timer(timer2_id)
    print(f"Deleted timer with ID: {timer2_id}")
    print("new!")
    show_timer_history(storage)
    print()

    #6. Demo PomodoroSession and TUI rendering
    print("\nStarting a Pomodoro session (shortened for demo)...")
    print("\n====================================================\n")
    session = PomodoroSession(work_duration=45, break_duration=5, total_cycles=2)
    session.start()

    while session.current_phase is not None:
        session.tick()
        status = session.get_status()

        current_sub_num = min(session.completed_cycles + 1, session.total_cycles)
        total_sub_num = session.total_cycles
        current_mins = status['remaining_seconds']
        total_mins = status.get('total_seconds', current_mins)
        is_resting = (status['phase'] == "break")

        render_full(current_sub_num, total_sub_num, current_mins, total_mins, is_resting)
        time.sleep(1)
    finish_session()
    print("====================================================\n")
    print("** Pomodoro session completed! **\n")

if __name__ == "__main__":
    main()