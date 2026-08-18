import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path
from time import monotonic
from dotenv import load_dotenv
from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal
from cerebras.cloud.sdk import Cerebras
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QPlainTextEdit,
    QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parent.parent

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': 'Read a UTF-8 text file in the project workspace.',
            'parameters': {
                'type': 'object',
                'properties': {'path': {'type': 'string', 'description': 'Project-relative file path'}},
                'required': ['path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_pwsh',
            'description': 'Run a PowerShell command in the project workspace.',
            'parameters': {
                'type': 'object',
                'properties': {'command': {'type': 'string', 'description': 'PowerShell command to run'}},
                'required': ['command'],
            },
        },
    },
]


def execute_tool(name, arguments):
    if name == 'read_file':
        requested = (PROJECT_ROOT / arguments['path']).resolve()
        if PROJECT_ROOT not in requested.parents and requested != PROJECT_ROOT:
            return 'Error: file must be inside the project workspace.'
        try:
            return requested.read_text(encoding='utf-8')[:100000]
        except OSError as error:
            return f'Error reading file: {error}'

    if name == 'run_pwsh':
        try:
            result = subprocess.run(
                ['pwsh', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', arguments['command']],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30,
            )
            output = (result.stdout + result.stderr).strip()
            return output[-100000:] if output else f'Command exited with code {result.returncode}.'
        except FileNotFoundError:
            return 'Error: pwsh was not found on this machine.'
        except subprocess.TimeoutExpired:
            return 'Error: PowerShell command timed out after 30 seconds.'
        except OSError as error:
            return f'Error running PowerShell: {error}'

    return f'Error: unknown tool {name}.'


class ChatWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)
    tool_started = pyqtSignal(str, str)

    def __init__(self, prompt, model):
        super().__init__()
        self.prompt = prompt
        self.model = model

    def run(self):
        try:
            client = Cerebras(api_key=os.environ['CEREBRAS_API_KEY'])
            messages = [
                {
                    'role': 'system',
                    'content': (
                        'Answer briefly and directly in plain text. Do not use Markdown, bullet symbols, '
                        'headings, code fences, or decorative formatting. Use the available tools when needed. '
                        'Never claim a command ran or a file was read unless the tool returned the result.'
                    ),
                },
                {'role': 'user', 'content': self.prompt},
            ]
            for _ in range(8):
                response = client.chat.completions.create(
                    model=self.model, messages=messages, tools=TOOLS,
                )
                message = response.choices[0].message
                tool_calls = message.tool_calls or []
                messages.append(message.model_dump(exclude_none=True))
                if not tool_calls:
                    self.finished.emit(message.content or '')
                    return
                for call in tool_calls:
                    try:
                        arguments = json.loads(call.function.arguments)
                        detail = arguments.get('path') or arguments.get('command') or 'running'
                        self.tool_started.emit(call.function.name, str(detail))
                        result = execute_tool(call.function.name, arguments)
                    except (ValueError, KeyError, TypeError) as error:
                        result = f'Tool input error: {error}'
                    messages.append({
                        'role': 'tool', 'tool_call_id': call.id, 'content': result,
                    })
            self.failed.emit('The model used too many tool calls without producing an answer.')
        except Exception as error:
            self.failed.emit(str(error))


class AutoGrowTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent); self.setPlaceholderText('Type an instruction...')
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def resize_to_content(self):
        return

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.window().send(); event.accept(); return
        super().keyPressEvent(event)



