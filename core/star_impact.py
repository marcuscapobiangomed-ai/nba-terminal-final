# Dicionario de Impacto de Estrelas no Spread (Estimativa)
# Valores indicam quanto o time PIORA se o jogador nÃ£o jogar.

STARS_IMPACT = {
    # Boston Celtics
    "BOS": {
        "Jayson Tatum": 4.5,
        "Jaylen Brown": 2.5,
        "Kristaps Porzingis": 2.0
    },
    # Denver Nuggets
    "DEN": {
        "Nikola Jokic": 7.5,
        "Jamal Murray": 3.0,
        "Aaron Gordon": 1.5
    },
    # Milwaukee Bucks
    "MIL": {
        "Giannis Antetokounmpo": 6.5,
        "Damian Lillard": 3.5,
        "Khris Middleton": 1.5
    },
    # Philadelphia 76ers
    "PHI": {
        "Joel Embiid": 7.0,
        "Tyrese Maxey": 3.0,
        "Paul George": 2.5
    },
    # Phoenix Suns
    "PHX": {
        "Kevin Durant": 4.0,
        "Devin Booker": 3.5,
        "Bradley Beal": 2.0
    },
    # LA Lakers
    "LAL": {
        "LeBron James": 4.5,
        "Anthony Davis": 5.0,
        "Austin Reaves": 1.0
    },
    # Golden State Warriors
    "GSW": {
        "Stephen Curry": 6.0,
        "Draymond Green": 2.5
    },
    # Dallas Mavericks
    "DAL": {
        "Luka Doncic": 7.0,
        "Kyrie Irving": 3.0
    },
    # Oklahoma City Thunder
    "OKC": {
        "S. Gilgeous-Alexander": 6.0,
        "Chet Holmgren": 2.5,
        "Jalen Williams": 2.0
    },
    # Minnesota Timberwolves
    "MIN": {
        "Anthony Edwards": 4.5,
        "Rudy Gobert": 2.5,
        "Karl-Anthony Towns": 3.0
    },
     # New York Knicks
    "NYK": {
        "Jalen Brunson": 5.0,
        "Julius Randle": 2.5,
        "OG Anunoby": 2.0
    },
     # Miami Heat
    "MIA": {
        "Jimmy Butler": 4.0,
        "Bam Adebayo": 3.0
    },
     # LA Clippers
    "LAC": {
        "Kawhi Leonard": 4.5,
        "James Harden": 3.0
    }
}

def get_team_stars(team_abbr: str):
    """Retorna o dicionario de estrelas para um time, ou vazio se nao encontrado."""
    return STARS_IMPACT.get(team_abbr, {})
