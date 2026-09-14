import os
import json
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QFrame, QComboBox, QCheckBox, QDialog,
    QLineEdit, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

CONFIG_PATH = "config_accounts.json"

# ==========================================
# 다중 계정 설정 다이얼로그 (최대 5개 지원)
# ==========================================
class AccountConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("출하 라인 (스토어 다중 계정) 설정")
        self.resize(450, 320)
        self.setStyleSheet("background-color: #2b2d30; color: #bcbec4;")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.inputs = {}
        for i in range(1, 4):
            id_in = QLineEdit()
            sec_in = QLineEdit()
            sec_in.setEchoMode(QLineEdit.Password)
            self.inputs[f"acc_{i}"] = (id_in, sec_in)
            form.addRow(QLabel(f"--- 릴리즈 채널 #{i} ---"))
            form.addRow("애플리케이션 ID:", id_in)
            form.addRow("시크릿 키:", sec_in)

        layout.addLayout(form)
        btn_save = QPushButton("설정 저장")
        btn_save.setStyleSheet("background-color: #3574f0; color: white; padding: 8px; font-weight: bold;")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        self.load_config()

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
        QMessageBox.information(self, "저장 완료", "계정 인증 정보가 정상 저장되었습니다.")
        self.accept()

# ==========================================
# 백그라운드 대량 전송 스레드 (QThread)
# ==========================================
class ReleaseUploadWorker(QThread):
    progress_signal = Signal(int, str, str)  # 진행률, LOT 식별자, 결과 상태
    finished_signal = Signal(int, int)       # 성공수, 실패수

    def __init__(self, data_list, accounts, round_robin=True, selected_acc=None):
        super().__init__()
        self.data_list = data_list
        self.accounts = accounts
        self.round_robin = round_robin
        self.selected_acc = selected_acc
        self.is_running = True

    def run(self):
        success, fail = 0, 0
        total = len(self.data_list)

        for idx, item in enumerate(self.data_list):
            if not self.is_running:
                break

            # 순환 분할 또는 단일 계정 선택
            target_acc = self.accounts[idx % len(self.accounts)] if self.round_robin else self.selected_acc
            
            # (실제 API 요청 페이로드 조립 및 전송 로직 진입 지점)
            # 1초당 3건 수준으로 Throttling 유지
            self.msleep(300) 

            # 임시 전송 성공 처리
            success += 1
            progress_pct = int(((idx + 1) / total) * 100)
            self.progress_signal.emit(progress_pct, item.get("code", f"LOT-{idx+1}"), "전송 완료")

        self.finished_signal.emit(success, fail)

    def stop(self):
        self.is_running = False

# ==========================================
# 시제품 확정 메인 페이지
# ==========================================
class ProductReleaserPage(QWidget):
    def __init__(self):
        super().__init__()
        self.raw_data = []
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 상단 제어 바
        top_panel = QFrame()
        top_panel.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 10px;")
        top_layout = QHBoxLayout(top_panel)

        self.btn_load_data = QPushButton("공정 데이터셋 적재 (Processed 파일)")
        self.btn_load_data.setStyleSheet("background-color: #365880; color: white; padding: 8px 14px; font-weight: bold; border-radius: 4px;")
        self.btn_load_data.clicked.connect(self.select_data_file)

        self.combo_accounts = QComboBox()
        self.combo_accounts.addItems(["릴리즈 채널 #1", "릴리즈 채널 #2", "릴리즈 채널 #3"])
        self.combo_accounts.setStyleSheet("background-color: #1e1f22; color: #dfe1e5; padding: 5px;")

        self.chk_round_robin = QCheckBox("3개 채널 자동 순환 균등 분할 배분")
        self.chk_round_robin.setChecked(True)
        self.chk_round_robin.setStyleSheet("color: #bcbec4; font-size: 12px; margin-left: 10px;")

        self.btn_config = QPushButton("채널 자격증명 설정")
        self.btn_config.setStyleSheet("background-color: #43454a; color: white; padding: 8px 10px; border-radius: 4px;")
        self.btn_config.clicked.connect(lambda: AccountConfigDialog(self).exec())

        self.btn_start = QPushButton("릴리즈 전송 시작")
        self.btn_start.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_upload)

        top_layout.addWidget(self.btn_load_data)
        top_layout.addWidget(self.combo_accounts)
        top_layout.addWidget(self.chk_round_robin)
        top_layout.addWidget(self.btn_config)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_start)
        layout.addWidget(top_panel)

        # 테이블
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["LOT 식별자", "품목 규격명", "카테고리 코드", "출하 공급가", "옵션 구성", "릴리즈 상태"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        layout.addWidget(self.table)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #2b2d30; border-radius: 4px; text-align: center; color: white; height: 18px; }
            QProgressBar::chunk { background-color: #3574f0; }
        """)
        layout.addWidget(self.progress_bar)

    def select_data_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "공정 데이터셋 선택", "", "Excel Files (*.xlsx)")
        if not path:
            return

        # Processed_1 699.xlsx 파싱
        df = pd.read_excel(path, sheet_name="엑셀 수정 업로드 상품 정보", header=None)
        self.raw_data.clear()
        self.table.setRowCount(0)

        # 3행부터 실제 데이터 시작
        for r in range(3, len(df)):
            item_code = str(df.iloc[r, 17]) if pd.notna(df.iloc[r, 17]) else f"LOT-{r-2:05d}"
            name = str(df.iloc[r, 1])
            cat = str(df.iloc[r, 4])
            price = f"{int(df.iloc[r, 19]):,}원" if pd.notna(df.iloc[r, 19]) else "0원"
            opt = str(df.iloc[r, 52]) if pd.notna(df.iloc[r, 52]) else "단품"

            self.raw_data.append({
                "code": item_code,
                "name": name,
                "cat": cat,
                "price": df.iloc[r, 19],
                "opt": opt,
                "thumb": df.iloc[r, 23],
                "desc": df.iloc[r, 32]
            })

            # 테이블 행 추가
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(item_code))
            self.table.setItem(row_idx, 1, QTableWidgetItem(name[:35] + "..."))
            self.table.setItem(row_idx, 2, QTableWidgetItem(cat))
            self.table.setItem(row_idx, 3, QTableWidgetItem(price))
            self.table.setItem(row_idx, 4, QTableWidgetItem(opt))
            self.table.setItem(row_idx, 5, QTableWidgetItem("대기"))

    def start_upload(self):
        if not self.raw_data:
            QMessageBox.warning(self, "데이터 없음", "먼저 Processed 엑셀 파일을 적재해 주세요.")
            return

        is_rr = self.chk_round_robin.isChecked()
        self.worker = ReleaseUploadWorker(self.raw_data, [1, 2, 3], round_robin=is_rr)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.start()

    def update_progress(self, pct, code, status):
        self.progress_bar.setValue(pct)