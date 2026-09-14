# [스마트스토어 대량 공정 자동화 프로그램: 전체 소스 코드 정밀 검토 요청]

현재 데스크톱(PySide6) 기반으로 개발 중인 네이버 커머스 API 대량 등록 및 동기화 도구의 전체 소스 코드입니다. 
시니어 개발자 관점에서 아래 4대 핵심 기준을 바탕으로 코드의 결함, API 정책 위반 가능성, 성능 최적화 포인트를 정밀 분석해 주세요.

---

### [핵심 검토 요청 항목]
1. **네이버 커머스 API v2 등록 스키마 적합성**:
   - eleaser_benchmark_page.py의 payload 구성 시 필수 누락 필드(배송비 템플릿 ID, 출고지/반품지 주소 ID, A/S 정보 등)로 인한 400 Bad Request 발생 가능성
   - 엑셀 데이터의 조합형 옵션(Col 52~57)을 API v2의 optionInfo.combinationOptions 구조로 매핑하는 올바른 JSON 규격
2. **기술 라이브러리(전수 DB화) 대량 호출 최적화**:
   - 	ech_library_page.py에서 1만 건 단위 스토어 데이터를 읽어올 때의 네이버 초당 호출 제한(Rate Limit) 및 HTTP 429 대응(Exponential Backoff) 방안
3. **PySide6 멀티스레딩 및 메모리 안정성**:
   - QThread 기반 is_running 플래그 중단 방식의 스레드 데드락 여부 및 안전한 종료(wait()) 처리
4. **리팩토링 및 예외 처리 제안**:
   - 토큰 만료(3시간) 갱신 로직, 네트워크 단절 시 재시도 루틴, 모듈 분리 방향

---
### [프로젝트 전체 소스 코드]

## [File: main.py]
``python
import sys
from pathlib import Path

# 모듈 경로 1순위 등록
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from pages.dashboard_page import DashboardPage
from pages.competitor_page import CompetitorPage
from pages.parts_page import PartsPage
from pages.review_page import ReviewPage
from pages.tech_library_page import TechLibraryPage
from pages.releaser_review_page import ReleaserReviewPage
from pages.releaser_benchmark_page import ReleaserBenchmarkPage


class EngineeringMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("기술 통합 자동화 관리 시스템 (v1.0.0)")
        self.resize(1340, 850)
        self.setStyleSheet("background-color: #1e1f22;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 사이드바
        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet("background-color: #2b2d30; border-right: 1px solid #393b40;")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 20, 10, 20)
        side_layout.setSpacing(8)

        logo_label = QLabel("PROCESS ENGINE")
        logo_label.setStyleSheet("color: #7a7e85; font-weight: bold; font-size: 11px; padding-left: 8px; margin-bottom: 12px;")
        side_layout.addWidget(logo_label)

        # 7대 메뉴 버튼 리스트
        self.btn_home = self.create_nav_button("홈")
        self.btn_competitor = self.create_nav_button("경쟁사/제품 분석")
        self.btn_parts = self.create_nav_button("자사 제품 분석")
        self.btn_review = self.create_nav_button("설계 검토")
        self.btn_tech_lib = self.create_nav_button("기술 라이브러리")
        self.btn_rel_review = self.create_nav_button("시제품 확정_설계검토")
        self.btn_rel_bench = self.create_nav_button("시제품 확정_벤치마킹")

        self.nav_buttons = [
            self.btn_home,
            self.btn_competitor,
            self.btn_parts,
            self.btn_review,
            self.btn_tech_lib,
            self.btn_rel_review,
            self.btn_rel_bench
        ]

        for btn in self.nav_buttons:
            side_layout.addWidget(btn)

        side_layout.addStretch()
        root_layout.addWidget(sidebar)

        # 페이지 스택
        self.pages_stack = QStackedWidget()
        
        self.page_dashboard = DashboardPage(self.navigate_by_index)
        self.page_competitor = CompetitorPage()
        self.page_parts = PartsPage()
        self.page_review = ReviewPage()
        self.page_tech_lib = TechLibraryPage()
        self.page_rel_review = ReleaserReviewPage()
        self.page_rel_bench = ReleaserBenchmarkPage()

        self.pages_stack.addWidget(self.page_dashboard)   # Index 0
        self.pages_stack.addWidget(self.page_competitor)  # Index 1
        self.pages_stack.addWidget(self.page_parts)       # Index 2
        self.pages_stack.addWidget(self.page_review)      # Index 3
        self.pages_stack.addWidget(self.page_tech_lib)    # Index 4
        self.pages_stack.addWidget(self.page_rel_review)  # Index 5
        self.pages_stack.addWidget(self.page_rel_bench)   # Index 6

        root_layout.addWidget(self.pages_stack)

        for idx, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(lambda _, index=idx: self.navigate_by_index(index))

        self.navigate_by_index(0)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #bcbec4; text-align: left;
                padding-left: 14px; font-weight: bold; border-radius: 4px; border: none; font-size: 13px;
            }
            QPushButton:hover { background-color: #35373c; color: #ffffff; }
        """)
        return btn

    def navigate_by_index(self, index):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3574f0; color: #ffffff; text-align: left;
                        padding-left: 14px; font-weight: bold; border-radius: 4px; border: none; font-size: 13px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent; color: #bcbec4; text-align: left;
                        padding-left: 14px; font-weight: bold; border-radius: 4px; border: none; font-size: 13px;
                    }
                    QPushButton:hover { background-color: #35373c; color: #ffffff; }
                """)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 팝업 전역 다크 테마 적용
    app.setStyleSheet("""
        QMessageBox {
            background-color: #2b2d30;
            border: 1px solid #393b40;
        }
        QMessageBox QLabel {
            color: #dfe1e5;
            font-size: 13px;
            min-height: 40px;
        }
        QMessageBox QPushButton {
            background-color: #3574f0;
            color: #ffffff;
            font-weight: bold;
            border-radius: 4px;
            padding: 6px 18px;
            min-width: 65px;
            min-height: 24px;
            border: none;
        }
        QMessageBox QPushButton:hover {
            background-color: #4a85f6;
        }
    """)

    window = EngineeringMainWindow()
    window.show()
    sys.exit(app.exec())
``

## [File: pages/competitor_page.py]
``python
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

``

## [File: pages/dashboard_page.py]
``python
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QGridLayout, QTextEdit, QButtonGroup
)
from PySide6.QtCore import Qt

