# core/excel_parser.py
"""
벤치마킹 규격셋(스마트스토어 표준 대량등록 엑셀 양식) 파서.

- 컬럼 번호 하드코딩 대신, 0행 헤더 텍스트로 매핑한다.
  → 판매자가 엑셀 컬럼 순서를 바꾸거나, 시즌에 따라 양식이 살짝 달라져도
    헤더 이름만 유지되면 깨지지 않는다.
- '조합형 옵션'은 여러 컬럼(옵션1~3, 추가금액, 재고수, 판매여부, 재고코드...)에
  콤마(,)로 병렬 인코딩되어 있으므로, zip으로 묶어 콤보 리스트로 복원한다.
"""

import re
import pandas as pd

DATA_START_ROW = 3  # 0~2행은 헤더/설명, 3행부터 실데이터 (기존 코드와 동일)


def _normalize_header(raw) -> str:
    """'⊙원산지\\n(최하단 카테고리 코드)' -> '원산지(최하단 카테고리 코드)' 처럼 정규화"""
    if not isinstance(raw, str):
        return ""
    return raw.replace("⊙", "").replace("\n", "").strip()


def build_column_map(df: pd.DataFrame) -> dict:
    """0행 헤더를 읽어 {정규화된 헤더명: 컬럼 인덱스} 딕셔너리를 만든다."""
    header_row = df.iloc[0]
    colmap = {}
    for idx, raw in enumerate(header_row):
        key = _normalize_header(raw)
        if key:
            colmap[key] = idx
    return colmap


# 이 양식에서 실제로 쓰는 정규화된 헤더명 상수
# (엑셀이 열리지 않는 환경에서도 어떤 필드를 참조하는지 한눈에 보이게 상수로 분리)
COL = {
    "seller_code": "자체상품코드",          # LOT 식별자로 사용 중인 필드
    "name": "상품명",
    "category_id": "카테고리 (최하단 카테고리 코드)",
    "tax_type": "세금구분",
    "origin_category_id": "원산지(최하단 카테고리 코드)",
    "origin_detail": "원산지(수입사 or 기타입력)",
    "delivery_fee_type": "배송비구분",
    "delivery_fee": "배송비",
    "cost_price": "원가",
    "sale_price": "판매가",
    "consumer_price": "소비자가",
    "thumb": "대표이미지",
    "desc_html": "상품설명정보",
    "adult_only": "성인전용",
    # 옵션 타입: 0=단품, 1=독립형, 2=조합형 (이 파일 기준)
    "option_type": "옵션 타입",
    # 단품
    "simple_stock": "재고수(단품)",
    # 조합형 (콤마로 병렬 인코딩)
    "combo_group_name": "옵션명(조합형)",
    "combo_opt1": "옵션1(조합형)",
    "combo_opt2": "옵션2(조합형)",
    "combo_opt3": "옵션3(조합형)",
    "combo_extra_price": "옵션 추가금액(조합형)",
    "combo_stock": "옵션 재고수(조합형)",
    "combo_usable": "판매여부(조합형)",
    "combo_seller_code": "판매자 재고코드(조합형)",
    # 독립형 (이 파일엔 안 쓰이지만 다른 배치에 나올 수 있어 대비)
    "solo_name": "옵션명(독립형)",
    "solo_value": "옵션값(독립형)",
    "solo_extra_price": "옵션 추가금액(독립형)",
    "solo_stock": "옵션 재고수(독립형)",
    "solo_usable": "판매여부(독립형)",
}


def _get(row, colmap, key, default=None):
    idx = colmap.get(COL[key])
    if idx is None or idx >= len(row):
        return default
    val = row[idx]
    return default if pd.isna(val) else val


def _split_csv_field(value, expected_count: int) -> list:
    """'A,B' -> ['A','B'] / NaN -> ['']*expected_count / 개수가 안 맞으면 패딩·절단"""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return [""] * expected_count
    parts = [p.strip() for p in str(value).split(",")]
    if len(parts) < expected_count:
        parts += [""] * (expected_count - len(parts))
    return parts[:expected_count]


