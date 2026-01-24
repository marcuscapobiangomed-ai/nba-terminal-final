import sys
import os
from pathlib import Path

# --- FIX DE IMPORTAÇÃO (STREAMLIT CLOUD) ---
# Adiciona o diretório raiz (../) ao sys.path para garantir que 'core' seja encontrado
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.dirname(current_dir)
    if root_path not in sys.path:
        sys.path.append(root_path)
    # Fallback: Adiciona também o diretório atual e '..' relativo
    sys.path.append(os.path.join(current_dir, '..'))
except Exception as e:
    print(f"Erro no Path Fix: {e}")

import streamlit as st
import pandas as pd
import textwrap
import plotly.express as px
from datetime import datetime

# --- CARREGA VARIÁVEIS DE AMBIENTE ---
from dotenv import load_dotenv
load_dotenv()

# --- IMPORTS DO CORE ---
from core.data_fetcher import get_team_stats, get_odds, get_live_scores, get_news
from core.player_props import PlayerPropsEngine
from core.star_impact import get_team_stars
# --- MIGRAÇÃO GOOGLE SHEETS ---
# Substituindo core.database por core.sheets_db
from core.sheets_db import save_bet as db_save_bet, load_history as db_load_history, update_bet_result

# --- 1. CONFIGURAÇÃO & ESTADO ---
st.set_page_config(page_title="NBA Terminal Pro", page_icon="🏀", layout="wide")

# Carrega variáveis de ambiente
load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")

# Banco de dados agora é Google Sheets (não precisa de init local)

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
    return db_load_history()

def save_bet(jogo, tipo, aposta, odd, valor):
    if db_save_bet(jogo, tipo, aposta, odd, valor):
        st.toast(f"✅ Registrado: {aposta}")
    else:
        st.error("Erro ao registrar aposta!")

# --- 4. INTERFACE ---
st.title("🏆 NBA Terminal Pro")

with st.sidebar:
    st.markdown("### 💰 Gestão de Banca")
    st.session_state.banca = st.number_input("Banca Total (R$)", value=st.session_state.banca, step=100.0)
    st.session_state.unidade_pct = st.slider("Unidade (%)", 0.5, 5.0, st.session_state.unidade_pct, step=0.5)
    val_unid = st.session_state.banca * (st.session_state.unidade_pct / 100)
    st.markdown("---")
    st.markdown(f"<div class='bankroll-card'><div style='color:#64748b;font-size:0.75rem;font-weight:700'>VALOR 1 UNIDADE</div><div style='color:#38bdf8;font-size:1.6rem;font-weight:800'>R$ {val_unid:.2f}</div></div>", unsafe_allow_html=True)

    # Status Conexão
    st.markdown("---")
    try:
        db_load_history()
        st.caption("🟢 Conectado ao Google Sheets")
    except Exception as e:
        st.error("🔴 Offline: Verifique segredos")


# Inicializa Engine
if 'props_engine' not in st.session_state:
    st.session_state.props_engine = PlayerPropsEngine()

tab_ops, tab_props, tab_adm = st.tabs(["⚡ MERCADO AO VIVO", "🎯 SMART PROPS", "📊 MINHA CARTEIRA"])

