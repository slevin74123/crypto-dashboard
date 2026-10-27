import time
import requests

BIRDEYE_KEY = None  # set from session state in caller

_TIMEFRAME_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900,
    "1H": 3600, "4H": 14400, "1D": 86400, "1W": 604800,
}


def fetch_ohlcv(token_address: str, timeframe: str, limit: int = 200, api_key: str = "") -> list:
    """
    Fetch OHLCV candles from Birdeye.
    timeframe options: "1m","5m","15m","1H","4H","1D","1W"
    Returns list of dicts: {open, high, low, close, volume, unixTime}
    """
    now = int(time.time())
    interval = _TIMEFRAME_SECONDS.get(timeframe, 3600)
    time_from = now - interval * limit

    r = requests.get(
        "https://public-api.birdeye.so/defi/ohlcv",
        headers={"X-API-KEY": api_key, "x-chain": "solana"},
        params={
            "address": token_address,
            "type": timeframe,
            "time_from": time_from,
            "time_to": now,
        },
        timeout=10,
    )
    if r.status_code != 200:
        print(f"OHLCV error {r.status_code}: {r.text[:200]}")
        return []

    items = r.json().get("data", {}).get("items", [])
    # normalize keys: o/h/l/c → open/high/low/close
    normalized = []
    for item in items:
        normalized.append({
            "unixTime": item.get("unixTime"),
            "open":     item.get("o") or item.get("open"),
            "high":     item.get("h") or item.get("high"),
            "low":      item.get("l") or item.get("low"),
            "close":    item.get("c") or item.get("close"),
            "volume":   item.get("vUsd") or item.get("v"),
        })
    return normalized
