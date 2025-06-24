"""
Módulo de previsão de partidas de futebol utilizando modelos híbridos Poisson + Elo.
Inclui funções para calcular forças de ataque/defesa, vantagens de casa, prever resultados e atualizar ratings Elo.
"""
import math
import pandas as pd

ELO_RATING_INICIAL = 1500
ELO_K_FACTOR_BASE = 30
ELO_VANTAGEM_CASA_PADRAO = 30
POISSON_MAX_GOLS = 8
ELO_INFLUENCE = 0.10

def poisson(lmbda, k):
    """
    Calcula a probabilidade de k ocorrências para uma média lmbda usando a distribuição de Poisson.
    """
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)

def calcular_forcas_poisson(df):
    """
    Calcula as forças de ataque e defesa (em casa e fora) para cada time usando a média de gols,
    com base no modelo de Poisson, e retorna também as médias da liga.
    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os jogos, mandantes, visitantes e gols.
    Retorna:
        tuple: (dicionário de forças por time, dicionário de médias da liga)
    """
    times = pd.unique(df['mandante'].tolist() + df['visitante'].tolist())
    forcas = {}
    # Médias da liga
    media_gols_casa = df['gols_mandante'].mean()
    media_gols_fora = df['gols_visitante'].mean()
    medias_liga = {'gols_casa': media_gols_casa, 'gols_fora': media_gols_fora}
    # Forças de ataque/defesa para cada time
    for time in times:
        # Ataque em casa: gols marcados em casa / jogos em casa / média da liga
        jogos_casa = df[df['mandante'] == time]
        jogos_fora = df[df['visitante'] == time]
        ataque_casa = (jogos_casa['gols_mandante'].mean() / media_gols_casa) if not jogos_casa.empty and media_gols_casa > 0 else 1.0
        defesa_casa = (jogos_casa['gols_visitante'].mean() / media_gols_fora) if not jogos_casa.empty and media_gols_fora > 0 else 1.0
        ataque_fora = (jogos_fora['gols_visitante'].mean() / media_gols_fora) if not jogos_fora.empty and media_gols_fora > 0 else 1.0
        defesa_fora = (jogos_fora['gols_mandante'].mean() / media_gols_casa) if not jogos_fora.empty and media_gols_casa > 0 else 1.0
        forcas[time] = {
            'ataque_casa': ataque_casa,
            'defesa_casa': defesa_casa,
            'ataque_fora': ataque_fora,
            'defesa_fora': defesa_fora
        }
    return forcas, medias_liga

def calcular_vantagens_casa(df):
    """
    Calcula a vantagem de jogar em casa para cada time com base no saldo médio de gols como mandante.
    Parâmetros:
        df (pd.DataFrame): DataFrame contendo os jogos, mandantes, visitantes e gols.
    Retorna:
        dict: Dicionário com a vantagem de casa (em pontos Elo) para cada time.
    """
    vantagens = {}
    times = pd.unique(df['mandante'])
    for time in times:
        jogos_casa = df[df['mandante'] == time]
        saldo_de_gols_medio = (jogos_casa['gols_mandante'] - jogos_casa['gols_visitante']).mean()
        if saldo_de_gols_medio and saldo_de_gols_medio > 0:
            vantagem_rating = 60 * (saldo_de_gols_medio ** 0.8)
        else:
            vantagem_rating = 0
        vantagens[time] = vantagem_rating
    return vantagens

