from __future__ import annotations
import requests


class SorsaClient:
    base_url = "https://api.sorsa.xyz"

    def __init__(self, api_key: str):
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Sorsa error: {e}")
            return {}

    def get_top_kols(self, limit: int = 20) -> list:
        data = self._get("/kols", params={"limit": limit})
        if isinstance(data, list):
            return data
        return data.get("data", data.get("kols", data.get("results", [])))

    def get_new_following_7d(self, limit: int = 20) -> list:
        data = self._get("/new-following-7d", params={"limit": limit})
        if isinstance(data, list):
            return data
        return data.get("data", data.get("users", data.get("results", [])))

    def get_kol_score(self, wallet: str) -> dict:
        data = self._get("/score", params={"wallet": wallet})
        return data if isinstance(data, dict) else {}

    def get_followers_stats(self, wallet: str) -> dict:
        data = self._get("/followers-stats", params={"wallet": wallet})
        return data if isinstance(data, dict) else {}


def test_connection(api_key: str) -> bool:
    url = f"{SorsaClient.base_url}/kols"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": 1},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Sorsa error: {e}")
        return False
