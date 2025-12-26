"""
NBA Terminal Pro v12.0 - Modular Edition
Versão refatorada com arquitetura modular e modelo matemático melhorado
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports dos módulos core
from core.config import get_config, STAR_PLAYERS, REBOUNDERS
from core.data_fetcher import (
    get_team_stats, get_odds, get_live_scores, get_news,
    find_team_stats, parse_market_odds
)
from core.odds_engine import (
    calculate_fair_spread, calculate_fair_total_simple,
    calculate_edge, get_stake_units, four_factors_advantage
)
from core.backoffice import (
    load_history, save_bet, update_results, calculate_metrics, get_cumulative_profit
)

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="NBA Terminal Pro v12", page_icon="🏆", layout="wide")

# Carrega configuração do .env
try:
    CONFIG = get_config()
except ValueError as e:
    st.error(str(e))
    st.stop()

# --- 2. CSS VISUAL (NEON DARK PRO) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Inter', 'Roboto', sans-serif; }
    
    /* Animação Live */
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(0, 255, 0, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); } }
    
    .live-dot { display: inline-block; width: 10px; height: 10px; background-color: #ff0000; border-radius: 50%; margin-right: 8px; animation: blink 1.5s infinite; box-shadow: 0 0 8px #ff0000; }
    
    /* Cards */
    .game-card { background: linear-gradient(145deg, #1c1e26, #22252e); border-radius: 12px; padding: 18px; margin-bottom: 14px; border-left: 4px solid #444; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: transform 0.2s, box-shadow 0.2s; }
    .game-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }
    .card-live { border-left: 4px solid #ff4b4b; background: linear-gradient(145deg, #251a1a, #2d1f1f); }
    .card-value { border-left: 4px solid #00ff88; }
    
    /* Badges */
    .stake-badge { background: linear-gradient(135deg, #00ff88, #00cc6a); color: #000; font-weight: 700; padding: 4px 12px; border-radius: 6px; font-size: 0.85em; animation: pulse 2s infinite; }
    .edge-badge { background-color: #4da6ff; color: #000; font-weight: 600; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; }
    
    /* Props */
    .prop-card { background-color: #25262b; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #333; transition: border-color 0.2s; }
    .prop-card:hover { border-color: #00ffaa; }
    .prop-good { border-left: 3px solid #00ffaa; }
    
    /* Métricas */
    .metric-box { background: linear-gradient(145deg, #1a1c24, #22252e); padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #333; }
    .metric-label { font-size: 0.7em; color: #888; text-transform: uppercase; letter-spacing: 1.5px; }
    .metric-val { font-size: 1.3em; font-weight: 700; color: #fff; }
    .metric-positive { color: #00ff88; }
    .metric-negative { color: #ff4b4b; }
    
    /* News */
    .news-card { background-color: #262730; padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid #4da6ff; font-size: 0.9em; }
    .news-alert { border-left: 3px solid #ff4b4b; background-color: #2d1b1b; }
    
    /* Inputs */
    div[data-baseweb="select"] > div { background-color: #262730; border-color: #444; }
    </style>
""", unsafe_allow_html=True)

# --- 3. ESTADO DA SESSÃO ---
if 'banca' not in st.session_state:
    st.session_state.banca = CONFIG.default_bankroll
