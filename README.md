# sem4

A Qt 5 desktop app (PyQt5) .

## Requirements

- Python 3.12 (managed with [uv](https://docs.astral.sh/uv/))

## Setup & run

```sh
uv sync
uv run python main.py
```

To use the live Cerebras chat backend, set an API key before starting the app:

```powershell
$env:CEREBRAS_API_KEY = "your-api-key-here"
# Optional; defaults to gpt-oss-120b
$env:CEREBRAS_MODEL = "gpt-oss-120b"
uv run python main.py
```

An API key is required to use the app. API requests execute on a background
thread so the window remains responsive. Keys are read only from the environment
and are not stored in the project.

## Usage

A window opens with a clean, minimal agent workspace for entering instructions,
running tasks, and viewing progress. Enter submits a prompt; Shift+Enter adds a
new line. The live backend uses the official `cerebras_cloud_sdk` package and
returns the model response in the conversation.
