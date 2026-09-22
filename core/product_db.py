from modules.product_releaser.naver_api import NaverCommerceAPI

def extract_row(detail_json: dict) -> dict:
    """API 응답을 화면 표시/저장용 딕셔너리로 변환 (기존과 동일)"""
    origin = detail_json.get("originProduct", {})
    images = origin.get("images", {})
    return {
        "origin_product_no": None,  # 호출부에서 채워줌
        "product_name": origin.get("name"),
        "sale_price": origin.get("salePrice"),
        "stock_quantity": origin.get("stockQuantity"),
        "representative_image": images.get("representativeImage", {}).get("url"),
        "optional_images": [img.get("url") for img in images.get("optionalImages", [])],
        "detail_content_html": origin.get("detailContent"),
    }

def fetch_all_products(api: NaverCommerceAPI) -> list[dict]:
    """
    1단계: 네이버에서 전체 상품을 가져오기만 함 (저장 X)
    화면에 표시할 리스트를 반환
    """
    all_rows = []
    page = 1
    while True:
        result = api.get_product_list(page=page)
        product_numbers = result.get("contents", [])  # ⚠️ 실제 키 확인 필요
        if not product_numbers:
            break
        for item in product_numbers:
            origin_no = item.get("originProductNo")
            detail = api.get_origin_product_detail(origin_no)
            row = extract_row(detail)
            row["origin_product_no"] = origin_no
            all_rows.append(row)
        page += 1
    return all_rows

def save_to_tech_library(selected_rows: list[dict]):
    """
    2단계: 승인된 항목만 기술 라이브러리에 저장
    ⚠️ tech_library_page.py가 실제로 쓰는 저장 방식(DB 테이블? JSON파일? 폴더?)에 맞춰 구현 필요
    """
    for row in selected_rows:
        ...  # tech_library_page.py의 기존 저장 로직 재사용