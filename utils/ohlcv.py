import requests

BIRDEYE_KEY = None  # set from session state in caller


def fetch_ohlcv(token_address: str, timeframe: str, limit: int = 200, api_key: str = "") -> list:
    """
    Fetch OHLCV candles from Birdeye.
    timeframe options: "1m","5m","15m","1H","4H","1D","1W"
    Returns list of dicts: {open, high, low, close, volume, unixTime}
    """
    r = requests.get(
        "https://public-api.birdeye.so/defi/ohlcv",
        headers={"X-API-KEY": api_key, "x-chain": "solana"},
        params={"address": token_address, "type": timeframe, "limit": limit},
        timeout=10
    )
    if r.status_code != 200:
        print(f"OHLCV error {r.status_code}: {r.text[:200]}")
        return []
    return r.json().get("data", {}).get("items", [])
