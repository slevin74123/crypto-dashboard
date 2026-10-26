from __future__ import annotations
import requests


class SorsaClient:
    def __init__(self, api_key: str, base_url: str = "https://api.sorsa.xyz"):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })

    def _get(self, endpoint: str, params: dict | None = None) -> dict | list:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            r = self._session.get(url, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            print(f"[SorsaClient] HTTP error {e.response.status_code} — {url}")
            return {}
        except requests.RequestException as e:
            print(f"[SorsaClient] Request failed — {url} — {e}")
            return {}
        except ValueError as e:
            print(f"[SorsaClient] JSON decode error — {url} — {e}")
            return {}

    def get_top_kols(self, limit: int = 20) -> list:
        data = self._get("kols/top", params={"limit": limit})
        if isinstance(data, list):
            return data
        return data.get("data", data.get("kols", data.get("results", [])))

    def get_new_following_7d(self, limit: int = 20) -> list:
        data = self._get("following/new", params={"days": 7, "limit": limit})
        if isinstance(data, list):
            return data
        return data.get("data", data.get("users", data.get("results", [])))

    def get_kol_score(self, wallet: str) -> dict:
        data = self._get("kols/score", params={"wallet": wallet})
        return data if isinstance(data, dict) else {}

    def get_followers_stats(self, wallet: str) -> dict:
        data = self._get("kols/followers/stats", params={"wallet": wallet})
        return data if isinstance(data, dict) else {}


def test_connection(api_key: str) -> bool:
    client = SorsaClient(api_key)
    try:
        r = requests.get(
            f"{client.base_url}/health",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        if r.ok:
            print(f"[SorsaClient] Connection OK — {client.base_url}")
            return True
        print(f"[SorsaClient] Connection failed — HTTP {r.status_code}")
        return False
    except requests.RequestException as e:
        print(f"[SorsaClient] Connection error — {e}")
        return False
