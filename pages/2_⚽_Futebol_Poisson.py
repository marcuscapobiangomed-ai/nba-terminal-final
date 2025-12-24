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
    </style>
""", unsafe_allow_html=True)

# --- 1. DADOS DE BACKUP (Para caso o site bloqueie) ---
BACKUP_STATS = {
    "Liverpool": [17, 36, 18], "Arsenal": [17, 38, 12], "Aston Villa": [17, 28, 22],
    "Man City": [17, 45, 15], "Newcastle Utd": [17, 30, 19], "Chelsea": [17, 32, 20],
    "Man Utd": [17, 24, 20], "Tottenham": [17, 33, 26], "Brighton": [17, 26, 25],
    "West Ham": [17, 24, 28], "Brentford": [17, 25, 27], "Wolves": [17, 17, 29],
    "Crystal Palace": [17, 19, 21], "Fulham": [17, 18, 26], "Bournemouth": [17, 20, 28],
    "Everton": [17, 16, 30], "Nott'm Forest": [17, 15, 28], "Leicester City": [17, 18, 35],
    "Ipswich Town": [17, 14, 36], "Southampton": [17, 12, 38]
}

# --- 2. MOTOR DE DADOS AO VIVO ---
@st.cache_data(ttl=600)  # Atualiza o cache automaticamente a cada 10 minutos
def obter_dados_live():
    """Vai na internet buscar a tabela atualizada."""
    url = "https://fbref.com/en/comps/9/Premier-League-Stats"
    stats = {}
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        # User-Agent e essencial para nao ser bloqueado como 'robo'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            dfs = pd.read_html(response.text)
            tabela = dfs[0]

            # Processar tabela
            for index, row in tabela.iterrows():
                time = row['Squad']
                jogos = row['MP']
                gf = row['GF']
                ga = row['GA']
                stats[time] = [jogos, gf, ga]

            return stats, "online", timestamp

    except Exception as e:
        pass

    return BACKUP_STATS, "backup", timestamp

# --- 3. CALCULO (POISSON) ---
def calcular_probs(time_casa, time_fora, stats):
    # Medias da Liga Atualizadas
    dados = list(stats.values())
    total_jogos = sum([d[0] for d in dados]) / 2
    total_gols = sum([d[1] for d in dados])
    if total_jogos == 0:
        return 0, 0, 0, 0, 0  # Evitar divisao por zero

    media_liga = total_gols / (total_jogos * 2)

    # Stats Especificas
    j_c, gf_c, ga_c = stats.get(time_casa, [1, 1, 1])
    j_f, gf_f, ga_f = stats.get(time_fora, [1, 1, 1])

    atk_casa = (gf_c / j_c) / media_liga
    def_casa = (ga_c / j_c) / media_liga
    atk_fora = (gf_f / j_f) / media_liga
    def_fora = (ga_f / j_f) / media_liga

    # xG (Expected Goals)
    xg_casa = atk_casa * def_fora * media_liga * 1.15  # Fator Casa
    xg_fora = atk_fora * def_casa * media_liga * 0.85

    # Probabilidades
    prob_c, prob_e, prob_f = 0, 0, 0
    for i in range(10):
        for j in range(10):
            p = poisson.pmf(i, xg_casa) * poisson.pmf(j, xg_fora)
            if i > j:
                prob_c += p
            elif i == j:
                prob_e += p
            else:
                prob_f += p

    return xg_casa, xg_fora, prob_c, prob_e, prob_f

# --- 4. INTERFACE ---
st.title("Premier League Live-Quant")

# --- BARRA LATERAL DE CONTROLE ---
with st.sidebar:
    st.header("Controle de Dados")
    if st.button("Forcar Atualizacao Agora", use_container_width=True):
        st.cache_data.clear()  # Limpa a memoria para baixar de novo
        st.rerun()

    st.markdown("---")
    st.info("O botao acima apaga a memoria do app e vai no site da Premier League buscar os numeros mais recentes.")

# Carregar Dados
stats, status, hora = obter_dados_live()

# Indicador de Status
if status == "online":
    st.markdown(f'<div class="status-badge status-ok">CONECTADO: DADOS AO VIVO ({hora})</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-badge status-backup">OFFLINE: USANDO BACKUP ({hora})</div>', unsafe_allow_html=True)

# Selecao de Times
times = sorted(list(stats.keys()))

c1, c2 = st.columns(2)
t_casa = c1.selectbox("Mandante", times, index=times.index("Man City") if "Man City" in times else 0)
t_fora = c2.selectbox("Visitante", times, index=times.index("Arsenal") if "Arsenal" in times else 1)

if t_casa != t_fora:
    xg_c, xg_f, pc, pe, pf = calcular_probs(t_casa, t_fora, stats)

    odd_c = 1 / pc if pc > 0 else 0
    odd_e = 1 / pe if pe > 0 else 0
    odd_f = 1 / pf if pf > 0 else 0

    # CARD VISUAL
    st.markdown(f"""
    <div class="game-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="text-align:center; flex:1;">
                <h3>{t_casa}</h3>
                <div style="color:#888; font-size:0.8em;">ATAQUE: {stats[t_casa][1]} Gols</div>
            </div>
            <div style="font-weight:bold; font-size:1.2em;">VS</div>
            <div style="text-align:center; flex:1;">
                <h3>{t_fora}</h3>
                <div style="color:#888; font-size:0.8em;">ATAQUE: {stats[t_fora][1]} Gols</div>
            </div>
        </div>

        <hr style="border-color:#333">

        <div style="display:flex; justify-content:space-around; margin-top:15px;">
            <div class="metric-box">
                <div class="metric-label">xG Esperado</div>
                <div class="metric-value">{xg_c:.2f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">xG Esperado</div>
                <div class="metric-value">{xg_f:.2f}</div>
            </div>
        </div>

        <div style="background-color:#000; padding:10px; border-radius:8px; margin-top:20px; text-align:center;">
            <div style="color:#888; font-size:0.8em; margin-bottom:5px;">ODDS JUSTAS (FAIR LINES)</div>
            <div style="display:flex; justify-content:space-between;">
                <div style="flex:1;"><span style="color:#0f0;">{odd_c:.2f}</span><br><small>Casa</small></div>
                <div style="flex:1;"><span style="color:#ccc;">{odd_e:.2f}</span><br><small>Empate</small></div>
                <div style="flex:1;"><span style="color:#0f0;">{odd_f:.2f}</span><br><small>Fora</small></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Calculadora de EV
    st.markdown("### Calculadora de Valor (+EV)")
    st.caption("Insira as odds do mercado para encontrar valor")

    ev_col1, ev_col2, ev_col3 = st.columns(3)

    with ev_col1:
        odd_mercado_casa = st.number_input(f"Odd {t_casa}", value=round(odd_c, 2), step=0.05, key="odd_casa")
        ev_casa = (pc * odd_mercado_casa) - 1
        if ev_casa > 0:
            st.success(f"+EV: {ev_casa*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_casa*100:.1f}%")

    with ev_col2:
        odd_mercado_empate = st.number_input("Odd Empate", value=round(odd_e, 2), step=0.05, key="odd_empate")
        ev_empate = (pe * odd_mercado_empate) - 1
        if ev_empate > 0:
            st.success(f"+EV: {ev_empate*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_empate*100:.1f}%")

    with ev_col3:
        odd_mercado_fora = st.number_input(f"Odd {t_fora}", value=round(odd_f, 2), step=0.05, key="odd_fora")
        ev_fora = (pf * odd_mercado_fora) - 1
        if ev_fora > 0:
            st.success(f"+EV: {ev_fora*100:.1f}% - VALOR!")
        else:
            st.error(f"EV: {ev_fora*100:.1f}%")

    # Resumo de apostas com valor
    apostas_valor = []
    if ev_casa > 0:
        apostas_valor.append(f"**{t_casa}** @ {odd_mercado_casa:.2f} (+EV: {ev_casa*100:.1f}%)")
    if ev_empate > 0:
        apostas_valor.append(f"**Empate** @ {odd_mercado_empate:.2f} (+EV: {ev_empate*100:.1f}%)")
    if ev_fora > 0:
        apostas_valor.append(f"**{t_fora}** @ {odd_mercado_fora:.2f} (+EV: {ev_fora*100:.1f}%)")

    if apostas_valor:
        st.markdown("---")
        st.success("**Apostas com Valor Encontradas:**")
        for aposta in apostas_valor:
            st.markdown(f"- {aposta}")

    # MATRIZ DE PLACARES (Substituindo o Heatmap Grafico por Texto Simples)
    with st.expander("Ver Probabilidades de Placar Exato"):
        st.write("Placares mais provaveis segundo o modelo:")

        lista_placares = []
        for i in range(5):
            for j in range(5):
                prob = poisson.pmf(i, xg_c) * poisson.pmf(j, xg_f)
                lista_placares.append((f"{i} - {j}", prob))

        # Ordenar e mostrar top 5
        lista_placares.sort(key=lambda x: x[1], reverse=True)

        for placar, prob in lista_placares[:5]:
            col_res, col_prob = st.columns([1, 3])
            col_res.write(f"**{placar}**")
            col_prob.progress(min(int(prob * 100), 100), text=f"{prob*100:.1f}%")

else:
    st.error("Selecione times diferentes.")

st.markdown("---")
st.caption("Modelo de Poisson | Premier League 24/25 | Dados: FBref")
