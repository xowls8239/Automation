from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ReviewPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel("설계 검토 (AI 규격 최적화 · 옵션 정제 · Fabric.js 도면 캔버스)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #7a7e85; font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)
