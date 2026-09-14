from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class PartsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        lbl = QLabel("자사 제품 분석 (형상 이미지 매칭 및 공급망 신뢰도 검증 엔진)")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #7a7e85; font-size: 16px; font-weight: bold;")
        layout.addWidget(lbl)