import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("yahrajApp")
        self.resize(800, 500)

        # Sidebar with navigation entries.
        self.sidebar: QListWidget = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.addItems(["Home", "Settings"])
        self.sidebar.setCurrentRow(0)

        # Pages shown on the right, one per sidebar entry.
        self.stack: QStackedWidget = QStackedWidget()
        self.home_page: QWidget = self._make_page("Hello homepage,")
        self.settings_page: QWidget = self._make_page("Hello setting page")
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.settings_page)

        # Selecting a sidebar entry switches the visible page.
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._apply_styles()

    @staticmethod
    def _make_page(text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px;")
        layout.addWidget(label)
        return page

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QListWidget {
                background-color: #2c313a;
                color: #d7dae0;
                border: none;
                font-size: 15px;
                outline: 0;
            }
            QListWidget::item {
                padding: 14px 18px;
            }
            QListWidget::item:selected {
                background-color: #3d8bfd;
                color: #ffffff;
                border-left: 4px solid #ffce00;
            }
            QListWidget::item:hover {
                background-color: #3a4150;
            }
            QStackedWidget {
                background-color: #f5f6f8;
            }
            """
        )


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
