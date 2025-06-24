import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

# Clubes-foco
clubes_foco = [
    'flamengo', 'fluminense', 'vasco', 'botafogo',
    'palmeiras', 'sao paulo', 'santos', 'corinthians',
    'atletico mineiro', 'cruzeiro', 'gremio', 'internacional'
]

# Carregar e normalizar dados
df = pd.read_csv('sassamaru-br-25\campeonato-brasileiro-full.csv', sep=',', encoding='utf-8')
df['mandante'] = df['mandante'].str.strip().str.lower()
df['visitante'] = df['visitante'].str.strip().str.lower()
df['vencedor'] = df['vencedor'].str.strip().str.lower()

if 'data' in df.columns:
    df['data'] = pd.to_datetime(df['data'], dayfirst=True)
    df = df.sort_values('data')
    df['ano'] = df['data'].dt.year
else:
    df['ano'] = 2000

# Parâmetros ELO
ELO_INICIAL = 1500
K_BASE = 20
VANTAGEM_CASA = 0

def calcular_vantagens(df):
    v = {}
    for t in pd.unique(df['mandante']):
        saldo = (df[df['mandante']==t]['mandante_Placar'] - df[df['mandante']==t]['visitante_Placar']).mean()
        v[t] = 60 * (saldo**0.8) if saldo > 0 else 0
    return v

def atualiza_elo(r_c, r_v, g_c, g_v, v_c):
    if g_c > g_v:
        res, diff = 1.0, g_c - g_v
    elif g_c < g_v:
        res, diff = 0.0, g_v - g_c
    else:
        res, diff = 0.5, 0
    k = K_BASE * math.log(diff + 1) if res != 0.5 else K_BASE
    e_c = 1 / (1 + 10 ** ((r_v - (r_c + v_c)) / 400))
    return r_c + k * (res - e_c), r_v + k * ((1 - res) - (1 - e_c))

anos_validos = sorted(df['ano'].unique())
elos = {t: {ano: ELO_INICIAL for ano in anos_validos} for t in clubes_foco}
elo_atual = {t: ELO_INICIAL for t in clubes_foco}
vant = calcular_vantagens(df)
for _, row in df.iterrows():
    ano = row['ano']
    m, v = row['mandante'], row['visitante']
    if m in clubes_foco or v in clubes_foco:
        em = elo_atual.get(m, ELO_INICIAL)
        ev = elo_atual.get(v, ELO_INICIAL)
        nc, nv = atualiza_elo(em, ev, row['mandante_Placar'], row['visitante_Placar'], vant.get(m, VANTAGEM_CASA))
        elo_atual[m], elo_atual[v] = nc, nv
        if m in clubes_foco:
            elos[m][ano] = nc
        if v in clubes_foco:
            elos[v][ano] = nv
df_elos = pd.DataFrame(elos).T[anos_validos].T  # anos como índice, clubes como colunas

# Insights
crescimento = df_elos.iloc[-1] - df_elos.iloc[0]
maior_crescimento = crescimento.idxmax()
maior_crescimento_valor = crescimento.max()

# Percentual de vitórias mandante
df_vit_mandante = df[df['mandante'].isin(clubes_foco)]
percent_vit = (df_vit_mandante['vencedor'] == df_vit_mandante['mandante']).groupby(df_vit_mandante['mandante']).mean()

# Percentual de empates como visitante
empates_fora = df[(df['visitante'].isin(clubes_foco)) & (df['vencedor'] == '-')].groupby('visitante').size()
total_fora = df[df['visitante'].isin(clubes_foco)].groupby('visitante').size()
percent_empate_fora = (empates_fora / total_fora).fillna(0)

# Confrontos grandes mais desequilibrados
confrontos = df[df['mandante'].isin(clubes_foco) & df['visitante'].isin(clubes_foco)]
grupo = confrontos.groupby(['mandante','visitante']).agg({
    'mandante_Placar':'sum','visitante_Placar':'sum','vencedor':'count'
})
grupo['diff_media_gols'] = (grupo['mandante_Placar'] - grupo['visitante_Placar']).abs() / grupo['vencedor']
top_confrontos = grupo['diff_media_gols'].sort_values(ascending=False).head(5)

# Markdown de insights
print(f"## Insights sobre os grandes clubes do Brasileirão\n")
print(f"- Clube com maior crescimento de Elo no período analisado: **{maior_crescimento.title()}** (+{maior_crescimento_valor:.2f} pontos)")
print(f"- Percentual de vitórias como mandante:\n{percent_vit.sort_values(ascending=False).to_markdown()}")
print(f"- Percentual de empates como visitante:\n{percent_empate_fora.sort_values(ascending=False).to_markdown()}")
print(f"- Confrontos grandes com maior desequilíbrio (diferença média de gols):\n{top_confrontos.to_markdown()}")
print("\n# Gráfico de evolução do Elo")
plt.figure(figsize=(12,7))
for clube in clubes_foco:
    plt.plot(df_elos.index, df_elos[clube], label=clube.title())
plt.title('Evolução do Elo dos Grandes Clubes (histórico completo)')
plt.xlabel('Ano')
plt.ylabel('Rating Elo')
plt.legend()
plt.grid(True)
plt.show()
