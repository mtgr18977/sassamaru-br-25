import csv
import re
from collections import Counter

# Set of known/official team names (add more as needed)
OFFICIAL_TEAMS = {
    "América-MG", "América-RN", "AméricaEmpateRN", "América", "América Mineiro",
    "Athletico-PR", "Atlético-GO", "Atlético-MG", "Atlético Paranaense", "Atlético Goianiense", "Atlético Mineiro",
    "Bahia", "Botafogo", "Botafogo-SP", "Bragantino", "Brasiliense", "Ceará", "Chapecoense", "Corinthians",
    "Coritiba", "Criciúma", "Cruzeiro", "CSA", "Cuiabá", "Figueirense", "flamengo", "Fluminense", "Fortaleza",
    "Goiás", "Grêmio", "Guarani", "internacional", "Ipatinga", "Joinville", "Juventude", "Mirassol", "Náutico",
    "Palmeiras", "Paraná", "Paysandu", "Ponte Preta", "Portuguesa", "Santa Cruz", "Santos", "Santo André",
    "Santo", "Santos", "Santos FC", "Santos Futebol Clube", "São Caetano", "São Paulo", "Sport", "Vasco",
    "vasco", "vasco", "Vitoria", "Vitória", "Vitória da Conquista", "Avaí", "Avaí FC"
}

# Normalization mapping (expand as needed)
NORMALIZATION_MAP = {
    "vasco": "Vasco",
    "internacional": "internacional",
    "corinthians": "Corinthians",
    "santo": "Santos",
    "vitoria": "Vitória",
    "figueirense": "Figueirense",
    "bahia": "Bahia",
    "flamengo": "flamengo",
    "fluminense": "Fluminense",
    "gremio": "Grêmio",
    "gremio prudente": "Grêmio Prudente",
    "ponte preta": "Ponte Preta",
    "sao paulo": "São Paulo",
    "sao caetano": "São Caetano",
    "juventude": "Juventude",
    "cruzeiro": "Cruzeiro",
    "goias": "Goiás",
    "guarani": "Guarani",
    "parana": "Paraná",
    "criciuma": "Criciúma",
    "avai": "Avaí",
    "fortaleza": "Fortaleza",
    "mirassol": "Mirassol",
    "americaempatern": "América-RN",
    "america mineiro": "América-MG",
    "america": "América-MG",
    "cap": "Athletico-PR",
    "cam": "Atlético-MG",
    "atletico goianense": "Atlético-GO",
    "atletico mineiro": "Atlético-MG",
    "atletico paranaense": "Athletico-PR",
    "cuiaba": "Cuiabá",
    "nautico": "Náutico",
    "chapecoense": "Chapecoense",
    "botafogo": "Botafogo",
    "bragantino": "Bragantino",
    "ceara": "Ceará",
    "portuguesa": "Portuguesa",
    "santa cruz": "Santa Cruz",
    "sport": "Sport",
    "figueirense": "Figueirense",
    "empate": "Empate",
    # Add more as needed
}

def normalize_team(name):
    n = name.strip().lower()
    return NORMALIZATION_MAP.get(n, name.strip())

def main():
    filename = "campeonato-brasileiro-full.csv"
    unique_teams = set()
    invalid_teams = set()
    malformed_rows = []
    non_integer_goals = []
    row_count = 0

    with open(filename, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for i, row in enumerate(reader, start=2):
            row_count += 1
            if len(row) != 5:
                malformed_rows.append((i, row))
                continue
            mandante, visitante, _, gols_mandante, gols_visitante = row
            unique_teams.add(mandante.strip())
            unique_teams.add(visitante.strip())
            # Validate goals
            if not gols_mandante.isdigit() or not gols_visitante.isdigit():
                non_integer_goals.append((i, gols_mandante, gols_visitante))
    # Normalize and validate
    normalized_teams = {team: normalize_team(team) for team in unique_teams}
    for team, norm in normalized_teams.items():
        if norm not in OFFICIAL_TEAMS and norm.lower() != "empate":
            invalid_teams.add(team)

    print("=== Unique Team Names (raw) ===")
    for team in sorted(unique_teams):
        print(team)
    print("\n=== Normalization Mapping ===")
    for team, norm in sorted(normalized_teams.items()):
        print(f"{team} -> {norm}")
    print("\n=== Invalid/Unknown Teams After Normalization ===")
    for team in sorted(invalid_teams):
        print(team)
    print(f"\nTotal rows: {row_count}")
    print(f"Malformed rows: {len(malformed_rows)}")
    if malformed_rows:
        print("First 5 malformed rows:")
        for r in malformed_rows[:5]:
            print(r)
    print(f"Rows with non-integer goals: {len(non_integer_goals)}")
    if non_integer_goals:
        print("First 5 non-integer goal rows:")
        for r in non_integer_goals[:5]:
            print(r)

if __name__ == "__main__":
    main()
