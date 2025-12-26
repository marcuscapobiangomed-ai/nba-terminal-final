import streamlit as st
import pandas as pd
import requests
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py

# --- SUA CHAVE ---
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS MODERNO E LIMPO ---
st.markdown("""
<style>
.stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }
.trade-strip {
    background-color: #1c1e26; border-radius: 8px; padding: 15px; margin-bottom: 12px;
    border-left: 4px solid #444; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.strip-value { border-left: 4px solid #00ff00; background-color: #1f291f; }
.time-text { color: #888; font-size: 0.8em; font-weight: bold; display: block; margin-bottom: 4px;}
.team-name { font-size: 1.1em; font-weight: 600; color: #eee; }
.rating-badge { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; color: #aaa; margin-left: 6px; vertical-align: middle;}
.odds-label { font-size: 0.7em; color: #777; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px;}
.odds-num { font-size: 1.4em; font-weight: bold; }
.odds-real { color: #fff; }
div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
.ev-badge {
    background-color: #00cc00; color: black; font-weight: bold;
    padding: 4px 10px; border-radius: 4px; font-size: 0.85em;
    display: inline-block; margin-bottom: 5px;
}
</style>
""", unsafe_allow_html=True)

# --- 1. CEREBRO ---
@st.cache_data(ttl=86400)
def get_nba_ratings():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        ratings = {}
        for _, row in df.iterrows():
            team = row['TeamName']
            net = row['PointsPG'] - row['OppPointsPG']
            ratings[team] = round(net, 1)
        return ratings
    except:
        return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5}

def get_live_odds(api_key):
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {'api_key': api_key, 'regions': 'us,eu', 'markets': 'spreads', 'oddsFormat': 'decimal', 'bookmakers': 'pinnacle,bet365'}
    try:
        return requests.get(url, params=params).json()
    except:
        return []

# --- 2. DATABASE DE LESOES ---
DB_LESAO_FULL = {
    "Nikola Jokic": [8.5, "Nuggets"], "Luka Doncic": [7.0, "Mavericks"], "Giannis Antetokounmpo": [6.5, "Bucks"],
    "Shai Gilgeous-Alexander": [6.5, "Thunder"], "Joel Embiid": [6.0, "76ers"], "Jayson Tatum": [5.0, "Celtics"],
    "Jaylen Brown": [3.5, "Celtics"], "Stephen Curry": [5.0, "Warriors"], "LeBron James": [4.5, "Lakers"],
    "Anthony Davis": [4.5, "Lakers"], "Kevin Durant": [4.5, "Suns"], "Devin Booker": [3.5, "Suns"],
    "Ja Morant": [4.0, "Grizzlies"], "Tyrese Haliburton": [3.5, "Pacers"], "Donovan Mitchell": [4.0, "Cavaliers"],
    "Darius Garland": [3.0, "Cavaliers"], "Jalen Brunson": [3.5, "Knicks"], "Karl-Anthony Towns": [3.0, "Knicks"],
    "Anthony Edwards": [4.0, "Timberwolves"], "Victor Wembanyama": [4.5, "Spurs"], "Trae Young": [3.0, "Hawks"],
    "Jimmy Butler": [3.5, "Heat"], "Damian Lillard": [3.0, "Bucks"], "Zion Williamson": [3.0, "Pelicans"],
    "Paolo Banchero": [2.5, "Magic"], "LaMelo Ball": [2.5, "Hornets"], "Cade Cunningham": [2.5, "Pistons"],
    "Alperen Sengun": [2.5, "Rockets"]
}

# --- APP PRINCIPAL ---
c_title, c_btn = st.columns([6, 1])
c_title.title("NBA Terminal Pro v3.1")
if c_btn.button("Scan", type="primary"):
    st.cache_data.clear()
    st.rerun()

RATINGS = get_nba_ratings()
odds_data = get_live_odds(API_KEY)

if not odds_data or isinstance(odds_data, dict):
    st.info("Mercado fechado ou sem creditos na API.")
