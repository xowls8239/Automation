@'
from .dashboard_page import DashboardPage
from .competitor_page import CompetitorPage
from .parts_page import PartsPage
from .review_page import ReviewPage
from .tech_library_page import TechLibraryPage
from .releaser_review_page import ReleaserReviewPage
from .releaser_benchmark_page import ReleaserBenchmarkPage

__all__ = [
    "DashboardPage",
    "CompetitorPage",
    "PartsPage",
    "ReviewPage",
    "TechLibraryPage",
    "ReleaserReviewPage",
    "ReleaserBenchmarkPage"
]
'@ | Set-Content -Path "pages\__init__.py" -Encoding utf8