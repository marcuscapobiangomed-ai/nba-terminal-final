
import streamlit as st
import pandas as pd
import requests
import feedparser
import os
import textwrap # <--- A SOLUÇÃO MÁGICA
import plotly.express as px
from datetime import datetime
from deep_translator import GoogleTranslator
from nba_api.stats.endpoints import leaguedashteamstats
from pathlib import Path
from core.player_props import PlayerPropsEngine

# --- 1. CONFIGURAÇÃO & ESTADO ---
st.set_page_config(page_title="NBA Terminal Pro", page_icon="🏀", layout="wide")
API_KEY = "e6a32983f406a1fbf89fda109149ac15"
# Define caminho absoluto para o arquivo na raiz do projeto
HISTORY_FILE = Path(__file__).parent.parent / "bets_history.csv"

if 'banca' not in st.session_state: st.session_state.banca = 1000.0
if 'unidade_pct' not in st.session_state: st.session_state.unidade_pct = 1.0

# --- 2. CSS "GLASS-NEON" ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&family=Roboto+Mono:wght@500;700&display=swap');
    
    .stApp { background: radial-gradient(circle at top left, #1e293b, #0f172a); font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #0b1120; border-right: 1px solid #1e293b; }
    
    .game-card {
        background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px;
        margin-bottom: 24px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2); overflow: hidden;
    }
    .card-live { border-left: 4px solid #ef4444; }
    
    .card-header {
        padding: 20px 24px; background: rgba(15, 23, 42, 0.4);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        display: flex; justify-content: space-between; align-items: center;
    }
    
    .status-badge {
        font-family: 'Roboto Mono', monospace; font-size: 0.75rem; font-weight: 800;
        color: #ffffff; background: #334155; padding: 4px 12px; border-radius: 6px; border: 1px solid #475569;
    }
    .live-badge { color: #fee2e2; border-color: #991b1b; background: #7f1d1d; }

    .team-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; width: 100%; }
    .team-name { font-size: 1.2rem; font-weight: 800; color: #ffffff; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    .team-score { font-family: 'Roboto Mono', monospace; font-size: 1.5rem; font-weight: 800; color: #ffffff; text-shadow: 0 0 10px rgba(255,255,255,0.2); }

    .card-body { padding: 20px 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .metric-col { background: rgba(0,0,0,0.3); border-radius: 10px; padding: 12px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
    .metric-lbl { font-size: 0.75rem; color: #cbd5e1; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px; }
    .metric-val { font-size: 1.25rem; color: #ffffff; font-weight: 700; font-family: 'Roboto Mono'; }
    .val-highlight { color: #38bdf8; text-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }

    .card-action {
        padding: 16px 24px; background: rgba(34, 197, 94, 0.1);
        border-top: 1px solid rgba(34, 197, 94, 0.2); display: flex; justify-content: space-between; align-items: center;
    }
    .value-tag { color: #4ade80; font-weight: 800; font-size: 0.85rem; display: flex; align-items: center; gap: 6px; }
    .bet-info { font-size: 1.1rem; color: #ffffff; font-weight: 900; }

    .news-item { background: #1e293b; border-radius: 8px; padding: 12px; margin-bottom: 8px; border-left: 3px solid #3b82f6; }
    .bankroll-card { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 1px solid #334155; border-radius: 12px; padding: 16px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 3. FUNÇÕES ---
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

with st.sidebar:
    st.markdown("### 💰 Gestão de Banca")
    st.session_state.banca = st.number_input("Banca Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    st.markdown("---")
    st.markdown(f"<div class='bankroll-card'><div style='color:#64748b;font-size:0.75rem;font-weight:700'>VALOR 1 UNIDADE</div><div style='color:#38bdf8;font-size:1.6rem;font-weight:800'>R$ {val_unid:.2f}</div></div>", unsafe_allow_html=True)

# Inicializa Engine
if 'props_engine' not in st.session_state:
    st.session_state.props_engine = PlayerPropsEngine()

tab_ops, tab_props, tab_adm = st.tabs(["⚡ MERCADO AO VIVO", "🎯 SMART PROPS", "📊 MINHA CARTEIRA"])

with tab_props:
    st.markdown("### 🤖 Projeção de Jogadores (Beta)")
    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
        p_name = st.text_input("Nome do Jogador:", placeholder="Ex: LeBron James, Curry...")
    with col_p2:
        opp_team = st.text_input("Contra (Sigla):", placeholder="Ex: GSW, BOS...")

    if p_name and opp_team and st.button("🔮 Calcular Projeção", type="primary"):
        with st.spinner(f"Analisando dados de {p_name}..."):
            proj = st.session_state.props_engine.get_projection(p_name, opp_team.upper())
            
        if proj:
            html_card = textwrap.dedent(f"""
            <div class="game-card" style="padding: 20px; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: 800; color: #fff; margin-bottom: 10px;">
                    {proj['player']} <span style="color:#64748b; font-size:1rem;">vs {proj['opponent']}</span>
                </div>
                
                <div style="display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 20px;">
                    <div style="text-align: right;">
                        <div style="font-size: 0.8rem; color: #94a3b8;">MÉDIA TEMP</div>
                        <div style="font-size: 1.2rem; font-weight: 700; color: #e2e8f0;">{proj['season_avg']}</div>
                    </div>
                    <div style="width: 1px; height: 40px; background: #334155;"></div>
                    <div style="text-align: left;">
                        <div style="font-size: 0.8rem; color: #38bdf8;">ÚLT. 5 JOGOS</div>
                        <div style="font-size: 1.2rem; font-weight: 700; color: #fff;">{proj['last_5_avg']}</div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 0.9rem; color: #cbd5e1; letter-spacing: 0.1em; font-weight: 700;">PROJEÇÃO FINAL</div>
                    <div style="font-size: 3rem; font-weight: 900; color: #4ade80; text-shadow: 0 0 20px rgba(74, 222, 128, 0.3);">
                        {proj['projection']} <span style="font-size: 1rem; color: #fff;">PTS</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                        Ajuste Matchup: <span style="color: {'#ef4444' if proj['matchup_adj'] < 0 else '#4ade80'}">{proj['matchup_adj']:+.1f}</span>
                    </div>
                </div>
            </div>
            """)
            st.markdown(html_card, unsafe_allow_html=True)
            
            if st.button(f"📥 Registrar Over {proj['projection']}", key="btn_prop"):
                save_bet(f"{proj['player']} (Props)", "Over Pts", f"Over {proj['projection']}", 1.90, st.session_state.banca * 0.01)
        else:
            st.error("Jogador não encontrado ou dados insuficientes.")

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
    
    STATS = get_advanced_team_stats()
    ODDS = get_odds(API_KEY)
    LIVE = get_live_scores()
    
    if not ODDS or isinstance(ODDS, dict):
        st.info("Mercado Fechado ou Sem Jogos.")
    else:
        col_1, col_2 = st.columns(2)
        for idx, game in enumerate(ODDS):
            h, a = game['home_team'], game['away_team']
            curr_col = col_1 if idx % 2 == 0 else col_2
            
            linfo = None
            for k, v in LIVE.items():
                if k in h or h in k: linfo = v; break
            is_live = linfo['live'] if linfo else False
            
            if is_live:
                badge_html = f"<span class='status-badge live-badge'>🔴 Q{linfo['period']} {linfo['clock']}</span>"
                s_a_txt = linfo['s_away']; s_h_txt = linfo['s_home']; css_live = "card-live"
            else:
                badge_html = f"<span class='status-badge'>{pd.to_datetime(game['commence_time']).strftime('%H:%M')}</span>"
                s_a_txt = "-"; s_h_txt = "-"; css_live = ""

            s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
            s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
            fair = -((s_h['net_rtg'] + 2.5) - s_a['net_rtg'])
            
            m_spr = 0.0
            for s in game.get('bookmakers', []):
                p = s['markets'][0]['outcomes'][0]['point']
                m_spr = -p if s['markets'][0]['outcomes'][0]['name'] != h else p; break
            if m_spr == 0.0: continue
            
            diff = abs(fair - m_spr)
            has_val = diff >= 1.5
            
            # --- CORREÇÃO FINAL: TEXTWRAP.DEDENT ---
            # Remove qualquer indentação acidental antes de renderizar
            html_card = textwrap.dedent(f"""
                <div class="game-card {css_live}">
                    <div class="card-header">
                        <div>{badge_html}</div>
                        <div style="text-align:right">
                            <div class="team-row"><span class="team-name">{a}</span> <span class="team-score">{s_a_txt}</span></div>
                            <div class="team-row"><span class="team-name">{h}</span> <span class="team-score">{s_h_txt}</span></div>
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
            """).strip()
            
            with curr_col:
                with st.container():
                    st.markdown(html_card, unsafe_allow_html=True)
                    
                    if has_val:
                        pick = h if fair < m_spr else a
                        line = m_spr if pick == h else -m_spr
                        units = 1.5 if diff > 3 else 0.75
                        val = val_unid * units
                        
                        html_footer = textwrap.dedent(f"""
                            <div class="card-action">
                                <div>
                                    <div class="value-tag">✨ VALOR ENCONTRADO</div>
                                    <div class="bet-info">{pick} {line:+.1f}</div>
                                </div>
                            </div>
                        """).strip()
                        st.markdown(html_footer, unsafe_allow_html=True)
                        
                        if st.button(f"📥 REGISTRAR (R$ {val:.0f})", key=f"b_{h}", type="secondary", use_container_width=True):
                             save_bet(f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val)
                    else:
                         st.markdown("""<div style="padding:15px; text-align:center; color:#475569; font-size:0.8rem; font-style:italic;">Sem oportunidade de valor</div>""", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

with tab_adm:
    st.subheader("📈 Performance da Carteira")
    df = load_history()
    if not df.empty:
        edited = st.data_editor(
            df, num_rows="dynamic", key="editor",
            column_config={"Resultado": st.column_config.SelectboxColumn("Status", options=["Pendente","Green","Red"]), "Lucro": st.column_config.NumberColumn("Lucro (R$)", format="%.2f")},
            hide_index=True
        )
        if st.button("💾 Salvar Alterações"):
            for i, r in edited.iterrows():
                if r['Resultado'] == 'Green': edited.at[i, 'Lucro'] = r['Valor'] * 0.91
                elif r['Resultado'] == 'Red': edited.at[i, 'Lucro'] = -r['Valor']
            edited.to_csv(HISTORY_FILE, index=False); st.rerun()
            
        finalizadas = edited[edited['Resultado']!='Pendente']
        if not finalizadas.empty:
            edited['Acumulado'] = edited['Lucro'].cumsum()
            fig = px.area(edited, x=edited.index, y='Acumulado', title='Crescimento da Banca (R$)', template='plotly_dark')
            fig.update_traces(line_color='#38bdf8', fill_color='rgba(56, 189, 248, 0.1)')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            roi = (finalizadas['Lucro'].sum() / finalizadas['Valor'].sum()) * 100
            k1, k2, k3 = st.columns(3)
            k1.metric("Lucro Liq.", f"R$ {finalizadas['Lucro'].sum():.2f}")
            k2.metric("ROI", f"{roi:.1f}%")
            k3.metric("Fechadas", len(finalizadas))
    else:
        st.info("Nenhuma aposta registrada ainda.")
