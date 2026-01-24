import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from core.data_fetcher import get_team_stats

class PlayerPropsEngine:
    def __init__(self):
        self.cache = {}
        self.team_defense = self._load_team_defense()

    def _load_team_defense(self):
        """Carrega DefRtg de todos os times para ajuste de matchup."""
        try:
            stats = get_team_stats()
            # Cria dicionario {TEAM_ABBREVIATION: DEFRTG}
            defense_map = {}
            for _, data in stats.items():
                if 'abbr' in data:
                    defense_map[data['abbr']] = data['def_rtg']
            return defense_map
        except:
            return {}

    def get_player_id(self, name):
        try:
            nba_players = players.get_players()
            found = [p for p in nba_players if name.lower() in p['full_name'].lower()]
            return found[0]['id'] if found else None
        except:
            return None

    def get_projection(self, player_name, opponent_abbr, stat_type='PTS'):
        """
        Gera projecao baseada em:
        - 50% Media da Temporada
        - 50% Ultimos 5 Jogos
        - Ajuste Matchup (Defesa do Oponente)
        """
        p_id = self.get_player_id(player_name)
        if not p_id: return None

        # Map display name to Dataframe Column
        stat_map = {
            'PTS': 'PTS',
            'REB': 'REB',
            'AST': 'AST',
            '3PM': 'FG3M',
            'PRA': 'PRA' # Special case handled below
        }
        col = stat_map.get(stat_type, 'PTS')

        try:
            # Busca Logs
            gamelog = playergamelog.PlayerGameLog(player_id=p_id, season='2024-25')
            df = gamelog.get_data_frames()[0]
            
            if df.empty:
                 gamelog = playergamelog.PlayerGameLog(player_id=p_id, season='2023-24')
                 df = gamelog.get_data_frames()[0]
            
            if df.empty: return None

            # Calculate PRA if needed
            if stat_type == 'PRA':
                df['PRA'] = df['PTS'] + df['REB'] + df['AST']

            # 1. Base Stats
            season_avg = df[col].mean()
            last_5_avg = df.head(5)[col].mean()

            # 2. Matchup Adjustment
            # General proxy: High DefRtg (bad defense) -> Bonus
            # Low DefRtg (good defense) -> Malus
            opp_def = self.team_defense.get(opponent_abbr, 112.0)
            
            # Scale factor based on stat magnitude
            # For 25 pts, 10% diff is 2.5. For 5 rebs, 10% is 0.5.
            # Using percentage-based adjustment is safer.
            
            base_def = 112.0 # League average approx
            diff_factor = (opp_def - base_def) / 100.0 # Ex: (120 - 112) / 100 = 0.08 (+8%)
            
            # Apply to projection
            # Weighted: 0.5 Season + 0.5 Last5
            weighted_avg = (season_avg * 0.5) + (last_5_avg * 0.5)
            
            matchup_adj = weighted_avg * diff_factor
            projection = weighted_avg + matchup_adj

            # Prepare Last 5 logs for display
            last_5_df = df.head(5).copy()
            last_5_logs = []
            for _, row in last_5_df.iterrows():
                last_5_logs.append({
                    'date': row['GAME_DATE'],
                    'matchup': row['MATCHUP'],
                    'value': row[col]
                })

            return {
                "player": player_name,
                "stat_type": stat_type,
                "projection": round(projection, 1),
                "season_avg": round(season_avg, 1),
                "last_5_avg": round(last_5_avg, 1),
                "matchup_adj": round(matchup_adj, 1),
                "opponent": opponent_abbr,
                "last_5_logs": last_5_logs
            }

        except Exception as e:
            print(f"Erro prop engine: {e}")
            return None
