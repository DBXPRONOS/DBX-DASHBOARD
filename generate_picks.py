"""
Script principal de génération des picks.
Tourne dans GitHub Actions chaque matin à 6h.
Source des matchs + cotes : The-Odds-API (gratuit 500 req/mois)
Couvre : Europe, Japon, Chine, Amérique du Sud, MLS, etc.
"""
import json
import os
import requests
import numpy as np
from datetime import datetime, date
from scipy.stats import poisson

TODAY = date.today().isoformat()
NOW = datetime.utcnow().strftime("%H:%M")

API_KEY = os.environ.get("ODDS_API_KEY", "e5862a0c1bf391a7894ca024ddff0a6b")

SPORTS = [
    "soccer_france_ligue_one","soccer_france_ligue_two",
    "soccer_epl","soccer_england_championship",
    "soccer_spain_la_liga","soccer_spain_segunda_division",
    "soccer_italy_serie_a","soccer_italy_serie_b",
    "soccer_germany_bundesliga","soccer_germany_bundesliga2",
    "soccer_netherlands_eredivisie","soccer_portugal_primeira_liga",
    "soccer_turkey_super_league","soccer_belgium_first_div",
    "soccer_scotland_premiership","soccer_japan_j_league",
    "soccer_china_superleague","soccer_brazil_campeonato",
    "soccer_argentina_primera_division","soccer_chile_campeonato",
    "soccer_mexico_ligamx","soccer_usa_mls",
    "soccer_colombia_primera_a","soccer_ecuador_primera_a",
    "soccer_conmebol_copa_libertadores",
    "soccer_uefa_champs_league","soccer_uefa_europa_league",
]

LEAGUE_LABELS = {
    "soccer_france_ligue_one":"FRA-Ligue 1","soccer_france_ligue_two":"FRA-Ligue 2",
    "soccer_epl":"ENG-Premier League","soccer_england_championship":"ENG-Championship",
    "soccer_spain_la_liga":"ESP-La Liga","soccer_spain_segunda_division":"ESP-La Liga 2",
    "soccer_italy_serie_a":"ITA-Serie A","soccer_italy_serie_b":"ITA-Serie B",
    "soccer_germany_bundesliga":"GER-Bundesliga","soccer_germany_bundesliga2":"GER-2.Bundesliga",
    "soccer_netherlands_eredivisie":"NED-Eredivisie","soccer_portugal_primeira_liga":"POR-Primeira Liga",
    "soccer_turkey_super_league":"TUR-Süper Lig","soccer_belgium_first_div":"BEL-Pro League",
    "soccer_scotland_premiership":"SCO-Premiership","soccer_japan_j_league":"JPN-J1 League",
    "soccer_china_superleague":"CHN-Super League","soccer_brazil_campeonato":"BRA-Brasileirao",
    "soccer_argentina_primera_division":"ARG-Primera División","soccer_chile_campeonato":"CHI-Primera División",
    "soccer_mexico_ligamx":"MEX-Liga MX","soccer_usa_mls":"USA-MLS",
    "soccer_colombia_primera_a":"COL-Liga BetPlay","soccer_ecuador_primera_a":"ECU-Liga Pro",
    "soccer_conmebol_copa_libertadores":"Copa Libertadores",
    "soccer_uefa_champs_league":"UEFA Champions League","soccer_uefa_europa_league":"UEFA Europa League",
}

def score_matrix(lam_h, lam_a, n=10):
    h = poisson.pmf(np.arange(n+1), lam_h)
    a = poisson.pmf(np.arange(n+1), lam_a)
    return np.outer(h, a)

def market_probs(mat):
    idx = np.add.outer(np.arange(mat.shape[0]), np.arange(mat.shape[0]))
    return {
        "1": float(np.tril(mat,-1).sum()),
        "X": float(np.trace(mat)),
        "2": float(np.triu(mat,1).sum()),
        "Over_2.5": float(mat[idx>2].sum()),
        "BTTS_Yes": float(mat[1:,1:].sum()),
    }

