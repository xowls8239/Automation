from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QGridLayout, QTextEdit, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DashboardPage(QWidget):
    def __init__(self, nav_callback):
        super().__init__()
        self.setFont(QFont("Malgun Gothic", 9))
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
        title = QLabel("기술 자동화 모니터링 시스템")
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
        btn_go_release.setMinimumHeight(42)
        btn_go_release.setStyleSheet("""
            QPushButton {
                background-color: #365880; color: white; font-weight: bold;
                border-radius: 5px; font-size: 13px; padding: 6px 10px;
            }
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
        sub_total.setStyleSheet("color: #bcbec4; font-size: 11px; font-weight: bold;")
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

        field_map = {0: ("total", "[전체] "), 1: ("month", "[금월] "), 2: ("today", "[금일] +")}
        field, prefix = field_map[btn_id]

        for key, card in self.card_widgets.items():
            val = self.metrics_data[key][field]
            card["main_val"].setText(f"{prefix}{val} {card['unit']}")