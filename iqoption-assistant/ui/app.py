from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.controller import UiController
from ui.main_window import MainWindow
from ui.theme import APP_STYLE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UI desktop premium do iqoption-assistant.")
    parser.add_argument("--smoke-test", action="store_true", help="Inicializa a UI em modo curto para validacao automatizada.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("IQ Option Assistant")
    app.setStyleSheet(APP_STYLE)

    base_dir = Path(__file__).resolve().parents[1]
    controller = UiController()
    controller.start()

    window = MainWindow(controller, base_dir)
    window.show()

    if args.smoke_test:
        QTimer.singleShot(1500, app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