def remove_vig(odds):
    inv = {k:1/v for k,v in odds.items() if v and v>1.0}
    total = sum(inv.values())
    return {k:v/total for k,v in inv.items()} if total else {}

def detect_value(model_p, odd, edge_min=0.05):
    if not odd or odd < 1.3: return False, 0
    edge = model_p - 1/odd
    return edge >= edge_min, round(edge*100,1)

def dbx_score(forme, h2h, contexte, xg, blessures):
    w = {"forme":0.25,"h2h":0.20,"contexte":0.20,"stats_xg":0.20,"blessures":0.15}
    s = {"forme":forme,"h2h":h2h,"contexte":contexte,"stats_xg":xg,"blessures":blessures}
    return round(sum(s[k]*w[k] for k in w), 2)

def forme_score(s):
    pts = {"W":3,"D":1,"L":0}
    p = sum(pts.get(c,0) for c in (s or "").upper()[:5])
    return round(p/15*10, 1)

def lambda_from_odds(odd_1, odd_x, odd_2, home):
    if not odd_1 or not odd_2: return 1.3 if home else 1.1
    odds = {"1":odd_1,"2":odd_2}
    if odd_x: odds["X"] = odd_x
    fair = remove_vig(odds)
    p = fair.get("1",0.45) if home else fair.get("2",0.30)
    lam = max(0.5, 0.5+p*2.5) if home else max(0.5, 0.5+p*2.0)
    return round(lam, 2)

def fetch_all_matches():
    all_matches = []
    for sport in SPORTS:
        try:
            r = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                params={"apiKey":API_KEY,"regions":"eu","markets":"h2h,totals","oddsFormat":"decimal","dateFormat":"iso"},
                timeout=15
            )
            if r.status_code != 200: continue
            for ev in r.json():
                if not ev.get("commence_time","").startswith(TODAY): continue
                home=ev.get("home_team",""); away=ev.get("away_team","")
                league=LEAGUE_LABELS.get(sport,sport)
                try:
                    dt=datetime.fromisoformat(ev["commence_time"].replace("Z","+00:00"))
                    time_str=dt.strftime("%Hh%M")
                except: time_str="TBD"
                odd_1=odd_x=odd_2=odd_over_25=None
                for bk in ev.get("bookmakers",[]):
                    for mk in bk.get("markets",[]):
                        if mk["key"]=="h2h":
                            for oc in mk.get("outcomes",[]):
                                if oc["name"]==home: odd_1=oc["price"]
                                elif oc["name"]==away: odd_2=oc["price"]
                                elif oc["name"]=="Draw": odd_x=oc["price"]
                        elif mk["key"]=="totals":
                            for oc in mk.get("outcomes",[]):
                                if oc["name"]=="Over" and abs(oc.get("point",0)-2.5)<0.1:
                                    odd_over_25=oc["price"]
                    if odd_1 and odd_2: break
                if not odd_1 or not odd_2: continue
                all_matches.append({
                    "home":home,"away":away,"league":league,"time":time_str,
                    "odd_1":odd_1,"odd_x":odd_x,"odd_2":odd_2,"odd_over_25":odd_over_25,
                    "lam_home":lambda_from_odds(odd_1,odd_x,odd_2,True),
                    "lam_away":lambda_from_odds(odd_1,odd_x,odd_2,False),
                    "forme_home":None,"forme_away":None,"h2h_home":None,
                    "motivation":5,"fatigue":2,"blessures_home":0,"blessures_away":0,"context_flags":[],
                })
        except Exception as e:
            print(f"Erreur {sport}: {e}")
    print(f"Matchs trouvés: {len(all_matches)}")
    return all_matches

MANUAL_PICKS = []

