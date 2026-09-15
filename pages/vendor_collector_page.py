import os
import re
import json
import webbrowser
from datetime import datetime
from urllib.parse import urlparse

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QSpinBox, QLineEdit, QCheckBox, QFrame, QMessageBox,
    QDialog, QFormLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal

# ----------------------------------------------------------------------
# 설정 파일 경로
# ----------------------------------------------------------------------
SEARCH_API_CONFIG_PATH = "config_search_api.json"       # 조회용 오픈API client_id/secret
VENDOR_JUDGE_DB_PATH = "vendor_judgement_db.json"        # 거래처 적합/부적합 판정 기록 (중복 방지용)


# ----------------------------------------------------------------------
# 조회용 오픈API 설정 다이얼로그
# ----------------------------------------------------------------------
class SearchApiConfigDialog(QDialog):
    """외부 데이터 조회용 오픈API 키를 입력/저장.
    거래처 계정 연동(커머스API)과는 완전히 별개의 서비스이며 IP 등록이 필요 없다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("조회용 오픈API 키 설정")
        self.resize(460, 220)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")

        layout = QVBoxLayout(self)
        desc = QLabel(
            "개발자센터에서 발급받은 조회용 오픈API의\n"
            "Client ID / Client Secret을 입력하세요. (IP 등록 불필요)"
        )
        desc.setStyleSheet("color: #8c8e94; font-size: 12px;")
        layout.addWidget(desc)

        form = QFormLayout()
        self.id_input = QLineEdit()
        self.id_input.setStyleSheet(self._input_style())
        self.secret_input = QLineEdit()
        self.secret_input.setEchoMode(QLineEdit.Password)
        self.secret_input.setStyleSheet(self._input_style())
        form.addRow("Client ID:", self.id_input)
        form.addRow("Client Secret:", self.secret_input)
        layout.addLayout(form)

        btn_save = QPushButton("저장")
        btn_save.setStyleSheet(
            "background-color: #3574f0; color: white; padding: 10px; font-weight: bold; border-radius: 4px;"
        )
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)

        self.load_config()

    @staticmethod
    def _input_style():
        return ("background-color: #1e1f22; color: #ffffff; padding: 6px;"
                " border: 1px solid #393b40; border-radius: 4px;")

    def load_config(self):
        if os.path.exists(SEARCH_API_CONFIG_PATH):
            with open(SEARCH_API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.id_input.setText(data.get("client_id", ""))
                self.secret_input.setText(data.get("client_secret", ""))

    def save_config(self):
        data = {
            "client_id": self.id_input.text().strip(),
            "client_secret": self.secret_input.text().strip(),
        }
        with open(SEARCH_API_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "저장 완료", "오픈API 키가 저장되었습니다.")
        self.accept()


def load_search_api_keys():
    if not os.path.exists(SEARCH_API_CONFIG_PATH):
        return "", ""
    with open(SEARCH_API_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("client_id", ""), data.get("client_secret", "")


# ----------------------------------------------------------------------
# 거래처 판정 DB (적합/부적합 기록 + 중복 조회 방지)
# ----------------------------------------------------------------------
def load_vendor_db() -> dict:
    if not os.path.exists(VENDOR_JUDGE_DB_PATH):
        return {}
    with open(VENDOR_JUDGE_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_vendor_db(db: dict):
    with open(VENDOR_JUDGE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def upsert_vendor_judgement(vendor_url: str, vendor_name: str, keyword: str, status: str):
    """적합/부적합 판정 기록. 조사 상태(research_status)는 건드리지 않는다 (별도 축)."""
    db = load_vendor_db()
    entry = db.get(vendor_url, {})
    entry.update({
        "vendor_name": vendor_name,
        "status": status,  # "미판정" / "적합" / "부적합"
        "last_keyword": keyword,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    entry.setdefault("first_seen_at", entry["updated_at"])
    entry.setdefault("research_status", "미완료")  # 신규 등록 시 기본값
    db[vendor_url] = entry
    save_vendor_db(db)
    return entry


def upsert_vendor_research_status(vendor_url: str, research_status: str):
    """거래처에서 상품 소싱(조사)을 완료했는지 여부만 별도로 기록.
    적합/부적합 판정과는 독립적인 축이다."""
    db = load_vendor_db()
    entry = db.get(vendor_url, {})
    entry["research_status"] = research_status  # "완료" / "미완료"
    entry["research_updated_at"] = datetime.now().isoformat(timespec="seconds")
    db[vendor_url] = entry
    save_vendor_db(db)
    return entry


def derive_vendor_url(item_link: str) -> str:
    """조회 결과 링크에서 '거래처 홈' 주소를 최대한 유추한다.
    일부 플랫폼은 경로에 거래처 식별자가 포함되므로 별도 처리, 그 외는 도메인 루트를 거래처 홈으로 간주."""
    try:
        parsed = urlparse(item_link)
    except Exception:
        return item_link

    if "smartstore.naver.com" in parsed.netloc or "brand.naver.com" in parsed.netloc:
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            return f"{parsed.scheme}://{parsed.netloc}/{parts[0]}"
    return f"{parsed.scheme}://{parsed.netloc}"


def strip_html_tags(text: str) -> str:
    return re.sub(r"</?b>", "", text or "")


# ----------------------------------------------------------------------
# 키워드 기반 거래처 조회 워커
# ----------------------------------------------------------------------
class KeywordVendorSearchWorker(QThread):
    log_signal = Signal(str)
    vendor_found_signal = Signal(dict)   # {vendor_url, vendor_name, keyword, sample_item}
    finished_signal = Signal(int)
    error_signal = Signal(str)

    def __init__(self, keywords: list[str], client_id: str, client_secret: str,
                 pages: int, rank_from: int, rank_to: int, skip_known: bool):
        super().__init__()
        self.keywords = keywords
        self.client_id = client_id
        self.client_secret = client_secret
        self.pages = max(1, pages)
        self.rank_from = rank_from
        self.rank_to = rank_to
        self.skip_known = skip_known
        self.is_running = True
        self.seen_vendors_this_run = set()

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            import httpx
        except ImportError:
            self.error_signal.emit("httpx 모듈이 없습니다. (pip install httpx)")
            return

        known_db = load_vendor_db() if self.skip_known else {}
        found_count = 0
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

        for keyword in self.keywords:
            if not self.is_running:
                break
            keyword = keyword.strip()
            if not keyword:
                continue

            self.log_signal.emit(f"[조회] '{keyword}' 키워드 조회 시작...")
            global_rank = 0

            with httpx.Client(timeout=10.0) as client:
                for page in range(self.pages):
                    if not self.is_running:
                        break

                    start = page * 100 + 1
                    if start > 1000:  # 오픈API 제약: start는 최대 1000
                        self.log_signal.emit(f"  - '{keyword}': 조회 가능 범위(최대 1,000건) 도달")
                        break

                    params = {"query": keyword, "display": 100, "start": start, "sort": "sim"}
                    try:
                        res = client.get(
                            "https://openapi.naver.com/v1/search/shop.json",
                            headers=headers, params=params
                        )
                    except Exception as e:
                        self.error_signal.emit(f"'{keyword}' 조회 중 통신 오류: {e}")
                        break

                    if res.status_code != 200:
                        self.error_signal.emit(
                            f"'{keyword}' 조회 실패 (HTTP {res.status_code}): {res.text[:200]}"
                        )
                        break

                    items = res.json().get("items", [])
                    if not items:
                        break

                    for item in items:
                        global_rank += 1
                        if self.rank_to and global_rank > self.rank_to:
                            break
                        if self.rank_from and global_rank < self.rank_from:
                            continue

                        vendor_name = item.get("mallName", "").strip()
                        link = item.get("link", "").strip()
                        if not vendor_name or not link:
                            continue

                        vendor_url = derive_vendor_url(link)

                        if vendor_url in self.seen_vendors_this_run:
                            continue  # 이번 실행 내 중복 제거
                        if self.skip_known and vendor_url in known_db:
                            continue  # 이미 판정된 거래처 제외

                        self.seen_vendors_this_run.add(vendor_url)
                        found_count += 1

                        self.vendor_found_signal.emit({
                            "vendor_url": vendor_url,
                            "vendor_name": vendor_name,
                            "keyword": keyword,
                            "rank": global_rank,
                            "sample_item": strip_html_tags(item.get("title", "")),
                        })

                    self.msleep(120)  # 호출 간 최소한의 간격

            self.log_signal.emit(f"[완료] '{keyword}' 조회 종료")

        self.finished_signal.emit(found_count)


# ----------------------------------------------------------------------
# 메인 페이지 위젯
# ----------------------------------------------------------------------
class VendorCollectorPage(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("거래처 수집기")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        subtitle = QLabel("키워드로 노출되는 거래처를 수집하고 조건으로 필터링합니다.")
        subtitle.setStyleSheet("color: #9da0a8; font-size: 12px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        # ---------------- 조회 설정 패널 ----------------
        panel = QFrame()
        panel.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 12px;")
        panel_layout = QVBoxLayout(panel)

        row_api = QHBoxLayout()
        self.lbl_api_status = QLabel()
        row_api.addWidget(self.lbl_api_status)
        btn_api_config = QPushButton("조회용 오픈API 키 설정")
        btn_api_config.setStyleSheet("background-color: #43454a; color: white; padding: 5px 10px; border-radius: 4px;")
        btn_api_config.clicked.connect(self.open_api_config)
        row_api.addWidget(btn_api_config)
        row_api.addStretch()
        panel_layout.addLayout(row_api)

        panel_layout.addWidget(QLabel("키워드 (한 줄에 하나씩 입력, 여러 줄 가능)"))
        self.txt_keywords = QTextEdit()
        self.txt_keywords.setPlaceholderText("A제품\nB제품\nC제품")
        self.txt_keywords.setFixedHeight(80)
        self.txt_keywords.setStyleSheet("background-color: #1e1f22; color: #dfe1e5; border: 1px solid #393b40;")
        panel_layout.addWidget(self.txt_keywords)

        row_opts = QHBoxLayout()
        row_opts.addWidget(QLabel("조회 페이지 수 (1페이지=100건)"))
        self.spin_pages = QSpinBox()
        self.spin_pages.setRange(1, 10)
        self.spin_pages.setValue(1)
        self.spin_pages.setStyleSheet("background-color: #1e1f22; color: white; padding: 3px;")
        row_opts.addWidget(self.spin_pages)

        row_opts.addSpacing(20)
        row_opts.addWidget(QLabel("전체 노출 순위 범위"))
        self.input_rank_from = QLineEdit()
        self.input_rank_from.setPlaceholderText("1")
        self.input_rank_from.setFixedWidth(60)
        self.input_rank_from.setStyleSheet("background-color: #1e1f22; color: white; padding: 3px;")
        self.input_rank_to = QLineEdit()
        self.input_rank_to.setPlaceholderText("비워두면 제한 없음")
        self.input_rank_to.setFixedWidth(120)
        self.input_rank_to.setStyleSheet("background-color: #1e1f22; color: white; padding: 3px;")
        row_opts.addWidget(self.input_rank_from)
        row_opts.addWidget(QLabel("-"))
        row_opts.addWidget(self.input_rank_to)
        row_opts.addStretch()
        panel_layout.addLayout(row_opts)

        self.chk_skip_known = QCheckBox("이미 판정한 거래처는 재수집에서 제외 (중복 방지)")
        self.chk_skip_known.setChecked(True)
        self.chk_skip_known.setStyleSheet("color: #dfe1e5;")
        panel_layout.addWidget(self.chk_skip_known)

        row_btns = QHBoxLayout()
        self.btn_start = QPushButton("수집 시작")
        self.btn_start.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_collection)
        self.btn_stop = QPushButton("중단")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #8c2e2e; color: white; padding: 8px 20px; font-weight: bold; border-radius: 4px; }
            QPushButton:disabled { background-color: #4a3636; color: #7a7a7a; }
        """)
        self.btn_stop.clicked.connect(self.stop_collection)
        row_btns.addWidget(self.btn_start)
        row_btns.addWidget(self.btn_stop)
        row_btns.addStretch()
        panel_layout.addLayout(row_btns)

        root.addWidget(panel)

        # ---------------- 진행 로그 ----------------
        root.addWidget(QLabel("진행 로그"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(90)
        self.txt_log.setStyleSheet("background-color: #1e1f22; color: #98c379; font-family: Consolas, monospace;")
        root.addWidget(self.txt_log)

        # ---------------- 결과 테이블 ----------------
        root.addWidget(QLabel("수집된 거래처 목록 (거래처명을 누르면 해당 페이지로 이동합니다)"))
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["거래처명 (클릭 시 이동)", "발견 키워드", "노출 순위", "샘플 품목명",
             "판정 상태", "판정", "조사 상태", "조사 처리"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        root.addWidget(self.table)

        self.refresh_api_status()

    # ------------------------------------------------------------
    def refresh_api_status(self):
        cid, csec = load_search_api_keys()
        if cid and csec:
            self.lbl_api_status.setText("● 오픈API 키 등록됨")
            self.lbl_api_status.setStyleSheet("color: #61afef; font-weight: bold;")
        else:
            self.lbl_api_status.setText("● 오픈API 키 미등록")
            self.lbl_api_status.setStyleSheet("color: #e06c75; font-weight: bold;")

    def open_api_config(self):
        dlg = SearchApiConfigDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.refresh_api_status()

    # ------------------------------------------------------------
    def start_collection(self):
        cid, csec = load_search_api_keys()
        if not cid or not csec:
            QMessageBox.critical(self, "API 키 필요", "[조회용 오픈API 키 설정]에서 Client ID/Secret을 먼저 등록해 주세요.")
            return

        keywords = [k for k in self.txt_keywords.toPlainText().splitlines() if k.strip()]
        if not keywords:
            QMessageBox.warning(self, "키워드 없음", "조회할 키워드를 한 줄에 하나씩 입력해 주세요.")
            return

        try:
            rank_from = int(self.input_rank_from.text().strip() or "1")
        except ValueError:
            rank_from = 1
        rank_to_text = self.input_rank_to.text().strip()
        rank_to = int(rank_to_text) if rank_to_text.isdigit() else 0  # 0 = 제한 없음

        self.table.setRowCount(0)
        self.txt_log.clear()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self.worker = KeywordVendorSearchWorker(
            keywords=keywords,
            client_id=cid,
            client_secret=csec,
            pages=self.spin_pages.value(),
            rank_from=rank_from,
            rank_to=rank_to,
            skip_known=self.chk_skip_known.isChecked(),
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.vendor_found_signal.connect(self.add_vendor_row)
        self.worker.error_signal.connect(self.on_error)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def stop_collection(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.append_log("[중단 요청됨] 진행 중인 요청까지만 처리하고 종료합니다.")
            self.btn_stop.setEnabled(False)

    def append_log(self, text: str):
        self.txt_log.append(text)

    def on_error(self, msg: str):
        self.append_log(f"[오류] {msg}")

    def on_finished(self, count: int):
        self.append_log(f"[전체 완료] 신규 거래처 {count:,}건 수집됨")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    # ------------------------------------------------------------
    def add_vendor_row(self, data: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # 거래처명 - 클릭 시 브라우저로 이동
        btn_link = QPushButton(data["vendor_name"])
        btn_link.setCursor(Qt.PointingHandCursor)
        btn_link.setStyleSheet(
            "text-align:left; color:#61afef; background:transparent; border:none; text-decoration: underline;"
        )
        btn_link.clicked.connect(lambda _, url=data["vendor_url"]: webbrowser.open(url))
        self.table.setCellWidget(row, 0, btn_link)

        self.table.setItem(row, 1, QTableWidgetItem(data["keyword"]))
        self.table.setItem(row, 2, QTableWidgetItem(str(data["rank"])))
        self.table.setItem(row, 3, QTableWidgetItem(data["sample_item"][:40]))

        status_item = QTableWidgetItem("미판정")
        status_item.setForeground(Qt.yellow)
        self.table.setItem(row, 4, status_item)

        # 적합/부적합 버튼
        judge_widget = QWidget()
        judge_layout = QHBoxLayout(judge_widget)
        judge_layout.setContentsMargins(2, 2, 2, 2)
        btn_ok = QPushButton("적합")
        btn_ok.setStyleSheet("background-color: #2e6930; color: white; padding: 3px 8px; border-radius: 3px;")
        btn_ng = QPushButton("부적합")
        btn_ng.setStyleSheet("background-color: #8c2e2e; color: white; padding: 3px 8px; border-radius: 3px;")

        vendor_url = data["vendor_url"]
        vendor_name = data["vendor_name"]
        keyword = data["keyword"]

        btn_ok.clicked.connect(lambda _, r=row: self.judge_vendor(r, vendor_url, vendor_name, keyword, "적합"))
        btn_ng.clicked.connect(lambda _, r=row: self.judge_vendor(r, vendor_url, vendor_name, keyword, "부적합"))
        judge_layout.addWidget(btn_ok)
        judge_layout.addWidget(btn_ng)
        self.table.setCellWidget(row, 5, judge_widget)

        # 조사 상태 (판정과 별개 축) - 신규 등록 시 기본 "미완료"
        research_item = QTableWidgetItem("미완료")
        research_item.setForeground(Qt.yellow)
        self.table.setItem(row, 6, research_item)

        research_widget = QWidget()
        research_layout = QHBoxLayout(research_widget)
        research_layout.setContentsMargins(2, 2, 2, 2)
        btn_research_done = QPushButton("조사완료")
        btn_research_done.setStyleSheet("background-color: #365880; color: white; padding: 3px 8px; border-radius: 3px;")
        btn_research_undo = QPushButton("미완료로")
        btn_research_undo.setStyleSheet("background-color: #43454a; color: white; padding: 3px 8px; border-radius: 3px;")

        btn_research_done.clicked.connect(lambda _, r=row, u=vendor_url: self.mark_research(r, u, "완료"))
        btn_research_undo.clicked.connect(lambda _, r=row, u=vendor_url: self.mark_research(r, u, "미완료"))
        research_layout.addWidget(btn_research_done)
        research_layout.addWidget(btn_research_undo)
        self.table.setCellWidget(row, 7, research_widget)

    def judge_vendor(self, row: int, vendor_url: str, vendor_name: str, keyword: str, status: str):
        upsert_vendor_judgement(vendor_url, vendor_name, keyword, status)
        status_item = QTableWidgetItem(status)
        status_item.setForeground(Qt.green if status == "적합" else Qt.red)
        self.table.setItem(row, 4, status_item)
        self.append_log(f"[판정] {vendor_name} -> {status} 로 기록됨")

    def mark_research(self, row: int, vendor_url: str, research_status: str):
        upsert_vendor_research_status(vendor_url, research_status)
        item = QTableWidgetItem(research_status)
        item.setForeground(Qt.green if research_status == "완료" else Qt.yellow)
        self.table.setItem(row, 6, item)
        self.append_log(f"[조사 상태] {vendor_url} -> {research_status} 로 기록됨")