import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pandas as pd
import datetime
import csv

# Caminho absoluto para o CSV, mantenha como no seu sistema
CSV_PATH = r'C:\Users\Paulo\OneDrive\Documentos\sassamaru-br-25\br-25.csv'

def load_matches():
    """
    Carrega partidas do CSV em DataFrame.
    Espera as colunas: mandante, gols_mandante, visitante, gols_visitante (exato)
    """
    try:
        df = pd.read_csv(CSV_PATH)
        expected_cols = ['mandante', 'gols_mandante', 'visitante', 'gols_visitante']
        for col in expected_cols:
            if col not in df.columns:
                raise ValueError(f"Coluna esperada '{col}' não encontrada no CSV.")
        return df
    except Exception as e:
        messagebox.showerror("Erro ao carregar CSV", f"Não foi possível carregar o arquivo CSV:\n{e}")
        return None

def run_simulation(df_matches, jogos, n_simulations, progress_callback=None):
    """
    Simula n_simulations para os jogos passados (lista de tuplas mandante, visitante).
    Usa somente os jogos informados pelo usuário, não todo o DataFrame.
    """
    import random
    results = []
    total = n_simulations
    for i in range(n_simulations):
        jogo = random.choice(jogos)
        results.append(jogo)
        if progress_callback:
            progress_callback(i + 1, total)
    return results

