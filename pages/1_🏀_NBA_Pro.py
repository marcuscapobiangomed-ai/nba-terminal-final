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
                
                # Render Card
                css_class = "game-card card-live" if is_live else "game-card"
                clock = f"Q{linfo['period']} {linfo['clock']}" if is_live and linfo else pd.to_datetime(game.get('commence_time', datetime.now())).strftime('%H:%M')
                status_class = "status-live" if is_live else "status-pre"
                
                score_a = linfo['s_away'] if is_live and linfo else "-"
                score_h = linfo['s_home'] if is_live and linfo else "-"
                
                # Constrói HTML do Botão de Aposta
                bet_html = ""
                
                # Só mostra botão se tiver valor real
                if edge >= CONFIG.min_edge_spread:
                    # Quem apostar?
                    # Se Fair (-5) < Mercado (-2), Home é favorito por mais pts que o mercado acha -> Bet Home
                    # Se Fair (-2) > Mercado (-5), Mercado superestima Home -> Bet Away
                    pick = h if fair < m_spr else a
                    line = m_spr if pick == h else -m_spr # Inverte sinal se for away
                    
                    # Calcula Stake com Kelly
                    units = odds_engine.kelly_stake(
                        edge=edge, 
                        odds=1.91, 
                        fraction=CONFIG.kelly_fraction,
                        max_stake=5.0
                    )
                    
                    # Fallback mínimo de unidades se o Kelly der muito baixo mas tem edge
                    if units < 0.1: units = 0.5
                    
                    val_bet = val_unid * units
                    
                    bet_html = f"""
                    <div class="bet-box">
                        <div class="bet-title">VALOR ENCONTRADO ({edge:.1f}pts)</div>
                        <div class="bet-pick">{pick} {line:+.1f}</div>
                        <div style="font-size:0.8rem; color:#a7f3d0;">Apostar R$ {val_bet:.0f} ({units:.1f}u)</div>
                    </div>
                    """
                else:
                    bet_html = """
                    <div style="text-align:center; padding:10px; opacity:0.5; font-size:0.8rem;">
                        Sem Edge Claro
                    </div>
                    """
                
                # Renderiza HTML Único
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
                    
                    {bet_html}
                </div>
                """, unsafe_allow_html=True)
                
                # Botão Save (invisible mas funcional via Streamlit native elements fora do HTML custom)
                if edge >= CONFIG.min_edge_spread:
                     if st.button("💾 Salvar Bet", key=f"save_{game['id']}", help="Registrar na Planilha"):
                         save_bet(CONFIG.bets_history_file, f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, val_bet)
                         st.toast("Aposta Salva!")

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
