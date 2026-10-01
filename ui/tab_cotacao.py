"""
Aba Cotação: preview dos itens das 2 filiais + geração do Excel cego.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import subprocess
from pathlib import Path

from core.cotacao import listar_itens_para_preview, salvar_qtd
from core.excel_cotacao import (
    gerar_excel_cego,
    listar_fornecedores_do_banco,
    PASTA_TRABALHO,
)


ARQUIVO_CEGO = PASTA_TRABALHO / "cotacao_cega.xlsx"


class TabCotacao:
    def __init__(self, master, app):
        self.app = app
        self.frame = ttk.Frame(master, padding=10)

        self._montar_rodape()   # rodapé primeiro pra ficar embaixo
        self._montar_tabelas()

    # ============================================================
    # TABELAS
    # ============================================================
    def _montar_tabelas(self):
        container = ttk.Frame(self.frame)
        container.pack(fill="both", expand=True)

        # ---- Cabeçalho Filial 1 (MJZ) ----
        nome_f1 = self.app.config.get("filiais", {}).get("1", {}).get("nome", "FILIAL 1")
        ttk.Label(container, text=nome_f1,
                  font=("Segoe UI", 12, "bold"),
                  background="#1F4E79", foreground="white",
                  anchor="center", padding=6).pack(fill="x", pady=(0, 4))

        self.tree_f1 = self._criar_treeview(container)

        # ---- Cabeçalho Filial 2 (SZ) ----
        ttk.Label(container, text=" ", padding=2).pack(fill="x")
        nome_f2 = self.app.config.get("filiais", {}).get("2", {}).get("nome", "FILIAL 2")
        ttk.Label(container, text=nome_f2,
                  font=("Segoe UI", 12, "bold"),
                  background="#1F4E79", foreground="white",
                  anchor="center", padding=6).pack(fill="x", pady=(0, 4))

        self.tree_f2 = self._criar_treeview(container)

    def _criar_treeview(self, parent):
        colunas = ("codigo", "descricao", "depto", "qtd", "vl_unit")
        tree = ttk.Treeview(parent, columns=colunas, show="headings", height=10)

        headers = {
            "codigo": ("Código", 90),
            "descricao": ("Produto", 480),
            "depto": ("Depto", 60),
            "qtd": ("QTD", 80),
            "vl_unit": ("VL Unit", 100),
        }
        for col, (titulo, largura) in headers.items():
            tree.heading(col, text=titulo)
            tree.column(col, width=largura, anchor="center" if col != "descricao" else "w")

        scroll_y = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)

        tree.pack(side="top", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        # Duplo clique edita QTD
        tree.bind("<Double-1>", lambda e, t=tree: self._editar_qtd(e, t))

        return tree

    # ============================================================
    # RODAPÉ
    # ============================================================
    def _montar_rodape(self):
        rodape = ttk.Frame(self.frame)
        rodape.pack(side="bottom", fill="x", pady=(8, 0))

        ttk.Button(rodape, text="📋 Gerar Excel Cego",
                   command=self._gerar_excel_cego).pack(side="left", padx=(0, 8))
        ttk.Button(rodape, text="📂 Abrir Excel Cego",
                   command=self._abrir_excel_cego).pack(side="left", padx=(0, 8))
        ttk.Button(rodape, text="🔄 Recarregar",
                   command=self.recarregar).pack(side="left", padx=(0, 8))

        self.lbl_info = ttk.Label(rodape, text="", foreground="#555")
        self.lbl_info.pack(side="right")

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        ano_mes = self.app.ano_mes_ativo()

        # Popula F1
        itens_f1 = listar_itens_para_preview(1, ano_mes)
        self._popular(self.tree_f1, itens_f1)

        # Popula F2
        itens_f2 = listar_itens_para_preview(2, ano_mes)
        self._popular(self.tree_f2, itens_f2)

        self.lbl_info.config(
            text=f"MJZ: {len(itens_f1)} itens  |  SZ: {len(itens_f2)} itens"
        )

    def _popular(self, tree, itens):
        for i in tree.get_children():
            tree.delete(i)

        for it in itens:
            tree.insert("", "end", iid=f"{tree}_{it['produto_id']}", values=(
                it["codigo_interno"],
                it["descricao"],
                it["departamento"] or "",
                f"{it['qtd']:.0f}",
                f"R$ {it['vl_unit']:.2f}",
            ))

    # ============================================================
    # EDIÇÃO DA QTD
    # ============================================================
    def _editar_qtd(self, evt, tree):
        item = tree.identify_row(evt.y)
        col = tree.identify_column(evt.x)
        if not item or col != "#4":   # coluna QTD
            return

        # Descobre a filial pela tree
        filial = 1 if tree == self.tree_f1 else 2
        ano_mes = self.app.ano_mes_ativo()

        # iid é "tree_<produto_id>"
        produto_id = int(item.split("_")[-1])

        valores = tree.item(item, "values")
        atual = valores[3] if len(valores) > 3 else "0"

        # Janela popup
        janela = tk.Toplevel(self.app.root)
        janela.title("Editar QTD")
        janela.geometry("300x130")
        janela.transient(self.app.root)
        janela.grab_set()

        ttk.Label(janela, text=f"Quantidade ({valores[1][:30]}):",
                  font=("Segoe UI", 10)).pack(pady=(15, 5))
        var = tk.StringVar(value=atual.replace(",", "."))
        entrada = ttk.Entry(janela, textvariable=var,
                            font=("Segoe UI", 11), justify="center")
        entrada.pack(pady=5, padx=20, fill="x")
        entrada.focus_set()
        entrada.select_range(0, "end")

        def confirmar(_evt=None):
            try:
                novo = float(var.get().replace(",", "."))
                if novo < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "Digite um número válido.")
                return

            # Grava no banco
            salvar_qtd(filial, produto_id, ano_mes, novo)

            # Atualiza a linha
            valores_lista = list(tree.item(item, "values"))
            valores_lista[3] = f"{novo:.0f}"
            tree.item(item, values=valores_lista)

            janela.destroy()

        entrada.bind("<Return>", confirmar)
        ttk.Button(janela, text="Confirmar", command=confirmar).pack(pady=8)

    # ============================================================
    # GERAR EXCEL CEGO
    # ============================================================
    def _gerar_excel_cego(self):
        ano_mes = self.app.ano_mes_ativo()

        # Pega itens das 2 filiais
        itens_f1 = listar_itens_para_preview(1, ano_mes)
        itens_f2 = listar_itens_para_preview(2, ano_mes)

        if not itens_f1 and not itens_f2:
            messagebox.showwarning("Aviso",
                "Nenhum item com QTD > 0.\nDecida as quantidades primeiro na aba Sugestão.")
            return

        # Monta lista de produtos pro Excel (só cód barras + descrição)
        produtos_f1 = [
            {"codigo_barras": it["codigo_barras"] or it["codigo_interno"],
             "descricao": it["descricao"]}
            for it in itens_f1
        ]
        produtos_f2 = [
            {"codigo_barras": it["codigo_barras"] or it["codigo_interno"],
             "descricao": it["descricao"]}
            for it in itens_f2
        ]

        fornecedores = listar_fornecedores_do_banco()

        # Se o Excel já existe, oferece backup
        if ARQUIVO_CEGO.exists():
            resp = messagebox.askyesno(
                "Backup",
                "Já existe um Excel cego gerado.\nDeseja fazer backup antes?"
            )
            if resp:
                from core.excel_cotacao import fazer_backup_excel
                fazer_backup_excel(ARQUIVO_CEGO, "cego_antes_gerar")

        try:
            gerar_excel_cego(
                produtos_f1=produtos_f1,
                produtos_f2=produtos_f2,
                fornecedores=fornecedores,
                config=self.app.config,
                caminho_destino=ARQUIVO_CEGO,
            )
            messagebox.showinfo("Excel cego gerado",
                f"Arquivo criado com sucesso:\n\n"
                f"• MJZ: {len(produtos_f1)} itens\n"
                f"• SZ:  {len(produtos_f2)} itens\n\n"
                f"{ARQUIVO_CEGO}")
        except Exception as e:
            messagebox.showerror("Erro ao gerar Excel cego", str(e))

    def _abrir_excel_cego(self):
        if not ARQUIVO_CEGO.exists():
            messagebox.showwarning("Aviso",
                "Gere o Excel cego primeiro (botão 📋).")
            return

        try:
            if sys.platform == "win32":
                os.startfile(ARQUIVO_CEGO)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ARQUIVO_CEGO])
            else:
                subprocess.Popen(["xdg-open", ARQUIVO_CEGO])
        except Exception as e:
            messagebox.showerror("Erro ao abrir", str(e))