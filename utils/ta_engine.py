def calculate_rsi(candles: list, period=14) -> float:
    closes = [c["close"] for c in candles]
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period + 1, len(closes)):
        diff = closes[i] - closes[i-1]
        avg_gain = (avg_gain * (period-1) + max(diff, 0)) / period
        avg_loss = (avg_loss * (period-1) + max(-diff, 0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def detect_trend_bias(candles: list) -> str:
    if len(candles) < 3:
        return "ranging"
    hh = sum(1 for i in range(1, len(candles)) if candles[i]["high"] > candles[i-1]["high"])
    hl = sum(1 for i in range(1, len(candles)) if candles[i]["low"] > candles[i-1]["low"])
    lh = sum(1 for i in range(1, len(candles)) if candles[i]["high"] < candles[i-1]["high"])
    ll = sum(1 for i in range(1, len(candles)) if candles[i]["low"] < candles[i-1]["low"])
    bull = hh + hl
    bear = lh + ll
    if bull > bear * 1.5:
        return "bullish"
    if bear > bull * 1.5:
        return "bearish"
    return "ranging"


def detect_bullish_ob(candles: list, move_threshold=0.03) -> list:
    obs = []
    for i in range(len(candles) - 2):
        if candles[i]["close"] < candles[i]["open"]:
            if candles[i+1]["open"] > 0:
                move = (candles[i+2]["high"] - candles[i+1]["open"]) / candles[i+1]["open"]
                if move >= move_threshold:
                    obs.append({
                        "zone": [candles[i]["low"], candles[i]["high"]],
                        "type": "bullish_ob",
                        "valid": True,
                        "time": candles[i]["unixTime"]
                    })
    return obs[-5:]


def detect_fvg(candles: list) -> list:
    fvgs = []
    for i in range(1, len(candles) - 1):
        gap_low = candles[i-1]["high"]
        gap_high = candles[i+1]["low"]
        if gap_high > gap_low:
            fvgs.append({
                "zone": [gap_low, gap_high],
                "type": "bullish_fvg",
                "filled": False,
                "time": candles[i]["unixTime"]
            })
    return fvgs[-5:]
