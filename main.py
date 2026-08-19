import sys
from pathlib import Path
from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication
from app.window import MainWindow


def main():
    load_dotenv()
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    qss = Path(__file__).parent / 'app' / 'style.qss'
    if qss.exists():
        app.setStyleSheet(qss.read_text(encoding='utf-8'))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
