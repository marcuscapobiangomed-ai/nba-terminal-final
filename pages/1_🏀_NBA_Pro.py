
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
API_KEY = "e6a32983f406a1fbf89fda109149ac15"
HISTORY_FILE = "bets_history.csv"

# Inicializa Estado
if 'banca' not in st.session_state: st.session_state.banca = 1000.0
if 'unidade_pct' not in st.session_state: st.session_state.unidade_pct = 1.0

# --- 2. CSS PREMIUM (DESIGN OVERHAUL v14) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@700&display=swap');
    
    /* BACKGROUND GERAL & SIDEBAR FORCE DARK */
    .stApp { background-color: #0b1120; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    
    /* CARDS */
    .game-card { 
        background: linear-gradient(180deg, #1e293b 0%, #172033 100%);
        border: 1px solid #334155; 
        border-radius: 16px; 
        padding: 24px; 
        margin-bottom: 20px; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    
    .card-live { 
        border-left: 4px solid #ef4444; 
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.05) 0%, rgba(30, 41, 59, 0.0) 30%), #1e293b;
    }
    
    /* TIPOGRAFIA */
    .team-name { font-size: 1.4rem; font-weight: 800; color: #f8fafc; margin-bottom: 8px; letter-spacing: -0.02em; }
    .score-big { font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 700; color: #fff; }
    
    .metric-label { font-size: 0.75rem; font-weight: 600; color: #94a3b8; letter-spacing: 0.1em; text-transform: uppercase; }
    .metric-value { font-size: 1.25rem; font-weight: 700; color: #e2e8f0; }
    
    .status-badge {
        font-size: 0.75rem; font-weight: 700; color: #94a3b8;
        background-color: #1e293b; border: 1px solid #334155;
        padding: 4px 12px; border-radius: 99px; display: inline-block; margin-bottom: 12px;
    }
    .live-badge { color: #fca5a5; border-color: #7f1d1d; background-color: #450a0a; }

    /* BOTÕES VISUAIS */
    .bet-box {
        background: rgba(34, 197, 94, 0.1); 
        border: 1px solid #22c55e;
        color: #4ade80;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 8px;
    }
    .bet-title { font-size: 0.7rem; font-weight: 700; color: #22c55e; letter-spacing: 0.1em; }
    .bet-pick { font-size: 1.1rem; font-weight: 800; color: #fff; }

    /* NOTÍCIAS */
    .news-card { background-color: #1e293b; padding: 15px; border-radius: 8px; border-bottom: 2px solid #334155; }
    .news-time { font-size: 0.75rem; color: #64748b; font-weight: 700; margin-bottom: 4px; }
    .news-title { font-size: 0.95rem; color: #cbd5e1; line-height: 1.4; }
    
    /* AJUSTES UI */
    div[data-testid="stExpander"] { border: none; background: transparent; }
    hr { border-color: #334155; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES (Lógica Preservada) ---
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
            data[row['TEAM_NAME']] = {'pace': row['PACE'], 'efg': row['EFG_PCT'], 'net_rtg': row['PTS'] - row['OPP_PTS']}
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

# --- 4. INTERFACE ---
st.title("🏆 NBA Terminal Pro")

# Sidebar Escura
with st.sidebar:
    st.markdown("### 💰 Gestão de Banca")
    st.session_state.banca = st.number_input("Banca Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    
    st.markdown("---")
    st.markdown(f"""
    <div style='background:#1e293b; padding:15px; border-radius:12px; text-align:center;'>
        <div style='color:#64748b; font-size:0.75rem; font-weight:700; margin-bottom:5px; letter-spacing:0.05em;'>VALOR DA UNIDADE</div>
        <div style='color:#38bdf8; font-size:1.5rem; font-weight:800;'>R$ {val_unid:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

tab_ops, tab_adm = st.tabs(["⚡ OPERAÇÕES", "📊 RESULTADOS"])

with tab_ops:
    if st.button("🔄 SCAN LIVE MARKET", type="primary", use_container_width=True):
        st.cache_data.clear(); st.rerun()
        
    news = get_news()
    if news:
        with st.expander("📰 BREAKING NEWS", expanded=False):
            cols = st.columns(3)
            for i, n in enumerate(news):
                with cols[i]: st.markdown(f"<div class='news-card'><div class='news-time'>{n['hora']}</div><div class='news-title'>{n['titulo']}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    STATS = get_advanced_team_stats()
    ODDS = get_odds(API_KEY)
    LIVE = get_live_scores()
    
    if not ODDS or isinstance(ODDS, dict):
        st.info("Mercado Fechado ou Sem Jogos.")
    else:
        for game in ODDS:
            h, a = game['home_team'], game['away_team']
            
            # Info Live
            linfo = None
            for k, v in LIVE.items():
                if k in h or h in k: linfo = v; break
            is_live = linfo['live'] if linfo else False
            
            if is_live:
                status_html = f"<span class='status-badge live-badge'>🔴 Q{linfo['period']} • {linfo['clock']}</span>"
                score_a = linfo['s_away']
                score_h = linfo['s_home']
                css_card = "game-card card-live"
            else:
                status_html = f"<span class='status-badge'>{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span>"
                score_a = ""
                score_h = ""
                css_card = "game-card"

            # Modelagem
            s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
            s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
            fair = -((s_h['net_rtg'] + 2.5) - s_a['net_rtg'])
            
            # Market
            m_spr = 0.0
            for s in game.get('bookmakers', []):
                p = s['markets'][0]['outcomes'][0]['point']
                m_spr = -p if s['markets'][0]['outcomes'][0]['name'] != h else p; break
            if m_spr == 0.0: continue
            
            # RENDERIZAÇÃO
            with st.container():
                st.markdown(f"""<div class="{css_card}">""", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([3.5, 1.5, 2.5])
                
                # C1: Times
                with c1:
                    st.markdown(status_html, unsafe_allow_html=True)
                    st.markdown(f"<div class='team-name'>{a}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='team-name'>{h}</div>", unsafe_allow_html=True)
                
                # C2: Placar (Alinhado à direita dos times ou centralizado)
                with c2:
                    if is_live:
                        st.markdown(f"""
                        <div style='display:flex; flex-direction:column; gap:8px;'>
                            <div class='score-big'>{score_a}</div>
                            <div class='score-big'>{score_h}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # C3: Dados e Ação
                with c3:
                    diff = abs(fair - m_spr)
                    has_val = diff >= 1.5
                    
                    # Linhas
                    st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; margin-bottom:15px; background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;'>
                        <div><div class='metric-label'>JUSTO</div><div class='metric-value' style='color:#38bdf8'>{fair:+.1f}</div></div>
                        <div style='text-align:right'><div class='metric-label'>BOOKIE</div><div class='metric-value'>{m_spr:+.1f}</div></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if has_val:
                        pick = h if fair < m_spr else a
                        line = m_spr if pick == h else -m_spr
                        units = 1.5 if diff > 3 else 0.75
                        val = val_unid * units
                        
                        # Box Visual de Aposta (Não clicável, apenas visual)
                        st.markdown(f"""
                        <div class='bet-box'>
                            <div class='bet-title'>VALOR ENCONTRADO (R$ {val:.0f})</div>
                            <div class='bet-pick'>{pick} {line:+.1f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Botão Funcional Discreto
                        if st.button("📥 SALVAR NA CARTEIRA", key=f"s_{h}"):
                             save_bet(f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val)

                    else:
                        st.markdown("<div style='text-align:center; padding:10px; color:#64748b; font-style:italic;'>Preço de Mercado Justo</div>", unsafe_allow_html=True)

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
        
        if not edited[edited['Resultado']!='Pendente'].empty:
            edited['Acumulado'] = edited['Lucro'].cumsum()
            fig = px.area(edited, y='Acumulado', title='Curva de Lucro (R$)', template='plotly_dark')
            fig.update_traces(line_color='#38bdf8', fill_color='rgba(56, 189, 248, 0.2)')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Seu histórico de apostas aparecerá aqui.")
