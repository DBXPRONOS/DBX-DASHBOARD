import json, os, requests, numpy as np
from datetime import datetime, date
from scipy.stats import poisson

TODAY = date.today().isoformat()
NOW = datetime.utcnow().strftime("%H:%M")
API_KEY = os.environ.get("ODDS_API_KEY", "e5862a0c1bf391a7894ca024ddff0a6b")

SPORTS = [
    "soccer_france_ligue_one","soccer_france_ligue_two",
    "soccer_epl","soccer_england_championship","soccer_england_league1","soccer_england_league2",
    "soccer_spain_la_liga","soccer_spain_segunda_division",
    "soccer_italy_serie_a","soccer_italy_serie_b",
    "soccer_germany_bundesliga","soccer_germany_bundesliga2",
    "soccer_netherlands_eredivisie","soccer_portugal_primeira_liga",
    "soccer_turkey_super_league","soccer_belgium_first_div",
    "soccer_scotland_premiership","soccer_sweden_allsvenskan",
    "soccer_switzerland_superleague","soccer_bulgaria_first_league",
    "soccer_greece_super_league","soccer_austria_bundesliga",
    "soccer_czech_liga","soccer_poland_ekstraklasa",
    "soccer_romania_liga1","soccer_croatia_hnl",
    "soccer_denmark_superliga","soccer_norway_eliteserien",
    "soccer_finland_veikkausliiga","soccer_russia_premier_league",
    "soccer_serbia_superliga","soccer_slovakia_superliga",
    "soccer_slovenia_prvaliga","soccer_ukraine_premier_league",
    "soccer_hungary_nb1","soccer_israel_premier_league",
    "soccer_cyprus_first_division","soccer_kazakhstan_premier_league",
    "soccer_uefa_champs_league","soccer_uefa_europa_league",
    "soccer_uefa_europa_conference_league",
    "soccer_france_coupe_de_france","soccer_england_fa_cup","soccer_england_efl_cup",
    "soccer_spain_copa_del_rey","soccer_italy_coppa_italia","soccer_germany_dfb_pokal",
    "soccer_netherlands_knvb_cup","soccer_portugal_taca_de_portugal",
    "soccer_turkey_cup","soccer_scotland_fa_cup","soccer_belgium_cup",
    "soccer_fifa_world_cup","soccer_conmebol_copa_america","soccer_concacaf_gold_cup",
    "soccer_africa_cup_of_nations","soccer_uefa_nations_league",
    "soccer_concacaf_nations_league","soccer_afc_asian_cup",
    "soccer_brazil_campeonato","soccer_brazil_serie_b",
    "soccer_argentina_primera_division","soccer_argentina_primera_b",
    "soccer_chile_campeonato","soccer_mexico_ligamx","soccer_mexico_ascenso_mx",
    "soccer_usa_mls","soccer_usa_usl_championship",
    "soccer_colombia_primera_a","soccer_ecuador_primera_a",
    "soccer_peru_primera_division","soccer_uruguay_primera_division",
    "soccer_venezuela_primera","soccer_paraguay_primera_division",
    "soccer_bolivia_primera_division","soccer_costa_rica_primera_division",
    "soccer_conmebol_copa_libertadores","soccer_conmebol_copa_sudamericana",
    "soccer_japan_j_league","soccer_japan_j_league_2",
    "soccer_china_superleague","soccer_south_korea_k_league1",
    "soccer_australia_aleague","soccer_india_super_league",
    "soccer_saudi_arabian_premier_league","soccer_uae_pro_league",
]

