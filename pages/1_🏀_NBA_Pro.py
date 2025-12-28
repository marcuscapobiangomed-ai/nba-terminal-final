import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Impor do Core (O Cérebro)
from core.config import get_config
from core import data_fetcher
from core import odds_engine
from core.backoffice import save_bet, load_history

# --- 1. CONFIGURAÇÃO & ESTADO ---
st.set_page_config(page_title="NBA Terminal Pro", page_icon="🏀", layout="wide")

# Carrega Config segura (Suporta Local .env e Cloud Secrets)
try:
    CONFIG = get_config()
except Exception as e:
    st.error(f"Erro de Configuração: {e}")
    st.stop()

# Inicializa Estado
if 'banca' not in st.session_state: st.session_state.banca = CONFIG.default_bankroll
if 'unidade_pct' not in st.session_state: st.session_state.unidade_pct = CONFIG.default_unit_percent

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

# --- 3. INTERFACE PRINCIPAL ---
st.title("🏆 NBA Terminal Pro")

# Sidebar
with st.sidebar:
    st.markdown("### 💰 Bankroll")
    st.session_state.banca = st.number_input("Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    st.markdown(f"**Unidade:** R$ {val_unid:.2f}")
    st.divider()
    st.caption(f"Core v1.0 • UI v13.1 • Season {CONFIG.nba_season}")

# Scan Button
if st.button("🔄 SCAN LIVE MARKET", type="primary", use_container_width=True):
    st.cache_data.clear(); st.rerun()

# --- 4. DATA FETCHING (VIA CORE) ---
# Usando o data_fetcher que tem cache e fallback
news = data_fetcher.get_news(max_items=3)
if news:
    with st.expander("📰 MANCHETES", expanded=False):
        cols = st.columns(3)
        for i, n in enumerate(news):
            with cols[i]: st.markdown(f"<div class='news-card'><div class='news-time'>{n['hora']}</div><div class='news-title'>{n['titulo']}</div></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Busca dados inteligentes
STATS = data_fetcher.get_team_stats(CONFIG.nba_season)
ODDS = data_fetcher.get_odds(CONFIG.odds_api_key) # Passa a chave da API
LIVE = data_fetcher.get_live_scores()

if not ODDS:
    st.info("Mercado Fechado, Limite de API Excedido ou Sem Jogos.")
else:
    # GRID DE JOGOS (2 JOGOS POR LINHA PARA "ENQUADRAMENTO")
    games_list = list(ODDS)
    rows = [games_list[i:i + 2] for i in range(0, len(games_list), 2)]
    
    for row in rows:
        cols = st.columns(2)
        for idx, game in enumerate(row):
            with cols[idx]:
                h, a = game['home_team'], game['away_team']
                
                # Live Info
                linfo = None
                for k, v in LIVE.items():
                    if k in h or h in k: linfo = v; break
                is_live = linfo['live'] if linfo else False
                
                # --- MODELAGEM (O CORAÇÃO DO SISTEMA) ---
                # Busca stats do dicionário
                s_h = data_fetcher.find_team_stats(h, STATS)
                s_a = data_fetcher.find_team_stats(a, STATS)
                
                # Calcula Linha Justa usando Odds Engine
                if s_h and s_a:
                    fair = odds_engine.calculate_fair_spread(
                        home_net_rtg=s_h['net_rtg'], 
                        away_net_rtg=s_a['net_rtg'],
                        home_advantage=CONFIG.home_advantage
                    )
                else:
                    fair = 0.0 # Sem dados suficientes
                
                # --- MERCADO ---
                m_spr = 0.0
                try:
                    # Parse odds usando helper
                    parsed = data_fetcher.parse_market_odds(game)
                    if parsed:
                        m_spr = parsed['spread']
                        # Ajusta sinal se necessário (parse_market_odds já deve retornar correto, mas garantindo ref)
                        # A função parse_market_odds retorna spread do home team
                except: pass
                
                if m_spr == 0.0: continue
                
                # --- DECISÃO (KELLY) ---
                edge = odds_engine.calculate_edge(fair, m_spr)
                
                # --- RENDERIZAÇÃO SEGURA (COMPATIBILIDADE STREAMLIT) ---
                css_card = "game-card card-live" if is_live else "game-card"
                status_class = "status-live" if is_live else "status-pre"
                
                # Prepara componentes visuais
                status_html = f"<span class='{status_class}'>{clock}</span>"
                team_a_html = f"<div class='team-name'>{a}</div>"
                team_h_html = f"<div class='team-name'>{h}</div>"
                
                # HTML Placar
                scores_html = ""
                if is_live:
                    scores_html = f"""
                    <div style='display:flex; flex-direction:column; justify-content:center; gap:5px;'>
                        <div class='score-big' style='background:#1f2937; padding:2px 8px; border-radius:4px; text-align:center; font-weight:800;'>{score_a}</div>
                        <div class='score-big' style='background:#1f2937; padding:2px 8px; border-radius:4px; text-align:center; font-weight:800;'>{score_h}</div>
                    </div>
                    """
                
                # Decisão / Botão
                decision_html = ""
                has_val = edge >= CONFIG.min_edge_spread
                
                if has_val:
                    pick = h if fair < m_spr else a
                    line = m_spr if pick == h else -m_spr
                    
                    # Recalcula Kelly
                    units = odds_engine.kelly_stake(edge, 1.91, CONFIG.kelly_fraction, 5.0)
                    if units < 0.1: units = 0.5
                    val_bet = val_unid * units
                    
                    bet_val_txt = f"APOSTAR R$ {val_bet:.0f}"
                    bet_pick_txt = f"{pick} {line:+.1f}"
                    
                    decision_html = f"""
                    <div class='bet-box'>
                        <div class='bet-title' style='color:#34d399; font-size:0.7rem;'>VALOR ENCONTRADO ({edge:.1f}pts)</div>
                        <div style='font-weight:bold; color:white;'>{bet_pick_txt}</div>
                        <div style='font-size:0.8rem; color:#a7f3d0;'>{bet_val_txt} ({units:.1f}u)</div>
                    </div>
                    """
                else:
                    decision_html = "<div style='text-align:right; margin-top:20px; opacity:0.5; font-size:0.75rem;'>Sem Valor</div>"

                # Renderiza Container do Card
                with st.container():
                    # Abre container visual (div wrapper)
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    
                    # Layout Colunas Internas
                    c1, c2, c3 = st.columns([3.5, 1.5, 3])
                    
                    with c1:
                        # Times e Status
                        st.markdown(f"""
                        <div style='margin-bottom:8px'>{status_html}</div>
                        {team_a_html}
                        {team_h_html}
                        """, unsafe_allow_html=True)
                    
                    with c2:
                        # Placares (centralizados verticalmente pelo flexbox css do card ou bruts force aqui)
                        st.markdown(scores_html, unsafe_allow_html=True)
                        
                    with c3:
                        # Métricas
                        st.markdown(f"""
                        <div class="data-grid" style="border:none; margin-top:0; padding-top:0;">
                            <div class="metric-col">
                                <div class="metric-lbl">MODELO</div>
                                <div class="metric-val" style='color:#38bdf8'>{fair:+.1f}</div>
                            </div>
                            <div class="metric-col">
                                <div class="metric-lbl">MERCADO</div>
                                <div class="metric-val">{m_spr:+.1f}</div>
                            </div>
                        </div>
                        {decision_html}
                        """, unsafe_allow_html=True)
                        
                        # Botão Nativo (Salva vidas)
                        if has_val:
                            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                            if st.button("💾 REGISTRAR", key=f"btn_{game['id']}", help="Salvar na Planilha"):
                                save_bet(CONFIG.bets_history_file, f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val_bet)
                                st.toast("✅ Aposta Registrada!")

                    # Fecha div do card
                    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. RESULTADOS (BACKOFFICE) ---
st.divider()
st.header("📊 Performance Recente")
try:
    df_hist = load_history(CONFIG.bets_history_file)
    if not df_hist.empty:
        df_hist['Acumulado'] = df_hist['Lucro'].cumsum()
        st.area_chart(df_hist, x='Data', y='Acumulado', color='#38bdf8')
    else:
        st.caption("Nenhuma aposta registrada ainda.")
except:
    st.caption("Histórico indisponível.")
