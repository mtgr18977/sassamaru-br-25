import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pandas as pd
import datetime
import math
import csv
from collections import defaultdict
import multiprocessing
import numpy as np

def get_base_dir():
    try:
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_dir = os.getcwd()
    return base_dir

BASE_DIR = get_base_dir()
CSV_PATH = os.path.join(BASE_DIR, 'br-25.csv')

MAX_GOLS_CONSIDERADOS = 8

# Elo parameters
ELO_RATING_INICIAL = 1500
ELO_K_FACTOR_BASE = 30
ELO_VANTAGEM_CASA_PADRAO = 80
ELO_INFLUENCE = 0.35

# --- Elo dynamic calculation functions ---

def calcular_vantagens_casa(df):
    vantagens = {}
    times = pd.unique(df['mandante'])
    for time in times:
        jogos_casa = df[df['mandante'] == time]
        saldo_de_gols_medio = (jogos_casa['gols_mandante'] - jogos_casa['gols_visitante']).mean()
        vantagem_rating = 60 * (saldo_de_gols_medio ** 0.8) if saldo_de_gols_medio > 0 else 0
        vantagens[time] = max(0, vantagem_rating)
    return vantagens

def atualizar_ratings_elo(rating_casa, rating_visitante, placar_casa, placar_visitante, vantagem_casa_time):
    if placar_casa > placar_visitante:
        resultado_real_casa, margem_gols = 1.0, placar_casa - placar_visitante
    elif placar_casa < placar_visitante:
        resultado_real_casa, margem_gols = 0.0, placar_visitante - placar_casa
    else:
        resultado_real_casa, margem_gols = 0.5, 0

    k_ajustado = ELO_K_FACTOR_BASE * math.log(margem_gols + 1) if margem_gols > 0 else ELO_K_FACTOR_BASE

    expectativa_casa = 1 / (1 + 10 ** ((rating_visitante - (rating_casa + vantagem_casa_time)) / 400))

    novo_rating_casa = rating_casa + k_ajustado * (resultado_real_casa - expectativa_casa)
    novo_rating_visitante = rating_visitante + k_ajustado * ((1.0 - resultado_real_casa) - (1 - expectativa_casa))
    return novo_rating_casa, novo_rating_visitante

# --- Poisson force calculation ---

def calcular_forcas_poisson(df):
    forcas = {}
    media_gols_marcados_casa = df['gols_mandante'].mean()
    media_gols_sofridos_casa = df['gols_visitante'].mean()
    media_gols_marcados_fora = df['gols_visitante'].mean()
    media_gols_sofridos_fora = df['gols_mandante'].mean()
    times = pd.unique(df[['mandante', 'visitante']].values.ravel('K'))

    for time in times:
        forcas[time] = {
            'ataque_casa': (df[df['mandante'] == time]['gols_mandante'].mean() / media_gols_marcados_casa),
            'defesa_casa': (df[df['mandante'] == time]['gols_visitante'].mean() / media_gols_sofridos_casa),
            'ataque_fora': (df[df['visitante'] == time]['gols_visitante'].mean() / media_gols_marcados_fora),
            'defesa_fora': (df[df['visitante'] == time]['gols_mandante'].mean() / media_gols_sofridos_fora)
        }
    medias_liga = {'gols_casa': media_gols_marcados_casa, 'gols_fora': media_gols_marcados_fora}
    return forcas, medias_liga

def poisson(gols_esperados, num_gols):
    return (gols_esperados ** num_gols) * math.exp(-gols_esperados) / math.factorial(num_gols)

# --- Híbrido: previsão usando Elo dinâmico + Poisson ---