def prever_partida_hibrido(time_casa, time_visitante, context):
    """
    Prevê o resultado de uma partida usando um modelo híbrido Poisson + Elo.

    Parâmetros:
        time_casa (str): Nome do time mandante.
        time_visitante (str): Nome do time visitante.
        context (dict): Dicionário com as chaves:
            - 'elo_ratings': dict com ratings Elo dos times
            - 'forcas_poisson': dict com forças de ataque/defesa dos times
            - 'medias_liga': dict com médias de gols da liga
            - 'vantagens_casa': dict com vantagens de casa dos times

    Retorna:
        dict: Resultados previstos da partida.
    """
    elo_ratings = context['elo_ratings']
    forcas_poisson = context['forcas_poisson']
    medias_liga = context['medias_liga']
    vantagens_casa = context['vantagens_casa']

    ataque_casa = forcas_poisson[time_casa]['ataque_casa']
    defesa_visitante = forcas_poisson[time_visitante]['defesa_fora']
    gols_base_casa = ataque_casa * defesa_visitante * medias_liga['gols_casa']
    ataque_visitante = forcas_poisson[time_visitante]['ataque_fora']
    defesa_casa = forcas_poisson[time_casa]['defesa_casa']
    gols_base_visitante = ataque_visitante * defesa_casa * medias_liga['gols_fora']
    rating_casa = elo_ratings.get(time_casa, ELO_RATING_INICIAL)
    rating_visitante = elo_ratings.get(time_visitante, ELO_RATING_INICIAL)
    vantagem_time_casa = vantagens_casa.get(time_casa, ELO_VANTAGEM_CASA_PADRAO)
    elo_diff = (rating_casa + vantagem_time_casa) - rating_visitante
    fator_ajuste_casa = 1 + (elo_diff / 1000) * ELO_INFLUENCE
    fator_ajuste_visitante = 1 - (elo_diff / 1000) * ELO_INFLUENCE
    gols_finais_casa = gols_base_casa * max(0.1, fator_ajuste_casa)
    gols_finais_visitante = gols_base_visitante * max(0.1, fator_ajuste_visitante)

    prob_vitoria_casa = 0
    prob_empate = 0
    prob_vitoria_visitante = 0
    for g_c in range(POISSON_MAX_GOLS + 1):
        for g_v in range(POISSON_MAX_GOLS + 1):
            prob_placar = poisson(gols_finais_casa, g_c) * poisson(gols_finais_visitante, g_v)
            if g_c > g_v:
                prob_vitoria_casa += prob_placar
            elif g_c == g_v:
                prob_empate += prob_placar
            else:
                prob_vitoria_visitante += prob_placar

    total_prob = prob_vitoria_casa + prob_empate + prob_vitoria_visitante
    probs = [prob_vitoria_casa, prob_empate, prob_vitoria_visitante]
    idx_max = probs.index(max(probs))
    palpite = ['Mandante', 'Empate', 'Visitante'][idx_max]
    return {
        'Mandante': time_casa.title(),
        'Visitante': time_visitante.title(),
        'Elo Mandante': int(rating_casa),
        'Elo Visitante': int(rating_visitante),
        'Gols Esp. Mandante': round(gols_finais_casa, 2),
        'Gols Esp. Visitante': round(gols_finais_visitante, 2),
        'P(Mandante)%': f"{prob_vitoria_casa / total_prob * 100:.1f}",
        'P(Empate)%': f"{prob_empate / total_prob * 100:.1f}",
        'P(Visitante)%': f"{prob_vitoria_visitante / total_prob * 100:.1f}",
        'Palpite': palpite
    }

def atualizar_ratings_elo(rating_c, rating_v, placar_c, placar_v, vantagem_c):
    """
    Atualiza os ratings Elo dos times mandante e visitante após uma partida.
    rating_c: Elo do mandante antes do jogo
    rating_v: Elo do visitante antes do jogo
    placar_c: Gols do mandante
    placar_v: Gols do visitante
    vantagem_c: Vantagem de casa (em pontos Elo)
    """
    # Resultado real
    if placar_c > placar_v:
        resultado_real = 1.0
    elif placar_c == placar_v:
        resultado_real = 0.5
    else:
        resultado_real = 0.0

    # Expectativa de resultado
    exp_c = 1 / (1 + 10 ** ((rating_v - (rating_c + vantagem_c)) / 400))
    exp_v = 1 - exp_c

    # K pode ser ajustado conforme a diferença de gols
    diff_gols = abs(placar_c - placar_v)
    k = ELO_K_FACTOR_BASE * (1 + 0.5 * max(0, diff_gols - 1))

    novo_rating_c = rating_c + k * (resultado_real - exp_c)
    novo_rating_v = rating_v + k * ((1 - resultado_real) - exp_v)
    return novo_rating_c, novo_rating_v

