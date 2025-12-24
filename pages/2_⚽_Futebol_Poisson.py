"""
Premier League Live - Modelo de Poisson com Dados Automaticos
Busca dados da web e calcula forcas de ataque/defesa
"""

import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
import requests
from datetime import datetime

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
    .status-badge {
        padding: 5px 10px; border-radius: 5px; font-size: 0.8em; font-weight: bold;
        display: inline-block; margin-bottom: 10px;
    }
    .status-ok { background-color: #1a2e1a; color: #00ff00; border: 1px solid #00ff00; }
    .status-backup { background-color: #332b00; color: #ffcc00; border: 1px solid #ffcc00; }
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

# --- 1. DADOS DE BACKUP (Caso a API falhe) ---
# Formato: {time: [jogos, gols_pro, gols_contra]}
BACKUP_STATS = {
    "Liverpool": [17, 45, 17],
    "Arsenal": [17, 33, 14],
    "Chelsea": [17, 38, 21],
    "Nottm Forest": [17, 25, 19],
    "Newcastle": [17, 26, 17],
    "Manchester City": [17, 33, 23],
    "Bournemouth": [17, 27, 21],
    "Brighton": [17, 25, 22],
    "Aston Villa": [17, 24, 22],
    "Fulham": [17, 22, 18],
    "Brentford": [17, 26, 27],
    "Tottenham": [17, 30, 23],
    "Manchester United": [17, 19, 20],
    "West Ham": [17, 21, 27],
    "Everton": [17, 15, 19],
    "Crystal Palace": [17, 17, 22],
    "Leicester": [17, 19, 32],
    "Wolves": [17, 18, 34],
    "Ipswich": [17, 16, 34],
    "Southampton": [17, 11, 38]
}

# --- 2. FUNCAO DE BUSCA DE DADOS ---
@st.cache_data(ttl=3600)  # Cache de 1 hora
def buscar_dados_pl():
    """Tenta buscar dados da Premier League via API publica"""
    try:
        # API Football-Data.org (gratuita com limite)
        url = "https://api.football-data.org/v4/competitions/PL/standings"
        headers = {"X-Auth-Token": "demo"}  # Token demo tem limite

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            standings = data['standings'][0]['table']

            stats = {}
            for team in standings:
                nome = team['team']['shortName']
                stats[nome] = [
                    team['playedGames'],
                    team['goalsFor'],
                    team['goalsAgainst']
                ]

            return stats, "Online (API)"
        else:
            return BACKUP_STATS, "Backup (API indisponivel)"

    except Exception as e:
        return BACKUP_STATS, "Backup (Erro de conexao)"

# --- 3. MOTOR MATEMATICO ---
def calcular_forcas(stats):
    """Calcula forca de ataque e defesa baseado na media da liga"""
    # Calcula medias da liga
    total_jogos = sum(s[0] for s in stats.values())
    total_gols = sum(s[1] for s in stats.values())
    media_gols = total_gols / total_jogos if total_jogos > 0 else 1.5

    forcas = {}
    for time, dados in stats.items():
        jogos, gf, gc = dados
        if jogos > 0:
            # Forca = Performance do time / Media da liga
            atk = (gf / jogos) / media_gols
            def_ = (gc / jogos) / media_gols
            forcas[time] = {'atk': atk, 'def': def_, 'gf': gf, 'gc': gc, 'jogos': jogos}
        else:
            forcas[time] = {'atk': 1.0, 'def': 1.0, 'gf': 0, 'gc': 0, 'jogos': 0}

    return forcas, media_gols

def prever_jogo(time_casa, time_fora, forcas, media_gols, hfa=1.25):
    """Calcula xG esperado com Home Field Advantage"""
    # xG Casa = Forca Ataque Casa * Forca Defesa Fora * Media Liga * HFA
    xg_casa = forcas[time_casa]['atk'] * forcas[time_fora]['def'] * media_gols * hfa

    # xG Fora = Forca Ataque Fora * Forca Defesa Casa * Media Liga
    xg_fora = forcas[time_fora]['atk'] * forcas[time_casa]['def'] * media_gols

    return xg_casa, xg_fora

def calcular_probabilidades_poisson(xg_casa, xg_fora, max_gols=10):
    """Calcula probabilidades 1X2 usando Poisson"""
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

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.header("Status do Sistema")

    if st.button("Forcar Atualizacao", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.header("Sobre o Modelo")
    st.info("""
    **Distribuicao de Poisson**

    Calcula a probabilidade de cada placar
    baseado na forca historica dos times.

    **HFA (Home Advantage):** +25% para mandante
    """)

# --- 5. INTERFACE PRINCIPAL ---
st.title("Premier League Live")

# Buscar dados
stats, status_dados = buscar_dados_pl()
forcas, media_gols = calcular_forcas(stats)
lista_times = sorted(list(stats.keys()))

# Status badge
if "Online" in status_dados:
    st.markdown(f'<span class="status-badge status-ok">{status_dados}</span>', unsafe_allow_html=True)
else:
    st.markdown(f'<span class="status-badge status-backup">{status_dados}</span>', unsafe_allow_html=True)

st.caption(f"Ultima atualizacao: {datetime.now().strftime('%H:%M:%S')}")

# Selecao de times
st.markdown("### Selecione a Partida")
col1, col2 = st.columns(2)

with col1:
    idx_casa = lista_times.index("Liverpool") if "Liverpool" in lista_times else 0
    time_casa = st.selectbox("Mandante (Casa)", lista_times, index=idx_casa)
with col2:
    idx_fora = lista_times.index("Arsenal") if "Arsenal" in lista_times else 1
    time_fora = st.selectbox("Visitante (Fora)", lista_times, index=idx_fora)

if time_casa == time_fora:
    st.error("Selecione times diferentes.")
else:
    # Previsao
    xg_casa, xg_fora = prever_jogo(time_casa, time_fora, forcas, media_gols)
    prob_casa, prob_empate, prob_fora = calcular_probabilidades_poisson(xg_casa, xg_fora)

    # Odds justas
    odd_justa_casa = 1 / prob_casa if prob_casa > 0 else 99
    odd_justa_empate = 1 / prob_empate if prob_empate > 0 else 99
    odd_justa_fora = 1 / prob_fora if prob_fora > 0 else 99

    st.markdown("---")

    # Card do Jogo
    st.markdown(f"""
    <div class="game-card">
        <h3 style="text-align:center; color:white; margin-bottom: 20px;">{time_casa} vs {time_fora}</h3>
        <div style="display:flex; justify-content:space-around;">
            <div class="metric-box">
                <div class="metric-label">xG {time_casa}</div>
                <div class="metric-value">{xg_casa:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">xG {time_fora}</div>
                <div class="metric-value">{xg_fora:.2f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Odds Justas
    st.markdown("### Odds Justas (Fair Lines)")
    o1, o2, o3 = st.columns(3)
    o1.metric(f"Vitoria {time_casa}", f"{odd_justa_casa:.2f}", f"{prob_casa*100:.1f}%")
    o2.metric("Empate", f"{odd_justa_empate:.2f}", f"{prob_empate*100:.1f}%")
    o3.metric(f"Vitoria {time_fora}", f"{odd_justa_fora:.2f}", f"{prob_fora*100:.1f}%")

    st.markdown("---")

    # Calculadora de Valor
    st.markdown("### Calculadora de Valor (+EV)")
    st.caption("Insira as odds do mercado para encontrar valor")

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
        st.markdown(f"**{time_casa}:**")
        st.write(f"- Forca de Ataque: {forcas[time_casa]['atk']:.2f}")
        st.write(f"- Forca de Defesa: {forcas[time_casa]['def']:.2f}")
        st.write(f"- Gols Pro: {forcas[time_casa]['gf']} | Gols Contra: {forcas[time_casa]['gc']}")

        st.markdown(f"**{time_fora}:**")
        st.write(f"- Forca de Ataque: {forcas[time_fora]['atk']:.2f}")
        st.write(f"- Forca de Defesa: {forcas[time_fora]['def']:.2f}")
        st.write(f"- Gols Pro: {forcas[time_fora]['gf']} | Gols Contra: {forcas[time_fora]['gc']}")

        st.markdown(f"**Media da Liga:** {media_gols:.2f} gols/jogo")

st.markdown("---")
st.caption("Modelo de Poisson | Premier League 24/25 | Use com responsabilidade")
