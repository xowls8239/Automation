import os
import json
import time
import base64
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QFrame, QComboBox, QCheckBox, QDialog,
    QLineEdit, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from core.excel_parser import load_benchmark_excel
from core.naver_payload import build_origin_product_payload, validate_account_defaults
from core.naver_addressbook import fetch_all_addressbooks, guess_id_field

import sys
import traceback

def _global_excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _global_excepthook

CONFIG_PATH = "config_accounts.json"

# ==========================================
# 1. 네이버 커머스 API 토큰 발급 및 전송 엔진
# ==========================================
class NaverCommerceClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.base_url = "https://api.commerce.naver.com/external"
        self.token = None
        self.token_expire = 0
        self._http = None  # 커넥션 재사용 (요청마다 새로 만들지 않음)

    @property
    def http(self):
        import httpx
        if self._http is None:
            self._http = httpx.Client(timeout=15.0)
        return self._http

    def close(self):
        if self._http is not None:
            self._http.close()
            self._http = None

    def get_token(self) -> str:
        """네이버 커머스 OAuth2 토큰 발급 (전자서명 기반)"""
        if not self.client_id or not self.client_secret:
            raise ValueError("애플리케이션 ID 또는 시크릿 키가 누락되었습니다.")

        now = time.time()
        if self.token and now < self.token_expire - 60:
            return self.token

        try:
            import bcrypt
        except ImportError:
            raise ImportError("필수 라이브러리가 없습니다. 터미널에서 'pip install bcrypt httpx'를 실행해 주세요.")

        timestamp = int(now * 1000)
        pwd = f"{self.client_id}_{timestamp}".encode("utf-8")
        hashed = bcrypt.hashpw(pwd, self.client_secret.encode("utf-8"))
        signature = base64.standard_b64encode(hashed).decode("utf-8")

        url = f"{self.base_url}/v1/oauth2/token"
        data = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF"
        }

        res = self.http.post(url, data=data)
        res_json = res.json()
        if res.status_code == 200 and "access_token" in res_json:
            self.token = res_json["access_token"]
            self.token_expire = now + res_json.get("expires_in", 10800)
            return self.token
        else:
            err_msg = res_json.get("message", res.text)
            raise Exception(f"인증 거부 ({res.status_code}): {err_msg}")

    def upload_product(self, payload: dict, max_retries: int = 3) -> dict:
        """스마트스토어 상품 등록 호출 (/v2/products). 429/5xx는 지수 백오프로 재시도."""
        token = self.get_token()
        url = f"{self.base_url}/v2/products"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        for attempt in range(max_retries + 1):
            res = self.http.post(url, headers=headers, json=payload)

            if res.status_code == 200:
                return res.json()

            if res.status_code == 429:
                wait_sec = 2 ** attempt
                time.sleep(wait_sec)
                continue

            if res.status_code >= 500:
                wait_sec = 2 ** attempt
                time.sleep(wait_sec)
                continue

            # 4xx (검증 오류 등) 는 재시도해도 결과가 같으므로 즉시 반환
            try:
                return res.json()
            except Exception:
                return {"message": f"HTTP {res.status_code}: {res.text[:200]}"}

        return {"message": f"{max_retries}회 재시도 후에도 실패 (마지막 상태코드 {res.status_code})"}

    def upload_images(self, image_urls: list) -> list:
        """외부 이미지 URL을 다운로드해 네이버 '상품 이미지 다건 등록 API'로 업로드하고,
        상품 등록에 실제로 쓸 수 있는 네이버 자체 URL 목록을 반환한다.
        (representativeImage.url에 외부 링크를 직접 넣으면 반려되기 때문에 반드시 필요한 단계)
        """
        if not image_urls:
            return []

        token = self.get_token()

        files = []
        for i, url in enumerate(image_urls):
            img_res = self.http.get(url, timeout=15.0, follow_redirects=True)
            img_res.raise_for_status()
            content_type = img_res.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if not content_type.startswith("image/"):
                content_type = "image/jpeg"
            ext = content_type.split("/")[-1]
            filename = f"image_{i}.{ext}"
            files.append(("imageFiles", (filename, img_res.content, content_type)))

        headers = {"Authorization": f"Bearer {token}"}
        upload_url = f"{self.base_url}/v1/product-images/upload"
        res = self.http.post(upload_url, headers=headers, files=files)

        try:
            res_json = res.json()
        except Exception:
            raise Exception(f"이미지 업로드 응답 파싱 실패 (HTTP {res.status_code}): {res.text[:200]}")

        if res.status_code != 200:
            err_msg = res_json.get("message", str(res_json))
            raise Exception(f"이미지 업로드 실패 (HTTP {res.status_code}): {err_msg}")

        images = res_json.get("images", [])
        urls = [img.get("url") for img in images if img.get("url")]
        if len(urls) != len(image_urls):
            raise Exception(f"이미지 업로드 개수 불일치: 요청 {len(image_urls)}건 / 응답 {len(urls)}건 - 응답 원문: {res_json}")
        return urls