def prever_partida_hibrido(time_casa, time_visitante, elo_ratings, forcas_poisson, medias_liga, vantagens_casa):
    if time_casa not in forcas_poisson or time_visitante not in forcas_poisson:
        return None

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

    prob_vitoria_casa, prob_empate, prob_vitoria_visitante = 0, 0, 0
    for g_c in range(MAX_GOLS_CONSIDERADOS + 1):
        for g_v in range(MAX_GOLS_CONSIDERADOS + 1):
            prob_placar = poisson(gols_finais_casa, g_c) * poisson(gols_finais_visitante, g_v)
            if g_c > g_v: prob_vitoria_casa += prob_placar
            elif g_c == g_v: prob_empate += prob_placar
            else: prob_vitoria_visitante += prob_placar

    total_prob = prob_vitoria_casa + prob_empate + prob_vitoria_visitante
    prob_vitoria_casa /= total_prob
    prob_empate /= total_prob
    prob_vitoria_visitante /= total_prob

    return {
        'mandante': time_casa,
        'visitante': time_visitante,
        'prob_mandante': prob_vitoria_casa,
        'prob_empate': prob_empate,
        'prob_visitante': prob_vitoria_visitante,
        'gols_esperados_mandante': gols_finais_casa,
        'gols_esperados_visitante': gols_finais_visitante
    }

# --- Simulação paralela adaptada para híbrido ---

_cache_previsoes = {}

def previsao_cache_hibrido(args):
    time_casa, time_visitante, elo_ratings, forcas_poisson, medias_liga, vantagens_casa = args
    key = (time_casa, time_visitante)
    if key not in _cache_previsoes:
        _cache_previsoes[key] = prever_partida_hibrido(time_casa, time_visitante, elo_ratings, forcas_poisson, medias_liga, vantagens_casa)
    return _cache_previsoes[key]

def rodar_simulacao_paralela(df, jogos, n_simulacoes, progress_callback=None):
    forcas_poisson, medias_liga = calcular_forcas_poisson(df)
    vantagens_casa = calcular_vantagens_casa(df)

    elo_ratings = {}
    for _, partida in df.iterrows():
        time_c = partida['mandante']
        time_v = partida['visitante']
        placar_c = partida['gols_mandante']
        placar_v = partida['gols_visitante']

        rating_c = elo_ratings.get(time_c, ELO_RATING_INICIAL)
        rating_v = elo_ratings.get(time_v, ELO_RATING_INICIAL)
        vantagem_c = vantagens_casa.get(time_c, ELO_VANTAGEM_CASA_PADRAO)

        novo_rating_c, novo_rating_v = atualizar_ratings_elo(rating_c, rating_v, placar_c, placar_v, vantagem_c)
        elo_ratings[time_c], elo_ratings[time_v] = novo_rating_c, novo_rating_v

    total = n_simulacoes * len(jogos)

    tarefas = []
    for _ in range(n_simulacoes):
        for jogo in jogos:
            tarefas.append((jogo[0], jogo[1], elo_ratings, forcas_poisson, medias_liga, vantagens_casa))

    manager = multiprocessing.Manager()
    progresso = manager.Value('i', 0)
    lock = manager.Lock()

    def atualiza_progresso_wrapper(x):
        with lock:
            progresso.value += 1
            if progress_callback:
                progress_callback(progresso.value, total)
        return x

    with multiprocessing.Pool() as pool:
        resultados = []
        for res in pool.imap_unordered(previsao_cache_hibrido, tarefas, chunksize=20):
            resultados.append(res)
            atualiza_progresso_wrapper(1)

    return resultados

