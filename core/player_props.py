import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, leaguedashteamstats

class PlayerPropsEngine:
    def __init__(self):
        self.cache = {}
        self.team_defense = self._load_team_defense()

    def _load_team_defense(self):
        """Carrega DefRtg de todos os times para ajuste de matchup."""
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(
                season='2024-25', measure_type_detailed_defense='Base'
            ).get_data_frames()[0]
            # Cria dicionario {TEAM_ABBREVIATION: DEFRTG}
            return dict(zip(stats['TEAM_ABBREVIATION'], stats['DEF_RATING']))
        except:
            return {}

    def get_player_id(self, name):
        try:
            nba_players = players.get_players()
            found = [p for p in nba_players if name.lower() in p['full_name'].lower()]
            return found[0]['id'] if found else None
        except:
            return None

    def get_projection(self, player_name, opponent_abbr):
        """
        Gera projecao de Pontos baseada em:
        - 40% Media da Temporada
        - 40% Ultimos 5 Jogos
        - 20% Fator Matchup (Defesa do Oponente)
        """
        p_id = self.get_player_id(player_name)
        if not p_id: return None

        try:
            # Busca Logs
            gamelog = playergamelog.PlayerGameLog(player_id=p_id, season='2024-25')
            df = gamelog.get_data_frames()[0]
            
            if df.empty:
                 gamelog = playergamelog.PlayerGameLog(player_id=p_id, season='2023-24')
                 df = gamelog.get_data_frames()[0]
            
            if df.empty: return None

            # 1. Base Stats
            season_avg = df['PTS'].mean()
            last_5_avg = df.head(5)['PTS'].mean()

            # 2. Matchup Adjustment
            # Se a defesa do oponente for ruim (> 115), ganha bonus. Se boa (< 110), perde.
            opp_def = self.team_defense.get(opponent_abbr, 112.0)
            matchup_factor = (opp_def - 112.0) * 0.1 # Ex: Def 120 (+8) -> +0.8 pts

            # 3. Formula Final
            # Weighted: 0.45 Season + 0.45 Last5 + 0.1 Matchup
            # Simplificado: Media Ponderada + Ajuste Matchup
            weighted_avg = (season_avg * 0.5) + (last_5_avg * 0.5)
            projection = weighted_avg + matchup_factor

            return {
                "player": player_name,
                "projection": round(projection, 1),
                "season_avg": round(season_avg, 1),
                "last_5_avg": round(last_5_avg, 1),
                "matchup_adj": round(matchup_factor, 1),
                "opponent": opponent_abbr
            }

        except Exception as e:
            print(f"Erro prop engine: {e}")
            return None
