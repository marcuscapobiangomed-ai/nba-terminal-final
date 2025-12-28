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

# --- 2. CSS PREMIUM (DESIGN OVERHAUL) ---
st.markdown("""
    <style>
    /* Importando Fontes Modernas */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* RESET GLOBAL */
    .stApp { 
        background-color: #0f172a; /* Slate 900 - Fundo Azulado Profundo */
        font-family: 'Inter', sans-serif;
    }
    
    /* CARD DESIGN (Glassmorphism Sutil) */
    .game-card { 
        background-color: #1e293b; /* Slate 800 */
        border: 1px solid #334155; /* Slate 700 */
        border-radius: 12px; 
        padding: 20px; 
        margin-bottom: 16px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    .game-card:hover { border-color: #475569; }
    
    .card-live { 
        background: linear-gradient(145deg, #1e293b 0%, #2a1b1b 100%);
        border-left: 5px solid #ef4444; 
    }
    
    /* TIPOGRAFIA HIERÁRQUICA */
    .team-name { 
        font-size: 1.25rem; /* 20px */
        font-weight: 700; 
        color: #f8fafc; /* Slate 50 */
        margin-bottom: 4px;
        line-height: 1.2;
    }
    
    .score-big { 
        font-size: 2rem; /* 32px */
        font-weight: 800; 
        color: #ffffff;
        letter-spacing: -1px;
    }
    
    .metric-label { 
        font-size: 0.85rem; /* 13.6px - Bem maior que antes */
        font-weight: 600;
        color: #94a3b8; /* Slate 400 */
        text-transform: uppercase; 
        letter-spacing: 0.05em;
        margin-bottom: 2px;
    }
    
    .metric-value { 
        font-size: 1.4rem; /* 22px */
        font-weight: 700; 
        color: #e2e8f0; 
    }
    
    .status-badge {
        font-size: 0.8rem;
        font-weight: 700;
        color: #cbd5e1;
        background-color: #334155;
        padding: 4px 10px;
        border-radius: 99px;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* BOTÕES DE AÇÃO */
    .bet-button {
        background-color: #22c55e; /* Green 500 */
        color: #022c22;
        font-weight: 800;
        padding: 8px 16px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 0 15px rgba(34, 197, 94, 0.4);
        border: 1px solid #4ade80;
    }
    
    .no-value {
        color: #64748b;
        font-size: 0.9rem;
        font-style: italic;
    }
    
    /* NOTÍCIAS */
    .news-card { background-color: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-bottom: 8px; }
    .news-title { font-size: 1rem; color: #e2e8f0; line-height: 1.4; }
    .news-time { font-size: 0.8rem; color: #94a3b8; font-weight: bold; margin-bottom: 4px; }
    
    /* AJUSTES STREAMLIT */
    div[data-testid="stExpander"] { background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES (MANTIDAS IGUAIS) ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return pd.DataFrame(columns=["Data", "Jogo", "Tipo", "Aposta", "Odd", "Valor", "Resultado", "Lucro"])
    return pd.read_csv(HISTORY_FILE)

def save_bet(jogo, tipo, aposta, odd, valor):
    df = load_history()
    new_row = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d %H:%M"), "Jogo": jogo, "Tipo": tipo, "Aposta": aposta, "Odd": odd, "Valor": valor, "Resultado": "Pendente", "Lucro": 0.0}])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False)
    st.toast(f"✅ Aposta Registrada: {aposta}")

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

# Sidebar Limpa
with st.sidebar:
    st.header("💰 Gestão")
    st.session_state.banca = st.number_input("Banca Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    st.markdown(f"""
    <div style="background:#1e293b; padding:15px; border-radius:10px; border:1px solid #334155; text-align:center;">
        <div style="color:#94a3b8; font-size:0.8rem; font-weight:600; margin-bottom:5px;">VALOR DA UNIDADE</div>
        <div style="color:#38bdf8; font-size:1.8rem; font-weight:800;">R$ {val_unid:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# Tabs
tab_ops, tab_adm = st.tabs(["⚡ OPERAÇÕES", "📊 RESULTADOS"])

with tab_ops:
    c_btn, c_news = st.columns([1, 4])
    if c_btn.button("🔄 SCAN LIVE", type="primary", use_container_width=True):
        st.cache_data.clear(); st.rerun()
        
    news = get_news()
    if news:
        with st.expander("📰 MANCHETES", expanded=False):
            cols = st.columns(3)
            for i, n in enumerate(news):
                with cols[i]: st.markdown(f"<div class='news-card'><div class='news-time'>{n['hora']}</div><div class='news-title'>{n['titulo']}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # DADOS
    STATS = get_advanced_team_stats()
    ODDS = get_odds(API_KEY)
    LIVE = get_live_scores()
    
    if not ODDS or isinstance(ODDS, dict) and 'message' in ODDS:
        st.info("Mercado Fechado ou Sem Jogos (API Limit ou Offseason).")
        # Fallback para debug se a API falhar
        # st.write(ODDS) 
    else:
        # Se ODDS for uma lista vazia ou válida
        if not ODDS:
             st.info("Nenhum jogo encontrado para hoje.")
        else:
            for game in ODDS:
                h, a = game['home_team'], game['away_team']
                
                # Info Live
                linfo = None
                for k, v in LIVE.items():
                    if k in h or h in k: linfo = v; break
                is_live = linfo['live'] if linfo else False
                
                # Modelagem
                s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
                s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
                fair = -((s_h['net_rtg'] + 2.5) - s_a['net_rtg'])
                
                # Market
                m_spr = 0.0
                try:
                    for s in game.get('bookmakers', []):
                        for m in s.get('markets', []):
                            if m['key'] == 'spreads':
                                for o in m['outcomes']:
                                    if o['name'] == h: p = o['point']; m_spr = p; break
                                    elif o['name'] == a: p = o['point']; m_spr = -p; break # Se away é favorito (-), spread home é (+). Logica simplificada aqui.
                                break # Achou spread
                        if m_spr != 0.0: break
                except:
                    pass
                
                if m_spr == 0.0: continue
                
                # Layout do Card
                css_card = "game-card card-live" if is_live else "game-card"
                
                with st.container():
                    st.markdown(f"""<div class="{css_card}">""", unsafe_allow_html=True)
                    
                    # Header: Status e Times
                    c1, c2, c3 = st.columns([3.5, 2, 2.5])
                    
                    status_txt = f"🔴 Q{linfo['period']} • {linfo['clock']}" if is_live and linfo else pd.to_datetime(game.get('commence_time', datetime.now())).strftime('%H:%M')
                    s_txt_a = linfo['s_away'] if is_live and linfo else ""
                    s_txt_h = linfo['s_home'] if is_live and linfo else ""
                    
                    with c1:
                        st.markdown(f"<span class='status-badge'>{status_txt}</span>", unsafe_allow_html=True)
                        st.markdown(f"<div class='team-name'>{a}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='team-name'>{h}</div>", unsafe_allow_html=True)
                    
                    # Scores (Coluna do Meio)
                    with c2:
                        if is_live:
                            st.markdown(f"""
                            <div style='display:flex; flex-direction:column; justify-content:center; height:100%;'>
                                <div class='score-big'>{s_txt_a}</div>
                                <div class='score-big'>{s_txt_h}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Dados & Decisão (Direita)
                    with c3:
                        diff = abs(fair - m_spr)
                        has_val = diff >= 1.5
                        
                        st.markdown(f"""
                        <div style='display:flex; justify-content:space-between; margin-bottom:10px;'>
                            <div><div class='metric-label'>MODELO</div><div class='metric-value' style='color:#38bdf8'>{fair:+.1f}</div></div>
                            <div style='text-align:right'><div class='metric-label'>MERCADO</div><div class='metric-value'>{m_spr:+.1f}</div></div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if has_val:
                            pick = h if fair < m_spr else a
                            line = m_spr if pick == h else -m_spr
                            units = 1.5 if diff > 3 else 0.75
                            val = val_unid * units
                            
                            cols_d = st.columns([2, 1])
                            with cols_d[0]:
                                st.markdown(f"""<div class='bet-button'>APOSTAR R$ {val:.0f}<br><span style='font-size:0.9rem; font-weight:500'>{pick} {line:+.1f}</span></div>""", unsafe_allow_html=True)
                            with cols_d[1]:
                                 if st.button("💾", key=f"s_{h}_{game['id']}", help="Salvar no Histórico"):
                                     save_bet(f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val)
                        else:
                            st.markdown("<div style='text-align:right; margin-top:10px;'><span class='no-value'>Sem Valor Claro</span></div>", unsafe_allow_html=True)

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