class DashboardPage(QWidget):
    def __init__(self, nav_callback):
        super().__init__()
        self.nav_callback = nav_callback
        
        # 샘플 공정 실적 데이터셋 (천 단위 구분 기호 및 백분율 적용)
        self.metrics_data = {
            "stores": {"name": "검증 거래처", "unit": "건", "total": "1,248", "month": "184", "today": "32", "rate": "92.5%"},
            "specs": {"name": "수집 규격 품목", "unit": "개", "total": "24,850", "month": "4,120", "today": "650", "rate": "88.2%"},
            "matched": {"name": "자사 매칭 부품", "unit": "개", "total": "18,420", "month": "3,050", "today": "480", "rate": "85.0%"},
            "reviewed": {"name": "설계 검토 완료", "unit": "개", "total": "12,150", "month": "2,210", "today": "310", "rate": "78.4%"},
            "released": {"name": "시제품 확정 릴리즈", "unit": "개", "total": "10,000", "month": "1,850", "today": "240", "rate": "82.3%"}
        }
        self.card_widgets = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        # 1. 상단 헤더 & 기간 선택 토글 바
        header_panel = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("공정 통합 자동화 모니터링 시스템")
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        subtitle = QLabel("전체 수집·매칭·검토·출하 파이프라인의 실시간 진행 현황을 관제합니다.")
        subtitle.setStyleSheet("color: #8c8e94; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_panel.addLayout(title_box)
        header_panel.addStretch()

        # 기간 필터 토글 버튼 그룹
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background-color: #2b2d30; border-radius: 6px; padding: 3px;")
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(4, 4, 4, 4)
        filter_layout.setSpacing(4)

        self.btn_group = QButtonGroup(self)
        self.btn_total = self.create_filter_button("전체 누적", True)
        self.btn_month = self.create_filter_button("금월 실적", False)
        self.btn_today = self.create_filter_button("금일 현황", False)

        self.btn_group.addButton(self.btn_total, 0)
        self.btn_group.addButton(self.btn_month, 1)
        self.btn_group.addButton(self.btn_today, 2)
        self.btn_group.idClicked.connect(self.update_card_focus)

        filter_layout.addWidget(self.btn_total)
        filter_layout.addWidget(self.btn_month)
        filter_layout.addWidget(self.btn_today)
        header_panel.addWidget(filter_frame)
        layout.addLayout(header_panel)

        # 2. KPI 핵심 지표 카드 영역 (3열 2행)
        kpi_layout = QGridLayout()
        kpi_layout.setSpacing(15)

        keys = ["stores", "specs", "matched", "reviewed", "released"]
        positions = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1)]

        for key, pos in zip(keys, positions):
            card = self.create_kpi_card(key, self.metrics_data[key])
            self.card_widgets[key] = card
            kpi_layout.addWidget(card["frame"], pos[0], pos[1])

        # 단축 실행 패널 (1행 2열 위치)
        quick_panel = QFrame()
        quick_panel.setStyleSheet("background-color: #2b2d30; border-radius: 8px; padding: 18px; border: 1px solid #393b40;")
        quick_layout = QVBoxLayout(quick_panel)
        quick_layout.setSpacing(10)
        
        quick_title = QLabel("공정 단축 실행")
        quick_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        quick_desc = QLabel("보유 데이터 10,000건 대량 전송")
        quick_desc.setStyleSheet("color: #8c8e94; font-size: 12px;")
        
        btn_go_release = QPushButton("시제품 확정 작업실 이동")
        btn_go_release.setFixedHeight(42)
        btn_go_release.setStyleSheet("""
            QPushButton { background-color: #365880; color: white; font-weight: bold; border-radius: 5px; font-size: 13px; }
            QPushButton:hover { background-color: #436d9d; }
        """)
        btn_go_release.clicked.connect(lambda: self.nav_callback(4))

        quick_layout.addWidget(quick_title)
        quick_layout.addWidget(quick_desc)
        quick_layout.addStretch()
        quick_layout.addWidget(btn_go_release)
        kpi_layout.addWidget(quick_panel, 1, 2)

        layout.addLayout(kpi_layout)

        # 3. 실시간 시스템 공정 엔진 로그 콘솔
        log_panel = QFrame()
        log_panel.setStyleSheet("background-color: #2b2d30; border-radius: 8px; padding: 15px; border: 1px solid #393b40;")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)

        log_title = QLabel("시스템 공정 실시간 모니터링 로그")
        log_title.setStyleSheet("color: #dfe1e5; font-weight: bold; font-size: 13px;")
        log_layout.addWidget(log_title)

        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setFixedHeight(130)
        self.txt_console.setStyleSheet("""
            QTextEdit {
                background-color: #1e1f22; color: #73c991; font-family: 'Consolas', monospace;
                font-size: 12px; border: 1px solid #393b40; border-radius: 4px; padding: 8px;
            }
        """)
        self.txt_console.append("[SYSTEM] 메인 엔진 프로세스가 정상 기동되었습니다.")
        self.txt_console.append("[INFO] 로컬 SQLite DB(WAL Mode) 인덱스 스캔 완료.")
        self.txt_console.append("[READY] 10,000건 대량 규격 데이터 적재 대기 중...")
        log_layout.addWidget(self.txt_console)

        layout.addWidget(log_panel)

    def create_filter_button(self, text, is_checked):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(is_checked)
        btn.setFixedHeight(30)
        btn.setFixedWidth(80)
        self.apply_filter_btn_style(btn, is_checked)
        return btn

    def apply_filter_btn_style(self, btn, is_active):
        if is_active:
            btn.setStyleSheet("background-color: #3574f0; color: white; font-weight: bold; border-radius: 4px; font-size: 12px; border: none;")
        else:
            btn.setStyleSheet("background-color: transparent; color: #9da0a8; border-radius: 4px; font-size: 12px; border: none;")

    def create_kpi_card(self, key, data):
        frame = QFrame()
        frame.setStyleSheet("background-color: #2b2d30; border-radius: 8px; padding: 14px; border: 1px solid #393b40;")
        card_layout = QVBoxLayout(frame)
        card_layout.setSpacing(8)

        # 상단 타이틀 및 달성률
        top_row = QHBoxLayout()
        lbl_title = QLabel(data["name"])
        lbl_title.setStyleSheet("color: #9da0a8; font-size: 12px; font-weight: bold;")
        lbl_rate = QLabel(f"달성률 {data['rate']}")
        lbl_rate.setStyleSheet("color: #3574f0; font-size: 11px; font-weight: bold;")
        top_row.addWidget(lbl_title)
        top_row.addStretch()
        top_row.addWidget(lbl_rate)
        card_layout.addLayout(top_row)

        # 메인 강조 숫자
        lbl_val = QLabel(f"{data['total']} {data['unit']}")
        lbl_val.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        card_layout.addWidget(lbl_val)

        # 하단 전체/금월/금일 3열 대조 그리드
        breakdown_box = QFrame()
        breakdown_box.setStyleSheet("background-color: #222427; border-radius: 4px; padding: 6px;")
        b_layout = QHBoxLayout(breakdown_box)
        b_layout.setContentsMargins(8, 4, 8, 4)

        sub_total = QLabel(f"전체: {data['total']}")
        sub_total.setStyleSheet("color: #bcbec4; font-size: 11px;")
        sub_month = QLabel(f"금월: {data['month']}")
        sub_month.setStyleSheet("color: #629755; font-size: 11px; font-weight: bold;")
        sub_today = QLabel(f"금일: +{data['today']}")
        sub_today.setStyleSheet("color: #e5c07b; font-size: 11px; font-weight: bold;")

        b_layout.addWidget(sub_total)
        b_layout.addStretch()
        b_layout.addWidget(sub_month)
        b_layout.addStretch()
        b_layout.addWidget(sub_today)
        card_layout.addWidget(breakdown_box)

        return {
            "frame": frame,
            "main_val": lbl_val,
            "unit": data["unit"],
            "key": key
        }

    def update_card_focus(self, btn_id):
        for btn in [self.btn_total, self.btn_month, self.btn_today]:
            self.apply_filter_btn_style(btn, btn == self.btn_group.button(btn_id))

        field_map = {0: ("total", ""), 1: ("month", "[금월] "), 2: ("today", "[금일] +")}
        field, prefix = field_map[btn_id]

        for key, card in self.card_widgets.items():
            val = self.metrics_data[key][field]
            card["main_val"].setText(f"{prefix}{val} {card['unit']}")
