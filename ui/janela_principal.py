"""
Janela principal do app — cabeçalho com seletores + Notebook com abas.
"""
import tkinter as tk
from tkinter import ttk

from core.config import salvar_config, caminho_pasta_entrada
from core.util_meses import eh_pasta_de_mes, calcular_ano_mes

from ui.tab_importacao import TabImportacao
from ui.tab_sugestao import TabSugestao
from ui.tab_cotacao import TabCotacao
from ui.tab_fechar_cotacao import TabFecharCotacao


class JanelaPrincipal:
    def __init__(self, root: tk.Tk, config: dict):
        self.root = root
        self.config = config

        self.root.title("Sistema de Compras — Cotação")
        self.root.geometry("1400x800")
        self.root.minsize(1000, 600)

        self._aplicar_estilo()
        self._montar_cabecalho()
        self._montar_notebook()

    # ============================================================
    # ESTILO
    # ============================================================
    def _aplicar_estilo(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TNotebook.Tab", padding=[12, 6], font=("Segoe UI", 9))
        style.configure("Titulo.TLabel", font=("Segoe UI", 11, "bold"))

    # ============================================================
    # CABEÇALHO
    # ============================================================
    def _montar_cabecalho(self):
        frame = ttk.Frame(self.root, padding=(10, 8))
        frame.pack(fill="x")

        ttk.Label(frame, text="🏪 Filial:").pack(side="left", padx=(0, 4))
        self.var_filial = tk.StringVar(value=f"Filial {self.config['filial_ativa']}")
        combo_filial = ttk.Combobox(
            frame, textvariable=self.var_filial,
            values=["Filial 1", "Filial 2"],
            state="readonly", width=12
        )
        combo_filial.pack(side="left", padx=(0, 20))
        combo_filial.bind("<<ComboboxSelected>>", self._on_filial_change)

        ttk.Label(frame, text="📅 Mês ativo:").pack(side="left", padx=(0, 4))
        self.var_mes = tk.StringVar(value=self.config["mes_ativo"])
        valores_mes = self._listar_meses_disponiveis()
        combo_mes = ttk.Combobox(
            frame, textvariable=self.var_mes,
            values=valores_mes, state="readonly", width=10
        )
        combo_mes.pack(side="left", padx=(0, 20))
        combo_mes.bind("<<ComboboxSelected>>", self._on_mes_change)

        ttk.Button(frame, text="🔄 Atualizar telas",
                   command=self._atualizar_tudo).pack(side="left", padx=5)

        self.lbl_status = ttk.Label(frame, text="", foreground="#555")
        self.lbl_status.pack(side="right")

    def _listar_meses_disponiveis(self):
        pasta = caminho_pasta_entrada(self.config)
        if not pasta.exists():
            return [self.config["mes_ativo"]]
        meses = [p.name for p in pasta.iterdir() if p.is_dir() and eh_pasta_de_mes(p.name)]
        meses.sort()
        return meses or [self.config["mes_ativo"]]

    def _on_filial_change(self, _evt=None):
        num = 1 if self.var_filial.get().endswith("1") else 2
        self.config["filial_ativa"] = num
        salvar_config(self.config)
        self._atualizar_tudo()

    def _on_mes_change(self, _evt=None):
        self.config["mes_ativo"] = self.var_mes.get()
        salvar_config(self.config)
        self._atualizar_tudo()

    # ============================================================
    # NOTEBOOK (ABAS)
    # ============================================================
    def _montar_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tab_importacao = TabImportacao(self.notebook, self)
        self.tab_sugestao = TabSugestao(self.notebook, self)
        self.tab_cotacao = TabCotacao(self.notebook, self)
        self.tab_fechar_cotacao = TabFecharCotacao(self.notebook, self)

        self.notebook.add(self.tab_importacao.frame, text="📥 Importação")
        self.notebook.add(self.tab_sugestao.frame, text="🧠 Sugestão")
        self.notebook.add(self.tab_cotacao.frame, text="💰 Cotação")
        self.notebook.add(self.tab_fechar_cotacao.frame, text="🔒 Fechar Cotação")

        for nome in ["📄 Pedidos", "🔎 Manual", "⚙️ Config"]:
            f = ttk.Frame(self.notebook)
            ttk.Label(f, text=f"{nome} — em construção",
                      font=("Segoe UI", 12)).pack(pady=40)
            self.notebook.add(f, text=nome)

    # ============================================================
    # AÇÕES GLOBAIS
    # ============================================================
    def _atualizar_tudo(self):
        """Chamado quando troca filial/mês ou clica 'Atualizar telas'."""
        # Segurança: só atualiza se a aba já existir
        if not hasattr(self, "tab_sugestao"):
            return

        self.lbl_status.config(text="Atualizando...")
        self.root.update_idletasks()

        try:
            self.tab_sugestao.recarregar()
        except Exception as e:
            print(f"Erro ao recarregar sugestão: {e}")

        try:
            if hasattr(self, "tab_cotacao"):
                self.tab_cotacao.recarregar()
        except Exception as e:
            print(f"Erro ao recarregar cotação: {e}")

        try:
            if hasattr(self, "tab_fechar_cotacao"):
                self.tab_fechar_cotacao.recarregar()
        except Exception as e:
            print(f"Erro ao recarregar fechar cotação: {e}")

        self.lbl_status.config(text="Pronto.")
        self.root.after(2000, lambda: self.lbl_status.config(text=""))

    def filial_ativa(self) -> int:
        return 1 if self.var_filial.get().endswith("1") else 2

    def ano_mes_ativo(self) -> str:
        return calcular_ano_mes(self.config["mes_ativo"])

    def set_status(self, texto: str):
        self.lbl_status.config(text=texto)