LEAGUE_LABELS = {
    "soccer_france_ligue_one":"FRA-Ligue 1","soccer_france_ligue_two":"FRA-Ligue 2",
    "soccer_epl":"ENG-Premier League","soccer_england_championship":"ENG-Championship",
    "soccer_england_league1":"ENG-League One","soccer_england_league2":"ENG-League Two",
    "soccer_spain_la_liga":"ESP-La Liga","soccer_spain_segunda_division":"ESP-La Liga 2",
    "soccer_italy_serie_a":"ITA-Serie A","soccer_italy_serie_b":"ITA-Serie B",
    "soccer_germany_bundesliga":"GER-Bundesliga","soccer_germany_bundesliga2":"GER-2.Bundesliga",
    "soccer_netherlands_eredivisie":"NED-Eredivisie","soccer_portugal_primeira_liga":"POR-Primeira Liga",
    "soccer_turkey_super_league":"TUR-Süper Lig","soccer_belgium_first_div":"BEL-Pro League",
    "soccer_scotland_premiership":"SCO-Premiership","soccer_sweden_allsvenskan":"SWE-Allsvenskan",
    "soccer_switzerland_superleague":"SUI-Super League","soccer_bulgaria_first_league":"BUL-First League",
    "soccer_greece_super_league":"GRE-Super League","soccer_austria_bundesliga":"AUT-Bundesliga",
    "soccer_czech_liga":"CZE-First League","soccer_poland_ekstraklasa":"POL-Ekstraklasa",
    "soccer_romania_liga1":"ROU-Liga 1","soccer_croatia_hnl":"CRO-HNL",
    "soccer_denmark_superliga":"DEN-Superliga","soccer_norway_eliteserien":"NOR-Eliteserien",
    "soccer_finland_veikkausliiga":"FIN-Veikkausliiga","soccer_russia_premier_league":"RUS-Premier League",
    "soccer_serbia_superliga":"SRB-SuperLiga","soccer_slovakia_superliga":"SVK-SuperLiga",
    "soccer_slovenia_prvaliga":"SVN-PrvaLiga","soccer_ukraine_premier_league":"UKR-Premier League",
    "soccer_hungary_nb1":"HUN-NB I","soccer_israel_premier_league":"ISR-Premier League",
    "soccer_cyprus_first_division":"CYP-First Division","soccer_kazakhstan_premier_league":"KAZ-Premier League",
    "soccer_uefa_champs_league":"UEFA Champions League","soccer_uefa_europa_league":"UEFA Europa League",
    "soccer_uefa_europa_conference_league":"UEFA Conference League",
    "soccer_france_coupe_de_france":"Coupe de France","soccer_england_fa_cup":"FA Cup",
    "soccer_england_efl_cup":"EFL Cup","soccer_spain_copa_del_rey":"Copa del Rey",
    "soccer_italy_coppa_italia":"Coppa Italia","soccer_germany_dfb_pokal":"DFB Pokal",
    "soccer_netherlands_knvb_cup":"KNVB Cup","soccer_portugal_taca_de_portugal":"Taça de Portugal",
    "soccer_turkey_cup":"Coupe Turquie","soccer_scotland_fa_cup":"Scottish FA Cup",
    "soccer_belgium_cup":"Coupe Belgique","soccer_fifa_world_cup":"Coupe du Monde FIFA",
    "soccer_conmebol_copa_america":"Copa América","soccer_concacaf_gold_cup":"Gold Cup",
    "soccer_africa_cup_of_nations":"CAN","soccer_uefa_nations_league":"UEFA Nations League",
    "soccer_concacaf_nations_league":"CONCACAF Nations League","soccer_afc_asian_cup":"AFC Asian Cup",
    "soccer_brazil_campeonato":"BRA-Brasileirao","soccer_brazil_serie_b":"BRA-Série B",
    "soccer_argentina_primera_division":"ARG-Primera División","soccer_argentina_primera_b":"ARG-Primera B",
    "soccer_chile_campeonato":"CHI-Primera División","soccer_mexico_ligamx":"MEX-Liga MX",
    "soccer_mexico_ascenso_mx":"MEX-Ascenso MX","soccer_usa_mls":"USA-MLS",
    "soccer_usa_usl_championship":"USA-USL Championship","soccer_colombia_primera_a":"COL-Liga BetPlay",
    "soccer_ecuador_primera_a":"ECU-Liga Pro","soccer_peru_primera_division":"PER-Liga 1",
    "soccer_uruguay_primera_division":"URU-Primera División","soccer_venezuela_primera":"VEN-Primera División",
    "soccer_paraguay_primera_division":"PAR-Primera División","soccer_bolivia_primera_division":"BOL-Primera División",
    "soccer_costa_rica_primera_division":"CRC-Primera División",
    "soccer_conmebol_copa_libertadores":"Copa Libertadores","soccer_conmebol_copa_sudamericana":"Copa Sudamericana",
    "soccer_japan_j_league":"JPN-J1 League","soccer_japan_j_league_2":"JPN-J2 League",
    "soccer_china_superleague":"CHN-Super League","soccer_south_korea_k_league1":"KOR-K League 1",
    "soccer_australia_aleague":"AUS-A-League","soccer_india_super_league":"IND-Super League",
    "soccer_saudi_arabian_premier_league":"SAU-Pro League","soccer_uae_pro_league":"UAE-Pro League",
}