``

## [File: pages/parts_page.py]
``python
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

``

## [File: pages/releaser_benchmark_page.py]
``python
import os
import json
import time
import base64
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
# 1. 네이버 커머스 API 토큰 발급 및 전송 엔진
# ==========================================
class NaverCommerceClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.base_url = "https://api.commerce.naver.com/external"
        self.token = None
        self.token_expire = 0

    def get_token(self) -> str:
        """네이버 커머스 OAuth2 토큰 발급 (전자서명 기반)"""
        if not self.client_id or not self.client_secret:
            raise ValueError("애플리케이션 ID 또는 시크릿 키가 누락되었습니다.")

        now = time.time()
        if self.token and now < self.token_expire - 60:
            return self.token

        try:
            import bcrypt
            import httpx
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

        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, data=data)
            res_json = res.json()
            if res.status_code == 200 and "access_token" in res_json:
                self.token = res_json["access_token"]
                self.token_expire = now + res_json.get("expires_in", 10800)
                return self.token
            else:
                err_msg = res_json.get("message", res.text)
                raise Exception(f"인증 거부 ({res.status_code}): {err_msg}")

    def upload_product(self, payload: dict) -> dict:
        """스마트스토어 상품 등록 호출 (/v2/products)"""
        import httpx
        token = self.get_token()
        url = f"{self.base_url}/v2/products"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        with httpx.Client(timeout=15.0) as client:
            res = client.post(url, headers=headers, json=payload)
            return res.json()

