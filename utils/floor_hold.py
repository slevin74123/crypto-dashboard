from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone


# ── Wallet archetype classifier ───────────────────────────────────────────────

def _classify_wallet(buys: int, sells: int, intervals: list[float]) -> str:
    total = buys + sells
    if total == 0:
        return "unknown"
    buy_pct = buys / total

    fast = sum(1 for i in intervals if i < 1.0)
    fast_ratio = fast / len(intervals) if intervals else 0

    if total <= 2:
        return "single_trader"
    if buy_pct >= 0.85 and fast_ratio >= 0.6:
        return "pure_support_bot"
    if buy_pct <= 0.25 and fast_ratio >= 0.5:
        return "pure_dump_bot"
    if buy_pct >= 0.7:
        return "accumulation_wallet"
    if buy_pct <= 0.35:
        return "distribution_wallet"
    return "mixed_trader"


# ── Dump event detector ───────────────────────────────────────────────────────

def _detect_dump_events(trades: list[dict], mc_history: list[dict]) -> list[dict]:
    """
    Identify sell clusters where MC drops ≥10% then recovers.
    Returns list of dump event dicts.
    """
    events = []
    if not mc_history or len(mc_history) < 3:
        return events

    for i in range(1, len(mc_history) - 1):
        prev_mc = mc_history[i - 1].get("mc") or mc_history[i - 1].get("marketCap", 0)
        curr_mc = mc_history[i].get("mc") or mc_history[i].get("marketCap", 0)
        if prev_mc <= 0 or curr_mc <= 0:
            continue
        drop_pct = (curr_mc - prev_mc) / prev_mc * 100
        if drop_pct >= -10:
            continue

        # look for recovery in next entries
        recovery_s = None
        t_dump = mc_history[i].get("time") or mc_history[i].get("timestamp", 0)
        for j in range(i + 1, min(i + 20, len(mc_history))):
            rec_mc = mc_history[j].get("mc") or mc_history[j].get("marketCap", 0)
            if rec_mc >= prev_mc * 0.9:
                t_rec = mc_history[j].get("time") or mc_history[j].get("timestamp", 0)
                recovery_s = round((t_rec - t_dump) / 1000, 3) if t_rec and t_dump else None
                break

        # trades in ±30s window
        t_ms = t_dump or 0
        window_trades = [
            t for t in trades
            if abs((t.get("timestamp") or t.get("time", 0)) - t_ms) <= 30_000
        ]
        buys_w = sum(1 for t in window_trades if t.get("type", "").lower() in ("buy", "b"))
        sells_w = sum(1 for t in window_trades if t.get("type", "").lower() in ("sell", "s"))

        pattern = "real_time_floor_hold" if recovery_s and recovery_s < 2 else (
            "bundler_graduation" if i < 5 else "unknown"
        )

        floor_score = 0
        if recovery_s is not None:
            floor_score += 40 if recovery_s < 1 else 20 if recovery_s < 5 else 5
        if buys_w > sells_w:
            floor_score += 30
        if drop_pct < -20:
            floor_score += 20
        floor_score = min(floor_score, 100)

        entry_signal = floor_score >= 50 and recovery_s is not None and recovery_s < 2

        events.append({
            "dump_pct": round(drop_pct, 1),
            "pattern": pattern,
            "recovery_s": recovery_s,
            "buys_window": buys_w,
            "sells_window": sells_w,
            "floor_score": floor_score,
            "entry_signal": entry_signal,
        })

    return events


# ── Main analysis function ────────────────────────────────────────────────────

