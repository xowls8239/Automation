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