import streamlit as st
import pandas as pd
import requests
import feedparser
from datetime import datetime
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py

# --- SUA CHAVE ---
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS MODERNO (Dark Mode Financeiro) ---
st.markdown("""
<style>
.stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }

/* Tira do Jogo */
.trade-strip {
    background-color: #1c1e26; border-radius: 8px; padding: 15px; margin-bottom: 12px;
    border-left: 4px solid #444; box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
.strip-value { border-left: 4px solid #00ff00; background-color: #1f291f; }

/* Textos */
.time-text { color: #888; font-size: 0.8em; font-weight: bold; display: block; margin-bottom: 4px;}
.team-name { font-size: 1.1em; font-weight: 600; color: #eee; }
.rating-badge { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; color: #aaa; margin-left: 6px; vertical-align: middle;}
.odds-label { font-size: 0.7em; color: #777; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px;}
.odds-num { font-size: 1.4em; font-weight: bold; }

/* Noticias */
.news-card { background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
.news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
.news-time { font-size: 0.75em; color: #888; margin-bottom: 4px; }
.news-title { color: #e0e0e0; font-weight: 500; }

/* Badges Financeiras */
.stake-badge {
    background-color: #00ff00; color: #000; font-weight: bold;
    padding: 4px 8px; border-radius: 4px; font-size: 0.9em;
    box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
}
.stake-normal { background-color: #ffff00; color: black; box-shadow: none; }
.stake-high { background-color: #ff00ff; color: white; box-shadow: 0 0 10px rgba(255, 0, 255, 0.4); }

div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; color: white; }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (GESTAO DE BANCA) ---
with st.sidebar:
    st.header("Gestao de Banca")

    # Inputs Financeiros
    banca_total = st.number_input("Banca Total (R$)", value=1000.0, step=100.0, min_value=100.0, format="%.2f")
    pct_unidade = st.slider("Valor da Unidade (%)", 0.5, 5.0, 1.0, step=0.5, help="Padrao profissional: 1% a 2%")

    # Calculo da Unidade
    valor_unidade = banca_total * (pct_unidade / 100)

    st.markdown("---")
    st.markdown(f"""
<div style="text-align:center; background-color: #1a1c24; padding: 10px; border-radius: 8px;">
<small style="color:#888">SUA UNIDADE (1u)</small><br>
<span style="font-size: 1.5em; color: #4da6ff; font-weight: bold;">R$ {valor_unidade:.2f}</span>
</div>
""", unsafe_allow_html=True)

    st.info("O App vai calcular o valor exato da aposta (em R$) baseado na forca da oportunidade.")

# --- 1. MOTOR DE NOTICIAS ---
@st.cache_data(ttl=300)
def get_nba_news():
    feed_url = "https://www.espn.com/espn/rss/nba/news"
    try:
        feed = feedparser.parse(feed_url)
        noticias = []
        keywords_alerta = ["injury", "out", "surgery", "suspended", "trade", "doubtful", "questionable", "miss"]

        for entry in feed.entries[:6]:
            titulo = entry.title
            link = entry.link
            try:
                dt = datetime(*entry.published_parsed[:6])
                hora = dt.strftime("%H:%M")
            except:
                hora = "Hoje"
            alerta = any(word in titulo.lower() for word in keywords_alerta)
            noticias.append({"titulo": titulo, "hora": hora, "link": link, "alerta": alerta})
        return noticias
    except:
        return []

# --- 2. CEREBRO (RATINGS) ---
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
        return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5, "Cavaliers": 8.0, "Knicks": 4.0}

def get_live_odds(api_key):
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {'api_key': api_key, 'regions': 'us,eu', 'markets': 'spreads', 'oddsFormat': 'decimal', 'bookmakers': 'pinnacle,bet365'}
    try:
        return requests.get(url, params=params).json()
    except:
        return []

# --- 3. DATABASE DE LESOES ---
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
c_title.title("NBA Terminal Pro v4.0")
if c_btn.button("Scan", type="primary"):
    st.cache_data.clear()
    st.rerun()

# --- NOTICIAS ---
with st.expander("BREAKING NEWS & LESOES", expanded=True):
    noticias = get_nba_news()
    if noticias:
        cols = st.columns(3)
        for i, news in enumerate(noticias):
            col_idx = i % 3
            css_class = "news-alert" if news['alerta'] else "news-card"
            icon = "🚨" if news['alerta'] else "ℹ️"
            with cols[col_idx]:
                st.markdown(f"""<div class="{css_class} news-card"><div class="news-time">{icon} {news['hora']}</div><div class="news-title"><a href="{news['link']}" target="_blank" style="text-decoration:none; color:inherit;">{news['titulo']}</a></div></div>""", unsafe_allow_html=True)
    else:
        st.info("Feed de noticias atualizado.")

st.divider()

# --- LOGICA DE TRADING ---
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
<div style="flex: 2; padding-left: 10px;">FILTRO DE LESAO</div>
<div style="flex: 1.5; text-align: right;">GESTAO (+EV)</div>
</div>
""", unsafe_allow_html=True)

    jogos_validos = 0

    for game in odds_data:
        home_full = game['home_team']
        away_full = game['away_team']
        time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')

        # Ratings
        r_home, r_away = 0.0, 0.0
        for n, r in RATINGS.items():
            if n in home_full: r_home = r
            if n in away_full: r_away = r

        fair_line_base = -((r_home + 2.5) - r_away)

        # Odds
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

        if market_line == 0.0: continue
        jogos_validos += 1

        # Filtro Jogadores
        jogadores_no_jogo = []
        for jogador, dados in DB_LESAO_FULL.items():
            if dados[1] in home_full or dados[1] in away_full:
                jogadores_no_jogo.append(jogador)
        jogadores_no_jogo.sort()

        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2.2, 2.2, 1.6], gap="small", vertical_alignment="center")

            with c1:
                st.markdown(f"""
<div style="line-height: 1.5;">
<span class="time-text">{time_start}</span>
<div style="display:flex; align-items:center;"><span class="team-name">{away_full}</span> <span class="rating-badge">{r_away:+.1f}</span></div>
<div style="color: #444; font-size: 0.8em; margin: 2px 0;">@</div>
<div style="display:flex; align-items:center;"><span class="team-name">{home_full}</span> <span class="rating-badge">{r_home:+.1f}</span></div>
</div>
""", unsafe_allow_html=True)

            with c3:
                player_out = st.selectbox("Quem esta fora?", ["-"] + jogadores_no_jogo, key=f"les_{home_full}", label_visibility="collapsed")

            # Ajuste
            adj_fair = fair_line_base
            if player_out != "-":
                imp, tm = DB_LESAO_FULL[player_out]
                if tm in home_full: adj_fair += imp
                elif tm in away_full: adj_fair -= imp

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
<div><div class="odds-label">MODELO</div><div class="odds-num" style="color: {cor_modelo};">{adj_fair:+.1f}</div><div style="font-size: 0.65em; color: #666; margin-top: -3px;">Linha Justa</div></div>
<div style="border-right: 1px solid #333;"></div>
<div><div class="odds-label">{bookie_name.upper()}</div><div class="odds-num odds-real">{market_line:+.1f}</div><div style="font-size: 0.65em; color: #666; margin-top: -3px;">Handicap</div></div>
</div>
""", unsafe_allow_html=True)

            # C4: GESTAO FINANCEIRA
            with c4:
                if has_value:
                    if diff < 3.0:
                        stake_units = 0.75
                        css_badge = "stake-normal"
                        label_txt = "APOSTAR"
                    elif diff < 5.0:
                        stake_units = 1.5
                        css_badge = "stake-badge"
                        label_txt = "VALOR"
                    else:
                        stake_units = 2.0
                        css_badge = "stake-high"
                        label_txt = "SUPER EV"

                    # Conversao para Reais
                    valor_aposta = stake_units * valor_unidade

                    st.markdown(f"""
<div style="text-align: right;">
<span class="{css_badge}">
{label_txt} R$ {valor_aposta:.2f}
</span><br>
<span style="font-weight: bold; color: {side_color}; font-size: 0.9em; display: block; margin-top: 4px;">
{pick} {line_pick:+.1f}
</span>
<span style="font-size: 0.75em; color: #888;">({stake_units}u | Edge: {diff:.1f})</span>
</div>
""", unsafe_allow_html=True)
                else:
                    st.markdown("""<div style="text-align: right; color: #555; font-size: 0.8em; margin-top: 10px;">Sem Valor<br>Linha Justa</div>""", unsafe_allow_html=True)

            # Divisoria
            st.markdown("<hr style='margin: 8px 0; border-color: #2d313a;'>", unsafe_allow_html=True)

    if jogos_validos == 0:
        st.warning("Sem jogos com linhas disponiveis no momento.")
