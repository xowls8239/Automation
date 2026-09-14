from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt

class ReleaserReviewPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 상단 제어 패널
        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 10px;")
        top_layout = QHBoxLayout(top_panel)

        self.btn_sync = QPushButton("설계 검토 완료 품목 동기화")
        self.btn_sync.setStyleSheet("background-color: #365880; color: white; padding: 8px 14px; font-weight: bold; border-radius: 4px;")
        self.btn_sync.clicked.connect(self.sync_reviewed_items)

        self.lbl_info = QLabel("검토 완료 대기: 0건")
        self.lbl_info.setStyleSheet("color: #bbbbbb; font-weight: bold; margin-left: 10px;")

        self.btn_host_and_release = QPushButton("도면 CDN 호스팅 및 최종 릴리즈")
        self.btn_host_and_release.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_host_and_release.clicked.connect(self.start_process)

        top_layout.addWidget(self.btn_sync)
        top_layout.addWidget(self.lbl_info)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_host_and_release)
        layout.addWidget(top_panel)

        # 설계 검토 전용 그리드
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["LOT 식별자", "품목 규격명", "로컬 도면 수", "CDN 변환 상태", "목표 마진가", "릴리즈 상태"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        layout.addWidget(self.table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2b2d30; border-radius: 4px; text-align: center; color: white; height: 18px; }
            QProgressBar::chunk { background-color: #3574f0; }
        """)
        layout.addWidget(self.progress_bar)

    def sync_reviewed_items(self):
        sample_items = [
            ("REV-2026-001", "초경 합금 엔드밀 가공용 스핀들 척", "4장", "변환 대기", "48,000원", "검토 완료"),
            ("REV-2026-002", "고정밀 다이아몬드 코어 드릴 비트", "6장", "변환 대기", "125,000원", "검토 완료")
        ]
        self.table.setRowCount(0)
        for row, data in enumerate(sample_items):
            self.table.insertRow(row)
            for col, val in enumerate(data):
                self.table.setItem(row, col, QTableWidgetItem(val))
        self.lbl_info.setText(f"검토 완료 대기: {len(sample_items)}건")

    def start_process(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "품목 없음", "동기화할 설계 검토 완료 품목이 없습니다.")
            return
        QMessageBox.information(self, "공정 실행", "로컬 도면 CDN 변환 및 최종 릴리즈 프로세스를 시작합니다.")
