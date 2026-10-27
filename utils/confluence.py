def calculate_confluence(
    token_address: str,
    birdeye_data: dict,
    ta_result: dict,
    kol_holdings: list,
) -> dict:
    """
    Score a token 0-100 across 4 dimensions.

    birdeye_data: dict with keys like holders, mc, volume24h (from Birdeye token overview)
    ta_result:    output of run_ta() — trend_bias, rsi, bullish_obs, fvgs, liquidity
    kol_holdings: list of wallet dicts that hold this token (from Sorsa / cache)
    """

    # ── Social score 0-25 ─────────────────────────────────────────────────────
    social = 0
    holders = birdeye_data.get("holder") or birdeye_data.get("holders") or 0
    kol_mentions = birdeye_data.get("kol_mentions") or 0

    if holders >= 2000:
        social += 15
    elif holders >= 1000:
        social += 10
    elif holders >= 500:
        social += 5

    if kol_mentions >= 5:
        social += 10
    elif kol_mentions >= 3:
        social += 7
    elif kol_mentions >= 1:
        social += 4

    social = min(social, 25)

    # ── Smart money score 0-25 ────────────────────────────────────────────────
    smart = 0
    n_kols = len(kol_holdings) if kol_holdings else 0

    if n_kols >= 10:
        smart = 25
    elif n_kols >= 5:
        smart = 18
    elif n_kols >= 3:
        smart = 12
    elif n_kols >= 1:
        smart = 6

    smart = min(smart, 25)

    # ── TA score 0-35 ─────────────────────────────────────────────────────────
    ta = 0
    rsi = ta_result.get("rsi")
    trend = ta_result.get("trend_bias", "ranging")
    obs = ta_result.get("bullish_obs") or []
    fvgs = ta_result.get("fvgs") or []

    # RSI 40-60 neutral zone = 10pt; extreme zones = 0pt
    if rsi is not None:
        if 40 <= rsi <= 60:
            ta += 10
        elif 30 <= rsi < 40 or 60 < rsi <= 70:
            ta += 5

    # Trend bias
    if trend == "bullish":
        ta += 15
    elif trend == "ranging":
        ta += 5

    # OB or FVG present = 10pt
    if obs or fvgs:
        ta += 10

    ta = min(ta, 35)

    # ── Market score 0-15 ─────────────────────────────────────────────────────
    market = 0
    mc = birdeye_data.get("mc") or birdeye_data.get("marketCap") or birdeye_data.get("fdv") or 0
    vol = birdeye_data.get("v24hUSD") or birdeye_data.get("volume24h") or birdeye_data.get("volume") or 0

    try:
        mc = float(mc)
    except (TypeError, ValueError):
        mc = 0
    try:
        vol = float(vol)
    except (TypeError, ValueError):
        vol = 0

    if mc >= 1_000_000:
        market += 5

    if mc > 0 and (vol / mc) >= 0.05:
        market += 5

    if holders >= 500:
        market += 5

    market = min(market, 15)

    # ── Total & signal ────────────────────────────────────────────────────────
    total = social + smart + ta + market

    if total >= 75:
        signal = "STRONG BUY"
    elif total >= 55:
        signal = "BUY"
    elif total >= 35:
        signal = "WATCH"
    else:
        signal = "AVOID"

    return {
        "total_score":       total,
        "social_score":      social,
        "smart_money_score": smart,
        "ta_score":          ta,
        "market_score":      market,
        "signal":            signal,
        "debug": {
            "holders":    holders,
            "kol_count":  n_kols,
            "rsi":        rsi,
            "trend":      trend,
            "ob_count":   len(obs),
            "fvg_count":  len(fvgs),
            "mc":         mc,
            "vol":        vol,
        },
    }
