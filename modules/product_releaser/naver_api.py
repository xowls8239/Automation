import time
import json
import bcrypt
import pybase64
import httpx
from pathlib import Path

class NaverCommerceAPI:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.commerce.naver.com/external"
        self.token = None
        self.token_expire_time = 0

    def get_token(self) -> str:
        """커머스 API 전자서명 기반 토큰 발급/갱신"""
        current_time = time.time()
        if self.token and current_time < self.token_expire_time - 60:
            return self.token

        timestamp = int(current_time * 1000)
        password = f"{self.client_id}_{timestamp}".encode("utf-8")
        hashed = bcrypt.hashpw(password, self.client_secret.encode("utf-8"))
        signature = pybase64.standard_b64encode(hashed).decode("utf-8")

        url = f"{self.base_url}/v1/oauth2/token"
        data = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF"
        }

        response = httpx.post(url, data=data, timeout=10.0)
        res_json = response.json()
        if "access_token" in res_json:
            self.token = res_json["access_token"]
            self.token_expire_time = current_time + res_json.get("expires_in", 10800)
            return self.token
        raise Exception(f"토큰 발급 실패: {res_json}")

    def upload_product(self, payload: dict) -> dict:
        """단일 상품 등록 API 호출"""
        token = self.get_token()
        url = f"{self.base_url}/v2/products"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        res = httpx.post(url, headers=headers, json=payload, timeout=15.0)
        return res.json()

    def get_product_list(self, page: int = 1, size: int = 100) -> dict:
        """
        상품 목록 조회 API
        - 등록된 상품들의 원상품번호(originProductNo) 목록을 페이징으로 가져옴
        - ⚠️ 정확한 엔드포인트 경로/파라미터명은 문서 확인 필요
        """
        token = self.get_token()
        url = f"{self.base_url}/v1/products/search"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        params = {"page": page, "size": size}
        res = httpx.get(url, headers=headers, params=params, timeout=15.0)
        return res.json()