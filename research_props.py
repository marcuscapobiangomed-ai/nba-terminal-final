from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
import pandas as pd

# 1. Encontrar ID do LeBron James
print("Buscando ID do LeBron...")
nba_players = players.get_players()
lebron = [p for p in nba_players if p['full_name'] == 'LeBron James'][0]
p_id = lebron['id']
print(f"LeBron ID: {p_id}")

# 2. Buscar Game Log da temporada atual (2024-25)
SEASON = '2024-25'
print(f"Buscando logs da temporada {SEASON}...")

try:
    gamelog = playergamelog.PlayerGameLog(player_id=p_id, season=SEASON)
    df = gamelog.get_data_frames()[0]
    
    if df.empty:
        print("DataFrame vazio. Tentando 2023-24 para teste...")
        gamelog = playergamelog.PlayerGameLog(player_id=p_id, season='2023-24')
        df = gamelog.get_data_frames()[0]

    if not df.empty:
        print(f"Sucesso! {len(df)} jogos encontrados.")
        print("\nUltimos 5 Jogos (Pts, Reb, Ast):")
        cols = ['GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'MIN']
        print(df[cols].head(5))
        
        # Calcular Medias
        last_5 = df.head(5)
        print("\nMedias:")
        print(f"Temporada (PTS): {df['PTS'].mean():.1f}")
        print(f"Ultimos 5 (PTS): {last_5['PTS'].mean():.1f}")
    else:
        print("Nao foi possivel obter dados nem de 23-24.")

except Exception as e:
    print(f"Erro na API: {e}")
