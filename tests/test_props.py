import sys
import os

# Add root project path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.player_props import PlayerPropsEngine

def test_engine():
    print("Initializing Engine...")
    engine = PlayerPropsEngine()
    
    player = "LeBron James"
    opponent = "GSW"
    
    print(f"\nTesting Projection for {player} vs {opponent}...")
    
    # Test Points
    print("\n--- POINTS ---")
    proj_pts = engine.get_projection(player, opponent, "PTS")
    if proj_pts:
        print(f"Projection: {proj_pts['projection']} {proj_pts['stat_type']}")
        print(f"Season Avg: {proj_pts['season_avg']}")
        print(f"L5 Avg: {proj_pts['last_5_avg']}")
        print(f"Logs: {len(proj_pts['last_5_logs'])} games found")
    else:
        print("Failed to get POINTS projection")

    # Test Assists
    print("\n--- ASSISTS ---")
    proj_ast = engine.get_projection(player, opponent, "AST")
    if proj_ast:
        print(f"Projection: {proj_ast['projection']} {proj_ast['stat_type']}")
        print(f"Season Avg: {proj_ast['season_avg']}")
    else:
        print("Failed to get ASSISTS projection")

if __name__ == "__main__":
    test_engine()
