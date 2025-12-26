"""
Módulo de Configuração
Carrega variáveis de ambiente de forma segura usando python-dotenv
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# Carrega .env do diretório raiz do projeto
_env_path = Path(__file__).parent.parent / '.env'
load_dotenv(_env_path)


@dataclass
class Config:
    """Configurações centralizadas da aplicação"""
    odds_api_key: str
    bets_history_file: str
    default_bankroll: float
    default_unit_percent: float
    nba_season: str
    
    # Constantes do modelo
    home_advantage: float = 2.5  # Vantagem de jogar em casa em pontos
    min_edge_spread: float = 1.5  # Edge mínimo para apostar em spread
    min_edge_total: float = 5.0   # Edge mínimo para apostar em total
    kelly_fraction: float = 0.25  # Fração do Kelly (mais conservador)
    
    # Thresholds para Props
    fast_pace_threshold: float = 102.0
    bad_defense_threshold: float = 115.0


def get_config() -> Config:
    """
    Retorna as configurações carregadas do .env
    Valida que as variáveis obrigatórias estão presentes
    """
    api_key = os.getenv('ODDS_API_KEY')
    
    if not api_key or api_key == 'your_api_key_here':
        raise ValueError(
            "❌ ODDS_API_KEY não configurada!\n"
            "Por favor, copie .env.example para .env e adicione sua API key."
        )
    
    return Config(
        odds_api_key=api_key,
        bets_history_file=os.getenv('BETS_HISTORY_FILE', 'bets_history.csv'),
        default_bankroll=float(os.getenv('DEFAULT_BANKROLL', '1000.0')),
        default_unit_percent=float(os.getenv('DEFAULT_UNIT_PERCENT', '1.0')),
        nba_season=os.getenv('NBA_SEASON', '2024-25')
    )


# Lista de jogadores estrela para Props (movido do arquivo principal)
STAR_PLAYERS = {
    "Lakers": ["LeBron James", "Anthony Davis"],
    "Warriors": ["Stephen Curry"],
    "Celtics": ["Jayson Tatum", "Jaylen Brown"],
    "Bucks": ["Giannis Antetokounmpo", "Damian Lillard"],
    "Nuggets": ["Nikola Jokic", "Jamal Murray"],
    "Suns": ["Kevin Durant", "Devin Booker"],
    "Mavericks": ["Luka Doncic", "Kyrie Irving"],
    "76ers": ["Joel Embiid", "Tyrese Maxey"],
    "Thunder": ["Shai Gilgeous-Alexander", "Chet Holmgren"],
    "Timberwolves": ["Anthony Edwards"],
    "Knicks": ["Jalen Brunson", "Karl-Anthony Towns"],
    "Spurs": ["Victor Wembanyama"],
    "Pacers": ["Tyrese Haliburton"],
    "Heat": ["Jimmy Butler", "Bam Adebayo"],
    "Cavaliers": ["Donovan Mitchell"],
    "Magic": ["Paolo Banchero"],
    "Rockets": ["Alperen Sengun"],
    "Grizzlies": ["Ja Morant"],
    "Hawks": ["Trae Young"],
    "Kings": ["De'Aaron Fox", "Domantas Sabonis"]
}

# Jogadores pivôs para análise de rebotes
REBOUNDERS = [
    "Nikola Jokic", "Anthony Davis", "Domantas Sabonis", 
    "Bam Adebayo", "Victor Wembanyama", "Alperen Sengun",
    "Karl-Anthony Towns", "Rudy Gobert"
]
