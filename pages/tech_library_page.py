import os
import json
import math
import time
import base64
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QFrame, QComboBox, QMessageBox, QDialog,
    QLineEdit, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal

CONFIG_PATH = "config_accounts.json"

# ==========================================
# 1. 네이버 토큰 검증 헬퍼
# ==========================================
def verify_naver_token(client_id: str, client_secret: str) -> tuple[bool, str]:
    """실제 네이버 서버와 통신해 토큰 발급(로그인 연동) 성공 여부 검증"""
    if not client_id.strip() or not client_secret.strip():
        return False, "애플리케이션 ID 또는 시크릿 키가 입력되지 않았습니다."
    try:
        import bcrypt
        import httpx
    except ImportError:
        return False, "필수 모듈 미설치 (터미널에서 'pip install bcrypt httpx' 실행 필요)"

    now = time.time()
    timestamp = int(now * 1000)
    pwd = f"{client_id.strip()}_{timestamp}".encode("utf-8")
    hashed = bcrypt.hashpw(pwd, client_secret.strip().encode("utf-8"))
    signature = base64.standard_b64encode(hashed).decode("utf-8")

    token_url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    token_data = {
        "client_id": client_id.strip(),
        "timestamp": timestamp,
        "client_secret_sign": signature,
        "grant_type": "client_credentials",
        "type": "SELF"
    }

    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.post(token_url, data=token_data)
            res_json = res.json()
            if res.status_code == 200 and "access_token" in res_json:
                return True, "네이버 커머스 인증 성공 (스토어 연동 완료)"
            return False, res_json.get("message", res.text)
    except Exception as e:
        return False, f"서버 통신 실패: {str(e)}"

# ==========================================
# 2. 계정 연동 및 로그인 설정 다이얼로그
# ==========================================
class AccountLinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("스마트스토어 채널 계정 연동 (로그인 인증 설정)")
        self.resize(520, 380)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        desc = QLabel("네이버 커머스 API 센터에서 발급받은 계정별 애플리케이션 정보를 입력합니다.")
        desc.setStyleSheet("color: #8c8e94; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(desc)

        form = QFormLayout()
        self.inputs = {}
        for i in range(1, 4):
            id_in = QLineEdit()
            id_in.setPlaceholderText("애플리케이션 ID 입력")
            id_in.setStyleSheet("background-color: #1e1f22; color: #ffffff; padding: 6px; border: 1px solid #393b40; border-radius: 4px;")
            
            sec_in = QLineEdit()
            sec_in.setPlaceholderText("시크릿 키(Secret Key) 입력")
            sec_in.setEchoMode(QLineEdit.Password)
            sec_in.setStyleSheet("background-color: #1e1f22; color: #ffffff; padding: 6px; border: 1px solid #393b40; border-radius: 4px;")

            btn_test = QPushButton(f"채널 #{i} 연동 테스트")
            btn_test.setStyleSheet("background-color: #43454a; color: white; padding: 5px 10px; border-radius: 4px; font-size: 11px;")
            btn_test.clicked.connect(lambda _, idx=i: self.test_connection(idx))

            btn_box = QHBoxLayout()
            btn_box.addWidget(sec_in)
            btn_box.addWidget(btn_test)

            self.inputs[f"acc_{i}"] = (id_in, sec_in)
            form.addRow(QLabel(f"<b>[ 릴리즈 스토어 채널 #{i} ]</b>"))
            form.addRow("클라이언트 ID:", id_in)
            form.addRow("시크릿 키:", btn_box)

        layout.addLayout(form)

        btn_save = QPushButton("계정 연동 저장")
        btn_save.setStyleSheet("background-color: #3574f0; color: white; padding: 10px; font-weight: bold; border-radius: 4px; font-size: 13px;")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)

        self.load_config()

    def test_connection(self, idx):
        id_in, sec_in = self.inputs[f"acc_{idx}"]
        cid = id_in.text().strip()
        csec = sec_in.text().strip()

        success, msg = verify_naver_token(cid, csec)
        if success:
            QMessageBox.information(self, f"채널 #{idx} 연동 성공", f"정상적으로 로그인 연동되었습니다.\n{msg}")
        else:
            QMessageBox.critical(self, f"채널 #{idx} 연동 실패", f"인증에 실패했습니다.\n\n사유: {msg}")

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, (id_in, sec_in) in self.inputs.items():
                    id_in.setText(data.get(k, {}).get("client_id", ""))
                    sec_in.setText(data.get(k, {}).get("client_secret", ""))

    def save_config(self):
        data = {}
        for k, (id_in, sec_in) in self.inputs.items():
            data[k] = {"client_id": id_in.text().strip(), "client_secret": sec_in.text().strip()}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "저장 완료", "스토어 연동 정보가 정상 저장되었습니다.")
        self.accept()

