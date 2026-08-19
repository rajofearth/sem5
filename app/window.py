import os
from html import escape
from time import monotonic
from PyQt5.QtCore import QThread, Qt
from PyQt5.QtWidgets import QFrame, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea, QToolButton, QWidget
from app.agent import MODEL_DEFAULT, ChatWorker
from app.widgets import AutoGrowTextEdit, Trace, hbox, vbox


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Sem4 Agent')
        self.resize(900, 600)
        self.running = False
        self.close_after_finish = False
        self.trace = None
        self.setCentralWidget(self.home())

    def home(self):
        page = QWidget()
        out = vbox(page, margins=(14, 14, 14, 12), spacing=10)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.messages = QWidget()
        self.feed = vbox(self.messages, margins=(28, 20, 28, 10), spacing=7)
        self.feed.addStretch()
        self.scroll.setWidget(self.messages)
        out.addWidget(self.scroll, 1)

        self.show_empty_state()

        composer = QFrame()
        composer.setObjectName('composer')
        composer.setFixedHeight(62)
        composer.setMaximumWidth(720)
        composer.setMinimumWidth(420)
        row = hbox(composer, margins=(12, 6, 6, 6), spacing=8)
        self.input = AutoGrowTextEdit()
        send = QToolButton()
        send.setText('↑')
        send.setObjectName('send')
        send.setFixedSize(34, 34)
        send.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(send, 0, Qt.AlignBottom)
        out.addWidget(composer, 0, Qt.AlignHCenter)
        return page

    def show_empty_state(self):
        empty = QFrame()
        empty.setObjectName('emptyState')
        layout = vbox(empty, margins=(0, 70, 0, 30), spacing=14)
        layout.setAlignment(Qt.AlignCenter)
        title = QLabel('What do you want me to do?')
        title.setObjectName('emptyTitle')
        layout.addWidget(title, 0, Qt.AlignCenter)
        for text in ('organize my downloads', 'open Excel and total column B', 'schedule a nightly backup of Documents'):
            button = QPushButton(text)
            button.setObjectName('suggestion')
            button.clicked.connect(lambda _, value=text: self.send(value))
            layout.addWidget(button)
        self.feed.insertWidget(0, empty)

    def clear_empty_state(self):
        for i in reversed(range(self.feed.count())):
            item = self.feed.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() == 'emptyState':
                widget.deleteLater()
                self.feed.removeItem(item)

    def send(self, text=None):
        if not os.environ.get('CEREBRAS_API_KEY'):
            self.show_error('CEREBRAS_API_KEY is missing. Add it to .env and restart the app.')
            return
        text = (text if text is not None else self.input.toPlainText()).strip()
        if not text or self.running:
            return
        self.clear_empty_state()
        self.running = True
        self.input.clear()
        self._append('user', escape(text))
        self.send_to_cerebras(text)

    def show_error(self, message):
        self.running = False
        self._append('agent', escape(message))

    def send_to_cerebras(self, text):
        self.started = monotonic()
        self.api_thread = QThread(self)
        self.worker = ChatWorker(text, os.environ.get('CEREBRAS_MODEL', MODEL_DEFAULT))
        self.worker.moveToThread(self.api_thread)
        self.api_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_cerebras_finished)
        self.worker.failed.connect(self.on_cerebras_failed)
        self.worker.tool_started.connect(self.on_tool_started)
        self.worker.finished.connect(self.api_thread.quit)
        self.worker.failed.connect(self.api_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.failed.connect(self.worker.deleteLater)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        self.api_thread.start()

    def on_tool_started(self, label, detail):
        if self.trace is None:
            self.trace = Trace(self.messages)
            self.feed.insertWidget(self.feed.count() - 1, self.trace)
        self.trace.add_step(label, detail)
        self.trace.refresh(round(monotonic() - self.started))
        self.scroll_to_bottom()

    def on_cerebras_finished(self, text):
        if self.trace is not None:
            self.trace.finish(round(monotonic() - self.started))
        self._append('agent', text, plain=True)
        self.running = False
        self.scroll_to_bottom()
        self._close_if_requested()

    def on_cerebras_failed(self, error):
        if self.trace is not None:
            self.trace.finish(round(monotonic() - self.started))
        self._append('agent', f'Request failed: {error}', plain=True)
        self.running = False
        self.scroll_to_bottom()
        self._close_if_requested()

    def _append(self, role, text, plain=False):
        bubble = QLabel(text)
        bubble.setObjectName(role)
        bubble.setWordWrap(True)
        if role == 'user':
            bubble.setMaximumWidth(430)
            bubble.setAlignment(Qt.AlignLeft)
            self.feed.insertWidget(self.feed.count() - 1, bubble, alignment=Qt.AlignRight)
        else:
            if plain:
                bubble.setTextFormat(Qt.PlainText)
            self.feed.insertWidget(self.feed.count() - 1, bubble)
        self.scroll_to_bottom()

    def _close_if_requested(self):
        if self.close_after_finish:
            self.close()

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if not self.running:
            event.accept()
            return
        box = QMessageBox(self)
        box.setWindowTitle('Agent still running')
        box.setText('The agent is still working. What should I do?')
        stop = box.addButton('Stop and close', QMessageBox.DestructiveRole)
        box.addButton('Run in background', QMessageBox.AcceptRole)
        cancel = box.addButton('Cancel', QMessageBox.RejectRole)
        box.exec_()
        if box.clickedButton() is cancel:
            event.ignore()
        elif box.clickedButton() is stop:
            self.worker.stop()
            self.api_thread.quit()
            self.api_thread.wait(5000)
            event.accept()
        else:
            self.close_after_finish = True
            self.hide()
            event.ignore()
