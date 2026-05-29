# Pymodoro

[![Build and Test](https://github.com/NarezIn/pymodoro/actions/workflows/build-test.yaml/badge.svg)](https://github.com/NarezIn/pymodoro/actions/workflows/build-test.yaml)

A Pomodoro timer that runs in the background while you keep using your
terminal. Start a session and forget about it — the progress bar shows up
above your prompt every time you press Enter, and alerts appear when work
or break sessions end.

## Installation

```bash
pip install pyodoro
```

Requires Python 3.12+.

## Usage

```bash
pymodoro
```

You'll be prompted for work duration, break duration, and number of
cycles. Press Enter at each prompt to accept the defaults. The timer
starts in the background and you get your terminal back immediately.

### Commands

| Command | Description |
|---|---|
| `pymodoro` | Start an interactive Pomodoro session in the background |
| `pymodoro --show` | Show a live-updating progress bar (Ctrl+C to dismiss) |
| `pymodoro --status` | Print the current progress bar and time remaining |
| `pymodoro --stop` | Stop the running session |
| `pymodoro --check-notify` | Print progress bar and phase alerts (used by shell integration below) |
| `pymodoro --version` | Show the package version |

### Prompt integration (bash / zsh)

To see the progress bar above every command prompt, add this to your `~/.bashrc` (or `~/.zshrc`):

```bash
PROMPT_COMMAND="pymodoro --check-notify;${PROMPT_COMMAND}"
```

Now every time you press Enter, the tomato bar and timer appear right
above your prompt. When a work or break session ends, the alert appears
there too.

### VS Code terminal

If you use VS Code's integrated terminal, make sure it runs bash as a
login shell so it sources your `.bashrc`. In `settings.json`:

```json
"terminal.integrated.shellArgs.windows": ["-l"]
```

## Development

```bash
git clone https://github.com/NarezIn/pymodoro.git
cd pymodoro
pip install pipenv
pipenv install --dev
pipenv shell
```

### Running tests

```bash
python -m pytest tests/ --cov=pomodoro
```

## License

[MIT](./LICENSE)