# ==========================================
# 3. 스토어 전수 추출 백그라운드 워커
# ==========================================
class StoreSyncWorker(QThread):
    progress_signal = Signal(int, int, str, dict)
    finished_signal = Signal(int, str)
    error_signal = Signal(str)

    def __init__(self, client_id: str, client_secret: str):
        super().__init__()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.is_running = True

    def run(self):
        try:
            import bcrypt
            import httpx
        except ImportError:
            self.error_signal.emit("필수 라이브러리(bcrypt, httpx)가 없습니다.")
            return

        now = time.time()
        timestamp = int(now * 1000)
        pwd = f"{self.client_id}_{timestamp}".encode("utf-8")
        hashed = bcrypt.hashpw(pwd, self.client_secret.encode("utf-8"))
        signature = base64.standard_b64encode(hashed).decode("utf-8")

        token_url = "https://api.commerce.naver.com/external/v1/oauth2/token"
        token_data = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF"
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(token_url, data=token_data)
                res_json = res.json()
                if res.status_code != 200 or "access_token" not in res_json:
                    raise Exception(f"토큰 발급 실패: {res_json.get('message', res.text)}")
                token = res_json["access_token"]
        except Exception as e:
            self.error_signal.emit(f"네이버 로그인 연동 차단:\n{str(e)}")
            return

        search_url = "https://api.commerce.naver.com/external/v2/products/search"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        page = 1
        size = 50
        total_extracted = 0
        total_elements = 0

        with httpx.Client(timeout=15.0) as client:
            while self.is_running:
                payload = {
                    "page": page,
                    "size": size,
                    "orderType": "REG_DATE",
                    "periodType": "ALL"
                }

                try:
                    res = client.post(search_url, headers=headers, json=payload)
                    res_json = res.json()
                except Exception as e:
                    self.error_signal.emit(f"목록 호출 오류: {str(e)}")
                    return

                contents = res_json.get("contents", [])
                if page == 1:
                    total_elements = res_json.get("totalElements", len(contents))
                    if total_elements == 0:
                        self.finished_signal.emit(0, "등록된 상품이 없습니다.")
                        return

                if not contents:
                    break

                for item in contents:
                    if not self.is_running:
                        break

                    channel_prod = item.get("channelProducts", [{}])[0] if item.get("channelProducts") else {}
                    prod_data = {
                        "prod_no": str(item.get("originProductNo", "")),
                        "name": str(channel_prod.get("name", item.get("name", ""))),
                        "category_id": str(channel_prod.get("categoryId", "")),
                        "price": int(channel_prod.get("salePrice", item.get("salePrice", 0))),
                        "stock": int(channel_prod.get("stockQuantity", item.get("stockQuantity", 0))),
                        "status": str(item.get("statusType", "SALE")),
                        "thumb": str(channel_prod.get("representativeImageUrl", "")),
                        "reg_date": str(item.get("regDate", ""))[:10]
                    }

                    total_extracted += 1
                    pct = min(100, int((total_extracted / max(1, total_elements)) * 100))
                    self.progress_signal.emit(pct, total_extracted, f"추출 중 ({total_extracted:,} / {total_elements:,}건)", prod_data)

                if len(contents) < size:
                    break

                page += 1
                self.msleep(150)

        self.finished_signal.emit(total_extracted, "스토어 품목 데이터베이스 동기화가 완료되었습니다.")

    def stop(self):
        self.is_running = False