def main():
    df = pd.read_csv('sassamaru-br-25/br-25.csv')
    df['mandante'] = df['mandante'].str.strip().str.lower()
    df['visitante'] = df['visitante'].str.strip().str.lower()
    df['gols_mandante'] = df['gols_mandante'].astype(int)
    df['gols_visitante'] = df['gols_visitante'].astype(int)
    forcas_poisson, medias_liga = calcular_forcas_poisson(df)
    vantagens_casa = calcular_vantagens_casa(df)
    elo_ratings = {}
    for _, partida in df.iterrows():
        time_c, time_v = partida['mandante'], partida['visitante']
        placar_c, placar_v = partida['gols_mandante'], partida['gols_visitante']
        rating_c = elo_ratings.get(time_c, ELO_RATING_INICIAL)
        rating_v = elo_ratings.get(time_v, ELO_RATING_INICIAL)
        vantagem_c = vantagens_casa.get(time_c, ELO_VANTAGEM_CASA_PADRAO)
        novo_rating_c, novo_rating_v = atualizar_ratings_elo(rating_c, rating_v, placar_c, placar_v, vantagem_c)
        elo_ratings[time_c], elo_ratings[time_v] = novo_rating_c, novo_rating_v

    jogos = [
        ('internacional','vitoria'),
        ('bahia','atletico mineiro'),
        ('corinthians','bragantino'),
        ('cruzeiro','gremio'),
        ('fortaleza','ceara'),
        ('juventude','sport'),
        ('flamengo','sao paulo'),
        ('vasco','botafogo'),
        ('santos','palmeiras'),
        ('mirassol','fluminense')
    ]
    resultados = []
    context = {
        'elo_ratings': elo_ratings,
        'forcas_poisson': forcas_poisson,
        'medias_liga': medias_liga,
        'vantagens_casa': vantagens_casa
    }
    for casa, visita in jogos:
        try:
            r = prever_partida_hibrido(casa, visita, context)
            resultados.append(r)
        except Exception as e:
            print(f"Erro na previsão {casa} x {visita}: {e}")
    df_resultados = pd.DataFrame(resultados)

    # Renomear e reordenar colunas para melhor apresentação em markdown
    df_resultados = df_resultados.rename(columns={
        'Mandante': 'Mandante',
        'Visitante': 'Visitante',
        'Gols Esp. Mandante': 'Gols Mandante',
        'Gols Esp. Visitante': 'Gols Visitante',
        'P(Mandante)%': 'Prob Mandante (%)',
        'P(Empate)%': 'Prob Empate (%)',
        'P(Visitante)%': 'Prob Visitante (%)',
        'Palpite': 'Palpite'
    })
    colunas = [
        'Mandante', 'Visitante',
        'Gols Mandante', 'Gols Visitante',
        'Prob Mandante (%)', 'Prob Empate (%)', 'Prob Visitante (%)',
        'Palpite'
    ]
    # Garantir que as colunas existem
    colunas = [c for c in colunas if c in df_resultados.columns]
    df_resultados = df_resultados[colunas]

    # Arredondar valores numéricos
    df_resultados['Gols Mandante'] = df_resultados['Gols Mandante'].astype(float).round(2)
    df_resultados['Gols Visitante'] = df_resultados['Gols Visitante'].astype(float).round(2)
    df_resultados['Prob Mandante (%)'] = df_resultados['Prob Mandante (%)'].astype(float).round(1)
    df_resultados['Prob Empate (%)'] = df_resultados['Prob Empate (%)'].astype(float).round(1)
    df_resultados['Prob Visitante (%)'] = df_resultados['Prob Visitante (%)'].astype(float).round(1)

    # Adicionar título antes da tabela
    print("# Previsão de Jogos - Modelo Híbrido Poisson + Elo\n")
    print(df_resultados.to_markdown(index=False))

if __name__ == "__main__":
    main()