with tab_props:
    st.markdown("### 🤖 Projeção de Jogadores (Beta)")
    col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
    with col_p1:
        p_name = st.text_input("Nome do Jogador:", placeholder="Ex: LeBron James...")
    with col_p2:
        opp_team = st.text_input("Contra (Sigla):", placeholder="Ex: GSW...")
    with col_p3:
        stat_type = st.selectbox("Estatística:", ["PTS", "REB", "AST", "PRA", "3PM"])

    if p_name and opp_team and st.button("🔮 Calcular Projeção", type="primary"):
        with st.spinner(f"Analisando {stat_type} de {p_name}..."):
            proj = st.session_state.props_engine.get_projection(p_name, opp_team.upper(), stat_type)
            
        if proj:
            # Determine Color based on Trend
            trend_color = "#4ade80" if proj['last_5_avg'] > proj['season_avg'] else "#facc15"
            
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
                        <div style="font-size: 0.8rem; color: {trend_color};">ÚLT. 5 JOGOS</div>
                        <div style="font-size: 1.2rem; font-weight: 700; color: #fff;">{proj['last_5_avg']}</div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 0.9rem; color: #cbd5e1; letter-spacing: 0.1em; font-weight: 700;">PROJEÇÃO FINAL</div>
                    <div style="font-size: 3rem; font-weight: 900; color: #4ade80; text-shadow: 0 0 20px rgba(74, 222, 128, 0.3);">
                        {proj['projection']} <span style="font-size: 1rem; color: #fff;">{proj['stat_type']}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #64748b; margin-top: 5px;">
                        Ajuste Matchup: <span style="color: {'#ef4444' if proj['matchup_adj'] < 0 else '#4ade80'}">{proj['matchup_adj']:+.1f}</span>
                    </div>
                </div>
            </div>
            """)
            st.markdown(html_card, unsafe_allow_html=True)
            
            # Action Buttons
            c_bet, c_info = st.columns([1, 1])
            with c_bet:
                if st.button(f"📥 Apostar Over {proj['projection']}", key="btn_prop_ov"):
                    save_bet(f"{proj['player']} ({proj['stat_type']})", "Player Prop", f"Over {proj['projection']}", 1.90, st.session_state.banca * 0.01)
            
            # Recent Games Log
            with st.expander("📜 Últimos 5 Jogos", expanded=True):
                # Simple HTML Table for logs
                rows = ""
                for g in proj['last_5_logs']:
                    rows += f"<tr><td style='padding:5px;border-bottom:1px solid #334155'>{g['date']}</td><td style='padding:5px;border-bottom:1px solid #334155'>{g['matchup']}</td><td style='padding:5px;border-bottom:1px solid #334155;color:white;font-weight:bold'>{g['value']}</td></tr>"
                
                table_html = f"""
                <table style='width:100%; font-size:0.9rem; color:#cbd5e1; border-collapse:collapse;'>
                    <thead>
                        <tr style='text-align:left; color:#94a3b8;'><th>DATA</th><th>JOGO</th><th>{proj['stat_type']}</th></tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
                """
                st.markdown(table_html, unsafe_allow_html=True)

        else:
            st.error("Jogador não encontrado ou dados insuficiente (Verifique a ortografia).")

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
    
    STATS = get_team_stats()
    ODDS = get_odds()
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

            # Mapping simplificado para testar (Ideal: Usar dados da NBA API)
            team_map = {
                "Boston Celtics": "BOS", "Denver Nuggets": "DEN", "Milwaukee Bucks": "MIL",
                "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX", "Los Angeles Lakers": "LAL",
                "Golden State Warriors": "GSW", "Dallas Mavericks": "DAL", "Oklahoma City Thunder": "OKC",
                "Minnesota Timberwolves": "MIN", "New York Knicks": "NYK", "Miami Heat": "MIA",
                "Los Angeles Clippers": "LAC", "Atlanta Hawks": "ATL", "Houston Rockets": "HOU"
            }
            
            # --- LESÕES E AJUSTES ---
            h_abbr, a_abbr = team_map.get(h, "UNK"), team_map.get(a, "UNK")
            h_stars, a_stars = get_team_stars(h_abbr), get_team_stars(a_abbr)
            
            penalty_h, penalty_a = 0.0, 0.0
            
            # Expander para Lesões (Só mostra se tiver estrelas mapeadas)
            if h_stars or a_stars:
                with st.expander(f"🚑 Ajuste de Desfalques ({a_abbr} @ {h_abbr})"):
                    c_inj_a, c_inj_h = st.columns(2)
                    
                    with c_inj_a:
                        if a_stars:
                            st.caption(f"Desfalques {a}")
                            for star, imp in a_stars.items():
                                if st.checkbox(f"{star} (-{imp})", key=f"inj_{idx}_{star}"):
                                    penalty_a += imp
                                    
                    with c_inj_h:
                        if h_stars:
                            st.caption(f"Desfalques {h}")
                            for star, imp in h_stars.items():
                                if st.checkbox(f"{star} (-{imp})", key=f"inj_{idx}_{star}"):
                                    penalty_h += imp

            s_h = next((v for k,v in STATS.items() if k in h or h in k), {'net_rtg':0})
            s_a = next((v for k,v in STATS.items() if k in a or a in k), {'net_rtg':0})
            
            # CÁLCULO DINÂMICO
            # NetRtg Ajustado = NetRtg Base - Penalidade por Lesão
            rtg_h_adj = s_h['net_rtg'] - penalty_h
            rtg_a_adj = s_a['net_rtg'] - penalty_a
            
            # Fair Line: (Home_Adj + 2.5 HomeAdv) - Away_Adj
            # Negativo = Home Fav (ex: -5.0)
            fair = -((rtg_h_adj + 2.5) - rtg_a_adj)
            
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
                            <div class="metric-lbl">MODELO (AJUSTADO)</div>
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
                        bet_value = val_unid * units
                        
                        html_footer = textwrap.dedent(f"""
                            <div class="card-action">
                                <div>
                                    <div class="value-tag">✨ VALOR ENCONTRADO</div>
                                    <div class="bet-info">{pick} {line:+.1f}</div>
                                </div>
                            </div>
                        """).strip()
                        st.markdown(html_footer, unsafe_allow_html=True)
                        
                        if st.button(f"📥 REGISTRAR (R$ {bet_value:.2f})", key=f"b_{h}", type="secondary", use_container_width=True):
                             st.toast(f"💰 Apostando: R$ {bet_value:.2f} ({units}u)")
                             save_bet(f"{a} @ {h}", "Spread", f"{pick} {line:+.1f}", 1.91, bet_value)
                    else:
                         st.markdown("""<div style="padding:15px; text-align:center; color:#475569; font-size:0.8rem; font-style:italic;">Sem oportunidade de valor</div>""", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)

with tab_adm:
    c_title, c_status = st.columns([3, 1])
    with c_title:
        st.subheader("📈 Performance da Carteira")
    with c_status:
        try:
            # Teste rápido se df carrega sem erro
            _ = load_history()
            st.markdown("<div style='text-align:right; color:#4ade80; font-weight:bold; font-size:0.8rem; margin-top:20px'>🟢 Online (Google Sheets)</div>", unsafe_allow_html=True)
        except:
             st.markdown("<div style='text-align:right; color:#ef4444; font-weight:bold; font-size:0.8rem; margin-top:20px'>🔴 Offline</div>", unsafe_allow_html=True)
    df = load_history()
    if not df.empty:
        edited = st.data_editor(
            df, num_rows="dynamic", key="editor",
            column_config={"Resultado": st.column_config.SelectboxColumn("Status", options=["Pendente","Green","Red"]), "Lucro": st.column_config.NumberColumn("Lucro (R$)", format="%.2f")},
            hide_index=True
        )
        if st.button("💾 Salvar Alterações"):
            for i, r in edited.iterrows():
                lucro = r['Lucro']
                # Cálculo de lucro automático
                if r['Resultado'] == 'Green': 
                    lucro = r['Valor'] * (r['Odd'] - 1)
                elif r['Resultado'] == 'Red': 
                    lucro = -r['Valor']
                elif r['Resultado'] == 'Pendente':
                    lucro = 0.0
                
                # Atualiza no Banco de Dados
                # O ID é necessário para update. load_history traz coluna 'ID'.
                if 'ID' in r:
                    update_bet_result(r['ID'], r['Resultado'], lucro)
            
            st.success("Alterações salvas no banco de dados!")
            st.rerun()
            
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