else:
    # Cabecalho
    st.markdown("""
<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px; font-weight: bold;">
<div style="flex: 3;">JOGO & RATING</div>
<div style="flex: 2; text-align: center;">LINHAS (MODELO vs CASA)</div>
<div style="flex: 2; padding-left: 10px;">FILTRO DE LESAO (AUTO)</div>
<div style="flex: 1.5; text-align: right;">DECISAO (+EV)</div>
</div>
""", unsafe_allow_html=True)

    jogos_validos = 0

    for game in odds_data:
        home_full = game['home_team']
        away_full = game['away_team']
        time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')

        # Match Ratings
        r_home, r_away = 0.0, 0.0
        for n, r in RATINGS.items():
            if n in home_full: r_home = r
            if n in away_full: r_away = r

        # Linha Base
        fair_line_base = -((r_home + 2.5) - r_away)

        # Busca Odds (Com validacao de 0.0)
        market_line = 0.0
        bookie_name = "N/A"
        sites = game.get('bookmakers', [])
        for site in sites:
            if site['key'] in ['pinnacle', 'bet365']:
                try:
                    p = site['markets'][0]['outcomes'][0]['point']
                    name = site['markets'][0]['outcomes'][0]['name']
                    if name != home_full: p = -p
                    market_line = p
                    bookie_name = site['title']
                    break
                except: pass

        # TRAVA DE SEGURANCA: Se a odd for 0.0 ou N/A, pular o jogo
        if market_line == 0.0:
            continue

        jogos_validos += 1

        # Filtro de Jogadores
        jogadores_no_jogo = []
        for jogador, dados in DB_LESAO_FULL.items():
            time_jogador = dados[1]
            if time_jogador in home_full or time_jogador in away_full:
                jogadores_no_jogo.append(jogador)
        jogadores_no_jogo.sort()

        # Renderizacao
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2.2, 2.2, 1.6], gap="small", vertical_alignment="center")

            with c1:
                st.markdown(f"""
<div style="line-height: 1.5;">
<span class="time-text">{time_start}</span>
<div style="display:flex; align-items:center;">
<span class="team-name">{away_full}</span>
<span class="rating-badge" title="Net Rating">{r_away:+.1f}</span>
</div>
<div style="color: #444; font-size: 0.8em; margin: 2px 0;">@</div>
<div style="display:flex; align-items:center;">
<span class="team-name">{home_full}</span>
<span class="rating-badge" title="Net Rating">{r_home:+.1f}</span>
</div>
</div>
""", unsafe_allow_html=True)

            with c3:
                player_out = st.selectbox(
                    "Quem esta fora?", ["-"] + jogadores_no_jogo, key=f"les_{home_full}", label_visibility="collapsed"
                )

            # Ajuste Lesao
            adj_fair = fair_line_base
            if player_out != "-":
                dados_jogador = DB_LESAO_FULL[player_out]
                impacto = dados_jogador[0]
                time_jogador = dados_jogador[1]
                if time_jogador in home_full: adj_fair += impacto
                elif time_jogador in away_full: adj_fair -= impacto

            # Decisao
            diff = abs(adj_fair - market_line)
            has_value = diff >= 1.5

            if adj_fair < market_line:
                pick = home_full
                line_pick = market_line
                side_color = "#4da6ff"
            else:
                pick = away_full
                line_pick = -market_line
                side_color = "#ffcc00"

            with c2:
                cor_modelo = "#ffeb3b" if player_out != "-" else "#4da6ff"
                st.markdown(f"""
<div style="display: flex; justify-content: space-around; text-align: center;">
<div>
<div class="odds-label">MODELO</div>
<div class="odds-num" style="color: {cor_modelo};">{adj_fair:+.1f}</div>
</div>
<div style="border-right: 1px solid #333; margin: 0 5px;"></div>
<div>
<div class="odds-label">{bookie_name.upper()}</div>
<div class="odds-num odds-real">{market_line:+.1f}</div>
</div>
</div>
""", unsafe_allow_html=True)

            # --- COLUNA 4: DECISAO COM GESTAO DE BANCA ---
            with c4:
                if has_value:
                    # Definindo o tamanho da aposta (Kelly Simplificado)
                    if diff < 3.0:
                        stake = "0.75u"
                        stake_color = "#ffff00"  # Amarelo (Normal)
                        label_txt = "APOSTAR"
                    elif diff < 5.0:
                        stake = "1.5u"
                        stake_color = "#00ff00"  # Verde (Forte)
                        label_txt = "VALOR"
                    else:
                        stake = "2.0u"
                        stake_color = "#ff00ff"  # Rosa/Magenta (Extremo)
                        label_txt = "SUPER EV"

                    st.markdown(f"""
<div style="text-align: right;">
<span style="background-color: {stake_color}; color: black; font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">
{label_txt} {stake}
</span><br>
<span style="font-weight: bold; color: {side_color}; font-size: 0.9em; display: block; margin-top: 4px;">
{pick} {line_pick:+.1f}
</span>
<span style="font-size: 0.75em; color: #888;">Edge: {diff:.1f} pts</span>
</div>
""", unsafe_allow_html=True)
                else:
                    st.markdown("""
<div style="text-align: right; color: #555; font-size: 0.8em; margin-top: 10px;">
Sem Valor<br>Linha Justa
</div>
""", unsafe_allow_html=True)

            # Divisoria
            st.markdown("<hr style='margin: 8px 0; border-color: #2d313a;'>", unsafe_allow_html=True)

    if jogos_validos == 0:
        st.warning("Mercado aberto, mas sem linhas de handicap disponiveis no momento. Tente novamente mais tarde.")
