from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QCheckBox, QMessageBox, QLabel
)

from core.account_config import create_naver_api_client
from core.product_db import fetch_all_products, save_to_tech_library


class ProductImportPage(QWidget):
    def __init__(self):
        super().__init__()
        self.api_client = None      # 지연 생성 (버튼 누를 때 생성)
        self.fetched_rows = []      # 가져온 원본 데이터 (승인 전 임시 보관)

        layout = QVBoxLayout(self)

        title = QLabel("샘플 데이터 (제품 가져오기)")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.fetch_btn = QPushButton("제품 가져오기")
        self.fetch_btn.setStyleSheet(
            "background-color: #365880; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;"
        )
        self.fetch_btn.clicked.connect(self.on_fetch_clicked)
        layout.addWidget(self.fetch_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["선택", "상품명", "가격", "재고"])
        layout.addWidget(self.table)

        self.approve_btn = QPushButton("선택 항목 기술 라이브러리에 저장")
        self.approve_btn.setStyleSheet(
            "background-color: #2e6930; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;"
        )
        self.approve_btn.setEnabled(False)
        self.approve_btn.clicked.connect(self.on_approve_clicked)
        layout.addWidget(self.approve_btn)

    def on_fetch_clicked(self):
        try:
            if self.api_client is None:
                self.api_client = create_naver_api_client()
        except ValueError as e:
            QMessageBox.critical(self, "설정 필요", str(e))
            return

        self.fetched_rows = fetch_all_products(self.api_client)
        self.table.setRowCount(len(self.fetched_rows))
        for i, row in enumerate(self.fetched_rows):
            checkbox = QCheckBox()
            self.table.setCellWidget(i, 0, checkbox)
            self.table.setItem(i, 1, QTableWidgetItem(row.get("product_name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.get("sale_price", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("stock_quantity", ""))))
        self.approve_btn.setEnabled(len(self.fetched_rows) > 0)

    def on_approve_clicked(self):
        selected_rows = []
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if checkbox and checkbox.isChecked():
                selected_rows.append(self.fetched_rows[i])

        if not selected_rows:
            QMessageBox.warning(self, "선택 없음", "저장할 항목을 하나 이상 선택해 주세요.")
            return

        save_to_tech_library(selected_rows)
        QMessageBox.information(self, "저장 완료", f"{len(selected_rows)}건이 기술 라이브러리에 저장되었습니다.")