# ==========================================
# 2. 주소록(출고지/반품지) 조회 & 선택 다이얼로그
#    응답 필드명을 100% 확신할 수 없으므로, 원본 데이터를 그대로 보여주고
#    사람이 직접 눈으로 보고 골라서 선택하게 한다.
# ==========================================
class AddressBookPickerDialog(QDialog):
    def __init__(self, client: "NaverCommerceClient", parent=None):
        super().__init__(parent)
        self.setWindowTitle("주소록 조회 (출고지/반품지 ID 확인)")
        self.resize(720, 420)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")
        self.selected_outbound = None
        self.selected_return = None

        layout = QVBoxLayout(self)
        desc = QLabel(
            "네이버에 등록된 주소록을 그대로 불러왔습니다.\n"
            "행을 확인하고 '출고지로 선택' / '반품지로 선택' 버튼을 눌러주세요.\n"
            "(항목의 정확한 용도는 주소/별칭 등을 보고 직접 판단해 주세요)"
        )
        desc.setStyleSheet("color: #8c8e94; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.table = QTableWidget(0, 0)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 4px; }
        """)
        layout.addWidget(self.table)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #e5c07b; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        try:
            self.items = fetch_all_addressbooks(client)
        except Exception as e:
            self.items = []
            self.lbl_status.setText(f"조회 실패: {e}")

        self._populate_table()

    def _populate_table(self):
        if not self.items:
            self.lbl_status.setText(self.lbl_status.text() or "조회된 주소록이 없습니다.")
            return

        # 첫 항목의 키를 기준으로 컬럼 구성 + 선택 버튼 2개 열 추가
        keys = list(self.items[0].keys())
        self.table.setColumnCount(len(keys) + 2)
        self.table.setHorizontalHeaderLabels(keys + ["출고지 선택", "반품지 선택"])
        self.table.setRowCount(len(self.items))

        for row, item in enumerate(self.items):
            for col, key in enumerate(keys):
                self.table.setItem(row, col, QTableWidgetItem(str(item.get(key, ""))))

            btn_out = QPushButton("출고지로 선택")
            btn_out.clicked.connect(lambda _, r=row: self._select(r, "outbound"))
            self.table.setCellWidget(row, len(keys), btn_out)

            btn_ret = QPushButton("반품지로 선택")
            btn_ret.clicked.connect(lambda _, r=row: self._select(r, "return"))
            self.table.setCellWidget(row, len(keys) + 1, btn_ret)

        self.table.resizeColumnsToContents()

    def _select(self, row, kind):
        item = self.items[row]
        _, guessed_id = guess_id_field(item)
        if guessed_id is None:
            QMessageBox.warning(
                self, "ID 필드 미확인",
                "이 항목에서 ID로 보이는 필드를 자동으로 찾지 못했습니다.\n"
                "테이블에서 ID에 해당하는 값을 직접 확인해 계정 설정 화면에 수동으로 입력해 주세요."
            )
            return
        if kind == "outbound":
            self.selected_outbound = guessed_id
            self.lbl_status.setText(f"출고지 선택됨: {guessed_id}")
        else:
            self.selected_return = guessed_id
            self.lbl_status.setText(f"반품지 선택됨: {guessed_id}")


# ==========================================
# 3. 다중 계정 설정 다이얼로그
#    (스토어별 인증 키 + 채널별 배송/AS 기본값 — 출고지/반품지는 채널마다 다르므로 공유하지 않음)
# ==========================================
class AccountConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("출하 라인 (스토어 다중 계정) 설정")
        self.resize(560, 760)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.inputs = {}       # acc_i -> (id_in, sec_in)
        self.defaults_inputs = {}  # acc_i -> (outbound_in, return_in, as_tel_in, as_guide_in)

        for i in range(1, 4):
            id_in = QLineEdit()
            sec_in = QLineEdit()
            sec_in.setEchoMode(QLineEdit.Password)
            self.inputs[f"acc_{i}"] = (id_in, sec_in)

            outbound_in = QLineEdit()
            outbound_in.setPlaceholderText("출고지 주소 ID")
            return_in = QLineEdit()
            return_in.setPlaceholderText("반품지 주소 ID")
            as_tel_in = QLineEdit()
            as_tel_in.setPlaceholderText("A/S 문의 전화번호 (예: 070-0000-0000)")
            as_guide_in = QLineEdit()
            as_guide_in.setPlaceholderText("A/S 안내 문구 (선택)")
            self.defaults_inputs[f"acc_{i}"] = (outbound_in, return_in, as_tel_in, as_guide_in)

            btn_lookup = QPushButton(f"채널 #{i} 출고지/반품지 자동조회")
            btn_lookup.setStyleSheet("background-color: #43454a; color: white; padding: 5px 8px; border-radius: 4px; font-size: 11px;")
            btn_lookup.clicked.connect(lambda _, idx=i: self.open_addressbook_picker(idx))

            form.addRow(QLabel(f"<b>--- 릴리즈 채널 #{i} ---</b>"))
            form.addRow("애플리케이션 ID:", id_in)
            form.addRow("시크릿 키:", sec_in)
            form.addRow(btn_lookup)
            form.addRow("출고지 ID:", outbound_in)
            form.addRow("반품지 ID:", return_in)
            form.addRow("A/S 전화번호:", as_tel_in)
            form.addRow("A/S 안내문구:", as_guide_in)

        layout.addLayout(form)
        btn_save = QPushButton("설정 저장")
        btn_save.setStyleSheet("background-color: #3574f0; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        self.load_config()

    def open_addressbook_picker(self, idx):
        id_in, sec_in = self.inputs[f"acc_{idx}"]
        cid, csec = id_in.text().strip(), sec_in.text().strip()
        if not cid or not csec:
            QMessageBox.warning(self, "정보 부족", f"채널 #{idx}의 애플리케이션 ID/시크릿 키를 먼저 입력해 주세요.")
            return

        client = NaverCommerceClient(cid, csec)
        try:
            client.get_token()
        except Exception as e:
            QMessageBox.critical(self, "인증 실패", f"토큰 발급에 실패했습니다:\n{e}")
            return

        dlg = AddressBookPickerDialog(client, self)
        dlg.exec()
        client.close()

        outbound_in, return_in, _, _ = self.defaults_inputs[f"acc_{idx}"]
        if dlg.selected_outbound is not None:
            outbound_in.setText(str(dlg.selected_outbound))
        if dlg.selected_return is not None:
            return_in.setText(str(dlg.selected_return))

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, (id_in, sec_in) in self.inputs.items():
                    id_in.setText(data.get(k, {}).get("client_id", ""))
                    sec_in.setText(data.get(k, {}).get("client_secret", ""))
                for k, (outbound_in, return_in, as_tel_in, as_guide_in) in self.defaults_inputs.items():
                    defaults = data.get(k, {}).get("defaults", {})
                    outbound_in.setText(str(defaults.get("outbound_location_id", "")))
                    return_in.setText(str(defaults.get("return_location_id", "")))
                    as_tel_in.setText(defaults.get("as_telephone", ""))
                    as_guide_in.setText(defaults.get("as_guide", ""))

    def save_config(self):
        data = {}
        for k in self.inputs:
            id_in, sec_in = self.inputs[k]
            outbound_in, return_in, as_tel_in, as_guide_in = self.defaults_inputs[k]
            data[k] = {
                "client_id": id_in.text().strip(),
                "client_secret": sec_in.text().strip(),
                "defaults": {
                    "outbound_location_id": outbound_in.text().strip(),
                    "return_location_id": return_in.text().strip(),
                    "as_telephone": as_tel_in.text().strip(),
                    "as_guide": as_guide_in.text().strip(),
                },
            }

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        QMessageBox.information(self, "저장 완료", "계정 인증 정보가 정상 저장되었습니다.")
        self.accept()


# ==========================================
# 3. 백그라운드 대량 전송 스레드
# ==========================================
class BenchmarkUploadWorker(QThread):
    progress_signal = Signal(int, int, str, str, str)  # 진행률, 행 인덱스, LOT 식별자, 결과 상태, 상세 내용
    finished_signal = Signal(int, int, str)            # 성공 수, 실패 수, 종료 사유
    error_signal = Signal(str)                         # 즉시 중단 에러

    def __init__(self, data_list, active_clients, client_defaults, round_robin=True):
        """
        client_defaults: active_clients와 같은 길이의 리스트.
        client_defaults[i] 는 active_clients[i]에 대응하는 출고지/반품지/AS 기본값 dict.
        (채널마다 출고지/반품지가 다르므로 클라이언트 1:1로 매칭해서 받는다)
        """
        super().__init__()
        self.data_list = data_list
        self.clients = active_clients
        self.client_defaults = client_defaults
        self.round_robin = round_robin
        self.is_running = True

    def run(self):
        success, fail = 0, 0
        total = len(self.data_list)

        try:
            # 0. 채널별 배송/AS 기본값 사전 검증
            for idx, defaults in enumerate(self.client_defaults):
                missing = validate_account_defaults(defaults)
                if missing:
                    self.error_signal.emit(
                        f"채널 #{idx+1}의 배송/AS 기본값이 비어 있습니다: " + ", ".join(missing) +
                        "\n[채널 자격증명 설정]에서 해당 채널의 '출고지/반품지 자동조회'를 먼저 실행해 주세요."
                    )
                    return

            # 1. 토큰 사전 검증
            for idx, client in enumerate(self.clients):
                try:
                    client.get_token()
                except Exception as e:
                    self.error_signal.emit(f"채널 #{idx+1} 네이버 API 토큰 발급 실패:\n{str(e)}")
                    return

            # 2. 실제 순차 전송 루프
            for row_idx, item in enumerate(self.data_list):
                if not self.is_running:
                    self.finished_signal.emit(success, fail, "사용자에 의해 작업이 중단되었습니다.")
                    return

                client_idx = row_idx % len(self.clients) if self.round_robin else 0
                client = self.clients[client_idx]
                defaults = self.client_defaults[client_idx]

                try:
                    thumb_url = item.get("thumb", "")
                    optional_urls = [u for u in (item.get("optional_images") or []) if u]
                    source_image_urls = [u for u in [thumb_url] + optional_urls if u]

                    item_for_payload = dict(item)
                    if source_image_urls:
                        uploaded_urls = client.upload_images(source_image_urls)
                        item_for_payload["thumb"] = uploaded_urls[0]
                        item_for_payload["optional_images"] = uploaded_urls[1:]

                    payload = build_origin_product_payload(item_for_payload, defaults)
                    res = client.upload_product(payload)
                    if "originProductNo" in res:
                        prod_no = res["originProductNo"]
                        status_text = f"성공 (No: {prod_no})"
                        success += 1
                    elif "message" in res:
                        base_msg = res.get("message", "")
                        invalid_list = res.get("invalidInputs") or res.get("invalidInputsErrors") or []
                        if invalid_list:
                            detail_parts = []
                            for d in invalid_list:
                                field = d.get("name") or d.get("field") or "?"
                                reason = d.get("message") or d.get("code") or ""
                                detail_parts.append(f"[{field}] {reason}")
                            base_msg = base_msg + " → " + " / ".join(detail_parts)
                        status_text = f"실패: {base_msg[:400]}"
                        fail += 1
                    else:
                        status_text = f"응답 확인 필요 ({str(res)[:200]})"
                        fail += 1
                except Exception as e:
                    status_text = f"오류: {str(e)[:300]}"
                    fail += 1

                progress_pct = int(((row_idx + 1) / total) * 100)
                self.progress_signal.emit(progress_pct, row_idx, item["code"] or f"LOT-{row_idx:05d}", status_text, "")

                # 스마트스토어 초당 호출 제한(Rate Limit) 준수
                self.msleep(350)

            for client in self.clients:
                client.close()

            self.finished_signal.emit(success, fail, "모든 규격 데이터 릴리즈가 완료되었습니다.")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(f"예상치 못한 오류로 작업이 중단되었습니다:\n{e}")

    def stop(self):
        self.is_running = False


# ==========================================
# 4. 벤치마킹 릴리즈 메인 화면
# ==========================================
class ReleaserBenchmarkPage(QWidget):
    def __init__(self):
        super().__init__()
        self.raw_data = []
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 10px;")
        top_layout = QHBoxLayout(top_panel)

        self.btn_load_data = QPushButton("벤치마킹 규격셋 적재 (Processed 파일)")
        self.btn_load_data.setStyleSheet("background-color: #365880; color: white; padding: 8px 14px; font-weight: bold; border-radius: 4px;")
        self.btn_load_data.clicked.connect(self.select_data_file)

        self.combo_accounts = QComboBox()
        self.combo_accounts.addItems(["릴리즈 채널 #1", "릴리즈 채널 #2", "릴리즈 채널 #3"])
        self.combo_accounts.setStyleSheet("background-color: #1e1f22; color: #dfe1e5; padding: 5px;")

        self.chk_round_robin = QCheckBox("3개 채널 자동 순환 균등 배분")
        self.chk_round_robin.setChecked(True)
        self.chk_round_robin.setStyleSheet("color: #bcbec4; font-size: 12px; margin-left: 8px;")

        self.btn_config = QPushButton("채널 자격증명 설정")
        self.btn_config.setStyleSheet("background-color: #43454a; color: white; padding: 8px 10px; border-radius: 4px;")
        self.btn_config.clicked.connect(lambda: AccountConfigDialog(self).exec())

        self.btn_start = QPushButton("릴리즈 전송 시작")
        self.btn_start.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_upload)

        self.btn_stop = QPushButton("전송 중단")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #8c2e2e; color: white; padding: 8px 16px; font-weight: bold; border-radius: 4px; }
            QPushButton:disabled { background-color: #4a3636; color: #7a7a7a; }
        """)
        self.btn_stop.clicked.connect(self.stop_upload)

        top_layout.addWidget(self.btn_load_data)
        top_layout.addWidget(self.combo_accounts)
        top_layout.addWidget(self.chk_round_robin)
        top_layout.addWidget(self.btn_config)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_stop)
        layout.addWidget(top_panel)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["LOT 식별자", "품목 규격명", "카테고리 코드", "출하 공급가", "옵션 구성", "릴리즈 상태"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        layout.addWidget(self.table)

        bottom_panel = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2b2d30; border-radius: 4px; text-align: center; color: white; height: 18px; }
            QProgressBar::chunk { background-color: #3574f0; }
        """)
        self.lbl_progress_info = QLabel("대기 중: 0건")
        self.lbl_progress_info.setStyleSheet("color: #9da0a8; font-size: 12px; margin-left: 10px;")

        bottom_panel.addWidget(self.progress_bar)
        bottom_panel.addWidget(self.lbl_progress_info)
        layout.addLayout(bottom_panel)

    def select_data_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "공정 데이터셋 선택", "", "Excel Files (*.xlsx)")
        if not path:
            return

        try:
            self.raw_data = load_benchmark_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "적재 실패", f"엑셀 파싱 중 오류가 발생했습니다:\n{e}")
            return

        self.table.setRowCount(0)
        for item in self.raw_data:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            name_disp = item["name"][:35] + ("..." if len(item["name"]) > 35 else "")
            price_str = f"{item['raw_price']:,}원"
            if item["combos"]:
                opt_str = f"조합형 {len(item['combos'])}종"
            else:
                opt_str = f"단품 (재고 {item['simple_stock']:,})"

            self.table.setItem(row_idx, 0, QTableWidgetItem(item["code"] or f"LOT-{row_idx:05d}"))
            self.table.setItem(row_idx, 1, QTableWidgetItem(name_disp))
            self.table.setItem(row_idx, 2, QTableWidgetItem(item["cat"]))
            self.table.setItem(row_idx, 3, QTableWidgetItem(price_str))
            self.table.setItem(row_idx, 4, QTableWidgetItem(opt_str))
            self.table.setItem(row_idx, 5, QTableWidgetItem("적재 완료 (대기)"))

        self.lbl_progress_info.setText(f"총 {len(self.raw_data):,}건 적재 완료")

    def start_upload(self):
        if not self.raw_data:
            QMessageBox.warning(self, "데이터 없음", "먼저 벤치마킹 엑셀 데이터를 적재해 주세요.")
            return

        if not os.path.exists(CONFIG_PATH):
            QMessageBox.critical(
                self, "인증 키 부재",
                "네이버 커머스 API 연동 키가 설정되지 않았습니다.\n"
                "[채널 자격증명 설정] 버튼을 눌러 애플리케이션 ID/시크릿 키와\n"
                "출고지·반품지·AS 정보를 먼저 등록해 주세요."
            )
            return

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        clients = []
        client_defaults = []
        if self.chk_round_robin.isChecked():
            for i in range(1, 4):
                acc = cfg.get(f"acc_{i}", {})
                cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")
                if cid and csec:
                    clients.append(NaverCommerceClient(cid, csec))
                    client_defaults.append(acc.get("defaults", {}))
            if not clients:
                QMessageBox.critical(
                    self, "인증 키 미입력",
                    "순환 배분을 위해 최소 1개 이상의 유효한 채널 ID/시크릿 키가 필요합니다."
                )
                return
        else:
            sel_idx = self.combo_accounts.currentIndex() + 1
            acc = cfg.get(f"acc_{sel_idx}", {})
            cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")
            if not cid or not csec:
                QMessageBox.critical(
                    self, "인증 키 미입력",
                    f"선택한 릴리즈 채널 #{sel_idx}의 ID 또는 시크릿 키가 비어 있습니다."
                )
                return
            clients.append(NaverCommerceClient(cid, csec))
            client_defaults.append(acc.get("defaults", {}))

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_load_data.setEnabled(False)

        self.worker = BenchmarkUploadWorker(
            self.raw_data, clients, client_defaults,
            round_robin=self.chk_round_robin.isChecked()
        )
        self.worker.progress_signal.connect(self.on_row_processed)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.finished_signal.connect(self.on_upload_finished)
        self.worker.start()

    def stop_upload(self):
        if self.worker and self.worker.isRunning():
            self.btn_stop.setEnabled(False)
            self.btn_stop.setText("중단 처리 중...")
            self.worker.stop()

    def on_row_processed(self, pct, row_idx, code, status, detail):
        self.progress_bar.setValue(pct)
        self.table.setItem(row_idx, 5, QTableWidgetItem(status))
        self.table.scrollToItem(self.table.item(row_idx, 0))
        self.lbl_progress_info.setText(f"진행률: {pct}% ({row_idx + 1:,} / {len(self.raw_data):,}건)")

    def on_worker_error(self, err_msg):
        QMessageBox.critical(self, "전송 시작 불가", err_msg)
        self.reset_ui_state()

    def on_upload_finished(self, success, fail, reason):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("공정 종료")
        msg_box.setText(f"{reason}\n\n• 정상 출하 성공: {success:,}건\n• 규격 누락/실패: {fail:,}건")
        msg_box.setFont(QFont("Malgun Gothic", 10))
        msg_box.setStyleSheet("""
            QLabel { min-width: 340px; min-height: 90px; }
            QPushButton { min-width: 80px; padding: 4px 12px; }
        """)
        msg_box.exec()
        self.reset_ui_state()
        
    def reset_ui_state(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("전송 중단")
        self.btn_load_data.setEnabled(True)

        if self.worker:
            self.worker.wait(3000)  # 스레드가 완전히 끝날 때까지 최대 3초 대기 (crash 방지)


# 호환성을 위한 클래스 별칭 부여
ProductReleaserPage = ReleaserBenchmarkPage