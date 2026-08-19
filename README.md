# sem4

A Qt 5 desktop app (PyQt5).

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
$env:CEREBRAS_MODEL = "gpt-oss-120b"
uv run python main.py
```

An API key is required to use the app. API requests execute on a background
thread so the window remains responsive. Keys are read from the environment or
from a `.env` file next to `main.py` (via `python-dotenv`) and are not stored in
the project.

## Usage

A window opens with an empty chat area and a composer at the bottom. Type an
instruction and press Enter to submit; Shift+Enter inserts a new line. The agent
calls the Cerebras API on a background thread, so the window stays responsive
while it works.

The model answers in plain text, not markdown. While the model is using a tool
(`read_file` or `run_pwsh`) to complete the task, a collapsible trace panel
appears above the response showing how long the agent has been working and each
tool step. A simple question that gets a direct answer shows no trace.

If you close the window while the agent is still working, the app asks what to
do: stop and close, run in the background (the window hides and the app exits
when the response finishes), or cancel and keep working.

## Project structure

```
sem4/
├── main.py          # entry point: loads .env, creates the Qt app, loads the stylesheet
└── app/
    ├── agent.py     # agent loop against the Cerebras API, capped at 8 rounds
    ├── tools.py     # tool definitions (schema and handler per tool)
    ├── widgets.py   # trace and input widgets
    ├── window.py    # main window UI, Enter handling, worker thread wiring
    └── style.qss    # Qt stylesheet (theme)
```

## Adding a tool

Add one entry to the `TOOLS` dict in `app/tools.py`. Each entry needs:

- `label`: short text shown in the trace
- `description`: what the tool does, shown to the model
- `parameters`: JSON Schema for the tool's arguments
- `run`: a handler function that takes the parsed arguments and returns a string result
- `describe` (optional): a callback that turns the arguments into a one-line trace detail

The agent loop picks the tool up automatically. No other file changes are needed.