def save_simulation_md(results):
    """
    Salva resultado da simulação em arquivo Markdown timestampado.
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'simulacao_resultado_{timestamp}.md'
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Resultado da Simulação\n\n")
            f.write("| mandante    | visitante  |\n")
            f.write("|-------------|------------|\n")
            for mandante, visitante in results:
                f.write(f"| {mandante} | {visitante} |\n")
        return filename
    except Exception as e:
        messagebox.showerror("Erro ao salvar arquivo MD", f"Erro ao salvar arquivo Markdown:\n{e}")
        return None

def append_to_csv(mandante, gols_mandante, visitante, gols_visitante):
    """
    Adiciona nova linha ao CSV mantendo ordem e nomes originais das colunas.
    """
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
    except Exception as e:
        messagebox.showerror("Erro ao ler CSV", f"Erro ao ler CSV para anexar dados:\n{e}")
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
        messagebox.showerror("Erro ao salvar CSV", f"Erro ao salvar dados no CSV:\n{e}")
        return False

class SimulationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Campeonato Brasileiro")
        self.root.geometry("500x320")
        self.root.resizable(False, False)

        self.df_matches = load_matches()
        btn_state = 'normal' if self.df_matches is not None else 'disabled'

        self.main_frame = ttk.Frame(root, padding=20)
        self.main_frame.pack(expand=True, fill='both')

        ttk.Label(self.main_frame, text="Menu Principal", font=("Arial", 16, "bold")).pack(pady=10)

        ttk.Button(self.main_frame, text="Rodar 10 mil simulações", state=btn_state, command=lambda: self.open_games_form(10000)).pack(fill='x', pady=5)
        ttk.Button(self.main_frame, text="Rodar 100 mil simulações", state=btn_state, command=lambda: self.open_games_form(100000)).pack(fill='x', pady=5)
        ttk.Button(self.main_frame, text="Adicionar dados", command=self.open_add_data_window).pack(fill='x', pady=5)
        ttk.Button(self.main_frame, text="Sair", command=root.quit).pack(fill='x', pady=5)

    def open_games_form(self, n_simulations):
        self.main_frame.pack_forget()
        self.games_form = GamesForm(self.root, self.df_matches, n_simulations, self.back_to_menu)

    def back_to_menu(self):
        if hasattr(self, 'games_form'):
            self.games_form.destroy()
        self.main_frame.pack(expand=True, fill='both')

    def open_add_data_window(self):
        AddDataWindow(self.root)

class GamesForm(tk.Toplevel):
    def __init__(self, master, df, n_simulations, on_close_callback):
        super().__init__(master)
        self.df = df
        self.n_simulations = n_simulations
        self.on_close_callback = on_close_callback
        self.title(f"Informe até 10 jogos para simulação ({n_simulations} rodadas)")
        self.geometry("520x460")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=15)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="Digite os jogos (mandante e visitante):", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=4, pady=(0,10))

        self.entries = []
        for i in range(10):
            ttk.Label(frame, text=f"Jogo {i+1} mandante:").grid(row=i+1, column=0, sticky='e', padx=2, pady=2)
            mand_entry = ttk.Entry(frame, width=20)
            mand_entry.grid(row=i+1, column=1, padx=2, pady=2)

            ttk.Label(frame, text="visitante:").grid(row=i+1, column=2, sticky='e', padx=2, pady=2)
            vis_entry = ttk.Entry(frame, width=20)
            vis_entry.grid(row=i+1, column=3, padx=2, pady=2)

            self.entries.append((mand_entry, vis_entry))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=12, column=0, columnspan=4, pady=15)

        ttk.Button(btn_frame, text="Iniciar Simulação", command=self.start_simulation).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Cancelar", command=self.cancel).pack(side='left', padx=10)

        # Progress widgets
        self.progress_label = ttk.Label(frame, text="Progresso da simulação:")
        self.progress_bar = ttk.Progressbar(frame, orient='horizontal', length=480, mode='determinate')
        self.progress_text = ttk.Label(frame, text="")

    def start_simulation(self):
        jogos = []
        for mand_entry, vis_entry in self.entries:
            mand = mand_entry.get().strip()
            vis = vis_entry.get().strip()
            if mand and vis:
                jogos.append((mand, vis))

        if len(jogos) == 0:
            messagebox.showwarning("Entrada inválida", "Informe pelo menos 1 jogo para simular.")
            return

        times_validos = set(self.df['mandante']).union(set(self.df['visitante']))
        invalids = [t for jogo in jogos for t in jogo if t not in times_validos]
        if invalids:
            messagebox.showerror("Erro de validação", f"Times inválidos encontrados:\n{', '.join(set(invalids))}")
            return

        # Oculta campos e mostra progresso
        for w in self.winfo_children():
            w.pack_forget() if hasattr(w, 'pack_info') else None
            w.grid_remove() if hasattr(w, 'grid_info') else None

        self.progress_label.pack(pady=10)
        self.progress_bar.pack()
        self.progress_text.pack(pady=10)

        self.progress_bar['maximum'] = self.n_simulations
        self.progress_bar['value'] = 0
        self.progress_text.config(text=f"0 / {self.n_simulations}")

        threading.Thread(target=self.simulation_thread, args=(jogos,), daemon=True).start()

    def simulation_thread(self, jogos):
        import random
        resultados = []
        total = self.n_simulations
        for i in range(total):
            resultados.append(random.choice(jogos))
            self.after(0, self.update_progress, i + 1, total)

        filename = save_simulation_md(resultados)

        def finish():
            messagebox.showinfo("Simulação concluída", f"Simulação salva em:\n{filename}")
            self.on_close_callback()
            self.destroy()

        self.after(0, finish)

    def update_progress(self, done, total):
        self.progress_bar['value'] = done
        self.progress_text.config(text=f"{done} / {total}")

    def cancel(self):
        self.on_close_callback()
        self.destroy()

class AddDataWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Adicionar Dados de Partida")
        self.geometry("400x280")
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=20)
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="mandante (Time da casa):").pack(anchor='w', pady=(0, 2))
        self.entry_mandante = ttk.Entry(frame)
        self.entry_mandante.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="gols_mandante:").pack(anchor='w', pady=(0, 2))
        self.entry_gols_mandante = ttk.Entry(frame)
        self.entry_gols_mandante.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="visitante (Time visitante):").pack(anchor='w', pady=(0, 2))
        self.entry_visitante = ttk.Entry(frame)
        self.entry_visitante.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="gols_visitante:").pack(anchor='w', pady=(0, 2))
        self.entry_gols_visitante = ttk.Entry(frame)
        self.entry_gols_visitante.pack(fill='x', pady=(0, 10))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(10, 0))

        ttk.Button(btn_frame, text="Adicionar", command=self.add_data).pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side='left', expand=True, fill='x', padx=5)

    def add_data(self):
        mandante = self.entry_mandante.get().strip()
        visitante = self.entry_visitante.get().strip()
        gols_mandante = self.entry_gols_mandante.get().strip()
        gols_visitante = self.entry_gols_visitante.get().strip()

        if not mandante:
            messagebox.showwarning("Entrada inválida", "Por favor, informe o time mandante.")
            return
        if not visitante:
            messagebox.showwarning("Entrada inválida", "Por favor, informe o time visitante.")
            return
        try:
            gols_mandante_int = int(gols_mandante)
            gols_visitante_int = int(gols_visitante)
            if gols_mandante_int < 0 or gols_visitante_int < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Entrada inválida", "Gols devem ser números inteiros positivos ou zero.")
            return

        try:
            with open(CSV_PATH, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
        except Exception as e:
            messagebox.showerror("Erro ao ler CSV", f"Erro ao ler CSV:\n{e}")
            return

        new_row = {col: '' for col in headers}
        new_row['mandante'] = mandante
        new_row['gols_mandante'] = gols_mandante_int
        new_row['visitante'] = visitante
        new_row['gols_visitante'] = gols_visitante_int

        try:
            with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writerow(new_row)
            messagebox.showinfo("Sucesso", "Dados adicionados ao arquivo CSV.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro ao salvar CSV", f"Erro ao salvar dados no CSV:\n{e}")

def main():
    root = tk.Tk()
    app = SimulationApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
