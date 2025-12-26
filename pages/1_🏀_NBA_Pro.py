import streamlit as st
import pandas as pd
import numpy as np
import requests
import feedparser
from datetime import datetime
from deep_translator import GoogleTranslator
from nba_api.stats.endpoints import leaguestandings, commonteamroster
from nba_api.stats.static import teams

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS VISUAL AVANCADO v8.0 ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    .live-dot { display: inline-block; width: 8px; height: 8px; background-color: #ff0000; border-radius: 50%; margin-right: 6px; animation: blink 1.5s infinite; box-shadow: 0 0 6px #ff0000; vertical-align: middle; }
    .status-live { background-color: #2d1b1b; color: #ff4b4b; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; border: 1px solid #5e2a2a; }
    .status-clock { color: #ffcc00; font-weight: bold; margin-left: 8px; font-family: monospace; font-size: 0.9em; }
    .status-q { color: #aaa; margin-left: 8px; font-size: 0.8em; font-weight: bold; }

    .game-card { background: linear-gradient(135deg, #1a1c24 0%, #0e1117 100%); border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #2d313a; }
    .game-card-live { border-left: 4px solid #ff4b4b; }

    .team-name { font-size: 1em; font-weight: 600; color: #eee; }
    .score-big { font-size: 2em; font-weight: bold; color: #fff; }

    .factor-table { background: #141418; border-radius: 6px; padding: 8px; font-size: 0.8em; }
    .factor-header { color: #666; font-size: 0.7em; text-transform: uppercase; }
    .factor-good { color: #00ffaa; font-weight: bold; }
    .factor-bad { color: #ff4466; font-weight: bold; }
    .factor-neutral { color: #888; }

    .news-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
    .news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
    .news-time { font-size: 0.75em; color: #aaa; margin-bottom: 4px; font-weight: bold; }

    .stake-badge { background-color: #00ff00; color: #000; font-weight: bold; padding: 4px 10px; border-radius: 4px; font-size: 0.85em; }
    .stake-normal { background-color: #ffff00; color: black; }

    .xscore-hot { color: #ff6b6b; font-weight: bold; }
    .xscore-cold { color: #4dabf7; font-weight: bold; }
    .over-signal { background-color: #51cf66; color: black; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .under-signal { background-color: #ff6b6b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }

    .insight-box { background: linear-gradient(90deg, #1a2a1a 0%, #1a1c24 100%); border-left: 3px solid #00ffaa; padding: 10px; border-radius: 0 6px 6px 0; margin-top: 10px; font-size: 0.85em; }
    .insight-box-warning { background: linear-gradient(90deg, #2a1a1a 0%, #1a1c24 100%); border-left: 3px solid #ff4466; }

    div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Gestao de Banca")
    banca_total = st.number_input("Banca (R$)", value=1000.0, step=100.0, format="%.2f")
    pct_unidade = st.slider("Unidade (%)", 0.5, 5.0, 1.0, step=0.5)
    valor_unidade = banca_total * (pct_unidade / 100)
    st.markdown(f"""<div style="text-align:center; background-color: #1a1c24; padding: 10px; border-radius: 8px; margin-top:10px;">
        <small style="color:#888">1 UNIDADE</small><br>
        <span style="font-size: 1.5em; color: #4da6ff; font-weight: bold;">R$ {valor_unidade:.2f}</span>
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.subheader("Modelos Ativos")
    use_xscore = st.checkbox("xScore (Qualidade)", value=True, help="Detecta divergencia entre pontos reais e esperados")
    use_pace = st.checkbox("Ritmo Dinamico", value=True, help="Ajusta projecao de totais em tempo real")
    use_factors = st.checkbox("Four Factors", value=True, help="Analise tatica de Dean Oliver")

# --- 1. IMPACTO DOS JOGADORES ---
PLAYER_IMPACTS = {
    "Estrela (Generico)": 4.5, "Titular Importante (Generico)": 2.5, "Role Player (Generico)": 1.5,
    "Nikola Jokic": 8.5, "Luka Doncic": 7.5, "Giannis Antetokounmpo": 7.0,
    "Shai Gilgeous-Alexander": 7.0, "Joel Embiid": 6.5, "Jayson Tatum": 5.5,
    "Stephen Curry": 5.5, "LeBron James": 5.0, "Kevin Durant": 5.0,
    "Anthony Davis": 5.0, "Victor Wembanyama": 5.0, "Anthony Edwards": 4.5,
    "Devin Booker": 4.0, "Ja Morant": 4.0, "Jalen Brunson": 4.0,
    "Donovan Mitchell": 4.0, "Tyrese Haliburton": 3.5, "Kyrie Irving": 3.5,
    "Trae Young": 3.5, "Jimmy Butler": 3.5, "Damian Lillard": 3.5,
    "Kawhi Leonard": 3.5, "James Harden": 3.5, "Zion Williamson": 3.5,
    "Paolo Banchero": 3.5, "De'Aaron Fox": 3.5, "Domantas Sabonis": 3.5,
    "Bam Adebayo": 3.0, "Jaylen Brown": 3.5, "LaMelo Ball": 3.0,
    "Cade Cunningham": 3.0, "Alperen Sengun": 3.0, "Tyrese Maxey": 3.0,
    "Paul George": 3.0, "Karl-Anthony Towns": 3.0, "Chet Holmgren": 3.0,
    "Jamal Murray": 2.5, "Darius Garland": 2.5, "Klay Thompson": 2.0
}

# --- 2. DADOS HISTORICOS DOS TIMES ---
@st.cache_data(ttl=86400)
def get_team_stats():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        stats = {}
        for _, row in df.iterrows():
            team = row['TeamName']
            ppg = row['PointsPG']
            opp_ppg = row['OppPointsPG']
            estimated_pace = (ppg + opp_ppg) / 2 * 0.92
            stats[team] = {
                'ppg': ppg, 'opp_ppg': opp_ppg,
                'net_rating': round(ppg - opp_ppg, 1),
                'pace': round(estimated_pace, 1),
                'off_rating': round(ppg * 100 / estimated_pace, 1),
                'def_rating': round(opp_ppg * 100 / estimated_pace, 1)
            }
        return stats
    except:
        return {
            "Celtics": {'ppg': 120, 'opp_ppg': 110, 'net_rating': 10, 'pace': 100, 'off_rating': 120, 'def_rating': 110},
            "Thunder": {'ppg': 118, 'opp_ppg': 108, 'net_rating': 10, 'pace': 98, 'off_rating': 120, 'def_rating': 110},
            "Nuggets": {'ppg': 115, 'opp_ppg': 110, 'net_rating': 5, 'pace': 97, 'off_rating': 118, 'def_rating': 113}
        }

# --- 3. FOUR FACTORS (Dean Oliver) ---
def calc_four_factors(stats):
    """
    Calcula os 4 Fatores de Dean Oliver a partir das estatisticas do box score
    Retorna: eFG%, TOV%, ORB, FTR
    """
    try:
        fgm = stats.get('fieldGoalsMade', 0)
        fga = stats.get('fieldGoalsAttempted', 1)
        fg3m = stats.get('threePointersMade', 0)
        ftm = stats.get('freeThrowsMade', 0)
        fta = stats.get('freeThrowsAttempted', 0)
        tov = stats.get('turnovers', 0)
        orb = stats.get('reboundsOffensive', 0)

        # 1. Effective Field Goal % (Peso 40% na vitoria)
        efg = (fgm + 0.5 * fg3m) / fga if fga > 0 else 0

        # 2. Turnover % (Peso 25%) - Estimado
        poss = fga + 0.44 * fta + tov
        tov_pct = tov / poss if poss > 0 else 0

        # 3. Offensive Rebound count (Peso 20%)
        # Usamos contagem bruta por falta de dados do oponente

        # 4. Free Throw Rate (Peso 15%)
        ft_rate = ftm / fga if fga > 0 else 0

        return {
            'efg': round(efg * 100, 1),
            'tov': round(tov_pct * 100, 1),
            'orb': orb,
            'ftr': round(ft_rate * 100, 1)
        }
    except:
        return {'efg': 0, 'tov': 0, 'orb': 0, 'ftr': 0}

# --- 4. xSCORE ---
def calculate_xscore(team_stats, current_score, minutes_played, is_home=True):
    if minutes_played <= 0:
        return 0, 0
    ppg = team_stats.get('ppg', 110)
    points_per_min = ppg / 48
    if is_home:
        points_per_min *= 1.02
    expected_score = points_per_min * minutes_played
    divergence = current_score - expected_score
    xscore = np.clip(divergence / 3, -10, 10)
    return round(xscore, 1), round(expected_score, 1)

# --- 5. RITMO DINAMICO BAYESIANO ---
def calculate_dynamic_pace(home_stats, away_stats, current_total, minutes_played, period):
    if minutes_played <= 0:
        expected_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2
        projected_total = (home_stats.get('ppg', 110) + away_stats.get('ppg', 110))
        return projected_total, expected_pace, 0

    prior_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2
    observed_pace = (current_total / minutes_played) * 48
    obs_weight = min(0.7, 0.2 + (minutes_played / 48) * 0.6)
    updated_pace = (prior_pace * (1 - obs_weight)) + (observed_pace * obs_weight)

    if period >= 4:
        updated_pace *= 0.95

    remaining_minutes = 48 - minutes_played
    projected_remaining = (updated_pace / 48) * remaining_minutes
    projected_total = current_total + projected_remaining
    pace_divergence = observed_pace - prior_pace

    return round(projected_total, 1), round(updated_pace, 1), round(pace_divergence, 1)

# --- 6. FUNCOES AUXILIARES ---
@st.cache_data(ttl=3600)
def get_team_id(team_name):
    nba_teams = teams.get_teams()
    for t in nba_teams:
        if t['nickname'] in team_name or team_name in t['full_name']:
            return t['id']
    return None

@st.cache_data(ttl=3600)
def get_dynamic_roster(team_name):
    tid = get_team_id(team_name)
    if not tid:
        return []
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=tid, season='2024-25').get_data_frames()[0]
        players_list = roster['PLAYER'].tolist()
        return [p for p in players_list if p in PLAYER_IMPACTS]
    except:
        return []

def clean_nba_clock(raw_clock):
    if not raw_clock: return ""
    try:
        clean = raw_clock.replace("PT", "").replace("S", "")
        if "M" in clean:
            parts = clean.split("M")
            return f"{parts[0]}:{parts[1].split('.')[0]}"
        return clean
    except: return raw_clock

def parse_clock_to_minutes(clock_str, period):
    try:
        if not clock_str:
            return period * 12
        parts = clock_str.split(":")
        mins_left = int(parts[0])
        mins_played_in_period = 12 - mins_left
        total_mins = ((period - 1) * 12) + mins_played_in_period
        return max(0, min(48, total_mins))
    except:
        return period * 12

# --- 7. DADOS AO VIVO COM BOX SCORE ---
# TTL=5s para "Janela de Ouro" (~20s de vantagem sobre TV)
@st.cache_data(ttl=5)
def get_nba_live_data():
    """Busca placares E estatisticas detalhadas ao vivo"""
    try:
        # Scoreboard basico
        data = requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json").json()
        live_games = {}

        for g in data['scoreboard']['games']:
            game_id = g['gameId']
            clock = clean_nba_clock(g['gameClock'])
            period = g['period']
            mins_played = parse_clock_to_minutes(clock, period)

            home_name = g['homeTeam']['teamName']
            away_name = g['awayTeam']['teamName']

            game_info = {
                "game_id": game_id,
                "live": g['gameStatus'] == 2,
                "period": period,
                "clock": clock,
                "minutes_played": mins_played,
                "home_name": home_name,
                "away_name": away_name,
                "score_home": g['homeTeam']['score'],
                "score_away": g['awayTeam']['score'],
                "total": g['homeTeam']['score'] + g['awayTeam']['score'],
                # Stats do box (se disponiveis)
                "home_stats": {},
                "away_stats": {}
            }

            # Tenta buscar box score detalhado
            if g['gameStatus'] == 2:  # So se estiver ao vivo
                try:
                    box_url = f"https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
                    box_data = requests.get(box_url, timeout=3).json()

                    home_box = box_data['game']['homeTeam']['statistics']
                    away_box = box_data['game']['awayTeam']['statistics']

                    game_info['home_stats'] = home_box
                    game_info['away_stats'] = away_box
                except:
                    pass

            live_games[home_name] = game_info
            live_games[away_name] = game_info

        return live_games
    except:
        return {}

@st.cache_data(ttl=600)
def get_news():
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nba/news")
        noticias = []
        keywords = ["injury", "out", "surgery", "suspended", "trade"]
        translator = GoogleTranslator(source='auto', target='pt')
        for entry in feed.entries[:4]:
            alerta = any(w in entry.title.lower() for w in keywords)
            try: tit = translator.translate(entry.title).replace("Fontes:", "").strip()
            except: tit = entry.title
            try: hora = datetime(*entry.published_parsed[:6]).strftime("%H:%M")
            except: hora = ""
            noticias.append({"titulo": tit, "hora": hora, "alerta": alerta})
        return noticias
    except: return []

def get_odds(api_key):
    try:
        return requests.get(
            f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'api_key': api_key,
                'regions': 'us,eu',
                'markets': 'spreads,totals',
                'oddsFormat': 'decimal',
                'bookmakers': 'pinnacle,bet365'
            }
        ).json()
    except: return []

# --- APP PRINCIPAL ---
c1, c2 = st.columns([5, 1])
c1.title("NBA Terminal Pro v8.0")
c1.caption("Four Factors + xScore + Ritmo Dinamico")
if c2.button("SCAN LIVE", type="primary"):
    st.cache_data.clear()
    st.rerun()

# Noticias
with st.expander("BREAKING NEWS", expanded=False):
    news = get_news()
    if news:
        cols = st.columns(4)
        for i, n in enumerate(news):
            css = "news-alert" if n['alerta'] else "news-card"
            with cols[i]: st.markdown(f"""<div class="{css} news-card"><div class="news-time">{n['hora']}</div>{n['titulo']}</div>""", unsafe_allow_html=True)

st.divider()

# Carrega dados
TEAM_STATS = get_team_stats()
ODDS = get_odds(API_KEY)
LIVE_DATA = get_nba_live_data()

if not ODDS or isinstance(ODDS, dict):
    st.info("Mercado fechado ou sem creditos na API.")
else:
    # Tabs para diferentes visoes
    tab_analysis, tab_totals = st.tabs(["ANALISE COMPLETA", "TOTALS (O/U)"])

    with tab_analysis:
        for game in ODDS:
            home = game['home_team']
            away = game['away_team']

            # Live Info
            live_info = None
            for k, v in LIVE_DATA.items():
                if k in home or home in k:
                    live_info = v
                    break
            is_live = live_info['live'] if live_info else False

            # Team Stats historicos
            home_stats = TEAM_STATS.get(home.split()[-1], TEAM_STATS.get(home, {'ppg': 110, 'net_rating': 0, 'pace': 98}))
            away_stats = TEAM_STATS.get(away.split()[-1], TEAM_STATS.get(away, {'ppg': 110, 'net_rating': 0, 'pace': 98}))

            # Fair Line
            r_home = home_stats.get('net_rating', 0)
            r_away = away_stats.get('net_rating', 0)
            fair_line = -((r_home + 2.5) - r_away)

            # Market Lines
            market_line = 0.0
            market_total = 0.0
            for s in game.get('bookmakers', []):
                if s['key'] in ['pinnacle', 'bet365']:
                    for mkt in s.get('markets', []):
                        if mkt['key'] == 'spreads' and market_line == 0.0:
                            p = mkt['outcomes'][0]['point']
                            if mkt['outcomes'][0]['name'] != home: p = -p
                            market_line = p
                        if mkt['key'] == 'totals' and market_total == 0.0:
                            market_total = mkt['outcomes'][0]['point']
            if market_line == 0.0: continue

            # Rosters para lesao
            roster_home = get_dynamic_roster(home)
            roster_away = get_dynamic_roster(away)
            generics = ["Estrela (Generico)", "Titular Importante (Generico)"]

            # Calculos ao vivo
            xscore_home, xscore_away = 0, 0
            h_factors, a_factors = None, None
            projected_total, current_pace, pace_div = 0, 0, 0

            if is_live:
                mins = live_info.get('minutes_played', 0)

                # xScore
                if use_xscore:
                    xscore_home, _ = calculate_xscore(home_stats, live_info['score_home'], mins, True)
                    xscore_away, _ = calculate_xscore(away_stats, live_info['score_away'], mins, False)

                # Four Factors
                if use_factors and live_info.get('home_stats'):
                    h_factors = calc_four_factors(live_info['home_stats'])
                    a_factors = calc_four_factors(live_info['away_stats'])

                # Pace/Total
                if use_pace:
                    projected_total, current_pace, pace_div = calculate_dynamic_pace(
                        home_stats, away_stats, live_info['total'], mins, live_info['period']
                    )

            # === CARD DO JOGO ===
            card_class = "game-card game-card-live" if is_live else "game-card"

            with st.container():
                # Header do Card
                if is_live:
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <div>
                                <span class="status-live"><span class="live-dot"></span>AO VIVO</span>
                                <span class="status-q">Q{live_info['period']}</span>
                                <span class="status-clock">{live_info['clock']}</span>
                            </div>
                            <div style="font-size:0.8em; color:#888;">
                                PACE: <b style="color:{'#51cf66' if pace_div > 3 else '#ff6b6b' if pace_div < -3 else '#fff'}">{current_pace:.0f}</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Placar Grande + Four Factors
                    if h_factors and a_factors and use_factors:
                        # Determina vantagens
                        efg_h_win = h_factors['efg'] > a_factors['efg']
                        efg_a_win = a_factors['efg'] > h_factors['efg']
                        tov_h_win = h_factors['tov'] < a_factors['tov']  # Menor eh melhor
                        tov_a_win = a_factors['tov'] < h_factors['tov']
                        orb_h_win = h_factors['orb'] > a_factors['orb']
                        orb_a_win = a_factors['orb'] > h_factors['orb']

                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                            <div style="text-align:left; width:28%;">
                                <div class="team-name">{away.split()[-1]}</div>
                                <div class="score-big">{live_info['score_away']}</div>
                                <div style="font-size:0.75em; color:#888;">xScore: <span class="{'xscore-hot' if xscore_away > 2 else 'xscore-cold' if xscore_away < -2 else ''}">{xscore_away:+.1f}</span></div>
                            </div>

                            <div class="factor-table" style="width:40%;">
                                <div style="display:flex; justify-content:space-between; padding:2px 0;" class="factor-header">
                                    <span>VIS</span><span>FATOR</span><span>CASA</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; padding:2px 0;">
                                    <span class="{'factor-good' if efg_a_win else 'factor-neutral'}">{a_factors['efg']:.1f}%</span>
                                    <span style="color:#aaa">eFG%</span>
                                    <span class="{'factor-good' if efg_h_win else 'factor-neutral'}">{h_factors['efg']:.1f}%</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; padding:2px 0;">
                                    <span class="{'factor-good' if tov_a_win else 'factor-bad' if tov_h_win else 'factor-neutral'}">{a_factors['tov']:.1f}%</span>
                                    <span style="color:#aaa">TO%</span>
                                    <span class="{'factor-good' if tov_h_win else 'factor-bad' if tov_a_win else 'factor-neutral'}">{h_factors['tov']:.1f}%</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; padding:2px 0;">
                                    <span class="{'factor-good' if orb_a_win else 'factor-neutral'}">{a_factors['orb']}</span>
                                    <span style="color:#aaa">OREB</span>
                                    <span class="{'factor-good' if orb_h_win else 'factor-neutral'}">{h_factors['orb']}</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; padding:2px 0;">
                                    <span style="color:#888">{a_factors['ftr']:.1f}%</span>
                                    <span style="color:#aaa">FTR</span>
                                    <span style="color:#888">{h_factors['ftr']:.1f}%</span>
                                </div>
                            </div>

                            <div style="text-align:right; width:28%;">
                                <div class="team-name">{home.split()[-1]}</div>
                                <div class="score-big">{live_info['score_home']}</div>
                                <div style="font-size:0.75em; color:#888;">xScore: <span class="{'xscore-hot' if xscore_home > 2 else 'xscore-cold' if xscore_home < -2 else ''}">{xscore_home:+.1f}</span></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Sem Four Factors, mostra placar simples
                        st.markdown(f"""
                        <div style="display:flex; justify-content:space-around; align-items:center; margin-bottom:15px;">
                            <div style="text-align:center;">
                                <div class="team-name">{away.split()[-1]}</div>
                                <div class="score-big">{live_info['score_away']}</div>
                            </div>
                            <div style="color:#444; font-size:1.5em;">vs</div>
                            <div style="text-align:center;">
                                <div class="team-name">{home.split()[-1]}</div>
                                <div class="score-big">{live_info['score_home']}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    # Jogo PRE-GAME
                    time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="color:#888; font-size:0.85em;">{time_start}</span><br>
                                <span style="color:#aaa">{away}</span> <span style="color:#666">({r_away:+.1f})</span><br>
                                <span style="color:#fff">@ {home}</span> <span style="color:#666">({r_home:+.1f})</span>
                            </div>
                    """, unsafe_allow_html=True)

                # Linha de Decisao (SPREADS)
                col1, col2, col3 = st.columns([2, 2, 2])

                with col1:
                    p_out_h = st.selectbox(f"Fora {home.split()[-1]}?", ["-"]+roster_home+generics, key=f"an_h_{home}", label_visibility="collapsed")
                    p_out_a = st.selectbox(f"Fora {away.split()[-1]}?", ["-"]+roster_away+generics, key=f"an_a_{home}", label_visibility="collapsed")

                    if p_out_h != "-":
                        fair_line += PLAYER_IMPACTS.get(p_out_h, 2.5)
                    if p_out_a != "-":
                        fair_line -= PLAYER_IMPACTS.get(p_out_a, 2.5)

                # Ajuste xScore
                if is_live and use_xscore:
                    xscore_adj = (xscore_home - xscore_away) * 0.3
                    fair_line -= xscore_adj

                diff = abs(fair_line - market_line)
                has_value = diff >= 1.5

                with col2:
                    st.markdown(f"""<div style="text-align:center; padding:10px;">
                        <div style="font-size:0.7em; color:#888;">MODELO vs MERCADO</div>
                        <div><span style="color:#4da6ff; font-weight:bold; font-size:1.2em;">{fair_line:+.1f}</span>
                        <span style="color:#666">vs</span>
                        <span style="color:#fff; font-weight:bold; font-size:1.2em;">{market_line:+.1f}</span></div>
                    </div>""", unsafe_allow_html=True)

                with col3:
                    if has_value:
                        pick = home if fair_line < market_line else away
                        line = market_line if pick == home else -market_line
                        units = 1.5 if diff > 3 else 0.75
                        val = valor_unidade * units
                        css_badge = "stake-badge" if diff > 3 else "stake-badge stake-normal"
                        st.markdown(f"""<div style="text-align:right; padding:10px;">
                            <span class="{css_badge}">R$ {val:.0f}</span><br>
                            <span style="color:{'#4da6ff' if pick==home else '#ffcc00'}; font-weight:bold;">{pick.split()[-1]} {line:+.1f}</span><br>
                            <span style="font-size:0.75em; color:#888;">Edge: {diff:.1f} pts</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:right; padding:10px; color:#555;'>Linha Justa</div>", unsafe_allow_html=True)

                # Insights baseados nos Four Factors
                if is_live and h_factors and a_factors and use_factors:
                    insights = []

                    # Time com eFG% muito baixo mas xScore alto = azar
                    if h_factors['efg'] < 40 and xscore_home > 0:
                        insights.append(f"<b>{home.split()[-1]}</b> esta errando arremessos abertos (eFG {h_factors['efg']:.0f}%). Tendencia de melhora.")
                    if a_factors['efg'] < 40 and xscore_away > 0:
                        insights.append(f"<b>{away.split()[-1]}</b> esta errando arremessos abertos (eFG {a_factors['efg']:.0f}%). Tendencia de melhora.")

                    # Time com muitos turnovers
                    if h_factors['tov'] > 18:
                        insights.append(f"<b>{home.split()[-1]}</b> cometendo muitos erros ({h_factors['tov']:.0f}% TO). Dificil recuperar.")
                    if a_factors['tov'] > 18:
                        insights.append(f"<b>{away.split()[-1]}</b> cometendo muitos erros ({a_factors['tov']:.0f}% TO). Dificil recuperar.")

                    if insights:
                        insight_class = "insight-box" if "melhora" in insights[0].lower() else "insight-box insight-box-warning"
                        st.markdown(f"""<div class="{insight_class}">
                            {'<br>'.join(insights)}
                        </div>""", unsafe_allow_html=True)

                if not is_live:
                    st.markdown("</div></div>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 10px 0; border-color: #2d313a;'>", unsafe_allow_html=True)

    with tab_totals:
        st.markdown("""<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;">
            <div style="flex: 2.5;">JOGO</div>
            <div style="flex: 2; text-align: center;">RITMO</div>
            <div style="flex: 2; text-align: center;">PROJ vs LINHA</div>
            <div style="flex: 1.5; text-align: right;">SINAL</div>
        </div>""", unsafe_allow_html=True)

        for game in ODDS:
            home = game['home_team']
            away = game['away_team']

            live_info = None
            for k, v in LIVE_DATA.items():
                if k in home or home in k: live_info = v; break
            is_live = live_info['live'] if live_info else False

            home_stats = TEAM_STATS.get(home.split()[-1], TEAM_STATS.get(home, {'ppg': 110, 'pace': 98}))
            away_stats = TEAM_STATS.get(away.split()[-1], TEAM_STATS.get(away, {'ppg': 110, 'pace': 98}))

            market_total = 0.0
            for s in game.get('bookmakers', []):
                if s['key'] in ['pinnacle', 'bet365']:
                    for mkt in s.get('markets', []):
                        if mkt['key'] == 'totals':
                            market_total = mkt['outcomes'][0]['point']
                            break
            if market_total == 0.0: continue

            if is_live and use_pace:
                mins = live_info.get('minutes_played', 0)
                current_total = live_info.get('total', 0)
                period = live_info.get('period', 1)
                projected_total, current_pace, pace_div = calculate_dynamic_pace(
                    home_stats, away_stats, current_total, mins, period
                )
            else:
                projected_total = home_stats.get('ppg', 110) + away_stats.get('ppg', 110)
                current_pace = (home_stats.get('pace', 98) + away_stats.get('pace', 98)) / 2
                pace_div = 0

            diff_total = projected_total - market_total
            has_signal = abs(diff_total) >= 3

            with st.container():
                c_g, c_p, c_t, c_s = st.columns([2.5, 2, 2, 1.5], gap="small", vertical_alignment="center")

                with c_g:
                    if is_live:
                        st.markdown(f"""<div style="line-height:1.2;">
                            <span class="status-live"><span class="live-dot"></span>LIVE</span>
                            <span class="status-q">Q{live_info['period']}</span>
                            <span class="status-clock">{live_info['clock']}</span><br>
                            <span style="color:#fff;font-size:1.1em"><b>{live_info['total']}</b> pts</span>
                        </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<div style="line-height:1.4;">
                            <span style="color:#888;font-size:0.8em">{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span><br>
                            {away.split()[-1]} @ {home.split()[-1]}
                        </div>""", unsafe_allow_html=True)

                with c_p:
                    pace_css = "color:#51cf66" if pace_div > 3 else ("color:#ff6b6b" if pace_div < -3 else "color:#aaa")
                    st.markdown(f"""<div style="text-align:center;">
                        <div style="font-size:0.7em;color:#888">PACE</div>
                        <div style="font-weight:bold;{pace_css}">{current_pace:.1f}</div>
                        <div style="font-size:0.7em;color:#666">({pace_div:+.1f})</div>
                    </div>""", unsafe_allow_html=True)

                with c_t:
                    st.markdown(f"""<div style="display:flex;justify-content:space-around;text-align:center;">
                        <div><div style="font-size:0.65em;color:#aaa">PROJ</div><div style="font-weight:bold;color:#9775fa">{projected_total:.1f}</div></div>
                        <div><div style="font-size:0.65em;color:#aaa">LINHA</div><div style="font-weight:bold;color:#fff">{market_total:.1f}</div></div>
                    </div>""", unsafe_allow_html=True)

                with c_s:
                    if has_signal:
                        if diff_total > 0:
                            st.markdown(f"""<div style="text-align:right;">
                                <span class="over-signal">OVER</span><br>
                                <span style="font-size:0.8em;color:#51cf66">+{diff_total:.1f}</span>
                            </div>""", unsafe_allow_html=True)
                        else:
                            st.markdown(f"""<div style="text-align:right;">
                                <span class="under-signal">UNDER</span><br>
                                <span style="font-size:0.8em;color:#ff6b6b">{diff_total:.1f}</span>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:right;color:#555;font-size:0.8em'>Neutro</div>", unsafe_allow_html=True)

                st.markdown("<hr style='margin: 5px 0; border-color: #2d313a;'>", unsafe_allow_html=True)
