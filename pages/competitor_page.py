from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt
from datetime import datetime

from .vendor_collector_page import VendorCollectorPage, load_vendor_db
from .product_sourcing_page import ProductSourcingPage


# ----------------------------------------------------------------------
# 1번 카드(경쟁사 탐색) / 2번 카드(경쟁사 검증) 통계 계산
# ----------------------------------------------------------------------


def compute_discovery_stats() -> dict:
    """1번 카드: 경쟁사 탐색 - 누적/금월/금일 발견 건수"""
    db = load_vendor_db()
    now = datetime.now()
    total = len(db)
    this_month = 0
    today = 0
    for v in db.values():
        seen = v.get("first_seen_at", "")
        try:
            seen_dt = datetime.fromisoformat(seen)
        except ValueError:
            continue
        if seen_dt.year == now.year and seen_dt.month == now.month:
            this_month += 1
        if seen_dt.date() == now.date():
            today += 1
    return {"total": total, "this_month": this_month, "today": today}


def compute_verification_stats() -> dict:
    """2번 카드: 경쟁사 검증 - 적합/부적합 + 제품조회 여부"""
    db = load_vendor_db()
    fit = sum(1 for v in db.values() if v.get("status") == "적합")
    unfit = sum(1 for v in db.values() if v.get("status") == "부적합")
    pending_judge = len(db) - fit - unfit
    research_done = sum(1 for v in db.values() if v.get("research_status") == "완료")
    research_pending = len(db) - research_done
    return {
        "fit": fit,
        "unfit": unfit,
        "pending_judge": pending_judge,
        "research_done": research_done,
        "research_pending": research_pending,
    }


# ----------------------------------------------------------------------
# 공통 카드 위젯
# ----------------------------------------------------------------------
class StageCard(QFrame):
    def __init__(self, index: int, title: str, on_click):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background-color: #2b2d30; border-radius: 8px; }
            QFrame:hover { background-color: #33353a; }
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title_lbl = QLabel(f"{index}. {title}")
        title_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        layout.addWidget(title_lbl)

        self.stat_container = QVBoxLayout()
        self.stat_container.setSpacing(4)
        layout.addLayout(self.stat_container)

        layout.addStretch()

        btn = QPushButton("바로가기")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "background-color: #3574f0; color: white; padding: 8px; font-weight: bold; border-radius: 4px;"
        )
        btn.clicked.connect(on_click)
        layout.addWidget(btn)

    def add_stat_line(self, text: str, color: str = "#bcbec4", bold: bool = False):
        lbl = QLabel(text)
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: {weight};")
        self.stat_container.addWidget(lbl)

    def clear_stats(self):
        while self.stat_container.count():
            item = self.stat_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()


