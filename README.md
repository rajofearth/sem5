# sem4

A Qt 5 desktop app (PyQt5) .

## Requirements

- Python 3.12 (managed with [uv](https://docs.astral.sh/uv/))

## Setup & run

```sh
uv sync
uv run python main.py
```

## Usage

A window opens with a clean, minimal sidebar containing two pages:

- **Home** — an agent workspace for entering instructions, running tasks, and viewing progress
- **Settings** — API/model configuration and native Windows permission toggles

Clicking an entry switches the page shown on the right. Use the sun button to switch between dark and light themes.