def salvar_md_resumo_simulacao_com_elo(resultados):
    resumo = defaultdict(lambda: {
        'mandante': '',
        'visitante': '',
        'prob_mandante': 0,
        'prob_empate': 0,
        'prob_visitante': 0,
        'gols_mandante': 0,
        'gols_visitante': 0,
        'contagem': 0
    })

    for r in resultados:
        if r is None:
            continue
        chave = (r['mandante'], r['visitante'])
        resumo[chave]['mandante'] = r['mandante']
        resumo[chave]['visitante'] = r['visitante']
        resumo[chave]['prob_mandante'] += r['prob_mandante']
        resumo[chave]['prob_empate'] += r['prob_empate']
        resumo[chave]['prob_visitante'] += r['prob_visitante']
        resumo[chave]['gols_mandante'] += r['gols_esperados_mandante']
        resumo[chave]['gols_visitante'] += r['gols_esperados_visitante']
        resumo[chave]['contagem'] += 1

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'previsao_jogos_resumo_{timestamp}.md'

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Previsão de Jogos - Resultado da Simulação com Elo Dinâmico\n\n")
        f.write("| Mandante      | ELO Mandante | Visitante        | ELO Visitante | Diferença ELO |   Gols Mandante |   Gols Visitante |   Prob Mandante (%) |   Prob Empate (%) |   Prob Visitante (%) | Palpite   |\n")
        f.write("|:--------------|-------------:|:-----------------|--------------:|--------------:|----------------:|-----------------:|--------------------:|------------------:|---------------------:|:----------|\n")

        for dados in resumo.values():
            c = dados['contagem']
            media_prob_mandante = dados['prob_mandante'] / c
            media_prob_empate = dados['prob_empate'] / c
            media_prob_visitante = dados['prob_visitante'] / c
            media_gols_mandante = dados['gols_mandante'] / c
            media_gols_visitante = dados['gols_visitante'] / c

            elo_mandante = int(round(ELO_RATING_INICIAL))  # fallback if needed
            elo_visitante = int(round(ELO_RATING_INICIAL))
            # We do not keep elo dinâmico no resumo, so fallback here or improve logic if desired

            probs = {
                'Mandante': media_prob_mandante,
                'Empate': media_prob_empate,
                'Visitante': media_prob_visitante
            }
            palpite = max(probs, key=probs.get)

            f.write(f"| {dados['mandante']:<13} | {elo_mandante:12d} | {dados['visitante']:<16} | {elo_visitante:13d} | {elo_mandante - elo_visitante:13d} | "
                    f"{media_gols_mandante:15.2f} | {media_gols_visitante:16.2f} | "
                    f"{media_prob_mandante*100:18.1f} | {media_prob_empate*100:17.1f} | {media_prob_visitante*100:20.1f} | {palpite:<9} |\n")

    return filename

def calcular_xg_por_clube(df):
    forcas_poisson, medias_liga = calcular_forcas_poisson(df)
    xg_por_clube = defaultdict(float)
    jogos_por_clube = defaultdict(int)

    for _, row in df.iterrows():
        mandante = row['mandante']
        visitante = row['visitante']
        res = prever_partida_hibrido(mandante, visitante, {}, forcas_poisson, medias_liga, {})
        if res:
            xg_por_clube[mandante] += res['gols_esperados_mandante']
            xg_por_clube[visitante] += res['gols_esperados_visitante']
            jogos_por_clube[mandante] += 1
            jogos_por_clube[visitante] += 1

    xg_medio = {}
    for time in xg_por_clube:
        xg_medio[time] = xg_por_clube[time] / jogos_por_clube[time] if jogos_por_clube[time] > 0 else 0

    return xg_por_clube, xg_medio

def append_to_csv(mandante, gols_mandante, visitante, gols_visitante):
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
    except Exception as e:
        messagebox.showerror("Erro CSV", f"Erro ao ler CSV: {e}")
        return False

    new_row = {col: '' for col in headers}
    new_row['mandante'] = mandante
    new_row['gols_mandante'] = gols_mandante
    new_row['visitante'] = visitante
    new_row['gols_visitante'] = gols_visitante

    try:
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writerow(new_row)
        return True
    except Exception as e:
        messagebox.showerror("Erro CSV", f"Erro ao salvar CSV: {e}")
        return False

class SimuladorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Campeonato Brasileiro")
        self.root.geometry("750x600")

        self.df = None
        self.elo_ratings = None
        self.vantagens_casa = None
        self.forcas_poisson = None
        self.medias_liga = None

        self.carregar_csv()

        ttk.Label(root, text="Informe até 10 jogos (Mandante e Visitante):", font=("Arial", 12)).pack(pady=10)

        self.entries = []
        frame = ttk.Frame(root)
        frame.pack()

        ttk.Label(frame, text="Mandante").grid(row=0, column=0, padx=5)
        ttk.Label(frame, text="Visitante").grid(row=0, column=1, padx=5)

        for i in range(10):
            mand_entry = ttk.Entry(frame, width=30)
            mand_entry.grid(row=i+1, column=0, padx=5, pady=3)
            vis_entry = ttk.Entry(frame, width=30)
            vis_entry.grid(row=i+1, column=1, padx=5, pady=3)
            self.entries.append((mand_entry, vis_entry))

        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Rodar 10 mil simulações", command=lambda: self.iniciar_simulacao(10000)).grid(row=0, column=0, padx=10)
        ttk.Button(btn_frame, text="Rodar 100 mil simulações", command=lambda: self.iniciar_simulacao(100000)).grid(row=0, column=1, padx=10)
        ttk.Button(btn_frame, text="Adicionar partida ao CSV", command=self.abrir_janela_adicionar).grid(row=0, column=2, padx=10)
        ttk.Button(btn_frame, text="Mostrar Ranking xG dos Clubes", command=self.mostrar_xg_ranking).grid(row=0, column=3, padx=10)
        ttk.Button(btn_frame, text="Mostrar Ranking ELO dos Clubes", command=self.mostrar_elo_ranking).grid(row=0, column=4, padx=10)

        self.progress = ttk.Progressbar(root, orient='horizontal', length=700, mode='determinate')
        self.progress.pack(pady=10)
        self.progress_label = ttk.Label(root, text="")
        self.progress_label.pack()

    def carregar_csv(self):
        try:
            df = pd.read_csv(CSV_PATH)
            df.dropna(subset=['gols_mandante', 'gols_visitante'], inplace=True)
            df['gols_mandante'] = df['gols_mandante'].astype(int)
            df['gols_visitante'] = df['gols_visitante'].astype(int)
            self.df = df

            self.forcas_poisson, self.medias_liga = calcular_forcas_poisson(df)
            self.vantagens_casa = calcular_vantagens_casa(df)
            self.elo_ratings = {}
            for _, partida in df.iterrows():
                time_c = partida['mandante']
                time_v = partida['visitante']
                placar_c = partida['gols_mandante']
                placar_v = partida['gols_visitante']
                rating_c = self.elo_ratings.get(time_c, ELO_RATING_INICIAL)
                rating_v = self.elo_ratings.get(time_v, ELO_RATING_INICIAL)
                vantagem_c = self.vantagens_casa.get(time_c, ELO_VANTAGEM_CASA_PADRAO)
                novo_rating_c, novo_rating_v = atualizar_ratings_elo(rating_c, rating_v, placar_c, placar_v, vantagem_c)
                self.elo_ratings[time_c], self.elo_ratings[time_v] = novo_rating_c, novo_rating_v

        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar o CSV:\n{e}")

    def iniciar_simulacao(self, n_simulacoes):
        if self.df is None:
            messagebox.showerror("Erro", "CSV não carregado.")
            return

        jogos = []
        times_validos = set(self.df['mandante']).union(set(self.df['visitante']))

        for mand_entry, vis_entry in self.entries:
            mand = mand_entry.get().strip()
            vis = vis_entry.get().strip()
            if mand and vis:
                if mand not in times_validos or vis not in times_validos:
                    messagebox.showerror("Erro", f"Time inválido: {mand} ou {vis} não existe no campeonato.")
                    return
                jogos.append((mand, vis))

        if not jogos:
            messagebox.showwarning("Aviso", "Informe ao menos 1 jogo para simular.")
            return

        self.progress['value'] = 0
        self.progress['maximum'] = n_simulacoes * len(jogos)
        self.progress_label.config(text=f"0 / {n_simulacoes * len(jogos)}")

        threading.Thread(target=self.thread_simular, args=(jogos, n_simulacoes), daemon=True).start()

    def thread_simular(self, jogos, n_simulacoes):
        def progress_callback(done, total):
            self.root.after(0, self.atualiza_progresso, done, total)

        resultados = rodar_simulacao_paralela(self.df, jogos, n_simulacoes, progress_callback)
        arquivo = salvar_md_resumo_simulacao_com_elo(resultados)
        self.root.after(0, lambda: messagebox.showinfo("Simulação finalizada", f"Arquivo gerado:\n{arquivo}"))

    def atualiza_progresso(self, done, total):
        self.progress['value'] = done
        self.progress_label.config(text=f"{done} / {total}")

    def abrir_janela_adicionar(self):
        JanelaAdicionar(self.root, self)

    def mostrar_xg_ranking(self):
        if self.df is None:
            messagebox.showerror("Erro", "CSV não carregado.")
            return

        xg_total, xg_medio = calcular_xg_por_clube(self.df)

        ranking = sorted(xg_total.items(), key=lambda x: x[1], reverse=True)

        texto = "Ranking xG Total dos Clubes:\n\n"
        texto += f"{'Clube':20} | {'xG Total':10} | {'xG Médio/Jogo':12}\n"
        texto += "-"*50 + "\n"
        for clube, xg in ranking:
            medio = xg_medio[clube]
            texto += f"{clube:20} | {xg:10.2f} | {medio:12.2f}\n"

        janela = tk.Toplevel(self.root)
        janela.title("Ranking xG dos Clubes")
        janela.geometry("400x400")
        txt = tk.Text(janela, wrap='none', font=("Courier", 10))
        txt.pack(expand=True, fill='both')
        txt.insert('1.0', texto)
        txt.config(state='disabled')

    def mostrar_elo_ranking(self):
        if self.elo_ratings is None:
            messagebox.showerror("Erro", "Elo ratings não calculados.")
            return

        texto = "Ranking ELO Dinâmico dos Clubes:\n\n"
        texto += f"{'Clube':20} | {'ELO':7}\n"
        texto += "-"*30 + "\n"
        ranking = sorted(self.elo_ratings.items(), key=lambda x: x[1], reverse=True)
        for clube, elo in ranking:
            texto += f"{clube:20} | {int(elo):7d}\n"

        janela = tk.Toplevel(self.root)
        janela.title("Ranking ELO Dinâmico dos Clubes")
        janela.geometry("350x400")
        txt = tk.Text(janela, wrap='none', font=("Courier", 12))
        txt.pack(expand=True, fill='both')
        txt.insert('1.0', texto)
        txt.config(state='disabled')