# ----------------------------------------------------------------------
# 뒤로가기 상단바 (세부 화면 공통 래퍼)
# ----------------------------------------------------------------------
class DetailPageWrapper(QWidget):
    def __init__(self, title: str, content_widget: QWidget, on_back):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        bar = QFrame()
        bar.setStyleSheet("background-color: #1e1f22; border-bottom: 1px solid #393b40;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 10, 16, 10)

        btn_back = QPushButton("〈 경쟁사/제품 분석")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(
            "background: transparent; color: #61afef; border: none; font-weight: bold; font-size: 13px;"
        )
        btn_back.clicked.connect(on_back)
        bar_layout.addWidget(btn_back)

        sep = QLabel(f"  /  {title}")
        sep.setStyleSheet("color: #9da0a8; font-size: 13px;")
        bar_layout.addWidget(sep)
        bar_layout.addStretch()

        layout.addWidget(bar)
        layout.addWidget(content_widget)


# ----------------------------------------------------------------------
# 경쟁사/제품 분석 메인 페이지
# ----------------------------------------------------------------------
class CompetitorPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # ---- 랜딩 화면 ----
        self.landing = QWidget()
        landing_layout = QVBoxLayout(self.landing)
        landing_layout.setContentsMargins(20, 20, 20, 20)
        landing_layout.setSpacing(16)

        title = QLabel("경쟁사/제품 분석")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        subtitle = QLabel("거래처 탐색 · 검증 · 실적 규격 마이닝 엔진")
        subtitle.setStyleSheet("color: #9da0a8; font-size: 12px;")
        landing_layout.addWidget(title)
        landing_layout.addWidget(subtitle)

        card_row = QHBoxLayout()
        card_row.setSpacing(16)

        # 카드1: 경쟁사 탐색 (연동됨 - 거래처 콜렉터의 키워드 조회 기능)
        self.card1 = StageCard(1, "경쟁사 탐색", self.open_vendor_collector)
        card_row.addWidget(self.card1)

        # 카드2: 경쟁사 검증 (연동됨 - 거래처 콜렉터의 적합/부적합 판정 기능)
        self.card2 = StageCard(2, "경쟁사 검증", self.open_vendor_collector)
        card_row.addWidget(self.card2)

        # 카드3: 경쟁사 제품 조회 (연동됨 - 적합·조사미완료 거래처 중 선택 소싱)
        self.card3 = StageCard(3, "경쟁사 제품 조회", self.open_product_sourcing)
        card_row.addWidget(self.card3)

        # 카드4: 제품 매칭 - 아직 방식 설계 전이라 준비중
        self.card4 = StageCard(4, "제품 매칭", self.open_placeholder)
        self.card4.add_stat_line("추후 연동 예정", color="#7a7a7a")
        card_row.addWidget(self.card4)

        landing_layout.addLayout(card_row)
        landing_layout.addStretch()

        self.stack.addWidget(self.landing)

        # ---- 카드1·2 공용 세부 화면 (거래처 콜렉터: 탐색+검증이 한 화면에서 이뤄짐) ----
        self.vendor_collector = VendorCollectorPage()
        self.vendor_collector_wrapped = DetailPageWrapper(
            "경쟁사 탐색 / 검증", self.vendor_collector, self.go_back_to_landing
        )
        self.stack.addWidget(self.vendor_collector_wrapped)

        # ---- 카드3 세부 화면 (경쟁사 제품 조회/소싱) ----
        self.product_sourcing = ProductSourcingPage()
        self.product_sourcing_wrapped = DetailPageWrapper(
            "경쟁사 제품 조회", self.product_sourcing, self.go_back_to_landing
        )
        self.stack.addWidget(self.product_sourcing_wrapped)

        self.refresh_all_stats()

    # ------------------------------------------------------------
    def refresh_all_stats(self):
        d_stats = compute_discovery_stats()
        self.card1.clear_stats()
        self.card1.add_stat_line(f"누적 탐색: {d_stats['total']:,}건")
        self.card1.add_stat_line(f"이번 달: {d_stats['this_month']:,}건", color="#61afef")
        self.card1.add_stat_line(f"오늘: {d_stats['today']:,}건", color="#98c379")

        v_stats = compute_verification_stats()
        self.card2.clear_stats()
        self.card2.add_stat_line(
            f"적합 {v_stats['fit']:,} / 부적합 {v_stats['unfit']:,}", color="#61afef", bold=True
        )
        self.card2.add_stat_line(f"판정 대기: {v_stats['pending_judge']:,}건", color="#e5c07b")
        self.card2.add_stat_line(
            f"제품조회완료 {v_stats['research_done']:,} / 미완료 {v_stats['research_pending']:,}",
            color="#98c379"
        )

    def open_vendor_collector(self):
        self.stack.setCurrentWidget(self.vendor_collector_wrapped)

    def open_product_sourcing(self):
        self.product_sourcing.refresh_candidate_list()  # 매번 들어갈 때 최신 '적합·미완료' 목록으로 갱신
        self.stack.setCurrentWidget(self.product_sourcing_wrapped)

    def open_placeholder(self):
        pass  # 카드4(제품 매칭) 세부 화면은 방식 설계 후 구현 예정

    def go_back_to_landing(self):
        self.refresh_all_stats()  # 검증/소싱 결과를 즉시 반영
        self.stack.setCurrentWidget(self.landing)

    def on_menu_reactivated(self):
        """사이드바에서 이 메뉴를 다시 클릭했을 때 main.py가 호출하는 훅.
        세부화면(카드1 등)에 들어가 있어도 랜딩 화면으로 되돌리고 통계를 갱신한다."""
        self.go_back_to_landing()