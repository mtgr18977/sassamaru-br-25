import pandas as pd
import math

# Parâmetros do Elo
ELO_INICIAL = 1500
K_BASE = 20
VANTAGEM_CASA = 0

# Clubes-foco (ajuste conforme seu critério)
clubes_foco = [
    'flamengo', 'fluminense', 'vasco', 'botafogo',
    'palmeiras', 'sao paulo', 'santos', 'corinthians',
    'atletico mineiro', 'cruzeiro', 'gremio', 'internacional'
]

# Carregar e normalizar dados
df = pd.read_csv('sassamaru-br-25\campeonato-brasileiro-full.csv', sep=',', encoding='utf-8')
df['mandante'] = df['mandante'].str.strip().str.lower()
df['visitante'] = df['visitante'].str.strip().str.lower()
df['resultado'] = df['resultado'].str.strip().str.lower()

def calcular_vantagens(df):
    v = {}
    for t in pd.unique(df['mandante']):
        saldo = (df[df['mandante']==t]['gols_mandante'] - df[df['mandante']==t]['gols_visitante']).mean()
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

# Calcula vantagens de mando
vant = calcular_vantagens(df)

# Inicializa Elo
elo = {}

# Processa cada jogo na ordem do arquivo
for _, r in df.iterrows():
    m, v = r['mandante'], r['visitante']
    em = elo.get(m, ELO_INICIAL)
    ev = elo.get(v, ELO_INICIAL)
    nc, nv = atualiza_elo(em, ev, r['gols_mandante'], r['gols_visitante'], vant.get(m, VANTAGEM_CASA))
    elo[m], elo[v] = nc, nv

# Seleciona os Elos finais dos clubes-foco
elos_foco = {club: elo.get(club, ELO_INICIAL) for club in clubes_foco}
elos_ordenado = dict(sorted(elos_foco.items(), key=lambda x: x[1], reverse=True))

# Mostra a tabela Markdown
import pandas as pd
df_elos = pd.DataFrame(list(elos_ordenado.items()), columns=['Clube', 'Elo Final'])
print(df_elos.to_markdown(index=False))
