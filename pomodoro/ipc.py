"""
IPC layer for the pymodoro daemon via JSON files in ~/.pymodoro/.

The daemon writes session state to session.json and reads commands from
command.json. CLI clients (--show-progress, --stop, --status) read
session.json and write commands to command.json.
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

DATA_DIR = Path.home() / ".pymodoro"
SESSION_FILE = DATA_DIR / "session.json"
COMMAND_FILE = DATA_DIR / "command.json"
LOCK_FILE = DATA_DIR / "daemon.lock"


def ensure_data_dir() -> None:
    """Create the pymodoro data directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_session() -> Optional[dict]:
    """
    Read the daemon session state from session.json.

    Returns:
        dict: the session state, or None if the file does not exist or is invalid.
    """
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_session(state: dict) -> None:
    """
    Write session state to session.json.

    Args:
        state (dict): the session state to persist.
    """
    ensure_data_dir()
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def read_command() -> Optional[dict]:
    """
    Read the pending command from command.json.

    Returns:
        dict: the command object, or None if no command is pending.
    """
    try:
        with open(COMMAND_FILE, "r") as f:
            data = json.load(f)
            return data if data else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_command(cmd: str) -> None:
    """
    Write a command for the daemon to process.

    Args:
        cmd (str): the command name (e.g. "stop", "show_progress").
    """
    ensure_data_dir()
    with open(COMMAND_FILE, "w", encoding="utf-8") as f:
        json.dump({"command": cmd}, f)


def clear_command() -> None:
    """Clear the command file so the daemon knows the command was processed."""
    try:
        os.unlink(COMMAND_FILE)
    except FileNotFoundError:
        pass


def write_pid(pid: int) -> None:
    """
    Write the daemon's PID to the lock file.

    Args:
        pid (int): the process ID of the daemon.
    """
    ensure_data_dir()
    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def remove_lock() -> None:
    """Remove the daemon lock file on clean exit."""
    try:
        os.unlink(LOCK_FILE)
    except FileNotFoundError:
        pass


def is_daemon_running() -> bool:
    """
    Check whether a daemon process is currently running.

    Returns:
        bool: True if the lock file exists and its PID is alive.
    """
    try:
        with open(LOCK_FILE, "r") as f:
            pid = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes

            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_INFORMATION = 0x0400
            STILL_ACTIVE = 259

            handle = ctypes.windll.kernel32.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, pid
            )
            if handle == 0:
                return False

            exit_code = ctypes.wintypes.DWORD()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return exit_code.value == STILL_ACTIVE
        except OSError:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def remove_data_dir() -> None:
    """Remove the entire pymodoro data directory (cleanup utility)."""
    import shutil
    shutil.rmtree(str(DATA_DIR), ignore_errors=True)
