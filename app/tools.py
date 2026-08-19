import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_file(args):
    requested = (PROJECT_ROOT / args['path']).resolve()
    if PROJECT_ROOT not in requested.parents and requested != PROJECT_ROOT:
        return 'Error: file must be inside the project workspace.'
    try:
        return requested.read_text(encoding='utf-8')[:100000]
    except OSError as error:
        return f'Error reading file: {error}'


def run_pwsh(args):
    try:
        result = subprocess.run(
            ['pwsh', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', args['command']],
            cwd=PROJECT_ROOT, capture_output=True, timeout=30, check=False,
        )
        output = (result.stdout + result.stderr).decode('utf-8', errors='replace').strip()
        return output[-100000:] if output else f'Command exited with code {result.returncode}.'
    except FileNotFoundError:
        return 'Error: pwsh was not found on this machine.'
    except subprocess.TimeoutExpired:
        return 'Error: PowerShell command timed out after 30 seconds.'
    except OSError as error:
        return f'Error running PowerShell: {error}'


TOOLS = {
    'read_file': {
        'label': 'Reading file',
        'description': 'Read text file from project workspace.',
        'parameters': {
            'type': 'object',
            'properties': {'path': {'type': 'string', 'description': 'Project-relative file path'}},
            'required': ['path'],
        },
        'run': read_file,
        'describe': lambda args: args.get('path', ''),
    },
    'run_pwsh': {
        'label': 'Running PowerShell',
        'description': 'Run Pwsh Command',
        'parameters': {
            'type': 'object',
            'properties': {'command': {'type': 'string', 'description': 'PowerShell command to run'}},
            'required': ['command'],
        },
        'run': run_pwsh,
        'describe': lambda args: args.get('command', ''),
    },
}


def schemas():
    return [
        {'type': 'function', 'function': {'name': name, 'description': spec['description'], 'parameters': spec['parameters']}}
        for name, spec in TOOLS.items()
    ]


def label(name):
    spec = TOOLS.get(name)
    return spec['label'] if spec else name


def detail(name, args):
    spec = TOOLS.get(name)
    if not spec:
        return ''
    describe = spec.get('describe')
    return describe(args) if describe else ''


def execute(name, args):
    spec = TOOLS.get(name)
    if not spec:
        return f'Error: unknown tool {name}.'
    return spec['run'](args)