if 'unidade_pct' not in st.session_state:
    st.session_state.unidade_pct = CONFIG.default_unit_percent

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.header("💰 Gestão de Banca")
    st.session_state.banca = st.number_input(
        "Banca (R$)", 
        value=st.session_state.banca, 
        step=100.0,
        min_value=100.0
    )
    st.session_state.unidade_pct = st.slider(
        "Unidade (%)", 
        0.5, 5.0, 
        st.session_state.unidade_pct, 
        step=0.5
    )
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Valor 1 Unidade</div>
        <div class="metric-val" style="color: #4da6ff;">R$ {val_unid:.2f}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Quick Stats
    df_hist = load_history()
    if not df_hist.empty:
        metrics = calculate_metrics(df_hist)
        st.markdown(f"""
        <div style="font-size: 0.85em; color: #aaa;">
            <b>📊 Quick Stats</b><br>
            Apostas: {metrics.total_bets} ({metrics.pending_bets} pendentes)<br>
            Winrate: <span style="color: {'#00ff88' if metrics.winrate > 50 else '#ff4b4b'}">{metrics.winrate:.1f}%</span><br>
            ROI: <span style="color: {'#00ff88' if metrics.roi > 0 else '#ff4b4b'}">{metrics.roi:+.1f}%</span>
        </div>
        """, unsafe_allow_html=True)

# --- 5. FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=86400)
def cached_team_stats():
    return get_team_stats(CONFIG.nba_season)

@st.cache_data(ttl=60)
def cached_odds():
    return get_odds()

@st.cache_data(ttl=20)
def cached_live_scores():
    return get_live_scores()

@st.cache_data(ttl=600)
def cached_news():
    return get_news()


def generate_prop_insights(home, away, pace_proj, mkt_total, stats_h, stats_a):
    """Gera insights para props baseado em correlações"""
    insights = []
    
    is_fast = pace_proj > CONFIG.fast_pace_threshold
    h_bad_def = stats_h.get('def_rtg', 110) > CONFIG.bad_defense_threshold
    a_bad_def = stats_a.get('def_rtg', 110) > CONFIG.bad_defense_threshold
    
    # Props de pontos
    for star in STAR_PLAYERS.get(away, []):
        if is_fast and h_bad_def:
            insights.append({
                "player": star,
                "type": "OVER PONTOS",
                "reason": f"Ritmo Alto ({pace_proj:.0f}) + {home} com defesa fraca (DefRtg {stats_h.get('def_rtg', 110):.0f})"
            })
    
    for star in STAR_PLAYERS.get(home, []):
        if is_fast and a_bad_def:
            insights.append({
                "player": star,
                "type": "OVER PONTOS",
                "reason": f"Ritmo Alto ({pace_proj:.0f}) + {away} com defesa fraca (DefRtg {stats_a.get('def_rtg', 110):.0f})"
            })
    
    # Props de rebotes
    if stats_h.get('efg', 0.55) < 0.52 and stats_a.get('efg', 0.55) < 0.52:
        all_players = STAR_PLAYERS.get(home, []) + STAR_PLAYERS.get(away, [])
        for player in all_players:
            if player in REBOUNDERS:
                insights.append({
                    "player": player,
                    "type": "OVER REBOTES",
                    "reason": "Baixa eficiência (eFG% < 52%) = mais erros = mais rebotes"
                })
    
    return insights


# --- 6. INTERFACE PRINCIPAL ---
st.title("🏆 NBA Terminal Pro v12.0")
st.caption("Arquitetura modular | Modelo matemático melhorado | Paper Trading")

# Abas Principais
tab_main, tab_backoffice = st.tabs(["⚡ TERMINAL DE OPERAÇÕES", "💼 BACKOFFICE & ROI"])

