import streamlit as st
import pandas as pd
import requests
from nba_api.stats.endpoints import leaguestandings

# --- CONFIGURACAO INICIAL ---
# st.set_page_config removido - esta no Home.py

# --- SUA CHAVE ---
API_KEY = "e6a32983f406a1fbf89fda109149ac15"

# --- CSS COMPACTO & VISUAL ---
st.markdown("""
<style>
.stApp { background-color: #0e1117; font-family: 'Roboto', sans-serif; }

/* Container do Jogo (A Tira Horizontal) */
.trade-strip {
    background-color: #1c1e26;
    border-radius: 8px;
    padding: 12px 15px;
    margin-bottom: 8px;
    border-left: 4px solid #444;
    display: flex; align-items: center; justify-content: space-between;
}

.strip-value {
    border-left: 4px solid #00ff00;
    background-color: #1f291f;
}

.time-text { color: #666; font-size: 0.75em; font-weight: bold; }
.team-text { font-size: 1em; font-weight: 600; color: #eee; }
.rating-badge { background: #333; padding: 1px 4px; border-radius: 3px; font-size: 0.7em; color: #aaa; margin-left: 5px;}

.odds-title { font-size: 0.7em; color: #888; text-transform: uppercase; letter-spacing: 1px; }

.ev-badge {
    background-color: #00cc00; color: black; font-weight: bold; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; display: inline-block;
}

/* Inputs menores */
div[data-baseweb="select"] > div { min-height: 30px; padding: 0px; font-size: 0.85em; }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (PROFESSOR) ---
with st.sidebar:
    st.header("Guia de Execucao")

    with st.expander("Como ler a 'Acao'?"):
        st.markdown("""
        O app calcula a matematica e te da a ordem final.

        Se aparecer: **Aposte Knicks +6.0**
        1. Va na Bet365/Pinnacle.
        2. Procure o jogo (Cavs vs Knicks).
        3. Va na aba **Handicap (Spread)**.
        4. Clique na opcao **Knicks +6.0**.
        """)

    with st.expander("O que e o Spread?"):
        st.info("""
        E a vantagem de pontos.
        * **-5.0**: O time tem que ganhar por 6 ou mais.
        * **+5.0**: O time pode perder por ate 4 (ou ganhar).
        """)

    st.divider()
    st.markdown("### Gestao de Banca")
    st.write("Edge > 1.5: **0.5 Unidade**")
    st.write("Edge > 4.0: **1.0 Unidade**")

# --- FUNCOES ---
@st.cache_data(ttl=86400)
def get_nba_ratings():
    try:
        standings = leaguestandings.LeagueStandings(season='2024-25')
        df = standings.get_data_frames()[0]
        ratings = {}
        for _, row in df.iterrows():
            ratings[row['TeamName']] = round(row['PointsPG'] - row['OppPointsPG'], 1)
        return ratings
    except:
        return {"Celtics": 10.5, "Thunder": 9.0, "Nuggets": 7.0, "Lakers": 1.5}

def get_live_odds(api_key):
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {'api_key': api_key, 'regions': 'us,eu', 'markets': 'spreads', 'oddsFormat': 'decimal', 'bookmakers': 'pinnacle,bet365'}
    try: return requests.get(url, params=params).json()
    except: return []

DB_LESAO = {
    "Nikola Jokic": 8.5, "Luka Doncic": 7.0, "Giannis": 6.5, "SGA": 6.5, "Embiid": 6.0,
    "Tatum": 5.0, "Steph Curry": 5.0, "LeBron": 4.5, "AD": 4.5, "Durant": 4.5,
    "Ja Morant": 4.0, "Haliburton": 3.5, "Mitchell": 3.5, "Brunson": 3.5
}

# --- APP PRINCIPAL ---
c_title, c_btn = st.columns([6, 1])
c_title.title("NBA Terminal Pro")
if c_btn.button("Scan", type="primary"):
    st.cache_data.clear()
    st.rerun()

RATINGS = get_nba_ratings()
odds_data = get_live_odds(API_KEY)

if not odds_data or isinstance(odds_data, dict):
    st.info("Aguardando mercado abrir ou verifique sua API Key.")
else:
    # Cabecalho da Tabela
    st.markdown("""
<div style="display: flex; color: #666; font-size: 0.8em; padding: 0 15px; margin-bottom: 5px;">
<div style="flex: 3;">CONFRONTO</div>
<div style="flex: 2; text-align: center;">LINHAS (MODELO vs CASAS)</div>
<div style="flex: 2;">FILTRO DE LESAO</div>
<div style="flex: 2; text-align: right;">DECISAO (+EV)</div>
</div>
""", unsafe_allow_html=True)

    for game in odds_data:
        home = game['home_team']
        away = game['away_team']
        time_start = pd.to_datetime(game['commence_time']).strftime('%H:%M')

        # Match Ratings
        r_home, r_away = 0.0, 0.0
        for n, r in RATINGS.items():
            if n in home: r_home = r
            if n in away: r_away = r

        # Linha Justa (Fair Line) Baseada em Ratings
        fair_line = -((r_home + 2.5) - r_away)

        market_line = 0.0
        sites = game.get('bookmakers', [])
        for site in sites:
            if site['key'] in ['pinnacle', 'bet365']:
                try:
                    p = site['markets'][0]['outcomes'][0]['point']
                    name = site['markets'][0]['outcomes'][0]['name']
                    if name != home: p = -p
                    market_line = p
                    break
                except: pass
        if market_line == 0.0 and sites:
            try:
                p = sites[0]['markets'][0]['outcomes'][0]['point']
                if sites[0]['markets'][0]['outcomes'][0]['name'] != home: p = -p
                market_line = p
            except: pass

        # --- O CONTAINER DO JOGO (LINHA UNICA) ---
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2.5, 2], gap="small", vertical_alignment="center")

            # --- COLUNA 1: TIMES ---
            with c1:
                st.markdown(f"""
<div style="line-height: 1.4;">
<span class="time-text">{time_start}</span><br>
<span class="team-text">{away}</span> <span class="rating-badge">{r_away:+.1f}</span><br>
<span class="team-text" style="color: #bbb;">@</span> <span class="team-text">{home}</span> <span class="rating-badge">{r_home:+.1f}</span>
</div>
""", unsafe_allow_html=True)

            # --- COLUNA 3: INPUT DE LESAO (AJUSTADO) ---
            with c3:
                col_input, col_check = st.columns([3, 2])

                with col_input:
                    player_out = st.selectbox(
                        "Lesao?",
                        ["-"] + list(DB_LESAO.keys()),
                        key=f"les_{home}",
                        label_visibility="collapsed"
                    )

                with col_check:
                    is_rival = st.checkbox("Rival", key=f"chk_{home}", help="Marque se a lesao for no time Visitante")

            # Calculo Dinamico
            adj_fair = fair_line
            if player_out != "-":
                impacto = DB_LESAO[player_out]
                if is_rival:
                    adj_fair -= impacto  # Melhora para o Home
                else:
                    adj_fair += impacto  # Piora para o Home

            # --- CALCULO DA DECISAO (LOGICA CORRIGIDA) ---
            diff = abs(adj_fair - market_line)
            has_value = diff >= 1.5

            # Decidir em quem apostar
            if adj_fair < market_line:
                # Modelo acha Home mais forte que mercado -> Apostar no HOME
                pick_team = home
                pick_line = market_line
            else:
                # Modelo acha Home mais fraco que mercado -> Apostar no VISITANTE
                pick_team = away
                pick_line = -market_line

            # --- COLUNA 2: NUMEROS ---
            with c2:
                cor_modelo = "#ffeb3b" if player_out != "-" else "#4da6ff"
                st.markdown(f"""
<div style="display: flex; justify-content: space-around; text-align: center;">
<div>
<div class="odds-title">MODELO</div>
<div style="color: {cor_modelo}; font-weight: bold; font-size: 1.2em;">{adj_fair:+.1f}</div>
</div>
<div style="border-left: 1px solid #444; margin: 0 10px;"></div>
<div>
<div class="odds-title">PINNACLE</div>
<div style="color: white; font-weight: bold; font-size: 1.2em;">{market_line:+.1f}</div>
</div>
</div>
""", unsafe_allow_html=True)

            # --- COLUNA 4: VEREDITO ---
            with c4:
                if has_value:
                    st.markdown(f"""
<div style="text-align: right;">
<span class="ev-badge">APOSTAR:</span><br>
<span style="font-weight: bold; color: #fff;">{pick_team} {pick_line:+.1f}</span><br>
<span style="font-size: 0.7em; color: #00ff00;">Edge: {diff:.1f}</span>
</div>
""", unsafe_allow_html=True)
                else:
                    st.markdown("""
<div style="text-align: right; color: #555; font-size: 0.8em;">
Sem Valor<br>Justo
</div>
""", unsafe_allow_html=True)

            # HR Personalizado
            st.markdown("<hr style='margin: 5px 0; border-color: #2d313a;'>", unsafe_allow_html=True)
