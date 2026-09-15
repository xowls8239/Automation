from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QFrame, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal

from .vendor_collector_page import load_vendor_db, upsert_vendor_research_status


# ----------------------------------------------------------------------
# 소싱 워커
# ----------------------------------------------------------------------
class ProductSourcingWorker(QThread):
    """선택된 거래처마다 '판매된 제품'만 골라 상품명/카테고리/가격/썸네일을 가져온다.

    ⚠ 실제 크롤링 로직(사이트별 상품목록 정렬 방식, 셀렉터 등)은 거래처 플랫폼마다
    구조가 달라 여기서는 자리(스텁)만 잡아뒀다. 스마트스토어인지, 별도 자사몰인지에 따라
    실제 페이지 URL 패턴/파싱 방식을 확정한 뒤 fetch_sold_products()의 내용을 채워야 한다.
    """
    log_signal = Signal(str)
    product_found_signal = Signal(dict)   # {vendor_url, name, category, price, thumbnail}
    vendor_done_signal = Signal(str)       # vendor_url (소싱 완료된 거래처)
    finished_signal = Signal(int)

    def __init__(self, vendor_urls: list[str]):
        super().__init__()
        self.vendor_urls = vendor_urls
        self.is_running = True

    def stop(self):
        self.is_running = False

    def fetch_sold_products(self, vendor_url: str) -> list[dict]:
        """TODO: 거래처별 '판매량순 정렬 + 마지막 리뷰 상품 이전까지'를 실제로 수집하는 부분.
        지금은 자리만 잡아둔 상태라 빈 리스트를 반환한다."""
        self.log_signal.emit(f"  - {vendor_url}: 상품 조회 로직 미구현 (TODO)")
        return []

    def run(self):
        total_found = 0
        for vendor_url in self.vendor_urls:
            if not self.is_running:
                break
            self.log_signal.emit(f"[조회] {vendor_url} 판매 제품 확인 중...")

            products = self.fetch_sold_products(vendor_url)
            for p in products:
                if not self.is_running:
                    break
                total_found += 1
                self.product_found_signal.emit({
                    "vendor_url": vendor_url,
                    "name": p.get("name", ""),
                    "category": p.get("category", ""),
                    "price": p.get("price", 0),
                    "thumbnail": p.get("thumbnail", ""),
                })

            # 조회를 마친 거래처는 조사완료로 표시 (제품이 0건이었어도 '확인은 했다'는 의미)
            upsert_vendor_research_status(vendor_url, "완료")
            self.vendor_done_signal.emit(vendor_url)

        self.finished_signal.emit(total_found)


# ----------------------------------------------------------------------
# 메인 페이지
# ----------------------------------------------------------------------
class ProductSourcingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.checkboxes = {}  # vendor_url -> QCheckBox

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("경쟁사 제품 조회")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        subtitle = QLabel("적합 판정되었고 아직 제품조회를 안 한 거래처 중에서 선택해 판매된 제품만 소싱합니다.")
        subtitle.setStyleSheet("color: #9da0a8; font-size: 12px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        # ---------------- 대상 거래처 선택 ----------------
        root.addWidget(QLabel("소싱 대상 거래처 (적합 + 제품조회 미완료)"))
        self.candidate_table = QTableWidget(0, 3)
        self.candidate_table.setHorizontalHeaderLabels(["선택", "거래처명", "거래처 주소"])
        self.candidate_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.candidate_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.candidate_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.candidate_table.setFixedHeight(160)
        self.candidate_table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        root.addWidget(self.candidate_table)

        row_btns = QHBoxLayout()
        self.btn_select_all = QPushButton("전체 선택")
        self.btn_select_all.setStyleSheet("background-color: #43454a; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_select_all.clicked.connect(lambda: self.toggle_all(True))
        self.btn_select_none = QPushButton("전체 해제")
        self.btn_select_none.setStyleSheet("background-color: #43454a; color: white; padding: 6px 14px; border-radius: 4px;")
        self.btn_select_none.clicked.connect(lambda: self.toggle_all(False))
        self.btn_start = QPushButton("선택 소싱 시작")
        self.btn_start.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_sourcing)
        row_btns.addWidget(self.btn_select_all)
        row_btns.addWidget(self.btn_select_none)
        row_btns.addStretch()
        row_btns.addWidget(self.btn_start)
        root.addLayout(row_btns)

        # ---------------- 진행 로그 ----------------
        root.addWidget(QLabel("진행 로그"))
        from PySide6.QtWidgets import QTextEdit
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(80)
        self.txt_log.setStyleSheet("background-color: #1e1f22; color: #98c379; font-family: Consolas, monospace;")
        root.addWidget(self.txt_log)

        # ---------------- 소싱 결과 ----------------
        root.addWidget(QLabel("소싱된 판매 제품 (상품명 / 카테고리 / 가격 / 썸네일)"))
        self.result_table = QTableWidget(0, 5)
        self.result_table.setHorizontalHeaderLabels(["거래처", "상품명", "카테고리", "가격", "썸네일 URL"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        root.addWidget(self.result_table)

        self.refresh_candidate_list()

    # ------------------------------------------------------------
    def refresh_candidate_list(self):
        """적합 + 제품조회 미완료인 거래처만 다시 불러온다."""
        self.candidate_table.setRowCount(0)
        self.checkboxes.clear()

        db = load_vendor_db()
        candidates = {
            url: v for url, v in db.items()
            if v.get("status") == "적합" and v.get("research_status") != "완료"
        }

        for vendor_url, info in candidates.items():
            row = self.candidate_table.rowCount()
            self.candidate_table.insertRow(row)

            chk = QCheckBox()
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.candidate_table.setCellWidget(row, 0, chk_widget)
            self.checkboxes[vendor_url] = chk

            self.candidate_table.setItem(row, 1, QTableWidgetItem(info.get("vendor_name", "")))
            self.candidate_table.setItem(row, 2, QTableWidgetItem(vendor_url))

    def toggle_all(self, checked: bool):
        for chk in self.checkboxes.values():
            chk.setChecked(checked)

    # ------------------------------------------------------------
    def start_sourcing(self):
        selected = [url for url, chk in self.checkboxes.items() if chk.isChecked()]
        if not selected:
            QMessageBox.warning(self, "선택 없음", "소싱할 거래처를 하나 이상 선택해 주세요.")
            return

        self.result_table.setRowCount(0)
        self.txt_log.clear()
        self.btn_start.setEnabled(False)

        self.worker = ProductSourcingWorker(selected)
        self.worker.log_signal.connect(self.append_log)
        self.worker.product_found_signal.connect(self.add_product_row)
        self.worker.vendor_done_signal.connect(self.on_vendor_done)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def append_log(self, text: str):
        self.txt_log.append(text)

    def add_product_row(self, data: dict):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(data["vendor_url"]))
        self.result_table.setItem(row, 1, QTableWidgetItem(data["name"]))
        self.result_table.setItem(row, 2, QTableWidgetItem(data["category"]))
        self.result_table.setItem(row, 3, QTableWidgetItem(f"{data['price']:,}원"))
        self.result_table.setItem(row, 4, QTableWidgetItem(data["thumbnail"]))

    def on_vendor_done(self, vendor_url: str):
        self.append_log(f"[완료] {vendor_url} 제품조회 완료 처리됨")

    def on_finished(self, total_found: int):
        self.append_log(f"[전체 완료] 총 {total_found:,}건 소싱됨")
        self.btn_start.setEnabled(True)
        self.refresh_candidate_list()  # 방금 완료 처리된 거래처는 목록에서 빠짐