"""Minimal main window for Martelo Orçamentos V3."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """Application shell window."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Martelo Orçamentos V3")
        self.resize(1100, 720)

        title = QLabel("Martelo Orçamentos V3")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(title)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