# ==========================================
# 4. 기술 라이브러리 메인 페이지
# ==========================================
class TechLibraryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.library_db = []
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 상단 제어 바
        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 10px;")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setSpacing(10)

        self.combo_channel = QComboBox()
        self.combo_channel.addItems(["릴리즈 채널 #1", "릴리즈 채널 #2", "릴리즈 채널 #3"])
        self.combo_channel.setStyleSheet("background-color: #1e1f22; color: #dfe1e5; padding: 6px; min-width: 120px;")
        self.combo_channel.currentIndexChanged.connect(self.check_channel_status)

        # 연동 상태 인디케이터 배지
        self.lbl_auth_badge = QLabel("● 연동 확인 중")
        self.lbl_auth_badge.setStyleSheet("color: #e5c07b; font-size: 12px; font-weight: bold; margin-right: 5px;")

        # 계정 연동 / 로그인 설정 버튼
        self.btn_account_config = QPushButton("스토어 계정 연동 관리")
        self.btn_account_config.setStyleSheet("background-color: #43454a; color: white; padding: 8px 12px; font-weight: bold; border-radius: 4px;")
        self.btn_account_config.clicked.connect(self.open_account_dialog)

        # 동기화 제어 버튼
        self.btn_sync = QPushButton("스토어 전수 규격 동기화")
        self.btn_sync.setStyleSheet("background-color: #365880; color: white; padding: 8px 15px; font-weight: bold; border-radius: 4px;")
        self.btn_sync.clicked.connect(self.start_sync)

        self.btn_stop = QPushButton("동기화 중지")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #8c2e2e; color: white; padding: 8px 14px; font-weight: bold; border-radius: 4px; }
            QPushButton:disabled { background-color: #4a3636; color: #7a7a7a; }
        """)
        self.btn_stop.clicked.connect(self.stop_sync)

        self.btn_export_chunks = QPushButton("1,000개 단위 분할 엑셀 추출")
        self.btn_export_chunks.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_export_chunks.clicked.connect(self.export_1000_chunks)

        top_layout.addWidget(self.combo_channel)
        top_layout.addWidget(self.lbl_auth_badge)
        top_layout.addWidget(self.btn_account_config)
        top_layout.addWidget(self.btn_sync)
        top_layout.addWidget(self.btn_stop)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_export_chunks)
        layout.addWidget(top_panel)

        # 데이터 테이블
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "LOT 식별자", "품목 규격명", "카테고리 ID", "출하가", "재고", "도면 CDN 주소", "등록일자"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        layout.addWidget(self.table)

        # 하단 프로그레스 바
        bottom_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2b2d30; border-radius: 4px; text-align: center; color: white; height: 18px; }
            QProgressBar::chunk { background-color: #3574f0; }
        """)
        self.lbl_status = QLabel("라이브러리 보관 규격: 0건")
        self.lbl_status.setStyleSheet("color: #9da0a8; font-size: 12px; margin-left: 10px;")

        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.lbl_status)
        layout.addLayout(bottom_layout)

        # 시작 시 현재 채널 연동 여부 체크
        self.check_channel_status()

    def check_channel_status(self):
        sel_idx = self.combo_channel.currentIndex() + 1
        if not os.path.exists(CONFIG_PATH):
            self.lbl_auth_badge.setText("● 미연동 (키 부재)")
            self.lbl_auth_badge.setStyleSheet("color: #e06c75; font-size: 12px; font-weight: bold;")
            return

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        acc = cfg.get(f"acc_{sel_idx}", {})
        cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")

        if cid and csec:
            self.lbl_auth_badge.setText("● 연동 정보 등록됨")
            self.lbl_auth_badge.setStyleSheet("color: #61afef; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_auth_badge.setText("● 미연동 (키 누락)")
            self.lbl_auth_badge.setStyleSheet("color: #e06c75; font-size: 12px; font-weight: bold;")

    def open_account_dialog(self):
        dlg = AccountLinkDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.check_channel_status()

    def start_sync(self):
        sel_idx = self.combo_channel.currentIndex() + 1
        if not os.path.exists(CONFIG_PATH):
            QMessageBox.critical(self, "연동 필요", "[스토어 계정 연동 관리]를 눌러 API 키를 먼저 입력해 주세요.")
            return

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        acc = cfg.get(f"acc_{sel_idx}", {})
        cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")

        if not cid or not csec:
            QMessageBox.critical(self, "연동 누락", f"선택한 {self.combo_channel.currentText()}의 인증 키가 없습니다.\n[스토어 계정 연동 관리]에서 등록해 주세요.")
            return

        self.library_db.clear()
        self.table.setRowCount(0)
        self.btn_sync.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export_chunks.setEnabled(False)

        self.worker = StoreSyncWorker(cid, csec)
        self.worker.progress_signal.connect(self.on_item_extracted)
        self.worker.error_signal.connect(self.on_sync_error)
        self.worker.finished_signal.connect(self.on_sync_finished)
        self.worker.start()

    def stop_sync(self):
        if self.worker and self.worker.isRunning():
            self.btn_stop.setEnabled(False)
            self.btn_stop.setText("중지 중...")
            self.worker.stop()

    def on_item_extracted(self, pct, count, status_text, item):
        self.library_db.append(item)
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"{status_text} (DB 누적: {count:,}건)")

        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        self.table.setItem(row_idx, 0, QTableWidgetItem(item["prod_no"]))
        self.table.setItem(row_idx, 1, QTableWidgetItem(item["name"][:35] + "..."))
        self.table.setItem(row_idx, 2, QTableWidgetItem(item["category_id"]))
        self.table.setItem(row_idx, 3, QTableWidgetItem(f"{item['price']:,}원"))
        self.table.setItem(row_idx, 4, QTableWidgetItem(f"{item['stock']:,}"))
        self.table.setItem(row_idx, 5, QTableWidgetItem(item["thumb"]))
        self.table.setItem(row_idx, 6, QTableWidgetItem(item["reg_date"]))
        self.table.scrollToItem(self.table.item(row_idx, 0))

    def on_sync_error(self, err_msg):
        QMessageBox.critical(self, "동기화 오류", err_msg)
        self.reset_ui()

    def on_sync_finished(self, total_count, msg):
        QMessageBox.information(self, "추출 완료", f"{msg}\n총 {total_count:,}건의 규격 데이터가 라이브러리에 적재되었습니다.")
        self.reset_ui()

    def reset_ui(self):
        self.btn_sync.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("동기화 중지")
        self.btn_export_chunks.setEnabled(True)

    def export_1000_chunks(self):
        if not self.library_db:
            QMessageBox.warning(self, "데이터 없음", "추출할 데이터가 없습니다. 먼저 스토어 동기화를 실행해 주세요.")
            return

        folder = QFileDialog.getExistingDirectory(self, "1,000개 단위 분할 엑셀 저장 폴더 선택")
        if not folder:
            return

        total_items = len(self.library_db)
        chunk_size = 1000
        num_chunks = math.ceil(total_items / chunk_size)
        channel_label = self.combo_channel.currentText().replace(" ", "_").replace("#", "")

        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, total_items)
            chunk_data = self.library_db[start_idx:end_idx]

            rows = []
            for item in chunk_data:
                rows.append({
                    "⊙상품코드": "",
                    "⊙상품명": item["name"],
                    "⊙카테고리 (최하단 카테고리 코드)": item["category_id"],
                    "⊙자체상품코드": item["prod_no"],
                    "⊙판매가": item["price"],
                    "재고수(단품)": item["stock"],
                    "⊙대표이미지": item["thumb"],
                    "등록일시": item["reg_date"]
                })

            df_chunk = pd.DataFrame(rows)
            file_name = f"Processed_DB_{channel_label}_Part{i+1:02d}_{start_idx+1}-{end_idx}.xlsx"
            save_path = os.path.join(folder, file_name)
            df_chunk.to_excel(save_path, index=False)

        QMessageBox.information(
            self, "분할 저장 완료",
            f"총 {total_items:,}건의 상품을 1,000개 단위로 분할하여 총 {num_chunks}개의 엑셀 파일로 추출했습니다.\n\n저장 위치: {folder}"
        )