class Trace(QFrame):
    def __init__(self, steps, parent):
        super().__init__(parent); self.steps = steps; self.open = True; self.done = False
        self.body_widget = QWidget(); self.body = QVBoxLayout(self.body_widget)
        self.body.setContentsMargins(10, 2, 0, 2); self.body.setSpacing(8)
        self.button = QPushButton(); self.button.setObjectName('traceButton'); self.button.clicked.connect(self.toggle)
        box = QVBoxLayout(self); box.setContentsMargins(0, 1, 0, 1); box.setSpacing(2); box.addWidget(self.button); box.addWidget(self.body_widget)
        self.refresh()

    def add_step(self, label, detail):
        row = QFrame(); layout = QVBoxLayout(row); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(2)
        title = QLabel(f'›  {label}'); title.setObjectName('stepTitle'); detail_label = QLabel(detail)
        detail_label.setObjectName('stepDetail'); detail_label.setWordWrap(True); detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title); layout.addWidget(detail_label); self.body.addWidget(row); self.refresh()

    def refresh(self, seconds=0):
        state = 'Worked for' if self.done else 'Working —'
        self.button.setText(f'{"⌄" if self.open else "›"}  {state} {seconds}s')
        self.body_widget.setVisible(self.open)

    def finish(self, seconds):
        self.done = True
        if not self.user_opened: self.open = False
        self.refresh(seconds)

    def toggle(self):
        self.user_opened = True; self.open = not self.open; self.refresh()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('Sem4 Agent'); self.resize(900, 600); self.running = False
        self.setCentralWidget(self.home()); self.setStyleSheet(self.styles())


    def home(self):
        page = QWidget(); out = QVBoxLayout(page); out.setContentsMargins(14, 14, 14, 12); out.setSpacing(10)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame)
        self.messages = QWidget(); self.feed = QVBoxLayout(self.messages); self.feed.setContentsMargins(28, 20, 28, 10); self.feed.setSpacing(7); self.feed.addStretch()
        self.scroll.setWidget(self.messages); out.addWidget(self.scroll, 1)
        self.show_empty_state()

        composer = QFrame(); composer.setObjectName('composer'); composer.setFixedHeight(62); composer.setMaximumWidth(720); composer.setMinimumWidth(420)
        row = QHBoxLayout(composer); row.setContentsMargins(12, 6, 6, 6); row.setSpacing(8)
        self.input = AutoGrowTextEdit()
        send = QToolButton(); send.setText('↑'); send.setObjectName('send'); send.setFixedSize(34, 34); send.clicked.connect(self.send)
        row.addWidget(self.input, 1); row.addWidget(send, 0, Qt.AlignBottom); out.addWidget(composer, 0, Qt.AlignHCenter); return page

    def show_empty_state(self):
        empty = QFrame(); empty.setObjectName('emptyState'); layout = QVBoxLayout(empty)
        layout.setContentsMargins(0, 70, 0, 30); layout.setAlignment(Qt.AlignCenter); layout.setSpacing(14)
        title = QLabel('What do you want me to do?'); title.setObjectName('emptyTitle'); layout.addWidget(title, 0, Qt.AlignCenter)
        for text in ('organize my downloads', 'open Excel and total column B', 'schedule a nightly backup of Documents'):
            button = QPushButton(text); button.setObjectName('suggestion'); button.clicked.connect(lambda _, value=text: self.send(value)); layout.addWidget(button)
        self.feed.insertWidget(0, empty)

    def clear_empty_state(self):
        for i in reversed(range(self.feed.count())):
            item = self.feed.itemAt(i); widget = item.widget()
            if widget and widget.objectName() == 'emptyState': widget.deleteLater(); self.feed.removeItem(item)


    def send(self, text=None):
        text = (text if text is not None else self.input.toPlainText()).strip()
        if not text or self.running:
            return
        self.clear_empty_state()
        self.running = True
        self.input.clear()
        user = QLabel(escape(text))
        user.setObjectName('user')
        user.setWordWrap(True)
        user.setMaximumWidth(430)
        user.setAlignment(Qt.AlignLeft)
        self.feed.insertWidget(self.feed.count() - 1, user, alignment=Qt.AlignRight)

        if not os.environ.get('CEREBRAS_API_KEY'):
            self.show_error('CEREBRAS_API_KEY is missing. Add it to .env and restart the app.')
            return
        self.send_to_cerebras(text)

    def show_error(self, message):
        self.running = False
        agent = QLabel(escape(message))
        agent.setObjectName('agent'); agent.setWordWrap(True)
        self.feed.insertWidget(self.feed.count() - 1, agent)
        self.scroll_to_bottom()


    def send_to_cerebras(self, text):
        self.started = monotonic()
        self.trace = Trace([('Contacting Cerebras', 'Sending request to the configured model')], self.messages)
        self.trace.user_opened = False
        self.feed.insertWidget(self.feed.count() - 1, self.trace)
        self.api_thread = QThread(self)
        self.worker = ChatWorker(text, os.environ.get('CEREBRAS_MODEL', 'gpt-oss-120b'))
        self.worker.moveToThread(self.api_thread)
        self.api_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_cerebras_finished)
        self.worker.failed.connect(self.on_cerebras_failed)
        self.worker.tool_started.connect(self.on_tool_started)
        self.worker.finished.connect(self.api_thread.quit)
        self.worker.failed.connect(self.api_thread.quit)
        self.api_thread.finished.connect(self.worker.deleteLater)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        self.api_thread.start()

    def on_tool_started(self, name, detail):
        labels = {'read_file': 'Reading file', 'run_pwsh': 'Running PowerShell'}
        self.trace.add_step(labels.get(name, name), detail)
        self.trace.refresh(round(monotonic() - self.started))
        self.scroll_to_bottom()

    def on_cerebras_finished(self, text):
        self.trace.finish(round(monotonic() - self.started))
        agent = QLabel(text)
        agent.setObjectName('agent'); agent.setWordWrap(True); agent.setTextFormat(Qt.PlainText)
        self.feed.insertWidget(self.feed.count() - 1, agent)
        self.running = False
        self.scroll_to_bottom()

    def on_cerebras_failed(self, error):
        self.trace.finish(round(monotonic() - self.started))
        agent = QLabel(f'Request failed: {error}')
        agent.setObjectName('agent'); agent.setWordWrap(True); agent.setTextFormat(Qt.PlainText)
        self.feed.insertWidget(self.feed.count() - 1, agent)
        self.running = False
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())


    def styles(self):
        return '''QWidget{background:#111213;color:#e6e6e6;font-family:Segoe UI;font-size:13px}


        QPushButton{background:#1a1b1c;color:#a5a6a7;border:1px solid #2a2b2c;border-radius:7px;padding:9px}
        QPushButton:hover{color:#fff;border-color:#666} QToolButton#send{background:#c9a15a;color:#161616;font-size:18px;border:0;border-radius:6px}

        QFrame#composer{background:#1a1b1c;border:1px solid #303133;border-radius:9px}
        QPlainTextEdit{background:transparent;border:0;padding:3px;color:#eee}
        QLabel#emptyTitle{color:#999;font-size:15px} QPushButton#suggestion{text-align:left;background:transparent;color:#999;border:1px solid #2a2b2c;border-radius:8px;padding:9px 12px;min-width:330px}
        QPushButton#suggestion:hover{background:#1a1b1c;color:#eee}
        QLabel#stepTitle{color:#aaa;font-size:12.5px} QLabel#stepDetail{color:#777;font-family:Consolas;font-size:11.5px;padding-left:18px}
        QToolButton#send{min-width:34px;min-height:34px}
        QLabel#user{background:#292a2b;border-radius:9px;padding:10px 13px}
        QLabel#agent{color:#b0b1b2;padding:8px 13px;margin:5px 100px 5px 0}
        QFrame{border:0} QPushButton#traceButton{background:transparent;border:0;text-align:left;padding:3px;color:#777}
        QLabel#step{color:#aaa;background:transparent;padding:0} QScrollArea{border:0}'''


def main():
    app = QApplication(sys.argv); app.setStyle('Fusion')
    window = MainWindow(); window.show(); sys.exit(app.exec_())


if __name__ == '__main__': main()
