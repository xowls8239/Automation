"""
네이버 커머스 API 주소록 조회 (출고지/반품지 ID 자동 확인 및 매핑용).
엔드포인트: GET /external/v1/seller/addressbooks-for-page?page=N
"""

import httpx

def fetch_all_addressbooks(client, max_pages: int = 10) -> list:
    """등록된 모든 주소록 항목을 페이지네이션으로 수집해 반환."""
    token = client.get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{client.base_url}/v1/seller/addressbooks-for-page"

    all_items = []
    with httpx.Client(timeout=10.0) as http:
        for page in range(1, max_pages + 1):
            res = http.get(url, headers=headers, params={"page": page, "size": 50})

            if res.status_code != 200:
                raise Exception(f"주소록 조회 실패 (HTTP {res.status_code}): {res.text[:300]}")

            data = res.json()
            items = data.get("addressBooks", [])
            if not items:
                # 혹시 다른 키로 들어올 경우를 대비한 방어 로직
                if isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, list):
                            items = v
                            break
                elif isinstance(data, list):
                    items = data

            if not items:
                break

            all_items.extend(items)
            if len(items) < 50:
                break

    return all_items

def guess_id_field(item: dict):
    """주소록 고유 번호(ID) 추출 (공식 필드: addressBookNo)."""
    for key in ("addressBookNo", "id", "addressId", "addrBookId", "seq"):
        if key in item and item[key] is not None:
            return key, item[key]
    return None, None

def get_classified_addresses(client) -> dict:
    """
    네이버 주소록을 조회하여 출고지(RELEASE)와 반품지(REFUND_OR_EXCHANGE) 목록으로 자동 분류.
    반환: {
        "outbound": [{"id": 12345, "name": "기본출고지", "addr": "인천 남동구..."}, ...],
        "return": [{"id": 67890, "name": "기본반품지", "addr": "인천 남동구..."}, ...]
    }
    """
    raw_list = fetch_all_addressbooks(client)
    result = {"outbound": [], "return": []}

    for item in raw_list:
        _, addr_id = guess_id_field(item)
        if not addr_id:
            continue

        name = item.get("name", "이름없음")
        base_addr = item.get("baseAddress", "")
        detail_addr = item.get("detailAddress", "")
        full_addr = f"{base_addr} {detail_addr}".strip()
        addr_type = item.get("addressType", "")

        entry = {
            "id": addr_id,
            "name": name,
            "addr": full_addr,
            "display": f"[{addr_id}] {name} ({full_addr[:25]}...)"
        }

        if "RELEASE" in addr_type:
            result["outbound"].append(entry)
        elif "REFUND" in addr_type or "EXCHANGE" in addr_type:
            result["return"].append(entry)
        else:
            # 유형이 불명확한 경우 양쪽 모두에 후보로 등록
            result["outbound"].append(entry)
            result["return"].append(entry)

    return result