# === TAB PRINCIPAL ===
with tab_main:
    col_title, col_btn = st.columns([5, 1])
    with col_btn:
        if st.button("🔴 SCAN", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # News Ticker
    news = cached_news()
    if news:
        with st.expander("📰 BREAKING NEWS", expanded=True):
            cols = st.columns(min(3, len(news)))
            for i, n in enumerate(news):
                css = "news-alert" if n.get('alerta') else "news-card"
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div class="{css}">
                        <b style="color:#ccc">{n['hora']}</b> {n['titulo']}
                    </div>
                    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Carrega Dados
    TEAM_STATS = cached_team_stats()
    ODDS = cached_odds()
    LIVE_SCORES = cached_live_scores()
    
    # Sub-Abas
    subtab_spread, subtab_totals, subtab_props = st.tabs([
        "📊 SPREAD & TÁTICA", 
        "⏱️ TOTALS (O/U)", 
        "🎯 PROPS CORRELATION"
    ])
    
    if not ODDS or isinstance(ODDS, dict):
        st.info("🔒 Mercado fechado ou limite de API excedido.")
    else:
        props_collection = []
        
        for game in ODDS:
            home = game['home_team']
            away = game['away_team']
            
            # Dados Live
            live_info = LIVE_SCORES.get(home, {})
            is_live = live_info.get('live', False)
            
            # Stats dos times
            s_h = find_team_stats(home, TEAM_STATS)
            s_a = find_team_stats(away, TEAM_STATS)
            
            # Odds de mercado
            market = parse_market_odds(game)
            if market['spread'] == 0.0:
                continue
            
            # === CÁLCULOS DO MODELO ===
            
            # Net Rating real
            home_net = s_h.get('net_rtg', s_h.get('off_rtg', 110) - s_h.get('def_rtg', 110))
            away_net = s_a.get('net_rtg', s_a.get('off_rtg', 110) - s_a.get('def_rtg', 110))
            
            # Fair Spread
            fair_spread = calculate_fair_spread(home_net, away_net, CONFIG.home_advantage)
            
            # Pace e Total
            avg_pace = (s_h.get('pace', 100) + s_a.get('pace', 100)) / 2
            pace_display = avg_pace
            proj_total = calculate_fair_total_simple(avg_pace, 2.2)
            
            # Ajuste para jogos ao vivo
            if is_live and live_info.get('period', 0) > 0:
                period = live_info['period']
                try:
                    mins_played = ((period - 1) * 12) + (12 - int(live_info.get('clock', '12:00').split(':')[0]))
                except:
                    mins_played = 1
                
                if mins_played > 5:
                    curr_pts = live_info.get('score_home', 0) + live_info.get('score_away', 0)
                    live_pace = (curr_pts / mins_played) * 48
                    weight = min(1.0, (mins_played / 40) ** 0.8)
                    pace_display = (avg_pace * (1 - weight)) + (live_pace * weight)
                    proj_total = (curr_pts / mins_played) * 48
            
            # Edge calculations
            edge_spread = calculate_edge(fair_spread, market['spread'])
            edge_total = calculate_edge(proj_total, market['total']) if market['total'] > 0 else 0
            
            # Four Factors
            ff = four_factors_advantage(
                s_h.get('efg', 0.54), s_h.get('tov', 0.14), s_h.get('orb', 0.25), s_h.get('ftr', 0.25),
                s_a.get('efg', 0.54), s_a.get('tov', 0.14), s_a.get('orb', 0.25), s_a.get('ftr', 0.25)
            )
            
            # Props
            game_props = generate_prop_insights(home, away, pace_display, market['total'], s_h, s_a)
            if game_props:
                props_collection.append({"game": f"{away} @ {home}", "props": game_props})
            
            # === RENDERIZAÇÃO SPREAD ===
            with subtab_spread:
                css_class = "card-live" if is_live else ("card-value" if edge_spread >= CONFIG.min_edge_spread else "game-card")
                
                with st.container():
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([3, 2, 2])
                    
                    # Status
                    if is_live:
                        status = f"<span class='live-dot'></span>Q{live_info.get('period', 1)} {live_info.get('clock', '')}"
                        score = f"{live_info.get('score_away', 0)} - {live_info.get('score_home', 0)}"
                    else:
                        status = pd.to_datetime(game['commence_time']).strftime('%H:%M')
                        score = "vs"
                    
                    with c1:
                        st.markdown(f"""
                        <b>{away}</b> {score} <b>{home}</b><br>
                        <span style="color:#aaa">{status}</span>
                        """, unsafe_allow_html=True)
                        
                        # Four Factors summary
                        if not is_live:
                            efg_color = "#00ffaa" if ff['efg_diff'] > 0 else "#ff4b4b"
                            st.markdown(f"""
                            <span style="font-size:0.8em">
                                eFG%: <b style="color:{efg_color}">{ff['efg_diff']:+.1%}</b> | 
                                4F Adv: <b>{ff['home_advantage']:+.2f}</b>
                            </span>
                            """, unsafe_allow_html=True)
                    
                    with c2:
                        st.markdown(f"""
                        <div style="text-align:center">
                            <small class="metric-label">MODELO vs MERCADO</small><br>
                            <b style="color:#4da6ff; font-size:1.2em">{fair_spread:+.1f}</b>
                            <small style="color:#666"> vs </small>
                            <b style="font-size:1.1em">{market['spread']:+.1f}</b><br>
                            <small style="color:#888">Edge: {edge_spread:.1f} pts</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with c3:
                        if edge_spread >= CONFIG.min_edge_spread:
                            pick = home if fair_spread < market['spread'] else away
                            line = market['spread'] if pick == home else -market['spread']
                            units = get_stake_units(edge_spread, CONFIG.min_edge_spread)
                            val_bet = val_unid * units
                            
                            c_txt, c_btn = st.columns([2, 1])
                            with c_txt:
                                st.markdown(f"""
                                <div style="text-align:right">
                                    <span class="stake-badge">R$ {val_bet:.0f}</span><br>
                                    <b>{pick}</b> {line:+.1f}
                                </div>
                                """, unsafe_allow_html=True)
                            with c_btn:
                                if st.button("📝", key=f"s_{game['id']}", help=f"Registrar {pick} {line:+.1f}"):
                                    save_bet(f"{away} @ {home}", "Spread", f"{pick} {line:+.1f}", 1.91, val_bet)
                                    st.toast(f"✅ Registrado: {pick} {line:+.1f}")
                        else:
                            st.markdown("<div style='text-align:right;color:#555'>Linha Justa</div>", unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # === RENDERIZAÇÃO TOTALS ===
            with subtab_totals:
                css_class = "card-live" if is_live else ("card-value" if edge_total >= CONFIG.min_edge_total else "game-card")
                
                with st.container():
                    st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns([3, 2, 2])
                    
                    with c1:
                        st.markdown(f"""
                        <b>{away} @ {home}</b><br>
                        <span style="color:#aaa">Pace: {pace_display:.1f}</span>
                        """, unsafe_allow_html=True)
                    
                    with c2:
                        st.markdown(f"""
                        <div style="text-align:center">
                            <small class="metric-label">PROJEÇÃO vs LINHA</small><br>
                            <b style="color:#4da6ff; font-size:1.2em">{proj_total:.0f}</b>
                            <small style="color:#666"> vs </small>
                            <b style="font-size:1.1em">{market['total']}</b>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with c3:
                        if edge_total >= CONFIG.min_edge_total and market['total'] > 0:
                            trend = "OVER" if proj_total > market['total'] else "UNDER"
                            color = "#00ffaa" if trend == "OVER" else "#ff4b4b"
                            units = get_stake_units(edge_total, CONFIG.min_edge_total)
                            val_bet = val_unid * units
                            
                            c_txt, c_btn = st.columns([2, 1])
                            with c_txt:
                                st.markdown(f"""
                                <div style="text-align:right">
                                    <span class="stake-badge" style="background:{color}">{trend}</span><br>
                                    <small>{abs(proj_total - market['total']):.1f} pts diff</small>
                                </div>
                                """, unsafe_allow_html=True)
                            with c_btn:
                                if st.button("📝", key=f"t_{game['id']}", help=f"Registrar {trend} {market['total']}"):
                                    save_bet(f"{away} @ {home}", "Total", f"{trend} {market['total']}", 1.91, val_bet)
                                    st.toast(f"✅ Registrado: {trend} {market['total']}")
                        else:
                            st.markdown("<div style='text-align:right;color:#555'>Sem Valor</div>", unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # === RENDERIZAÇÃO PROPS ===
        with subtab_props:
            if not props_collection:
                st.info("🎯 Sem correlações fortes no momento (jogos lentos ou defesas boas)")
            else:
                for item in props_collection:
                    st.markdown(f"**{item['game']}**")
                    cols = st.columns(min(3, len(item['props'])))
                    for idx, prop in enumerate(item['props']):
                        with cols[idx % len(cols)]:
                            st.markdown(f"""
                            <div class="prop-card prop-good">
                                <b>🎯 {prop['player']}</b><br>
                                <span style="color:#00ffaa">{prop['type']}</span><br>
                                <small style="color:#aaa">{prop['reason']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    st.divider()

# === TAB BACKOFFICE ===
with tab_backoffice:
    st.header("💼 Auditoria de Performance")
    
    df = load_history()
    
    if df.empty:
        st.info("📝 Nenhuma aposta registrada. Use o botão 📝 no Terminal para salvar entradas.")
    else:
        # Editor de Resultados
        st.caption("Defina o resultado (Green/Red/Void) e clique em Salvar para calcular lucro.")
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            column_config={
                "Resultado": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Pendente", "Green", "Red", "Void"],
                    required=True,
                    width="small"
                ),
                "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "Lucro": st.column_config.NumberColumn("Lucro (R$)", format="R$ %.2f"),
                "Odd": st.column_config.NumberColumn("Odd", format="%.2f", width="small")
            },
            key="history_editor",
            use_container_width=True
        )
        
        col_save, col_export = st.columns([1, 1])
        with col_save:
            if st.button("💾 Salvar & Calcular Lucro", type="primary", use_container_width=True):
                updated = update_results(edited_df)
                st.success("✅ Resultados atualizados!")
                st.rerun()
        
        with col_export:
            if st.button("📊 Exportar Excel", use_container_width=True):
                from core.backoffice import export_to_excel
                if export_to_excel(df):
                    st.success("✅ Exportado para bets_export.xlsx")
        
        st.divider()
        
        # Dashboard de Métricas
        metrics = calculate_metrics(df)
        
        if metrics.completed_bets > 0:
            k1, k2, k3, k4 = st.columns(4)
            
            with k1:
                delta_color = "normal" if metrics.total_profit >= 0 else "inverse"
                st.metric(
                    "Lucro Líquido",
                    f"R$ {metrics.total_profit:.2f}",
                    delta=f"R$ {metrics.total_profit:.2f}",
                    delta_color=delta_color
                )
            
            with k2:
                st.metric(
                    "ROI",
                    f"{metrics.roi:.1f}%",
                    delta=f"{metrics.roi:+.1f}%",
                    delta_color="normal" if metrics.roi >= 0 else "inverse"
                )
            
            with k3:
                st.metric(
                    "Winrate",
                    f"{metrics.winrate:.1f}%",
                    delta=f"{metrics.greens}/{metrics.completed_bets}"
                )
            
            with k4:
                streak_text = f"+{metrics.current_streak}" if metrics.current_streak > 0 else str(metrics.current_streak)
                st.metric(
                    "Streak Atual",
                    streak_text,
                    delta="🔥" if metrics.current_streak > 2 else ("❄️" if metrics.current_streak < -2 else "")
                )
            
            # Gráfico de Curva de Lucro
            df['Acumulado'] = get_cumulative_profit(df)
            
            fig = px.area(
                df,
                y='Acumulado',
                title='📈 Curva de Crescimento da Banca',
                labels={'Acumulado': 'Lucro Acumulado (R$)', 'index': 'Aposta #'}
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                hovermode='x unified'
            )
            fig.update_traces(
                fill='tozeroy',
                line_color='#00ff88' if metrics.total_profit >= 0 else '#ff4b4b'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⏳ Marque alguns resultados como Green ou Red para ver as métricas.")

# Footer
st.divider()
st.caption(f"NBA Terminal Pro v12.0 | Season {CONFIG.nba_season} | 🔐 API Key protegida")
