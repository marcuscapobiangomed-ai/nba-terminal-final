"""
Premier League Pro Quant - Modelo de Poisson
Calcula forca de ataque/defesa e odds justas automaticamente
"""

import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson

# --- CONFIGURACAO VISUAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; font-family: 'Segoe UI', sans-serif; }
    .game-card {
        background: linear-gradient(145deg, #1e2229, #16191f);
        padding: 20px; border-radius: 12px;
        border: 1px solid #303642; margin-bottom: 20px;
    }
    .metric-box { text-align: center; }
    .metric-value { font-size: 1.5em; font-weight: bold; color: #4da6ff; }
    .metric-label { font-size: 0.8em; color: #888; }
    .prediction-box {
        background-color: #1a2e1a;
        border-left: 4px solid #00ff00;
        padding: 15px;
        margin-top: 15px;
        border-radius: 5px;
    }
    .no-value-box {
        background-color: #2e1a1a;
        border-left: 4px solid #ff4444;
        padding: 15px;
        margin-top: 15px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. DATABASE PREMIER LEAGUE 24/25 ---
# Dados baseados em resultados reais da temporada (atualize periodicamente)
# Formato: {time: {'gf_casa': gols feitos em casa, 'gc_casa': gols sofridos em casa,
#                  'gf_fora': gols feitos fora, 'gc_fora': gols sofridos fora,
#                  'jogos_casa': n jogos, 'jogos_fora': n jogos}}

DADOS_PL_2425 = {
    "Liverpool": {"gf_casa": 28, "gc_casa": 5, "gf_fora": 17, "gc_fora": 8, "jogos_casa": 9, "jogos_fora": 8},
    "Arsenal": {"gf_casa": 18, "gc_casa": 8, "gf_fora": 15, "gc_fora": 6, "jogos_casa": 8, "jogos_fora": 9},
    "Chelsea": {"gf_casa": 21, "gc_casa": 10, "gf_fora": 17, "gc_fora": 11, "jogos_casa": 9, "jogos_fora": 8},
    "Nottm Forest": {"gf_casa": 15, "gc_casa": 10, "gf_fora": 10, "gc_fora": 9, "jogos_casa": 8, "jogos_fora": 9},
    "Newcastle": {"gf_casa": 13, "gc_casa": 7, "gf_fora": 13, "gc_fora": 10, "jogos_casa": 8, "jogos_fora": 9},
    "Manchester City": {"gf_casa": 18, "gc_casa": 12, "gf_fora": 15, "gc_fora": 11, "jogos_casa": 9, "jogos_fora": 8},
    "Bournemouth": {"gf_casa": 14, "gc_casa": 10, "gf_fora": 13, "gc_fora": 11, "jogos_casa": 8, "jogos_fora": 9},
    "Brighton": {"gf_casa": 15, "gc_casa": 12, "gf_fora": 10, "gc_fora": 10, "jogos_casa": 9, "jogos_fora": 8},
    "Aston Villa": {"gf_casa": 13, "gc_casa": 10, "gf_fora": 11, "gc_fora": 12, "jogos_casa": 9, "jogos_fora": 8},
    "Fulham": {"gf_casa": 11, "gc_casa": 8, "gf_fora": 11, "gc_fora": 10, "jogos_casa": 8, "jogos_fora": 9},
    "Brentford": {"gf_casa": 18, "gc_casa": 15, "gf_fora": 8, "gc_fora": 12, "jogos_casa": 9, "jogos_fora": 8},
    "Tottenham": {"gf_casa": 20, "gc_casa": 8, "gf_fora": 10, "gc_fora": 15, "jogos_casa": 8, "jogos_fora": 9},
    "Manchester United": {"gf_casa": 10, "gc_casa": 10, "gf_fora": 9, "gc_fora": 10, "jogos_casa": 8, "jogos_fora": 9},
    "West Ham": {"gf_casa": 13, "gc_casa": 13, "gf_fora": 8, "gc_fora": 14, "jogos_casa": 9, "jogos_fora": 8},
    "Everton": {"gf_casa": 7, "gc_casa": 9, "gf_fora": 8, "gc_fora": 10, "jogos_casa": 8, "jogos_fora": 9},
    "Crystal Palace": {"gf_casa": 10, "gc_casa": 10, "gf_fora": 7, "gc_fora": 12, "jogos_casa": 9, "jogos_fora": 8},
    "Leicester": {"gf_casa": 11, "gc_casa": 17, "gf_fora": 8, "gc_fora": 15, "jogos_casa": 9, "jogos_fora": 8},
    "Wolves": {"gf_casa": 11, "gc_casa": 16, "gf_fora": 7, "gc_fora": 18, "jogos_casa": 8, "jogos_fora": 9},
    "Ipswich": {"gf_casa": 9, "gc_casa": 17, "gf_fora": 7, "gc_fora": 17, "jogos_casa": 9, "jogos_fora": 8},
    "Southampton": {"gf_casa": 7, "gc_casa": 17, "gf_fora": 4, "gc_fora": 21, "jogos_casa": 8, "jogos_fora": 9}
}

# --- 2. MOTOR MATEMATICO ---
def calcular_forcas_liga():
    """Calcula forca de ataque e defesa de cada time baseado na media da liga"""
    # Medias da Liga
    total_gols_casa = sum(d['gf_casa'] for d in DADOS_PL_2425.values())
    total_jogos_casa = sum(d['jogos_casa'] for d in DADOS_PL_2425.values())
    media_gols_casa = total_gols_casa / total_jogos_casa

    total_gols_fora = sum(d['gf_fora'] for d in DADOS_PL_2425.values())
    total_jogos_fora = sum(d['jogos_fora'] for d in DADOS_PL_2425.values())
    media_gols_fora = total_gols_fora / total_jogos_fora

    forcas = {}
    for time, dados in DADOS_PL_2425.items():
        # Media do time
        media_gf_casa = dados['gf_casa'] / dados['jogos_casa']
        media_gc_casa = dados['gc_casa'] / dados['jogos_casa']
        media_gf_fora = dados['gf_fora'] / dados['jogos_fora']
        media_gc_fora = dados['gc_fora'] / dados['jogos_fora']

        # Forca = Performance do time / Media da liga
        forcas[time] = {
            'atk_casa': media_gf_casa / media_gols_casa,
            'def_casa': media_gc_casa / media_gols_fora,  # Gols sofridos em casa vs media de gols fora
            'atk_fora': media_gf_fora / media_gols_fora,
            'def_fora': media_gc_fora / media_gols_casa   # Gols sofridos fora vs media de gols casa
        }

    return forcas, media_gols_casa, media_gols_fora

def prever_jogo(time_casa, time_fora, forcas, media_casa, media_fora):
    """Calcula xG esperado para cada time"""
    # xG Casa = Forca Ataque Casa * Forca Defesa Fora (adversario) * Media Liga Casa
    xg_casa = forcas[time_casa]['atk_casa'] * forcas[time_fora]['def_fora'] * media_casa

    # xG Fora = Forca Ataque Fora * Forca Defesa Casa (adversario) * Media Liga Fora
    xg_fora = forcas[time_fora]['atk_fora'] * forcas[time_casa]['def_casa'] * media_fora

    return xg_casa, xg_fora

def calcular_probabilidades_poisson(xg_casa, xg_fora, max_gols=10):
    """Calcula probabilidades 1X2 usando distribuicao de Poisson"""
    prob_casa = 0
    prob_empate = 0
    prob_fora = 0

    for i in range(max_gols):
        for j in range(max_gols):
            p = poisson.pmf(i, xg_casa) * poisson.pmf(j, xg_fora)
            if i > j:
                prob_casa += p
            elif i == j:
                prob_empate += p
            else:
                prob_fora += p

    return prob_casa, prob_empate, prob_fora

def calcular_matriz_placares(xg_casa, xg_fora, max_gols=6):
    """Gera matriz de probabilidade de cada placar"""
    matriz = np.zeros((max_gols, max_gols))
    for i in range(max_gols):
        for j in range(max_gols):
            matriz[i, j] = poisson.pmf(i, xg_casa) * poisson.pmf(j, xg_fora)
    return matriz

# --- 3. BARRA LATERAL ---
with st.sidebar:
    st.header("Sobre o Modelo")
    st.info("""
    **Distribuicao de Poisson**

    Calcula a probabilidade de cada placar
    baseado na forca historica dos times.

    **Forca de Ataque:** Gols marcados vs media da liga
    **Forca de Defesa:** Gols sofridos vs media da liga
    """)
    st.markdown("---")
    st.caption("Dados: Premier League 24/25")
    st.caption("Atualize os dados periodicamente")

# --- 4. INTERFACE PRINCIPAL ---
st.title("Premier League Pro Quant")
st.caption("Modelo de Poisson com Forca de Ataque/Defesa")

# Calcular forcas da liga
forcas, media_casa, media_fora = calcular_forcas_liga()
lista_times = sorted(list(DADOS_PL_2425.keys()))

# Selecao de times
st.markdown("### Selecione a Partida")
col1, col2 = st.columns(2)

with col1:
    time_casa = st.selectbox("Mandante (Casa)", lista_times, index=lista_times.index("Liverpool"))
with col2:
    time_fora = st.selectbox("Visitante (Fora)", lista_times, index=lista_times.index("Arsenal"))

if time_casa == time_fora:
    st.error("Selecione times diferentes.")
else:
    # Previsao
    xg_casa, xg_fora = prever_jogo(time_casa, time_fora, forcas, media_casa, media_fora)
    prob_casa, prob_empate, prob_fora = calcular_probabilidades_poisson(xg_casa, xg_fora)

    # Odds justas
    odd_justa_casa = 1 / prob_casa if prob_casa > 0 else 99
    odd_justa_empate = 1 / prob_empate if prob_empate > 0 else 99
    odd_justa_fora = 1 / prob_fora if prob_fora > 0 else 99

    st.markdown("---")

    # Exibicao xG
    st.markdown("### Expectativa de Gols (xG)")
    c1, c2, c3 = st.columns([2, 1, 2])

    with c1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{xg_casa:.2f}</div>
            <div class="metric-label">{time_casa}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">vs</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{xg_fora:.2f}</div>
            <div class="metric-label">{time_fora}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Odds Justas
    st.markdown("### Odds Justas (Fair Lines)")
    o1, o2, o3 = st.columns(3)
    o1.metric(f"Vitoria {time_casa}", f"{odd_justa_casa:.2f}", f"{prob_casa*100:.1f}%")
    o2.metric("Empate", f"{odd_justa_empate:.2f}", f"{prob_empate*100:.1f}%")
    o3.metric(f"Vitoria {time_fora}", f"{odd_justa_fora:.2f}", f"{prob_fora*100:.1f}%")

    st.markdown("---")

    # Calculadora de Valor
    st.markdown("### Calculadora de Valor (+EV)")
    st.caption("Compare as odds do mercado com as odds justas do modelo")

    ev_col1, ev_col2, ev_col3 = st.columns(3)

    with ev_col1:
        odd_mercado_casa = st.number_input(f"Odd {time_casa}", value=round(odd_justa_casa, 2), step=0.05, key="odd_casa")
        ev_casa = (prob_casa * odd_mercado_casa) - 1
        if ev_casa > 0:
            st.markdown(f"""
            <div class="prediction-box">
                <b>+EV: {ev_casa*100:.1f}%</b><br>
                <small>VALOR!</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="no-value-box">
                <b>EV: {ev_casa*100:.1f}%</b><br>
                <small>Sem valor</small>
            </div>
            """, unsafe_allow_html=True)

    with ev_col2:
        odd_mercado_empate = st.number_input("Odd Empate", value=round(odd_justa_empate, 2), step=0.05, key="odd_empate")
        ev_empate = (prob_empate * odd_mercado_empate) - 1
        if ev_empate > 0:
            st.markdown(f"""
            <div class="prediction-box">
                <b>+EV: {ev_empate*100:.1f}%</b><br>
                <small>VALOR!</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="no-value-box">
                <b>EV: {ev_empate*100:.1f}%</b><br>
                <small>Sem valor</small>
            </div>
            """, unsafe_allow_html=True)

    with ev_col3:
        odd_mercado_fora = st.number_input(f"Odd {time_fora}", value=round(odd_justa_fora, 2), step=0.05, key="odd_fora")
        ev_fora = (prob_fora * odd_mercado_fora) - 1
        if ev_fora > 0:
            st.markdown(f"""
            <div class="prediction-box">
                <b>+EV: {ev_fora*100:.1f}%</b><br>
                <small>VALOR!</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="no-value-box">
                <b>EV: {ev_fora*100:.1f}%</b><br>
                <small>Sem valor</small>
            </div>
            """, unsafe_allow_html=True)

    # Resumo de apostas com valor
    apostas_valor = []
    if ev_casa > 0:
        apostas_valor.append(f"**{time_casa}** @ {odd_mercado_casa:.2f} (+EV: {ev_casa*100:.1f}%)")
    if ev_empate > 0:
        apostas_valor.append(f"**Empate** @ {odd_mercado_empate:.2f} (+EV: {ev_empate*100:.1f}%)")
    if ev_fora > 0:
        apostas_valor.append(f"**{time_fora}** @ {odd_mercado_fora:.2f} (+EV: {ev_fora*100:.1f}%)")

    if apostas_valor:
        st.markdown("---")
        st.success("**Apostas com Valor Encontradas:**")
        for aposta in apostas_valor:
            st.markdown(f"- {aposta}")

    # Matriz de placares
    with st.expander("Ver Matriz de Placares"):
        matriz = calcular_matriz_placares(xg_casa, xg_fora)
        df_matriz = pd.DataFrame(
            matriz * 100,
            index=[f"{time_casa} {i}" for i in range(6)],
            columns=[f"{time_fora} {i}" for i in range(6)]
        )
        st.dataframe(df_matriz.style.format("{:.2f}%").background_gradient(cmap='YlOrRd'), use_container_width=True)

        # Top placares
        st.markdown("**Top 5 Placares Mais Provaveis:**")
        placares = []
        for i in range(6):
            for j in range(6):
                placares.append({'Placar': f"{i} x {j}", 'Prob': matriz[i, j] * 100})
        df_top = pd.DataFrame(placares).sort_values('Prob', ascending=False).head(5)
        df_top['Prob'] = df_top['Prob'].apply(lambda x: f"{x:.2f}%")
        st.table(df_top.reset_index(drop=True))

    # Forcas dos times
    with st.expander("Ver Forcas dos Times"):
        st.markdown(f"**{time_casa} (Casa):**")
        st.write(f"- Ataque Casa: {forcas[time_casa]['atk_casa']:.2f}")
        st.write(f"- Defesa Casa: {forcas[time_casa]['def_casa']:.2f}")

        st.markdown(f"**{time_fora} (Fora):**")
        st.write(f"- Ataque Fora: {forcas[time_fora]['atk_fora']:.2f}")
        st.write(f"- Defesa Fora: {forcas[time_fora]['def_fora']:.2f}")

        st.markdown("**Medias da Liga:**")
        st.write(f"- Gols por jogo (Casa): {media_casa:.2f}")
        st.write(f"- Gols por jogo (Fora): {media_fora:.2f}")

st.markdown("---")
st.caption("Modelo de Poisson | Premier League 24/25 | Use com responsabilidade")
