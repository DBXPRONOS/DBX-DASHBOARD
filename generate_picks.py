"""
Script principal de génération des picks.
Tourne dans GitHub Actions chaque matin à 6h.
Écrit le fichier picks.json qui alimente le dashboard.
"""
import json
import sys
from datetime import datetime, date

import numpy as np
import pandas as pd
from scipy.stats import poisson

TODAY = date.today().isoformat()
NOW = datetime.utcnow().strftime("%H:%M")

def score_matrix(lam_h, lam_a, n=10):
    h = poisson.pmf(np.arange(n+1), lam_h)
    a = poisson.pmf(np.arange(n+1), lam_a)
    return np.outer(h, a)

def market_probs(mat):
    idx = np.add.outer(np.arange(mat.shape[0]), np.arange(mat.shape[0]))
    return {
        "1":        float(np.tril(mat, -1).sum()),
        "X":        float(np.trace(mat)),
        "2":        float(np.triu(mat, 1).sum()),
        "Over_2.5": float(mat[idx > 2].sum()),
        "BTTS_Yes": float(mat[1:, 1:].sum()),
    }

def remove_vig(odds: dict) -> dict:
    inv = {k: 1/v for k,v in odds.items() if v and v > 1.0}
    total = sum(inv.values())
    return {k: v/total for k,v in inv.items()} if total else {}

def detect_value(model_p, selection, odd, edge_min=0.05):
    if not odd or odd < 1.3:
        return False, 0
    implied = 1 / odd
    edge = model_p - implied
    return edge >= edge_min, round(edge * 100, 1)

def dbx_score(forme, h2h, contexte, xg, blessures):
    weights = {"forme": 0.25, "h2h": 0.20, "contexte": 0.20, "stats_xg": 0.20, "blessures": 0.15}
    scores = {"forme": forme, "h2h": h2h, "contexte": contexte, "stats_xg": xg, "blessures": blessures}
    return round(sum(scores[k] * weights[k] for k in weights), 2)

def forme_score(s):
    pts = {"W":3,"D":1,"L":0}
    p = sum(pts.get(c,0) for c in (s or "").upper()[:5])
    return round(p / 15 * 10, 1)

def fetch_fixtures_today():
    try:
        import soccerdata as sd
        leagues = ["ENG-Premier League", "ESP-La Liga", "ITA-Serie A",
                   "GER-Bundesliga", "FRA-Ligue 1"]
        season = "2025-2026"
        all_fixtures = []
        for lg in leagues:
            try:
                fbref = sd.FBref(leagues=lg, seasons=season)
                sched = fbref.read_schedule().reset_index()
                today_m = sched[sched.get("date", pd.Series()).astype(str).str.startswith(TODAY)]
                for _, r in today_m.iterrows():
                    all_fixtures.append({
                        "home": str(r.get("home_team", "")),
                        "away": str(r.get("away_team", "")),
                        "league": lg,
                        "time": "TBD",
                    })
            except Exception:
                continue
        return all_fixtures
    except Exception:
        return []

MANUAL_PICKS = [
    {
        "home": "Leganes",
        "away": "Huesca",
        "league": "ESP-La Liga 2",
        "time": "20h30",
        "lam_home": 1.3,
        "lam_away": 1.1,
        "forme_home": "LLLLD",
        "forme_away": "LLLWL",
        "h2h_home": "WWDWL",
        "motivation": 8,
        "fatigue": 4,
        "blessures_home": 0,
        "blessures_away": 0,
        "odd_1": 1.89,
        "odd_x": 3.70,
        "odd_over_25": 2.05,
        "context_flags": ["low_stakes_favorite"],
    },
]

