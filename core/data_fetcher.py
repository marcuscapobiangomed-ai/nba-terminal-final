"""
Módulo de Busca de Dados
Centraliza todas as chamadas de API e tratamento de dados
"""
import os
import json
import requests
import feedparser
from datetime import datetime
from typing import Dict, List, Optional, Any
from nba_api.stats.endpoints import leaguedashteamstats
from deep_translator import GoogleTranslator

from .config import get_config

# Caminho do cache de odds
ODDS_CACHE_FILE = "odds_cache.json"


def get_team_stats(season: Optional[str] = None) -> Dict[str, Dict]:
    """
    Busca estatísticas avançadas dos times da NBA.
    
    Args:
        season: Temporada no formato '2024-25' (usa config se não fornecido)
    
    Returns:
        Dict com nome do time como chave e estatísticas como valor
    """
    config = get_config()
    season = season or config.nba_season
    
    try:
        stats = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            measure_type_detailed_defense='Base'
        ).get_data_frames()[0]
        
        data = {}
        for _, row in stats.iterrows():
            # Net Rating real = OffRtg - DefRtg
            net_rtg = row['OFF_RATING'] - row['DEF_RATING'] if 'OFF_RATING' in row else row['PTS'] - row['OPP_PTS']
            
            data[row['TEAM_NAME']] = {
                'pace': row['PACE'],
                'off_rtg': row.get('OFF_RATING', 110.0),
                'def_rtg': row.get('DEF_RATING', 110.0),
                'net_rtg': net_rtg,
                'efg': row['EFG_PCT'],
                'tov': row['TM_TOV_PCT'],
                'orb': row.get('OREB_PCT', 0.25),
                'ftr': row.get('FTA_RATE', 0.25),
                'wins': row['W'],
                'losses': row['L'],
                'win_pct': row['W_PCT']
            }
        return data
        
    except Exception as e:
        print(f"Erro ao buscar stats da NBA: {e}")
        return {}