def parse_combination_options(row, colmap) -> list:
    """조합형 옵션 컬럼들을 zip으로 묶어 optionCombinations 후보 리스트로 복원.

    반환 예:
    [
      {"opt1": "A. 우드 칼라", "opt2": "", "opt3": "", "extra_price": 0,
       "stock": 200, "usable": True, "seller_code": "5292295850343"},
      ...
    ]
    """
    opt1_raw = _get(row, colmap, "combo_opt1")
    if opt1_raw is None:
        return []

    combo_count = len(str(opt1_raw).split(","))

    opt1_list = _split_csv_field(opt1_raw, combo_count)
    opt2_list = _split_csv_field(_get(row, colmap, "combo_opt2"), combo_count)
    opt3_list = _split_csv_field(_get(row, colmap, "combo_opt3"), combo_count)
    price_list = _split_csv_field(_get(row, colmap, "combo_extra_price"), combo_count)
    stock_list = _split_csv_field(_get(row, colmap, "combo_stock"), combo_count)
    usable_list = _split_csv_field(_get(row, colmap, "combo_usable"), combo_count)
    seller_code_list = _split_csv_field(_get(row, colmap, "combo_seller_code"), combo_count)

    combos = []
    for i in range(combo_count):
        if not opt1_list[i]:
            continue  # 옵션명 자체가 비어있는 슬롯은 건너뜀
        try:
            extra_price = int(float(price_list[i])) if price_list[i] else 0
        except ValueError:
            extra_price = 0
        try:
            stock = int(float(stock_list[i])) if stock_list[i] else 0
        except ValueError:
            stock = 0

        combos.append({
            "opt1": opt1_list[i],
            "opt2": opt2_list[i],
            "opt3": opt3_list[i],
            "extra_price": extra_price,
            "stock": stock,
            "usable": (usable_list[i].upper() == "Y") if usable_list[i] else True,
            "seller_code": seller_code_list[i] or None,
        })
    return combos


def parse_row(row, colmap) -> dict:
    """엑셀 한 행을 업로드용 dict로 변환. 단품/독립형/조합형을 자동 분기."""
    option_type = _get(row, colmap, "option_type", default=0)
    try:
        option_type = int(option_type)
    except (TypeError, ValueError):
        option_type = 0

    combos = []
    simple_stock = 0

    if option_type == 2:  # 조합형
        combos = parse_combination_options(row, colmap)
    elif option_type == 1:  # 독립형 (단일 차원 옵션)
        names = _split_csv_field(_get(row, colmap, "solo_value"), 999)
        prices = _split_csv_field(_get(row, colmap, "solo_extra_price"), len(names))
        stocks = _split_csv_field(_get(row, colmap, "solo_stock"), len(names))
        for n, p, s in zip(names, prices, stocks):
            if not n:
                continue
            combos.append({
                "opt1": n, "opt2": "", "opt3": "",
                "extra_price": int(float(p)) if p else 0,
                "stock": int(float(s)) if s else 0,
                "usable": True,
                "seller_code": None,
            })
    else:  # 단품 (옵션 없음)
        simple_stock = _get(row, colmap, "simple_stock", default=0)
        try:
            simple_stock = int(float(simple_stock))
        except (TypeError, ValueError):
            simple_stock = 0

    seller_code = _get(row, colmap, "seller_code")
    name = _get(row, colmap, "name", default="")
    sale_price = _get(row, colmap, "sale_price", default=0)
    try:
        sale_price = int(float(sale_price))
    except (TypeError, ValueError):
        sale_price = 0

    return {
        "code": str(seller_code) if seller_code else None,          # LOT 식별자
        "name": str(name) if name else "",
        "cat": str(_get(row, colmap, "category_id", default="")),
        "raw_price": sale_price,
        "option_type": option_type,
        "combos": combos,               # 조합형/독립형이면 채워짐
        "simple_stock": simple_stock,   # 단품이면 채워짐
        "thumb": str(_get(row, colmap, "thumb", default="")),
        "desc": str(_get(row, colmap, "desc_html", default="")),
        "origin_category_id": str(_get(row, colmap, "origin_category_id", default="")),
        "origin_detail": str(_get(row, colmap, "origin_detail", default="")),
        "delivery_fee_type": str(_get(row, colmap, "delivery_fee_type", default="")),
        "delivery_fee": _get(row, colmap, "delivery_fee", default=0),
        "adult_only": str(_get(row, colmap, "adult_only", default="N")).upper() == "Y",
    }


def load_benchmark_excel(path: str, sheet_name: str = "엑셀 수정 업로드 상품 정보") -> list:
    """벤치마킹 규격셋 엑셀을 읽어 업로드용 dict 리스트로 반환."""
    df = pd.read_excel(path, sheet_name=sheet_name, header=None)
    colmap = build_column_map(df)

    missing = [v for v in COL.values() if v not in colmap]
    if missing:
        # 필수는 아니지만, 양식이 바뀐 경우 조기에 알 수 있도록 경고성 정보 포함
        print(f"[WARN] 엑셀에서 찾지 못한 헤더: {missing}")

    results = []
    for r in range(DATA_START_ROW, len(df)):
        row = df.iloc[r]
        if pd.isna(row[colmap.get(COL["name"], 1)]):
            continue  # 상품명 없는 빈 행은 스킵
        results.append(parse_row(row, colmap))
    return results