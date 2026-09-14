def validate_account_defaults(defaults: dict) -> list[str]:
    """스마트스토어 등록 필수 기본값 누락 여부 점검"""
    missing = []
    if not defaults.get("outbound_location_id"):
        missing.append("출고지 주소 ID")
    if not defaults.get("return_location_id"):
        missing.append("반품지 주소 ID")
    if not defaults.get("as_telephone"):
        missing.append("A/S 문의 전화번호")
    return missing

def build_origin_product_payload(item: dict, defaults: dict) -> dict:
    """네이버 커머스 API v2 표준 상품등록(POST /v2/products) 페이로드 조립"""
    outbound_id = defaults.get("outbound_location_id", "")
    return_id = defaults.get("return_location_id", "")
    as_tel = defaults.get("as_telephone", "070-0000-0000")
    as_guide = defaults.get("as_guide", "") or "상세페이지를 참조해 주시기 바랍니다."

    shipping_addr_id = int(outbound_id) if str(outbound_id).isdigit() else outbound_id
    return_addr_id = int(return_id) if str(return_id).isdigit() else return_id

    origin_product = {
        "statusType": "SALE",
        "name": item["name"][:100],
        "leafCategoryId": str(item["cat"]),
        "detailContent": item.get("desc", "<p>상세정보 참조</p>"),
        "images": {
            "representativeImage": {"url": item["thumb"]}
        },
        "salePrice": int(item["raw_price"]),
        "stockQuantity": int(item.get("simple_stock", 100)) if not item.get("combos") else sum(c["stockQuantity"] for c in item["combos"]),
        "deliveryInfo": {
            "deliveryType": "DELIVERY",
            "deliveryAttributeType": "NORMAL",
            "deliveryFee": {
                "deliveryFeeType": "FREE",
                "baseFee": 0
            },
            "claimDeliveryInfo": {
                "returnDeliveryFee": 3000,
                "exchangeDeliveryFee": 6000,
                "shippingAddressId": shipping_addr_id,
                "returnAddressId": return_addr_id
            }
        },
        "detailAttribute": {
            "afterServiceInfo": {
                "afterServiceTelephoneNumber": as_tel,
                "afterServiceGuideContent": as_guide
            },
            "originAreaInfo": {
                "originAreaCode": "0200037",
                "importer": "상세페이지 참조"
            },
            "minorPurchasable": True
        }
    }

    if item.get("optional_images"):
        origin_product["images"]["optionalImages"] = [{"url": u} for u in item["optional_images"][:9]]

    if item.get("combos"):
        origin_product["detailAttribute"]["optionInfo"] = {
            "optionSimple": [],
            "optionCustom": [],
            "optionCombinationGroupNames": {
                "optionGroupName1": item.get("opt_name") or "사양"
            },
            "optionCombinations": item["combos"]
        }

    return {"originProduct": origin_product}