def process_match(m):
    home=m.get("home","?"); away=m.get("away","?")
    league=m.get("league",""); time_=m.get("time","")
    mat=score_matrix(m.get("lam_home",1.3),m.get("lam_away",1.1))
    probs=market_probs(mat)
    score=dbx_score(
        forme_score(m.get("forme_home")),forme_score(m.get("h2h_home")),
        max(0,min(10,m.get("motivation",5)-m.get("fatigue",2)*0.5)),5.0,
        max(0,min(10,5-m.get("blessures_home",0)*1.5+m.get("blessures_away",0)*1.5))
    )
    tags=[]; flags=m.get("context_flags",[])
    pick_type="grid"; selection=None; market=None; odd_taken=None; model_prob=None
    odd_1=m.get("odd_1"); odd_over=m.get("odd_over_25")
    if probs["1"]>=0.80 and score>=6.0 and odd_1 and odd_1>=1.20 and m.get("blessures_home",0)<2 and "derby" not in flags:
        pick_type="safe"; selection=f"{home} gagne"; market="1X2 — 1"; odd_taken=odd_1; model_prob=probs["1"]
        tags.append(f"🛡️ Safe VIP · {round(probs['1']*100)}%")
    elif probs["Over_2.5"]>=0.80 and score>=6.0 and odd_over:
        pick_type="safe"; selection="Over 2.5 buts"; market="Over/Under 2.5"; odd_taken=odd_over; model_prob=probs["Over_2.5"]
        tags.append(f"🛡️ Safe VIP · Over 2.5 · {round(probs['Over_2.5']*100)}%")
    elif odd_1 and score>=6.0:
        is_val,edge=detect_value(probs["1"],odd_1)
        if is_val:
            pick_type="value"; selection=f"{home} gagne"; market="1X2 — 1"; odd_taken=odd_1; model_prob=probs["1"]
            tags.append(f"🔥 Value +{edge}pp edge")
    elif odd_over and score>=6.0:
        is_val,edge=detect_value(probs["Over_2.5"],odd_over)
        if is_val:
            pick_type="value"; selection="Over 2.5 buts"; market="Over/Under 2.5"; odd_taken=odd_over; model_prob=probs["Over_2.5"]
            tags.append(f"🔥 Value Over 2.5 · +{edge}pp")
    if m.get("blessures_away",0)>=2: tags.append(f"🚑 {m['blessures_away']} blessés clés {away}")
    if "derby" in flags: tags.append("⚠️ Derby — volatilité haute")
    if "low_stakes_favorite" in flags: tags.append("⚠️ Piège — enjeu faible")
    if "post_european_fatigue" in flags: tags.append("⚠️ Fatigue européenne")
    if score<6.0:
        pick_type="skip"; tags=["⚠️ Sous seuil DBX 6/10"]; selection=None; odd_taken=None
    stake=0.03 if(pick_type in("safe","value") and score>=8.0) else 0.02 if pick_type in("safe","value","grid") else 0.0
    return {
        "home_team":home,"away_team":away,"league":league,"time":time_,
        "type":pick_type,"score":score,"selection":selection,"market":market,
        "odd":odd_taken,"model_prob":round(model_prob,4) if model_prob else None,
        "stake_pct":stake,"tags":tags,
    }

def main():
    auto=fetch_all_matches()
    manual_ids={(m["home"],m["away"]) for m in MANUAL_PICKS}
    all_matches=MANUAL_PICKS+[f for f in auto if (f["home"],f["away"]) not in manual_ids]
    picks=[process_match(m) for m in all_matches]
    picks.sort(key=lambda p:(["safe","value","grid","skip"].index(p["type"]) if p["type"] in["safe","value","grid","skip"] else 99,-p["score"]))
    active=[p for p in picks if p["type"]!="skip"]
    output={
        "date":TODAY,"updated_at":NOW,
        "stats":{
            "total_picks":len(active),
            "safes_vip":sum(1 for p in active if p["type"]=="safe"),
            "value_bets":sum(1 for p in active if p["type"]=="value"),
            "score_moyen":round(sum(p["score"] for p in active)/len(active),1) if active else 0,
        },
        "picks":picks,
    }
    with open("picks.json","w",encoding="utf-8") as f:
        json.dump(output,f,ensure_ascii=False,indent=2)
    print(f"OK — {len(active)} picks actifs / {len(picks)} matchs analysés pour {TODAY}")

if __name__=="__main__":
    main()
