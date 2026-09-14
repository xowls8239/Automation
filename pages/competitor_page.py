from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class CompetitorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        lbl = QLabel("경쟁사/제품 분석 (거래처 탐색 · 검증 · 실적 규격 마이닝 엔진)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #7a7e85; font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)
