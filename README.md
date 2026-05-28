# Pomodoro Penguin

[![Build and Test](https://github.com/NarezIn/pymodoro/actions/workflows/build-test.yaml/badge.svg)](https://github.com/NarezIn/pymodoro/actions/workflows/build-test.yaml)

A terminal-based Pomodoro timer with configurable work/break cycles, progress bars, and session history.

## Installation

```bash
$ python -m pip install pomodoro-penguin
```

Or install locally:

```bash
$ git clone https://github.com/NarezIn/pymodoro.git
$ cd pymodoro
$ python -m pip install .
```

## Usage

```bash
$ python -m pomodoro --work 25 --break 5 --cycles 4
```

### Options

| Flag | Description | Default |
|---|---|---|
| `--work` | Work duration in minutes | 25 |
| `--break` | Break duration in minutes | 5 |
| `--cycles` | Number of Pomodoro cycles | 4 |
| `--history` | Show history of past timers | — |
| `--use-timer` | Reuse a saved timer by its ID | — |
| `--version` | Show the package version | — |

### Examples

```bash
# 10-minute work, 3-minute break, 2 cycles
python -m pomodoro --work 10 --break 3 --cycles 2

# View timer history
python -m pomodoro --history

# Reuse a previously saved timer
python -m pomodoro --use-timer <timer_id>

# Check version
python -m pomodoro --version
```

## Development

### Setup

```bash
$ git clone https://github.com/NarezIn/pymodoro.git
$ cd pymodoro
$ python -m pip install pipenv
$ python -m pipenv install --dev
$ python -m pipenv shell
```

### Running tests

```bash
$ python -m pytest tests/ --cov=pomodoro
```

### Example script

[example.py](./example.py) walks through the package API programmatically.

## Screenshot

<img src="img/image.png" alt="Pomodoro TUI screenshot" />

## License

[MIT](./LICENSE)
