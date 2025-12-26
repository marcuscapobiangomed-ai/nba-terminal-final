"""
Motor de Cálculo de Odds
Contém toda a lógica matemática para calcular linhas justas, edge e stakes
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TeamStats:
    """Estatísticas de um time"""
    pace: float = 100.0       # Posses por 48 minutos
    off_rtg: float = 110.0    # Offensive Rating (pontos por 100 posses)
    def_rtg: float = 110.0    # Defensive Rating (pontos permitidos por 100 posses)
    net_rtg: float = 0.0      # Net Rating = OffRtg - DefRtg
    efg_pct: float = 0.54     # Effective Field Goal %
    tov_pct: float = 0.14     # Turnover %
    orb_pct: float = 0.25     # Offensive Rebound %
    ft_rate: float = 0.25     # Free Throw Rate


@dataclass
class FairLines:
    """Linhas justas calculadas pelo modelo"""
    spread: float             # Spread justo (positivo = underdog, negativo = favorito)
    total: float              # Total de pontos projetado
    home_win_prob: float      # Probabilidade de vitória do mandante
    away_win_prob: float      # Probabilidade de vitória do visitante


def calculate_net_rating(off_rtg: float, def_rtg: float) -> float:
    """
    Calcula Net Rating real.
    Net RTG = Offensive Rating - Defensive Rating
    
    Diferente de PTS - OPP_PTS que não considera ritmo.
    """
    return off_rtg - def_rtg


def calculate_fair_spread(
    home_net_rtg: float, 
    away_net_rtg: float, 
    home_advantage: float = 2.5
) -> float:
    """
    Calcula o spread justo baseado em Net Rating.
    
    Fórmula: Fair Spread = -((Home_NetRtg + HCA) - Away_NetRtg)
    
    Args:
        home_net_rtg: Net Rating do time da casa
        away_net_rtg: Net Rating do time visitante
        home_advantage: Vantagem de jogar em casa (default: 2.5 pontos)
    
    Returns:
        Spread justo (negativo = casa favorita, positivo = visitante favorito)
    """
    return -((home_net_rtg + home_advantage) - away_net_rtg)


def calculate_fair_total(
    home_pace: float,
    away_pace: float,
    home_off_rtg: float,
    away_off_rtg: float,
    home_def_rtg: float,
    away_def_rtg: float
) -> float:
    """
    Calcula o total de pontos projetado usando Pace × Efficiency.
    
    Mais preciso que simplesmente Pace × 2.3
    
    Fórmula:
    - Expected Pace = média dos dois times
    - Home Points = Pace × (Home_OffRtg vs Away_DefRtg) / 100
    - Away Points = Pace × (Away_OffRtg vs Home_DefRtg) / 100
    - Total = Home Points + Away Points
    
    Args:
        home_pace, away_pace: Ritmo de cada time
        home_off_rtg, away_off_rtg: Offensive Rating de cada time
        home_def_rtg, away_def_rtg: Defensive Rating de cada time
    
    Returns:
        Total de pontos projetado
    """
    expected_pace = (home_pace + away_pace) / 2
    
    # Ajuste para confronto específico
    # Home ataca vs Away defesa, Away ataca vs Home defesa
    home_adjusted_off = (home_off_rtg + (110 - away_def_rtg)) / 2
    away_adjusted_off = (away_off_rtg + (110 - home_def_rtg)) / 2
    
    home_pts = expected_pace * (home_adjusted_off / 100)
    away_pts = expected_pace * (away_adjusted_off / 100)
    
    return home_pts + away_pts


def calculate_fair_total_simple(pace: float, multiplier: float = 2.2) -> float:
    """
    Cálculo simplificado de total quando não temos todos os dados.
    
    Args:
        pace: Ritmo médio esperado do jogo
        multiplier: Fator de conversão (default 2.2 para NBA moderna)
    
    Returns:
        Total de pontos projetado
    """
    return pace * multiplier


def calculate_edge(fair_line: float, market_line: float) -> float:
    """
    Calcula o edge (vantagem) entre linha justa e linha de mercado.
    
    Args:
        fair_line: Linha calculada pelo modelo
        market_line: Linha oferecida pelo mercado
    
    Returns:
        Edge absoluto em pontos
    """
    return abs(fair_line - market_line)


def calculate_win_probability(spread: float) -> float:
    """
    Estima probabilidade de vitória baseado no spread.
    Usando aproximação linear simplificada.
    
    Args:
        spread: Spread do jogo (negativo = favorito)
    
    Returns:
        Probabilidade de vitória do favorito
    """
    # Cada ponto de spread ≈ 3% de probabilidade
    # Spread -7 ≈ 70% de chance
    base_prob = 0.50
    adjustment = (-spread) * 0.03
    return min(0.95, max(0.05, base_prob + adjustment))


def kelly_stake(
    edge: float, 
    odds: float = 1.91, 
    fraction: float = 0.25,
    max_stake: float = 3.0
) -> float:
    """
    Calcula stake usando Kelly Criterion fracionado.
    
    Fórmula Kelly: f* = (p*b - q) / b
    Onde:
        p = probabilidade de ganhar
        q = probabilidade de perder (1 - p)
        b = odds - 1 (lucro líquido por unidade apostada)
    
    Args:
        edge: Vantagem em pontos
        odds: Odds decimais (default 1.91 para spread -110)
        fraction: Fração do Kelly a usar (0.25 = Quarter Kelly, mais conservador)
        max_stake: Stake máximo em unidades
    
    Returns:
        Stake recomendado em unidades
    """
    # Converte edge em probabilidade estimada
    # Edge de 3 pontos ≈ 59% de probabilidade
    prob = 0.50 + (edge / 20)
    prob = min(0.75, max(0.52, prob))  # Limita entre 52% e 75%
    
    q = 1 - prob
    b = odds - 1
    
    # Kelly original
    kelly = (prob * b - q) / b
    
    # Aplica fração e limites
    stake = kelly * fraction
    stake = max(0, min(max_stake, stake))
    
    return round(stake, 2)


def get_stake_units(edge: float, min_edge: float = 1.5) -> float:
    """
    Retorna unidades simplificadas baseado no edge.
    
    Args:
        edge: Vantagem em pontos
        min_edge: Edge mínimo para considerar aposta
    
    Returns:
        Unidades recomendadas (0.5, 0.75, 1.0, 1.5, 2.0)
    """
    if edge < min_edge:
        return 0.0
    elif edge < 2.0:
        return 0.5
    elif edge < 3.0:
        return 0.75
    elif edge < 4.0:
        return 1.0
    elif edge < 5.0:
        return 1.5
    else:
        return 2.0


def four_factors_advantage(
    home_efg: float, home_tov: float, home_orb: float, home_ftr: float,
    away_efg: float, away_tov: float, away_orb: float, away_ftr: float
) -> dict:
    """
    Analisa vantagem nos Four Factors de Dean Oliver.
    
    Four Factors (por ordem de importância):
    1. eFG% (40%): Effective Field Goal % - eficiência de arremesso
    2. TOV% (25%): Turnover % - cuidado com a bola
    3. ORB% (20%): Offensive Rebound % - segundas chances
    4. FT Rate (15%): Free Throw Rate - idas à linha
    
    Args:
        Estatísticas de casa e visitante para cada fator
    
    Returns:
        Dict com análise detalhada de cada fator
    """
    return {
        'efg_diff': home_efg - away_efg,
        'tov_diff': away_tov - home_tov,  # Invertido: menos turnovers = melhor
        'orb_diff': home_orb - away_orb,
        'ftr_diff': home_ftr - away_ftr,
        'home_advantage': (
            (home_efg - away_efg) * 0.40 +
            (away_tov - home_tov) * 0.25 +
            (home_orb - away_orb) * 0.20 +
            (home_ftr - away_ftr) * 0.15
        )
    }