def score_matrix(lam_h, lam_a, n=10):
    return np.outer(poisson.pmf(np.arange(n+1),lam_h), poisson.pmf(np.arange(n+1),lam_a))

def market_probs(mat):
    idx = np.add.outer(np.arange(mat.shape[0]), np.arange(mat.shape[0]))
    return {
        "1":float(np.tril(mat,-1).sum()), "X":float(np.trace(mat)), "2":float(np.triu(mat,1).sum()),
        "Over_2.5":float(mat[idx>2].sum()), "BTTS_Yes":float(mat[1:,1:].sum()),
    }

def remove_vig(odds):
    inv={k:1/v for k,v in odds.items() if v and v>1.0}
    t=sum(inv.values())
    return {k:v/t for k,v in inv.items()} if t else {}

def detect_value(model_p, odd, edge_min=0.05):
    if not odd or odd<1.3: return False,0
    edge=model_p-1/odd
    return edge>=edge_min, round(edge*100,1)

def lambda_from_odds(odd_1, odd_x, odd_2, home):
    if not odd_1 or not odd_2: return 1.3 if home else 1.1
    odds={"1":odd_1,"2":odd_2}
    if odd_x: odds["X"]=odd_x
    fair=remove_vig(odds)
    p=fair.get("1",0.45) if home else fair.get("2",0.30)
    return round(max(0.5,0.5+p*(2.5 if home else 2.0)),2)

def fetch_all_matches():
    all_matches=[]
    for sport in SPORTS:
        try:
            r=requests.get(
                f"https://api.the-odds-api.com/v4/sports/{sport}/odds/",
                params={"apiKey":API_KEY,"regions":"eu","markets":"h2h,totals","oddsFormat":"decimal","dateFormat":"iso"},
                timeout=15
            )
            if r.status_code!=200: continue
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
                })
        except Exception as e:
            print(f"Erreur {sport}: {e}")
    print(f"Matchs trouvés: {len(all_matches)}")
    return all_matches

MANUAL_PICKS=[]

def process_match(m):
    home=m.get("home","?"); away=m.get("away","?")
    league=m.get("league",""); time_=m.get("time","")
    mat=score_matrix(m.get("lam_home",1.3),m.get("lam_away",1.1))
    probs=market_probs(mat)
    odd_1=m.get("odd_1"); odd_over=m.get("odd_over_25")
    tags=[]; pick_type="grid"; selection=None; market=None; odd_taken=None; model_prob=None
    p1=probs["1"]; po=probs["Over_2.5"]
    score=round(max(p1,po)*10,1)

    if p1>=0.75 and odd_1 and odd_1>=1.15:
        pick_type="safe"; selection=f"{home} gagne"; market="1X2 — 1"; odd_taken=odd_1; model_prob=p1
        tags.append(f"🛡️ Safe VIP · {round(p1*100)}%")
    elif po>=0.75 and odd_over:
        pick_type="safe"; selection="Over 2.5 buts"; market="Over/Under 2.5"; odd_taken=odd_over; model_prob=po
        tags.append(f"🛡️ Safe VIP · Over 2.5 · {round(po*100)}%")
    elif odd_1:
        is_val,edge=detect_value(p1,odd_1)
        if is_val:
            pick_type="value"; selection=f"{home} gagne"; market="1X2 — 1"; odd_taken=odd_1; model_prob=p1
            tags.append(f"🔥 Value +{edge}pp edge")
    elif odd_over:
        is_val,edge=detect_value(po,odd_over)
        if is_val:
            pick_type="value"; selection="Over 2.5 buts"; market="Over/Under 2.5"; odd_taken=odd_over; model_prob=po
            tags.append(f"🔥 Value Over 2.5 · +{edge}pp")

    stake=0.03 if(pick_type in("safe","value") and score>=8.0) else 0.02 if pick_type in("safe","value","grid") else 0.0
    return {
        "home_team":home,"away_team":away,"league":league,"time":time_,
        "type":pick_type,"score":score,"selection":selection,"market":market,
        "odd":odd_taken,"model_prob":round(model_prob,4) if model_prob else None,
        "stake_pct":stake,"tags":tags,
        "prob_1":round(probs["1"],4),"prob_x":round(probs["X"],4),
        "prob_2":round(probs["2"],4),"prob_over":round(probs["Over_2.5"],4),
        "odd_1":m.get("odd_1"),"odd_x":m.get("odd_x"),
        "odd_2":m.get("odd_2"),"odd_over_25":m.get("odd_over_25"),
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
            "score_moyen":round(sum(p["score"] fo
