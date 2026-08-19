from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)


def vbox(widget, margins=(0, 0, 0, 0), spacing=0):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def hbox(widget, margins=(0, 0, 0, 0), spacing=0):
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


class AutoGrowTextEdit(QPlainTextEdit):
    MAX_HEIGHT = 140

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText('Type an instruction...')
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.textChanged.connect(self.resize_to_content)
        self.resize_to_content()

    def resize_to_content(self):
        height = int(self.document().size().height()) + 14
        self.setFixedHeight(min(max(height, 42), self.MAX_HEIGHT))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.window().send()
            event.accept()
            return
        super().keyPressEvent(event)


class Trace(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.open = True
        self.done = False
        self.user_opened = False
        self.button = QPushButton()
        self.button.setObjectName('traceButton')
        self.button.clicked.connect(self.toggle)
        self.body_widget = QWidget()
        self.body = vbox(self.body_widget, margins=(10, 2, 0, 2), spacing=8)
        box = vbox(self, margins=(0, 1, 0, 1), spacing=2)
        box.addWidget(self.button)
        box.addWidget(self.body_widget)
        self.refresh()

    def add_step(self, label, detail):
        row = QFrame()
        layout = vbox(row, spacing=2)
        title = QLabel(f'›  {label}')
        title.setObjectName('stepTitle')
        detail_label = QLabel(detail)
        detail_label.setObjectName('stepDetail')
        detail_label.setWordWrap(True)
        detail_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(title)
        layout.addWidget(detail_label)
        self.body.addWidget(row)
        self.refresh()

    def refresh(self, seconds=0):
        state = 'Worked for' if self.done else 'Working for'
        self.button.setText(f'{"⌄" if self.open else "›"}  {state} {seconds}s')
        self.body_widget.setVisible(self.open)

    def finish(self, seconds):
        self.done = True
        if not self.user_opened:
            self.open = False
        self.refresh(seconds)

    def toggle(self):
        self.user_opened = True
        self.open = not self.open
        self.refresh()