def get_odds(regions: str = 'us,eu', markets: str = 'spreads,totals') -> List[Dict]:
    """
    Busca odds ao vivo da The Odds API com fallback para cache local.
    
    Se a API estiver offline ou limite excedido, usa dados salvos anteriormente.
    
    Args:
        regions: Regiões das casas de apostas
        markets: Mercados a buscar (spreads, totals, h2h)
    
    Returns:
        Lista de jogos com odds
    """
    config = get_config()
    
    try:
        # 1. Tenta buscar da API
        response = requests.get(
            'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'api_key': config.odds_api_key,
                'regions': regions,
                'markets': markets,
                'oddsFormat': 'decimal',
                'bookmakers': 'pinnacle,bet365,draftkings,fanduel'
            },
            timeout=5  # Timeout curto para falhar rápido
        )
        response.raise_for_status()
        data = response.json()
        
        # Log de uso da API (opcional)
        remaining = response.headers.get('x-requests-remaining', '?')
        print(f"[OK] Odds API | Requests restantes: {remaining}")
        
        # 2. Se deu certo, salva no cache local (o "cofre")
        try:
            with open(ODDS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f)
        except Exception as cache_error:
            print(f"[WARN] Erro ao salvar cache: {cache_error}")
        
        return data
        
    except Exception as e:
        # 3. Fallback: usa cache local se disponível
        print(f"[WARN] Erro na API de Odds: {e}")
        
        if os.path.exists(ODDS_CACHE_FILE):
            try:
                with open(ODDS_CACHE_FILE, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    cache_time = cached.get('timestamp', 'desconhecido')
                    print(f"[CACHE] Usando cache de: {cache_time}")
                    return cached.get('data', [])
            except Exception as cache_read_error:
                print(f"[ERROR] Erro ao ler cache: {cache_read_error}")
                return []
        else:
            print("[ERROR] Nenhum cache disponivel")
            return []


def _clean_nba_clock(raw_clock: str) -> str:
    """Limpa o formato do relógio da NBA API"""
    if not raw_clock:
        return ""
    try:
        clean = raw_clock.replace("PT", "").replace("S", "")
        if "M" in clean:
            parts = clean.split('M')
            return f"{parts[0]}:{parts[1].split('.')[0]}"
        return clean
    except:
        return raw_clock


def get_live_scores() -> Dict[str, Dict]:
    """
    Busca placares ao vivo da NBA.
    
    Returns:
        Dict com nome do time como chave e info do jogo como valor
    """
    try:
        response = requests.get(
            "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
            timeout=10
        )
        data = response.json()
        
        live_data = {}
        for game in data['scoreboard']['games']:
            clock = _clean_nba_clock(game['gameClock'])
            
            info = {
                "live": game['gameStatus'] == 2,
                "status": game['gameStatus'],  # 1=scheduled, 2=live, 3=final
                "period": game['period'],
                "clock": clock,
                "score_home": game['homeTeam']['score'],
                "score_away": game['awayTeam']['score'],
                "home_team": game['homeTeam']['teamName'],
                "away_team": game['awayTeam']['teamName'],
                "game_id": game['gameId']
            }
            
            # Indexa por ambos os times para facilitar busca
            live_data[game['homeTeam']['teamName']] = info
            live_data[game['awayTeam']['teamName']] = info
            
        return live_data
        
    except Exception as e:
        print(f"Erro ao buscar scores live: {e}")
        return {}


def get_news(max_items: int = 4, translate: bool = True) -> List[Dict]:
    """
    Busca notícias da NBA via ESPN RSS.
    
    Args:
        max_items: Número máximo de notícias
        translate: Se deve traduzir para português
    
    Returns:
        Lista de notícias com título, hora e flag de alerta
    """
    alert_keywords = ["injury", "out", "surgery", "suspended", "trade", "ruled out", "questionable"]
    
    try:
        feed = feedparser.parse("https://www.espn.com/espn/rss/nba/news")
        noticias = []
        
        translator = GoogleTranslator(source='auto', target='pt') if translate else None
        
        for entry in feed.entries[:max_items]:
            # Detecta se é notícia de alerta (lesão, trade, etc)
            is_alert = any(w in entry.title.lower() for w in alert_keywords)
            
            # Traduz título
            try:
                title = translator.translate(entry.title) if translate else entry.title
                title = title.replace("Fontes:", "").strip()
            except:
                title = entry.title
            
            # Extrai hora de publicação
            try:
                pub_time = datetime(*entry.published_parsed[:6]).strftime("%H:%M")
            except:
                pub_time = ""
            
            noticias.append({
                "titulo": title,
                "hora": pub_time,
                "alerta": is_alert,
                "link": entry.get('link', '')
            })
            
        return noticias
        
    except Exception as e:
        print(f"Erro ao buscar notícias: {e}")
        return []


def parse_market_odds(game: Dict, bookmaker_priority: List[str] = None) -> Dict:
    """
    Extrai odds de mercado de um jogo.
    
    Args:
        game: Objeto de jogo da The Odds API
        bookmaker_priority: Lista de casas em ordem de preferência
    
    Returns:
        Dict com spread e total do mercado
    """
    if bookmaker_priority is None:
        bookmaker_priority = ['pinnacle', 'bet365', 'draftkings', 'fanduel']
    
    result = {
        'spread': 0.0,
        'spread_odds': 1.91,
        'total': 0.0,
        'total_over_odds': 1.91,
        'total_under_odds': 1.91,
        'bookmaker': None
    }
    
    home_team = game.get('home_team', '')
    
    for bookie in game.get('bookmakers', []):
        if bookie['key'] in bookmaker_priority:
            result['bookmaker'] = bookie['key']
            
            for market in bookie.get('markets', []):
                if market['key'] == 'spreads':
                    for outcome in market['outcomes']:
                        if outcome['name'] == home_team:
                            result['spread'] = outcome['point']
                            result['spread_odds'] = outcome['price']
                            break
                            
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            result['total'] = outcome['point']
                            result['total_over_odds'] = outcome['price']
                        elif outcome['name'] == 'Under':
                            result['total_under_odds'] = outcome['price']
                            
            if result['spread'] != 0.0:
                break
    
    return result


def find_team_stats(team_name: str, stats_dict: Dict) -> Dict:
    """
    Busca estatísticas de um time, lidando com variações de nome.
    
    Args:
        team_name: Nome do time (pode ser parcial)
        stats_dict: Dicionário de estatísticas
    
    Returns:
        Estatísticas do time ou valores padrão
    """
    default_stats = {
        'pace': 100.0,
        'off_rtg': 110.0,
        'def_rtg': 110.0,
        'net_rtg': 0.0,
        'efg': 0.54,
        'tov': 0.14,
        'orb': 0.25
    }
    
    # Busca exata
    if team_name in stats_dict:
        return stats_dict[team_name]
    
    # Busca parcial (ex: "Los Angeles Lakers" contém "Lakers")
    for key, value in stats_dict.items():
        if key in team_name or team_name in key:
            return value
    
    return default_stats
