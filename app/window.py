import os
import sys
from html import escape
from time import monotonic
from dotenv import load_dotenv
from PyQt5.QtCore import QObject, QThread, Qt, QTimer, pyqtSignal
from cerebras.cloud.sdk import Cerebras
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QPlainTextEdit,
    QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

load_dotenv()


class ChatWorker(QObject):
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, prompt, model):
        super().__init__()
        self.prompt = prompt
        self.model = model

    def run(self):
        try:
            client = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.prompt}],
            )
            self.finished.emit(response.choices[0].message.content or "")
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


PLANS = {
    'download': ([('Reading Downloads folder', r'C:\Users\Yashraj\Downloads — 23 items'),
                  ('Classifying files by type', '14 documents, 6 images, 3 archives'),
                  ('Creating destination folders', r'mkdir Documents\Sorted, Images\Sorted'),
                  ('Moving files', r'moved 14 → Documents\Sorted, 6 → Images\Sorted'),
                  ('Moving archives', r'moved 3 → Documents\Sorted\Archives')],
                 'Sorted 23 files into 3 folders. Your Downloads folder is organized.'),
    'excel': ([('Opening Excel', 'launched EXCEL.EXE'), ('Locating workbook', 'opened Q3_report.xlsx'),
               ('Reading column B', '42 rows, range B2:B43'), ('Computing total', 'SUM(B2:B43) = 184,220.50'),
               ('Writing result', 'wrote total to B45 and saved workbook')],
              'Column B totals 184,220.50 — written into B45 and saved.'),
    'schedule': ([('Reading target folder', r'C:\Users\Yashraj\Documents'),
                  ('Creating scheduled task', 'Task Scheduler — “nightly-backup”'),
                  ('Setting trigger', 'runs daily at 23:30'),
                  ('Setting action', r'robocopy Documents → D:\Backups\Documents /MIR')],
                 'Scheduled a nightly backup at 11:30 PM. The first run is tonight.'),
}


def plan(text):
    q = text.lower()
    for key in PLANS:
        if key in q or (key == 'download' and 'organi' in q) or (key == 'excel' and 'spreadsheet' in q):
            return PLANS[key]
    return ([('Planning task', f'parsed instruction: “{text}”'), ('Taking control', 'focused active desktop session'),
             ('Executing', 'running planned actions'), ('Verifying result', 'checked final state')],
            'Done — let me know if you want any adjustments.')


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

    def send_demo(self, text):
        steps, debrief = plan(text)
        self.trace = Trace(steps, self.messages)
        self.trace.user_opened = False
        self.feed.insertWidget(self.feed.count() - 1, self.trace)
        self.started = monotonic(); self.index = 0; self.debrief = debrief
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(900)
        self.tick()

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
        self.worker.finished.connect(self.api_thread.quit)
        self.worker.failed.connect(self.api_thread.quit)
        self.api_thread.finished.connect(self.worker.deleteLater)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        self.api_thread.start()

    def on_cerebras_finished(self, text):
        self.trace.finish(round(monotonic() - self.started))
        agent = QLabel(escape(text))
        agent.setObjectName('agent'); agent.setWordWrap(True)
        self.feed.insertWidget(self.feed.count() - 1, agent)
        self.running = False
        self.scroll_to_bottom()

    def on_cerebras_failed(self, error):
        self.trace.finish(round(monotonic() - self.started))
        agent = QLabel(f'<b>Request failed:</b> {escape(error)}')
        agent.setObjectName('agent'); agent.setWordWrap(True); agent.setTextFormat(Qt.RichText)
        self.feed.insertWidget(self.feed.count() - 1, agent)
        self.running = False
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def tick(self):
        if self.index < len(self.trace.steps): self.trace.add_step(*self.trace.steps[self.index]); self.index += 1
        else:
            self.timer.stop(); self.running = False; self.trace.finish(round(monotonic() - self.started)); agent = QLabel(self.debrief); agent.setObjectName('agent'); agent.setWordWrap(True); self.feed.insertWidget(self.feed.count() - 1, agent)
        self.trace.refresh(round(monotonic() - self.started)); self.scroll_to_bottom()

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