# ==========================================
# 2. 다중 계정 설정 다이얼로그
# ==========================================
class AccountConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("출하 라인 (스토어 다중 계정) 설정")
        self.resize(460, 320)
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
        btn_save.setStyleSheet("background-color: #3574f0; color: white; padding: 8px; font-weight: bold; border-radius: 4px;")
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
# 3. 백그라운드 대량 전송 스레드
# ==========================================
class BenchmarkUploadWorker(QThread):
    progress_signal = Signal(int, int, str, str, str)  # 진행률, 행 인덱스, LOT 식별자, 결과 상태, 상세 내용
    finished_signal = Signal(int, int, str)            # 성공 수, 실패 수, 종료 사유
    error_signal = Signal(str)                         # 즉시 중단 에러

    def __init__(self, data_list, active_clients, round_robin=True):
        super().__init__()
        self.data_list = data_list
        self.clients = active_clients
        self.round_robin = round_robin
        self.is_running = True

    def run(self):
        success, fail = 0, 0
        total = len(self.data_list)

        # 1. 전송 시작 전 각 계정별 토큰 사전 검증
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

            client = self.clients[row_idx % len(self.clients)] if self.round_robin else self.clients[0]

            # 네이버 표준 상품 등록 페이로드 구성
            payload = {
                "originProduct": {
                    "statusType": "SALE",
                    "name": item["name"],
                    "leafCategoryId": item["cat"],
                    "detailContent": item.get("desc", "<p>상세정보 참조</p>"),
                    "images": {
                        "representativeImage": {"url": item["thumb"]}
                    },
                    "salePrice": int(item["raw_price"]),
                    "stockQuantity": 100
                }
            }

            try:
                # 실제 네이버 커머스 API 전송 호출
                res = client.upload_product(payload)
                
                # API 응답 판정
                if "originProductNo" in res:
                    prod_no = res["originProductNo"]
                    status_text = f"성공 (No: {prod_no})"
                    success += 1
                elif "message" in res:
                    status_text = f"실패: {res.get('message')}"
                    fail += 1
                else:
                    status_text = f"응답 확인 필요 ({str(res)[:25]})"
                    fail += 1

            except Exception as e:
                status_text = f"오류: {str(e)[:30]}"
                fail += 1

            progress_pct = int(((row_idx + 1) / total) * 100)
            self.progress_signal.emit(progress_pct, row_idx, item["code"], status_text, "")
            
            # 스마트스토어 초당 호출 제한(Rate Limit) 준수 (350ms 대기)
            self.msleep(350)

        self.finished_signal.emit(success, fail, "모든 규격 데이터 릴리즈가 완료되었습니다.")

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

        # 상단 제어 바
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

        # 전송 시작 버튼
        self.btn_start = QPushButton("릴리즈 전송 시작")
        self.btn_start.setStyleSheet("background-color: #2e6930; color: white; padding: 8px 18px; font-weight: bold; border-radius: 4px;")
        self.btn_start.clicked.connect(self.start_upload)

        # 전송 중단 버튼 (신규 추가)
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

        # 데이터 그리드
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["LOT 식별자", "품목 규격명", "카테고리 코드", "출하 공급가", "옵션 구성", "릴리즈 상태"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #1e1f22; color: #bcbec4; gridline-color: #393b40; border: none; }
            QHeaderView::section { background-color: #2b2d30; color: #dfe1e5; padding: 5px; border: 1px solid #393b40; }
        """)
        layout.addWidget(self.table)

        # 프로그레스 바 & 진행 수치 라벨
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

        df = pd.read_excel(path, sheet_name="엑셀 수정 업로드 상품 정보", header=None)
        self.raw_data.clear()
        self.table.setRowCount(0)

        for r in range(3, len(df)):
            item_code = str(df.iloc[r, 17]) if pd.notna(df.iloc[r, 17]) else f"LOT-{r-2:05d}"
            name = str(df.iloc[r, 1])
            cat = str(df.iloc[r, 4])
            raw_price = df.iloc[r, 19] if pd.notna(df.iloc[r, 19]) else 0
            price_str = f"{int(raw_price):,}원"
            opt = str(df.iloc[r, 52]) if pd.notna(df.iloc[r, 52]) else "단품"
            thumb = str(df.iloc[r, 23]) if pd.notna(df.iloc[r, 23]) else ""
            desc = str(df.iloc[r, 32]) if pd.notna(df.iloc[r, 32]) else ""

            self.raw_data.append({
                "code": item_code,
                "name": name,
                "cat": cat,
                "raw_price": raw_price,
                "price_str": price_str,
                "opt": opt,
                "thumb": thumb,
                "desc": desc
            })

            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(item_code))
            self.table.setItem(row_idx, 1, QTableWidgetItem(name[:35] + "..."))
            self.table.setItem(row_idx, 2, QTableWidgetItem(cat))
            self.table.setItem(row_idx, 3, QTableWidgetItem(price_str))
            self.table.setItem(row_idx, 4, QTableWidgetItem(opt))
            self.table.setItem(row_idx, 5, QTableWidgetItem("적재 완료 (대기)"))

        self.lbl_progress_info.setText(f"총 {len(self.raw_data):,}건 적재 완료")

    def start_upload(self):
        if not self.raw_data:
            QMessageBox.warning(self, "데이터 없음", "먼저 벤치마킹 엑셀 데이터를 적재해 주세요.")
            return

        # 1. API 자격증명 설정 파일 존재 여부 및 필드 검증
        if not os.path.exists(CONFIG_PATH):
            QMessageBox.critical(
                self, "인증 키 부재",
                "네이버 커머스 API 연동 키가 설정되지 않았습니다.\n"
                "[채널 자격증명 설정] 버튼을 눌러 애플리케이션 ID와 시크릿 키를 먼저 등록해 주세요."
            )
            return

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        clients = []
        if self.chk_round_robin.isChecked():
            # 3개 채널 순환 검사
            for i in range(1, 4):
                acc = cfg.get(f"acc_{i}", {})
                cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")
                if cid and csec:
                    clients.append(NaverCommerceClient(cid, csec))
            if not clients:
                QMessageBox.critical(
                    self, "인증 키 미입력",
                    "순환 배분을 위해 최소 1개 이상의 유효한 채널 ID/시크릿 키가 필요합니다.\n"
                    "[채널 자격증명 설정]에서 계정 정보를 입력해 주세요."
                )
                return
        else:
            # 단일 선택 채널 검사
            sel_idx = self.combo_accounts.currentIndex() + 1
            acc = cfg.get(f"acc_{sel_idx}", {})
            cid, csec = acc.get("client_id", ""), acc.get("client_secret", "")
            if not cid or not csec:
                QMessageBox.critical(
                    self, "인증 키 미입력",
                    f"선택한 릴리즈 채널 #{sel_idx}의 ID 또는 시크릿 키가 비어 있습니다.\n"
                    "[채널 자격증명 설정]에서 인증 정보를 입력해 주세요."
                )
                return
            clients.append(NaverCommerceClient(cid, csec))

        # 2. UI 버튼 상태 전이
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_load_data.setEnabled(False)

        # 3. 전송 워커 기동
        self.worker = BenchmarkUploadWorker(self.raw_data, clients, round_robin=self.chk_round_robin.isChecked())
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
        QMessageBox.critical(self, "API 인증 차단", f"네이버 API 연동 오류로 작업을 시작할 수 없습니다:\n\n{err_msg}")
        self.reset_ui_state()

    def on_upload_finished(self, success, fail, reason):
        QMessageBox.information(
            self, "공정 종료",
            f"{reason}\n\n• 정상 출하 성공: {success:,}건\n• 규격 누락/실패: {fail:,}건"
        )
        self.reset_ui_state()

    def reset_ui_state(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("전송 중단")
        self.btn_load_data.setEnabled(True)

# 호환성을 위한 클래스 별칭 부여
ProductReleaserPage = ReleaserBenchmarkPage
``

## [File: pages/releaser_review_page.py]
``python
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

``

## [File: pages/review_page.py]
``python
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

``

## [File: pages/tech_library_page.py]
``python
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

``

## [File: pages/__init__.py]
``python

``