def process_match(m):
    home = m.get("home", "?")
    away = m.get("away", "?")
    league = m.get("league", "")
    time_ = m.get("time", "")
    lam_h = m.get("lam_home", 1.3)
    lam_a = m.get("lam_away", 1.1)
    mat = score_matrix(lam_h, lam_a)
    probs = market_probs(mat)
    forme_h = forme_score(m.get("forme_home"))
    h2h_v   = forme_score(m.get("h2h_home"))
    ctx     = max(0, min(10, m.get("motivation", 5) - m.get("fatigue", 2) * 0.5))
    xg_v    = 5.0
    bles    = max(0, min(10, 5 - m.get("blessures_home",0)*1.5 + m.get("blessures_away",0)*1.5))
    score   = dbx_score(forme_h, h2h_v, ctx, xg_v, bles)
    tags = []
    flags = m.get("context_flags", [])
    pick_type = "grid"
    selection = None
    market = None
    odd_taken = None
    model_prob = None
    odd_1 = m.get("odd_1")
    if probs["1"] >= 0.80 and score >= 6.0 and odd_1 and odd_1 >= 1.20 \
       and m.get("blessures_home", 0) < 2 and "derby" not in flags:
        pick_type = "safe"
        selection = f"{home} gagne"
        market = "1X2 — 1"
        odd_taken = odd_1
        model_prob = probs["1"]
        tags.append(f"🛡️ Safe VIP · {round(probs['1']*100)}%")
    elif probs["Over_2.5"] >= 0.80 and score >= 6.0 and m.get("odd_over_25"):
        pick_type = "safe"
        selection = "Over 2.5 buts"
        market = "Over/Under 2.5"
        odd_taken = m.get("odd_over_25")
        model_prob = probs["Over_2.5"]
        tags.append(f"🛡️ Safe VIP · Over 2.5 · {round(probs['Over_2.5']*100)}%")
    elif odd_1 and score >= 6.0:
        is_val, edge = detect_value(probs["1"], "1", odd_1)
        if is_val:
            pick_type = "value"
            selection = f"{home} gagne"
            market = "1X2 — 1"
            odd_taken = odd_1
            model_prob = probs["1"]
            tags.append(f"🔥 Value +{edge}pp edge")
    elif m.get("odd_over_25") and score >= 6.0:
        is_val, edge = detect_value(probs["Over_2.5"], "Over_2.5", m["odd_over_25"])
        if is_val:
            pick_type = "value"
            selection = "Over 2.5 buts"
            market = "Over/Under 2.5"
            odd_taken = m["odd_over_25"]
            model_prob = probs["Over_2.5"]
            tags.append(f"🔥 Value Over 2.5 · +{edge}pp")
    if m.get("blessures_away", 0) >= 2:
        tags.append(f"🚑 {m['blessures_away']} blessés clés {away}")
    if "derby" in flags:
        tags.append("⚠️ Derby — volatilité haute")
    if "low_stakes_favorite" in flags:
        tags.append("⚠️ Piège — enjeu faible")
    if "post_european_fatigue" in flags:
        tags.append("⚠️ Fatigue européenne")
    if score < 6.0:
        pick_type = "skip"
        tags = ["⚠️ Sous seuil DBX 6/10"]
        selection = None
        odd_taken = None
    stake = 0.03 if (pick_type in ("safe","value") and score >= 8.0) else \
            0.02 if pick_type in ("safe","value","grid") else 0.0
    return {
        "home_team": home,
        "away_team": away,
        "league": league,
        "time": time_,
        "type": pick_type,
        "score": score,
        "selection": selection,
        "market": market,
        "odd": odd_taken,
        "model_prob": round(model_prob, 4) if model_prob else None,
        "stake_pct": stake,
        "tags": tags,
    }

def main():
    fixtures = fetch_fixtures_today()
    manual_ids = {(m["home"], m["away"]) for m in MANUAL_PICKS}
    auto = [f for f in fixtures if (f["home"], f["away"]) not in manual_ids]
    all_matches = MANUAL_PICKS + auto
    picks = [process_match(m) for m in all_matches]
    picks.sort(key=lambda p: (-["safe","value","grid","skip"].index(p["type"]) if p["type"] in ["safe","value","grid","skip"] else 99, -p["score"]))
    active = [p for p in picks if p["type"] != "skip"]
    output = {
        "date": TODAY,
        "updated_at": NOW,
        "stats": {
            "total_picks": len(active),
            "safes_vip": sum(1 for p in active if p["type"] == "safe"),
            "value_bets": sum(1 for p in active if p["type"] == "value"),
            "score_moyen": round(sum(p["score"] for p in active) / len(active), 1) if active else 0,
        },
        "picks": picks,
    }
    with open("picks.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"OK — {len(active)} picks générés pour {TODAY}")

if __name__ == "__main__":
    main()
