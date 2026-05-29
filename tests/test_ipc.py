"""
Tests for the IPC module — state file and command file read/write.
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pomodoro.ipc import (
    DATA_DIR,
    SESSION_FILE,
    COMMAND_FILE,
    LOCK_FILE,
    ensure_data_dir,
    read_session,
    write_session,
    read_command,
    write_command,
    clear_command,
    write_pid,
    remove_lock,
    is_daemon_running,
)


@pytest.fixture
def tmp_data_dir(monkeypatch, tmp_path):
    """Redirect all file paths to a temporary directory."""
    monkeypatch.setattr("pomodoro.ipc.DATA_DIR", Path(tmp_path))
    monkeypatch.setattr("pomodoro.ipc.SESSION_FILE", Path(tmp_path) / "session.json")
    monkeypatch.setattr("pomodoro.ipc.COMMAND_FILE", Path(tmp_path) / "command.json")
    monkeypatch.setattr("pomodoro.ipc.LOCK_FILE", Path(tmp_path) / "daemon.lock")
    return tmp_path


class TestSessionFile:
    """Tests for session state persistence."""

    def test_read_nonexistent_returns_none(self, tmp_data_dir):
        assert read_session() is None

    def test_read_empty_file_returns_none(self, tmp_data_dir):
        (tmp_data_dir / "session.json").write_text("")
        assert read_session() is None

    def test_read_invalid_json_returns_none(self, tmp_data_dir):
        (tmp_data_dir / "session.json").write_text("{not valid")
        assert read_session() is None

    def test_write_and_read_roundtrip(self, tmp_data_dir):
        state = {"version": 1, "session": {"phase": "work", "remaining_seconds": 1200}}
        write_session(state)

        result = read_session()
        assert result is not None
        assert result["version"] == 1
        assert result["session"]["phase"] == "work"
        assert result["session"]["remaining_seconds"] == 1200

    def test_write_overwrites_previous(self, tmp_data_dir):
        write_session({"version": 1, "key": "old"})
        write_session({"version": 2, "key": "new"})

        result = read_session()
        assert result["version"] == 2
        assert result["key"] == "new"

    def test_ensure_data_dir_creates_directory(self, tmp_data_dir):
        # Remove the tmp dir first
        import shutil
        shutil.rmtree(str(tmp_data_dir), ignore_errors=True)

        ensure_data_dir()
        assert tmp_data_dir.exists()


class TestCommandFile:
    """Tests for command file operations."""

    def test_read_nonexistent_returns_none(self, tmp_data_dir):
        assert read_command() is None

    def test_write_and_read_command(self, tmp_data_dir):
        write_command("stop")
        result = read_command()
        assert result is not None
        assert result["command"] == "stop"

    def test_clear_removes_command_file(self, tmp_data_dir):
        write_command("show_progress")
        clear_command()
        assert not (tmp_data_dir / "command.json").exists()

    def test_clear_nonexistent_does_not_raise(self, tmp_data_dir):
        clear_command()  # Should not raise

    def test_write_then_clear_then_read_returns_none(self, tmp_data_dir):
        write_command("stop")
        clear_command()
        assert read_command() is None


class TestLockFile:
    """Tests for daemon lock/PID file operations."""

    def test_write_pid_creates_file(self, tmp_data_dir):
        write_pid(12345)
        assert (tmp_data_dir / "daemon.lock").exists()
        assert (tmp_data_dir / "daemon.lock").read_text().strip() == "12345"

    def test_remove_lock_deletes_file(self, tmp_data_dir):
        write_pid(12345)
        remove_lock()
        assert not (tmp_data_dir / "daemon.lock").exists()

    def test_remove_lock_nonexistent_does_not_raise(self, tmp_data_dir):
        remove_lock()  # Should not raise

    def test_is_daemon_running_nonexistent_lock_returns_false(self, tmp_data_dir):
        assert is_daemon_running() is False

    def test_is_daemon_running_invalid_pid_returns_false(self, tmp_data_dir):
        (tmp_data_dir / "daemon.lock").write_text("not_a_pid")
        assert is_daemon_running() is False

    def test_is_daemon_running_valid_pid(self, tmp_data_dir):
        # Write our own PID — it should be running
        write_pid(os.getpid())
        result = is_daemon_running()
        # Our own process is running
        assert result is True

    def test_is_daemon_running_dead_pid(self, tmp_data_dir):
        # Use a very high PID that likely doesn't exist
        write_pid(99999999)
        result = is_daemon_running()
        assert result is False
