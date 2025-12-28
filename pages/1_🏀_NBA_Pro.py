
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

if 'banca' not in st.session_state: st.session_state.banca = 1000.0
if 'unidade_pct' not in st.session_state: st.session_state.unidade_pct = 1.0

# --- 2. CSS "GLASS-NEON" PREMIUM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&family=Roboto+Mono:wght@500;700&display=swap');
    
    /* FUNDO GERAL */
    .stApp { 
        background: radial-gradient(circle at top left, #1e293b, #0f172a);
        font-family: 'Inter', sans-serif;
    }
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {
        background-color: #0b1120;
        border-right: 1px solid #1e293b;
    }
    
    /* CARD PRINCIPAL (GLASS EFFECT) */
    .game-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 0; /* Padding controlado internamente */
        margin-bottom: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        overflow: hidden;
        transition: all 0.3s ease;
    }
    .game-card:hover {
        border-color: rgba(255, 255, 255, 0.1);
        transform: translateY(-2px);
    }
    
    .card-live {
        border-left: 4px solid #ef4444;
    }
    
    /* HEADER DO CARD (Status e Times) */
    .card-header {
        padding: 20px 24px;
        background: rgba(15, 23, 42, 0.4);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .status-badge {
        font-family: 'Roboto Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        color: #94a3b8;
        background: #1e293b;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #334155;
    }
    .live-badge { color: #fca5a5; border-color: #7f1d1d; background: #450a0a; }

    .team-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .team-name { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; }
    .team-score { font-family: 'Roboto Mono', monospace; font-size: 1.4rem; font-weight: 700; color: #fff; }

    /* CORPO DO CARD (Métricas) */
    .card-body {
        padding: 20px 24px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }
    
    .metric-col {
        background: rgba(255,255,255,0.03);
        border-radius: 10px;
        padding: 10px;
        text-align: center;
    }
    .metric-lbl { font-size: 0.65rem; color: #64748b; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
    .metric-val { font-size: 1.1rem; color: #e2e8f0; font-weight: 700; font-family: 'Roboto Mono'; }
    .val-highlight { color: #38bdf8; }

    /* RODAPÉ DE AÇÃO */
    .card-action {
        padding: 16px 24px;
        background: rgba(34, 197, 94, 0.05);
        border-top: 1px solid rgba(34, 197, 94, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .value-tag {
        color: #4ade80;
        font-weight: 700;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .bet-info { font-size: 1rem; color: #fff; font-weight: 800; }

    /* NOTÍCIAS */
    .news-item {
        background: #1e293b;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        border-left: 3px solid #3b82f6;
    }
    
    /* GESTÃO BANCA SIDEBAR */
    .bankroll-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }

    </style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES (Mesma Lógica Robusta) ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return pd.DataFrame(columns=["Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"])
    return pd.read_csv(HISTORY_FILE)

def save_bet(jogo, tipo, aposta, odd, valor):
    df = load_history()
    new_row = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d %H:%M"), "Jogo": jogo, "Tipo": tipo, "Aposta": aposta, "Odd": odd, "Valor": valor, "Resultado": "Pendente", "Lucro": 0.0}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False)
    st.toast(f"✅ Registrado na Carteira: {aposta}")

@st.cache_data(ttl=86400)
def get_advanced_team_stats():
    try:
        stats = leaguedashteamstats.LeagueDashTeamStats(season='2024-25', measure_type_detailed_defense='Base').get_data_frames()[0]
        data = {}
        for _, row in stats.iterrows():
            data[row['TEAM_NAME']] = {'net_rtg': row['PTS'] - row['OPP_PTS']}
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
    try: return requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds', params={'api_key': api_key, 'markets': 'spreads', 'bookmakers': 'pinnacle'}).json()
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

# Sidebar
with st.sidebar:
    st.markdown("### 💰 Gestão de Banca")
    st.session_state.banca = st.number_input("Banca Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    
    st.markdown("---")
    st.markdown(f"""
    <div class='bankroll-card'>
        <div style='color:#64748b; font-size:0.75rem; font-weight:700; margin-bottom:5px; letter-spacing:0.05em;'>VALOR 1 UNIDADE</div>
        <div style='color:#38bdf8; font-size:1.6rem; font-weight:800;'>R$ {val_unid:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

tab_ops, tab_adm = st.tabs(["⚡ MERCADO AO VIVO", "📊 MINHA CARTEIRA"])

with tab_ops:
    c_scan, c_news = st.columns([1.5, 4])
    with c_scan:
        if st.button("🔄 ATUALIZAR ODDS", type="primary", use_container_width=True):
            st.cache_data.clear(); st.rerun()
    
    with c_news:
        news = get_news()
        if news and st.toggle("Mostrar Notícias", False):
            for n in news:
                st.markdown(f"<div class='news-item'><b style='color:#94a3b8; font-size:0.8rem'>{n['hora']}</b> <span style='color:#e2e8f0; font-size:0.9rem'>{n['titulo']}</span></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    
    # DADOS
    STATS = get_advanced_team_stats()
    ODDS = get_odds(API_KEY)
    LIVE = get_live_scores()
    
    if not ODDS or isinstance(ODDS, dict):
        st.info("Mercado Fechado ou Sem Jogos no momento.")
    else:
        # GRID LAYOUT (2 Colunas para telas grandes)
        col_grid_1, col_grid_2 = st.columns(2)
        
        for idx, game in enumerate(ODDS):
            h, a = game['home_team'], game['away_team']
            
            # Coloca metade dos jogos na esquerda, metade na direita
            current_col = col_grid_1 if idx % 2 == 0 else col_grid_2
            
            linfo = None
            for k, v in LIVE.items():
                if k in h or h in k: linfo = v; break
            is_live = linfo['live'] if linfo else False
            
            s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
            s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
            fair = -((s_h['net_rtg'] + 2.5) - s_a['net_rtg'])
            
            m_spr = 0.0
            for s in game.get('bookmakers', []):
                p = s['markets'][0]['outcomes'][0]['point']
                m_spr = -p if s['markets'][0]['outcomes'][0]['name'] != h else p; break
            if m_spr == 0.0: continue
            
            # VARIÁVEIS DE VISUALIZAÇÃO
            if is_live:
                badge_html = f"<span class='status-badge live-badge'>🔴 Q{linfo['period']} {linfo['clock']}</span>"
                s_a_txt = linfo['s_away']
                s_h_txt = linfo['s_home']
                css_live = "card-live"
            else:
                badge_html = f"<span class='status-badge'>{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span>"
                s_a_txt = "-"
                s_h_txt = "-"
                css_live = ""

            diff = abs(fair - m_spr)
            has_val = diff >= 1.5
            
            # --- CARD RENDER ---
            with current_col:
                with st.container():
                    st.markdown(f"""
                    <div class="game-card {css_live}">
                        <div class="card-header">
                            <div>{badge_html}</div>
                            <div style="text-align:right">
                                <div class="team-row">
                                    <span class="team-name">{a}</span> <span class="team-score">{s_a_txt}</span>
                                </div>
                                <div class="team-row">
                                    <span class="team-name">{h}</span> <span class="team-score">{s_h_txt}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="card-body">
                            <div class="metric-col">
                                <div class="metric-lbl">MODELO</div>
                                <div class="metric-val val-highlight">{fair:+.1f}</div>
                            </div>
                            <div class="metric-col">
                                <div class="metric-lbl">MERCADO</div>
                                <div class="metric-val">{m_spr:+.1f}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if has_val:
                        pick = h if fair < m_spr else a
                        line = m_spr if pick == h else -m_spr
                        units = 1.5 if diff > 3 else 0.75
                        val = val_unid * units
                        
                        st.markdown(f"""
                        <div class="card-action">
                            <div>
                                <div class="value-tag">✨ VALOR ENCONTRADO</div>
                                <div class="bet-info">{pick} {line:+.1f}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Botão Nativo para Salvar
                        if st.button(f"📥 REGISTRAR APOSTA (R$ {val:.0f})", key=f"b_{h}", type="secondary", use_container_width=True):
                             save_bet(f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val)
                    
                    else:
                         st.markdown("""<div style="padding:15px; text-align:center; color:#475569; font-size:0.8rem; font-style:italic;">Sem oportunidade de valor</div>""", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

with tab_adm:
    st.subheader("📈 Performance da Carteira")
    df = load_history()
    if not df.empty:
        # Editor
        edited = st.data_editor(
            df, 
            num_rows="dynamic", 
            key="editor", 
            column_config={
                "Resultado": st.column_config.SelectboxColumn("Status", options=["Pendente","Green","Red"]),
                "Lucro": st.column_config.NumberColumn("Lucro (R$)", format="%.2f")
            },
            hide_index=True
        )
        
        c_upd, c_del = st.columns([1,4])
        if c_upd.button("💾 Salvar Alterações"):
            for i, r in edited.iterrows():
                if r['Resultado'] == 'Green': edited.at[i, 'Lucro'] = r['Valor'] * 0.91
                elif r['Resultado'] == 'Red': edited.at[i, 'Lucro'] = -r['Valor']
            edited.to_csv(HISTORY_FILE, index=False); st.rerun()
            
        # Gráfico
        finalizadas = edited[edited['Resultado']!='Pendente']
        if not finalizadas.empty:
            edited['Acumulado'] = edited['Lucro'].cumsum()
            
            fig = px.area(edited, x=edited.index, y='Acumulado', title='Crescimento da Banca (R$)', template='plotly_dark')
            fig.update_traces(line_color='#38bdf8', fill_color='rgba(56, 189, 248, 0.1)')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            # KPIs
            roi = (finalizadas['Lucro'].sum() / finalizadas['Valor'].sum()) * 100
            k1, k2, k3 = st.columns(3)
            k1.metric("Lucro Líquido", f"R$ {finalizadas['Lucro'].sum():.2f}")
            k2.metric("ROI Total", f"{roi:.1f}%")
            k3.metric("Apostas Fechadas", len(finalizadas))
    else:
        st.info("Nenhuma aposta registrada ainda.")