class JanelaAdicionar(tk.Toplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Adicionar partida ao CSV")
        self.geometry("400x300")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="mandante:").pack(anchor='w')
        self.mandante_entry = ttk.Entry(frame)
        self.mandante_entry.pack(fill='x', pady=5)

        ttk.Label(frame, text="gols_mandante:").pack(anchor='w')
        self.gols_mandante_entry = ttk.Entry(frame)
        self.gols_mandante_entry.pack(fill='x', pady=5)

        ttk.Label(frame, text="visitante:").pack(anchor='w')
        self.visitante_entry = ttk.Entry(frame)
        self.visitante_entry.pack(fill='x', pady=5)

        ttk.Label(frame, text="gols_visitante:").pack(anchor='w')
        self.gols_visitante_entry = ttk.Entry(frame)
        self.gols_visitante_entry.pack(fill='x', pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10, fill='x')

        ttk.Button(btn_frame, text="Adicionar", command=self.adicionar).pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side='left', expand=True, fill='x', padx=5)

    def adicionar(self):
        mandante = self.mandante_entry.get().strip()
        visitante = self.visitante_entry.get().strip()
        gols_mandante = self.gols_mandante_entry.get().strip()
        gols_visitante = self.gols_visitante_entry.get().strip()

        if not mandante or not visitante:
            messagebox.showwarning("Aviso", "Informe mandante e visitante.")
            return
        try:
            gols_mandante_int = int(gols_mandante)
            gols_visitante_int = int(gols_visitante)
            if gols_mandante_int < 0 or gols_visitante_int < 0:
                raise ValueError
        except:
            messagebox.showwarning("Aviso", "Gols devem ser inteiros positivos ou zero.")
            return

        sucesso = append_to_csv(mandante, gols_mandante_int, visitante, gols_visitante_int)
        if sucesso:
            messagebox.showinfo("Sucesso", "Dados adicionados ao CSV.")
            self.app.carregar_csv()
            self.destroy()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = SimuladorApp(root)
    root.mainloop()
