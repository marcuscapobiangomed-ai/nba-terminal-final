import streamlit as st
import pandas as pd
import requests
import feedparser
import os
import plotly.express as px
from datetime import datetime
from deep_translator import GoogleTranslator
from nba_api.stats.endpoints import leaguedashteamstats

# --- 1. CONFIGURAÇÃO & ESTADO ---
st.set_page_config(page_title="NBA Terminal Pro", page_icon="🏀", layout="wide")

# Tenta pegar a chave dos segredos ou usa a hardcoded (fallback)
try:
    API_KEY = st.secrets["ODDS_API_KEY"]
except:
    API_KEY = "e6a32983f406a1fbf89fda109149ac15"

HISTORY_FILE = "bets_history.csv"

# Inicializa Estado
if 'banca' not in st.session_state: st.session_state.banca = 1000.0
if 'unidade_pct' not in st.session_state: st.session_state.unidade_pct = 1.0

# --- 2. CSS PREMIUM (DESIGN OVERHAUL - V13.1) ---
st.markdown("""
    <style>
    /* Importando Fontes */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap');
    
    /* Configuração Global */
    .stApp { 
        background-color: #0b0f19; /* Obsidian Dark */
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* SIDEBAR FORÇADA DARK */
    [data-testid="stSidebar"] {
        background-color: #111827; /* Gray 900 */
        border-right: 1px solid #1f2937;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: #e5e7eb !important;
    }
    
    /* CARD DESIGN PRO */
    .game-card { 
        background-color: #161e2e; /* Gray 850 */
        border: 1px solid #374151; /* Gray 700 */
        border-radius: 8px; 
        padding: 16px; 
        margin-bottom: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    
    .card-live { 
        border-left: 4px solid #ef4444; 
        background: linear-gradient(90deg, #161e2e 0%, #1f1212 100%);
    }
    
    /* HEADER DO CARD */
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #374151;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    
    .status-live { color: #ef4444; font-weight: 800; letter-spacing: 0.05em; font-size: 0.8rem; }
    .status-pre { color: #9ca3af; font-weight: 600; font-size: 0.8rem; }
    
    /* PLACAR E TIMES */
    .team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    
    .team-name { 
        font-size: 1.1rem; 
        font-weight: 700; 
        color: #f3f4f6; 
    }
    
    .team-score { 
        font-size: 1.3rem; 
        font-weight: 800; 
        color: #ffffff; 
        background: #1f2937;
        padding: 2px 10px;
        border-radius: 4px;
        min-width: 40px;
        text-align: center;
    }
    
    /* DATA GRID */
    .data-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid #374151;
    }
    
    .metric-col { text-align: center; }
    .metric-lbl { color: #9ca3af; font-size: 0.7rem; font-weight: 700; margin-bottom: 2px; }
    .metric-val { color: #e5e7eb; font-size: 1.1rem; font-weight: 700; }
    .val-good { color: #34d399; } /* Green 400 */
    .val-bad { color: #f87171; } /* Red 400 */
    
    /* BOTÃO APOSTA */
    .bet-box {
        background: #064e3b; /* Emerald 900 */
        border: 1px solid #059669; /* Emerald 600 */
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        margin-top: 10px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .bet-box:hover { background: #065f46; transform: translateY(-1px); }
    .bet-title { color: #34d399; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .bet-pick { color: #ffffff; font-size: 1.1rem; font-weight: 800; }

    </style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES (MANTIDAS) ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return pd.DataFrame(columns=["Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"])
    return pd.read_csv(HISTORY_FILE)

def save_bet(jogo, tipo, aposta, odd, valor):
    df = load_history()
    new_row = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d %H:%M"), "Jogo": jogo, "Tipo": tipo, "Aposta": aposta, "Odd": odd, "Valor": valor, "Resultado": "Pendente", "Lucro": 0.0}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False)
    st.toast(f"✅ Registrado: {aposta}")

@st.cache_data(ttl=86400)
def get_advanced_team_stats():
    try:
        stats = leaguedashteamstats.LeagueDashTeamStats(season='2024-25', measure_type_detailed_defense='Base').get_data_frames()[0]
        data = {}
        for _, row in stats.iterrows():
            data[row['TEAM_NAME']] = {'pace': row['PACE'], 'efg': row['EFG_PCT'], 'net_rtg': row['PTS'] - row['OPP_PTS'], 'def_rtg': row['DEF_RATING']}
        return data
    except: return {}

def clean_clock(raw):
    if not raw: return ""
    if "M" in raw: return f"{raw.replace('PT','').split('M')[0]}:{raw.split('M')[1].replace('S','').split('.')[0]}"
    return raw

@st.cache_data(ttl=20)
def get_live_scores():
    try:
        data = requests.get("https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json").json()
        live = {}
        for g in data['scoreboard']['games']:
            info = {"live": g['gameStatus'] == 2, "period": g['period'], "clock": clean_clock(g['gameClock']), 
                    "s_home": g['homeTeam']['score'], "s_away": g['awayTeam']['score']}
            live[g['homeTeam']['teamName']] = info; live[g['awayTeam']['teamName']] = info
        return live
    except: return {}

def get_odds(api_key):
    try: return requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds', params={'api_key': api_key, 'markets': 'spreads,totals', 'bookmakers': 'pinnacle'}).json()
    except: return []

@st.cache_data(ttl=600)
def get_news():
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nba/news")
        noticias = []
        trans = GoogleTranslator(source='auto', target='pt')
        for e in feed.entries[:3]:
            try: tit = trans.translate(e.title).replace("Fontes:", "").strip()
            except: tit = e.title
            noticias.append({"titulo": tit, "hora": datetime(*e.published_parsed[:6]).strftime("%H:%M")})
        return noticias
    except: return []

# --- 4. INTERFACE PRINCIPAL ---
st.title("🏆 NBA Terminal Pro")

# Sidebar
with st.sidebar:
    st.markdown("### 💰 Bankroll")
    st.session_state.banca = st.number_input("Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    st.markdown(f"**Unidade:** R$ {val_unid:.2f}")
    st.divider()
    st.caption("v13.1 Stable • Slate Theme")

# Scan Button
if st.button("🔄 SCAN LIVE MARKET", type="primary", use_container_width=True):
    st.cache_data.clear(); st.rerun()

# DADOS
STATS = get_advanced_team_stats()
ODDS = get_odds(API_KEY)
LIVE = get_live_scores()

if not ODDS or isinstance(ODDS, dict) and 'message' in ODDS:
    st.info("Mercado Fechado ou Offseason.")
else:
    # GRID DE JOGOS (2 JOGOS POR LINHA PARA "ENQUADRAMENTO")
    if not ODDS:
        st.info("Nenhum jogo encontrado.")
    else:
        # Divide em chunks de 2 jogos para criar linhas
        games_list = list(ODDS)
        rows = [games_list[i:i + 2] for i in range(0, len(games_list), 2)]
        
        for row in rows:
            cols = st.columns(2) # 2 Colunas para melhor uso de tela
            for idx, game in enumerate(row):
                with cols[idx]:
                    h, a = game['home_team'], game['away_team']
                    
                    # Live Info
                    linfo = None
                    for k, v in LIVE.items():
                        if k in h or h in k: linfo = v; break
                    is_live = linfo['live'] if linfo else False
                    
                    # Model
                    s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
                    s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
                    fair = -((s_h['net_rtg'] + 2.5) - s_a['net_rtg'])
                    
                    # Market Spread
                    m_spr = 0.0
                    try:
                        for s in game.get('bookmakers', []):
                             for m in s.get('markets', []):
                                if m['key'] == 'spreads':
                                    m_spr = m['outcomes'][0]['point'] if m['outcomes'][0]['name'] == h else -m['outcomes'][0]['point']
                                    break
                    except: pass
                    if m_spr == 0.0: continue
                    
                    # Render Card
                    css_class = "game-card card-live" if is_live else "game-card"
                    clock = f"Q{linfo['period']} {linfo['clock']}" if is_live and linfo else pd.to_datetime(game.get('commence_time', datetime.now())).strftime('%H:%M')
                    status_class = "status-live" if is_live else "status-pre"
                    
                    score_a = linfo['s_away'] if is_live and linfo else "-"
                    score_h = linfo['s_home'] if is_live and linfo else "-"
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        <div class="card-header">
                            <span class="{status_class}">{clock}</span>
                            <span style="font-size:0.8rem; color:#6b7280;">SPREAD</span>
                        </div>
                        
                        <div class="team-row">
                            <span class="team-name">{a}</span>
                            <span class="team-score">{score_a}</span>
                        </div>
                        <div class="team-row">
                            <span class="team-name">{h}</span>
                            <span class="team-score">{score_h}</span>
                        </div>
                        
                        <div class="data-grid">
                            <div class="metric-col">
                                <div class="metric-lbl">MODELO</div>
                                <div class="metric-val">{fair:+.1f}</div>
                            </div>
                            <div class="metric-col">
                                <div class="metric-lbl">MERCADO</div>
                                <div class="metric-val">{m_spr:+.1f}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    diff = abs(fair - m_spr)
                    if diff >= 1.5:
                        pick = h if fair < m_spr else a
                        line = m_spr if pick == h else -m_spr
                        val = val_unid * (1.5 if diff > 3 else 0.75)
                        
                        st.markdown(f"""
                        <div class="bet-box">
                            <div class="bet-title">VALOR ENCONTRADO</div>
                            <div class="bet-pick">{pick} {line:+.1f}</div>
                            <div style="font-size:0.8rem; color:#a7f3d0;">Apostar R$ {val:.0f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="text-align:center; padding:10px; opacity:0.5; font-size:0.8rem;">
                            Sem Edge Claro
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

with tab_adm:
    st.subheader("📈 Performance")
    df = load_history()
    if not df.empty:
        edited = st.data_editor(df, num_rows="dynamic", key="editor", column_config={"Resultado": st.column_config.SelectboxColumn("Status", options=["Pendente","Green","Red"])})
        if st.button("Atualizar Lucro"):
            for i, r in edited.iterrows():
                if r['Resultado'] == 'Green': edited.at[i, 'Lucro'] = r['Valor'] * 0.91
                elif r['Resultado'] == 'Red': edited.at[i, 'Lucro'] = -r['Valor']
            edited.to_csv(HISTORY_FILE, index=False); st.rerun()
        
        # Gráfico Clean
        if not edited[edited['Resultado']!='Pendente'].empty:
            edited['Acumulado'] = edited['Lucro'].cumsum()
            fig = px.area(edited, y='Acumulado', title='Curva de Lucro (R$)', template='plotly_dark')
            fig.update_traces(line_color='#38bdf8', fill_color='rgba(56, 189, 248, 0.2)')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Histórico vazio.")