def analyze_trades(data: dict) -> dict:
    """
    Analyze a GMGN trade export dict.

    Expected keys: trades, mcHistory, stats, coinName, coinId
    Returns: wallet_breakdown, dump_events, confluence_score, entry_signal, insight
    """
    trades: list[dict] = data.get("trades", [])
    mc_history: list[dict] = data.get("mcHistory", [])
    stats: dict = data.get("stats", {})
    coin_name: str = data.get("coinName", "Unknown")
    coin_id: str = data.get("coinId", "")

    # ── time window ──────────────────────────────────────────────
    timestamps = [t.get("timestamp") or t.get("time", 0) for t in trades if t]
    timestamps = [ts for ts in timestamps if ts]
    time_first = datetime.fromtimestamp(min(timestamps) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if timestamps else "—"
    time_last  = datetime.fromtimestamp(max(timestamps) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if timestamps else "—"

    # ── wallet breakdown ─────────────────────────────────────────
    wallet_trades: dict[str, dict] = defaultdict(lambda: {"buys": 0, "sells": 0, "intervals": []})
    sorted_trades = sorted(trades, key=lambda t: t.get("timestamp") or t.get("time", 0))
    for i, t in enumerate(sorted_trades):
        wallet = t.get("wallet") or t.get("address") or t.get("maker", f"w{i}")
        kind   = t.get("type", "").lower()
        if kind in ("buy", "b"):
            wallet_trades[wallet]["buys"] += 1
        elif kind in ("sell", "s"):
            wallet_trades[wallet]["sells"] += 1
        if i > 0:
            prev_ts = sorted_trades[i - 1].get("timestamp") or sorted_trades[i - 1].get("time", 0)
            curr_ts = t.get("timestamp") or t.get("time", 0)
            if prev_ts and curr_ts and curr_ts > prev_ts:
                wallet_trades[wallet]["intervals"].append((curr_ts - prev_ts) / 1000)

    archetype_counts: dict[str, int] = defaultdict(int)
    for wdata in wallet_trades.values():
        arch = _classify_wallet(wdata["buys"], wdata["sells"], wdata["intervals"])
        archetype_counts[arch] += 1

    total_wallets = len(wallet_trades) or 1
    wallet_breakdown = {
        arch: {"count": cnt, "pct": round(cnt / total_wallets * 100, 1)}
        for arch, cnt in archetype_counts.items()
    }

    # ── dump events ──────────────────────────────────────────────
    dump_events = _detect_dump_events(trades, mc_history)

    # ── confluence ───────────────────────────────────────────────
    bs_ratio = stats.get("bs_ratio") or stats.get("buyRatio") or (
        (stats.get("buys", 0) / stats.get("sells", 1)) if stats.get("sells") else None
    )

    floor_scores = [e["floor_score"] for e in dump_events]
    avg_floor    = round(sum(floor_scores) / len(floor_scores), 1) if floor_scores else 0
    support_bots = archetype_counts.get("pure_support_bot", 0)
    dump_bots    = archetype_counts.get("pure_dump_bot", 0)
    bot_score    = min(support_bots / max(dump_bots, 1) * 10, 30)
    bs_score     = min((bs_ratio or 1) * 10, 20) if bs_ratio else 0
    confluence   = min(round(avg_floor * 0.5 + bot_score + bs_score), 100)

    entry_signal = (
        confluence >= 50
        and any(e["entry_signal"] for e in dump_events)
        and (bs_ratio or 0) >= 1.5
    )

    # ── dominant pattern ─────────────────────────────────────────
    pattern_counts: dict[str, int] = defaultdict(int)
    for e in dump_events:
        pattern_counts[e["pattern"]] += 1
    dominant = max(pattern_counts, key=pattern_counts.get) if pattern_counts else None

    if dominant == "real_time_floor_hold":
        insight = f"Floor hold pattern dominant across {pattern_counts[dominant]} dump events — bot support active."
    elif dominant == "bundler_graduation":
        insight = f"Bundler graduation detected at launch — coordinated accumulation signal."
    elif dominant == "exit_scam":
        insight = "Exit scam pattern detected — avoid entry."
    else:
        insight = "Insufficient dump events to determine dominant pattern."

    if not dump_events:
        insight = "No significant dump events detected in MC history."

    return {
        "coin_name":        coin_name,
        "coin_id":          coin_id,
        "total_trades":     len(trades),
        "time_first":       time_first,
        "time_last":        time_last,
        "bs_ratio":         round(bs_ratio, 2) if bs_ratio else None,
        "wallet_breakdown": wallet_breakdown,
        "dump_events":      dump_events,
        "confluence_score": confluence,
        "entry_signal":     entry_signal,
        "insight":          insight,
    }


TRAINING_EXAMPLES = {
    "swordcat": {
        "token": "5tCju6YNxHq5zrA6tGndr6F7TK42mpUFmeE31cSFpump",
        "chain": "solana",
        "age_days": 26,
        "mc_current": 2190000,
        "mc_ath": 4910000,
        "pct_from_ath": -55.4,
        "bs_ratio": 2.16,
        "support_bots": 132,
        "dump_bots": 75,
        "patterns": ["bundler_graduation", "real_time_floor_hold"],
        "dump_events": 9,
        "avg_recovery_s": 0.75,
        "outcome": "positive",
        "notes": "Classic bundler grad at launch + sustained floor hold at $2.19M"
    },
    "dacitycoin": {
        "token": "DKYcjobF7HPtL9RyQBRdeRQ2iWvizpfbgWwPWNXdpump",
        "chain": "solana",
        "age_days": 9,
        "mc_current": 1600000,
        "mc_ath": 5080000,
        "pct_from_ath": -68.5,
        "bs_ratio": 2.16,
        "support_bots": 127,
        "dump_bots": 74,
        "patterns": ["bundler_graduation", "real_time_floor_hold"],
        "dump_events": 9,
        "avg_recovery_s": 0.9,
        "outcome": "positive",
        "notes": "Double bundler graduation confirmed, U-shape recovery at $1.6M"
    },
    "hooked": {
        "token": "C1mBfBoDkwWfd6uTFZp62ARHLjeVp3bDpCDMfMZtPngE",
        "chain": "solana",
        "age_days": 25,
        "mc_current": 1400000,
        "mc_ath": 16550000,
        "pct_from_ath": -91.5,
        "bs_ratio": 1.93,
        "support_bots": 9,
        "dump_bots": 5,
        "patterns": ["real_time_floor_hold"],
        "dump_events": 3,
        "avg_recovery_s": 0.086,
        "flags": ["dev_sold", "tax_3pct"],
        "outcome": "positive",
        "notes": "Deep value recovery signal, 91.5% from ATH, sub-0.3s recovery, dev sold 25d ago so sell pressure cleared"
    }
}
