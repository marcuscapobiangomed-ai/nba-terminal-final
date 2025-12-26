# Core module initialization
from .config import get_config, Config
from .odds_engine import calculate_fair_spread, calculate_fair_total, calculate_edge, kelly_stake
from .data_fetcher import get_team_stats, get_odds, get_live_scores, get_news
from .backoffice import load_history, save_bet, calculate_metrics

__all__ = [
    'get_config', 'Config',
    'calculate_fair_spread', 'calculate_fair_total', 'calculate_edge', 'kelly_stake',
    'get_team_stats', 'get_odds', 'get_live_scores', 'get_news',
    'load_history', 'save_bet', 'calculate_metrics'
]
