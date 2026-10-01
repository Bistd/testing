"""
Aba Sugestão: lista os produtos que passaram na regra dos 60%,
permite gerar o Excel de trabalho, abrir, salvar QTDs.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import subprocess
from pathlib import Path

from core.calculos import montar_sugestoes
from core.cotacao import salvar_qtds_em_lote, carregar_qtds, zerar_qtds
from core.excel_cotacao import (
    gerar_excel_trabalho,
    ler_excel_trabalho,
    fazer_backup_excel,
    PASTA_TRABALHO,
)
from core.database import conectar


ARQUIVO_TRABALHO = PASTA_TRABALHO / "cotacao_trabalho.xlsx"


class TabSugestao:
    def __init__(self, master, app):
        self.app = app
        self.frame = ttk.Frame(master, padding=10)
        self.dados = []

        self._montar_filtros()
        self._montar_tabela()
        self._montar_rodape()

    # ============================================================
    # FILTROS
    # ============================================================
    def _montar_filtros(self):
        topo = ttk.Frame(self.frame)
        topo.pack(fill="x", pady=(0, 8))

        ttk.Label(topo, text="Departamento:").pack(side="left")
        self.var_depto = tk.StringVar()
        self.combo_depto = ttk.Combobox(topo, textvariable=self.var_depto, width=10)
        self.combo_depto.pack(side="left", padx=(4, 15))
        self.combo_depto.bind("<Return>", lambda e: self.recarregar())
        self.combo_depto.bind("<<ComboboxSelected>>", lambda e: self.recarregar())

        ttk.Label(topo, text="Fornecedor:").pack(side="left")
        self.var_forn = tk.StringVar()
        self.combo_forn = ttk.Combobox(topo, textvariable=self.var_forn, width=10)
        self.combo_forn.pack(side="left", padx=(4, 15))
        self.combo_forn.bind("<Return>", lambda e: self.recarregar())
        self.combo_forn.bind("<<ComboboxSelected>>", lambda e: self.recarregar())

        ttk.Button(topo, text="🔍 Filtrar", command=self.recarregar).pack(side="left", padx=5)
        ttk.Button(topo, text="♻ Limpar", command=self._limpar_filtros).pack(side="left", padx=5)

        self.lbl_info = ttk.Label(topo, text="", foreground="#555")
        self.lbl_info.pack(side="right")

    def _limpar_filtros(self):
        self.var_depto.set("")
        self.var_forn.set("")
        self.recarregar()

    # ============================================================
    # TABELA
    # ============================================================
    def _montar_tabela(self):
        colunas = ("codigo", "descricao", "depto", "forn",
                   "sugestao", "vl_unit", "pct")
        self.tree = ttk.Treeview(self.frame, columns=colunas, show="headings", height=20)

        headers = {
            "codigo": ("Código", 90),
            "descricao": ("Produto", 420),
            "depto": ("Depto", 60),
            "forn": ("Forn.", 60),
            "sugestao": ("SUG", 80),
            "vl_unit": ("VL Unit", 90),
            "pct": ("% Vend.", 80),
        }
        for col, (titulo, largura) in headers.items():
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura, anchor="center" if col != "descricao" else "w")

        scroll_y = ttk.Scrollbar(self.frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

    def _montar_rodape(self):
        rodape = ttk.Frame(self.frame)
        rodape.pack(fill="x", pady=(8, 0))

        # ============ LINHA 1 — fluxo principal ============
        linha1 = ttk.Frame(rodape)
        linha1.pack(fill="x", pady=(0, 4))

        ttk.Button(linha1, text="📤 Enviar para Excel",
                   command=self._enviar_excel).pack(side="left", padx=(0, 8))
        ttk.Button(linha1, text="📂 Abrir Excel",
                   command=self._abrir_excel).pack(side="left", padx=(0, 8))
        ttk.Button(linha1, text="💾 Salvar quantidades",
                   command=self._salvar_qtds).pack(side="left", padx=(0, 8))

        # ============ LINHA 2 — sync + nova cotação ============
        linha2 = ttk.Frame(rodape)
        linha2.pack(fill="x")

        ttk.Button(linha2, text="📤 Exportar minhas QTDs",
                   command=self._exportar_qtds).pack(side="left", padx=(0, 8))
        ttk.Button(linha2, text="📥 Importar QTDs de outro PC",
                   command=self._importar_qtds).pack(side="left", padx=(0, 8))

        ttk.Separator(linha2, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Button(linha2, text="🆕 Nova Cotação",
                   command=self._nova_cotacao).pack(side="left", padx=(0, 8))

        self.lbl_info_rodape = ttk.Label(linha2, text="", foreground="#555")
        self.lbl_info_rodape.pack(side="right")

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        filial = self.app.filial_ativa()
        ano_mes = self.app.ano_mes_ativo()

        depto = self.var_depto.get().strip() or None
        forn = self.var_forn.get().strip() or None

        try:
            self.dados = montar_sugestoes(
                filial_id=filial,
                ano_mes_atual=ano_mes,
                config=self.app.config,
                filtro_departamento=depto,
                filtro_fornecedor=forn,
            )
        except Exception as e:
            messagebox.showerror("Erro ao carregar sugestões", str(e))
            self.dados = []

        # Carrega QTDs já salvas
        qtds = carregar_qtds(filial, ano_mes)
        for d in self.dados:
            d["qtd_comprador"] = qtds.get(d["produto_id"], 0.0)

        self._popular_tabela()
        self._atualizar_combos()

    def _popular_tabela(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for d in self.dados:
            self.tree.insert("", "end", iid=str(d["produto_id"]), values=(
                d["codigo_interno"],
                d["descricao"],
                d["departamento"] or "",
                d["fornecedor_codigo"] or "",
                f"{d['sugestao']:.0f}",
                f"R$ {d['vl_unit']:.2f}",
                f"{d['pct_vendido']:.1f}%",
            ))

        self.lbl_info.config(text=f"{len(self.dados)} produtos na sugestão")
        self._atualizar_total()

    def _atualizar_combos(self):
        deptos = sorted({d["departamento"] for d in self.dados if d["departamento"]})
        forns = sorted({d["fornecedor_codigo"] for d in self.dados if d["fornecedor_codigo"]})
        self.combo_depto["values"] = [""] + deptos
        self.combo_forn["values"] = [""] + forns

    # ============================================================
    # ENVIAR PARA EXCEL
    # ============================================================
    def _enviar_excel(self):
        if not self.dados:
            messagebox.showwarning("Aviso", "Não há produtos na tela para enviar.")
            return

        filial = self.app.filial_ativa()
        ano_mes = self.app.ano_mes_ativo()

        # Se já existe Excel de trabalho, faz backup antes
        if ARQUIVO_TRABALHO.exists():
            resp = messagebox.askyesno(
                "Backup",
                "Já existe um Excel de trabalho.\n"
                "Deseja fazer backup antes de gerar um novo?\n\n"
                "(recomendado se você ainda não salvou as quantidades)"
            )
            if resp:
                backup = fazer_backup_excel(ARQUIVO_TRABALHO, "antes_gerar")
                messagebox.showinfo("Backup feito", f"Salvo em:\n{backup}")

        try:
            # Monta lista de produtos com histórico
            produtos_excel = self._montar_produtos_para_excel(filial, ano_mes)
            if not produtos_excel:
                messagebox.showwarning("Aviso", "Nenhum produto encontrado.")
                return

            gerar_excel_trabalho(produtos_excel, ano_mes, ARQUIVO_TRABALHO, self.app.config)
            messagebox.showinfo(
                "Excel gerado",
                f"Arquivo criado com {len(produtos_excel)} produtos:\n\n{ARQUIVO_TRABALHO}"
            )
        except Exception as e:
            messagebox.showerror("Erro ao gerar Excel", str(e))

    def _montar_produtos_para_excel(self, filial_id: int, ano_mes: str) -> list:
        """Pega todos os dados necessários pra montar o Excel."""
        from core.util_meses import ultimos_n_meses
        lista_meses = ultimos_n_meses(ano_mes, 12)

        conn = conectar()
        cur = conn.cursor()
        produtos = []

        for d in self.dados:
            pid = d["produto_id"]

            # Histórico dos últimos 12 meses
            ph = ",".join("?" * len(lista_meses))
            cur.execute(f"""
                SELECT ano_mes, qtd_entrada, qtd_venda
                FROM historico_mensal
                WHERE filial_id = ? AND produto_id = ?
                  AND ano_mes IN ({ph})
            """, [filial_id, pid] + lista_meses)

            hist = {r["ano_mes"]: {"qtd_entrada": r["qtd_entrada"] or 0,
                                   "qtd_venda": r["qtd_venda"] or 0}
                    for r in cur.fetchall()}

            produtos.append({
                "codigo_interno": d["codigo_interno"],
                "codigo_barras": "",
                "descricao": d["descricao"],
                "vl_unit": d["vl_unit"],
                "estoque": d["estoque_atual"],
                "sugestao": d["sugestao"],
                "qtd_por_caixa": d.get("qtd_por_caixa", 1),
                "hist": hist,
            })

        # Busca código de barras real
        for p in produtos:
            cur.execute("SELECT codigo_barras FROM produtos WHERE codigo_interno = ?",
                        (p["codigo_interno"],))
            r = cur.fetchone()
            if r:
                p["codigo_barras"] = r[0] or ""

        conn.close()
        return produtos

    # ============================================================
    # ABRIR EXCEL
    # ============================================================
    def _abrir_excel(self):
        if not ARQUIVO_TRABALHO.exists():
            messagebox.showwarning("Aviso",
                "Não existe Excel de trabalho.\nClique em '📤 Enviar para Excel' primeiro.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(ARQUIVO_TRABALHO)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ARQUIVO_TRABALHO])
            else:
                subprocess.Popen(["xdg-open", ARQUIVO_TRABALHO])
        except Exception as e:
            messagebox.showerror("Erro ao abrir", str(e))

    # ============================================================
    # SALVAR QUANTIDADES
    # ============================================================
    def _salvar_qtds(self):
        if not ARQUIVO_TRABALHO.exists():
            messagebox.showwarning("Aviso",
                "Não existe Excel de trabalho.\nGere e edite o Excel primeiro.")
            return

        filial = self.app.filial_ativa()
        ano_mes = self.app.ano_mes_ativo()

        try:
            linhas_excel = ler_excel_trabalho(ARQUIVO_TRABALHO)
        except Exception as e:
            messagebox.showerror("Erro ao ler Excel", str(e))
            return

        if not linhas_excel:
            messagebox.showwarning("Aviso", "Nenhuma linha encontrada no Excel.")
            return

        # Converte código_interno → produto_id
        conn = conectar()
        cur = conn.cursor()
        lista_salvar = []
        nao_encontrados = []

        for linha in linhas_excel:
            cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?",
                        (linha["codigo_interno"],))
            r = cur.fetchone()
            if r:
                lista_salvar.append({"produto_id": r[0], "qtd": linha["qtd"]})
            else:
                nao_encontrados.append(linha["codigo_interno"])

        conn.close()

        try:
            n = salvar_qtds_em_lote(filial, ano_mes, lista_salvar)
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return

        # Backup do Excel após salvar
        fazer_backup_excel(ARQUIVO_TRABALHO, f"salvo_{filial}_{ano_mes}")

        msg = f"{n} quantidades salvas!"
        if nao_encontrados:
            msg += f"\n\n⚠ {len(nao_encontrados)} códigos não encontrados."
        messagebox.showinfo("Salvo", msg)

        self.recarregar()





    def _nova_cotacao(self):
        """Zera QTDs salvas + apaga Excel de trabalho + faz backup."""
        filial = self.app.filial_ativa()
        ano_mes = self.app.ano_mes_ativo()

        if not messagebox.askyesno(
            "Confirmar Nova Cotação",
            f"Isso vai:\n\n"
            f"• Apagar TODAS as QTDs salvas (filial {filial}, {ano_mes})\n"
            f"• Fazer backup do Excel atual\n"
            f"• Apagar o Excel de trabalho\n\n"
            f"Começar uma nova cotação do zero?"
        ):
            return

        # 1. Backup do Excel atual (se existir)
        if ARQUIVO_TRABALHO.exists():
            try:
                fazer_backup_excel(ARQUIVO_TRABALHO, f"nova_cot_{filial}_{ano_mes}")
            except Exception:
                pass
            try:
                ARQUIVO_TRABALHO.unlink()
            except Exception as e:
                messagebox.showerror("Erro", f"Não consegui apagar o Excel: {e}")
                return

        # 2. Zera QTDs no banco
        zerar_qtds(filial, ano_mes)

        # 3. Recarrega tabela
        self.recarregar()

        messagebox.showinfo("Nova Cotação", "Tudo zerado! Pode começar de novo.")      


    def _exportar_qtds(self):
        """Exporta QTDs para arquivo .json (para passar pro outro PC)."""
        from core.sync_qtds import exportar_qtds
        from tkinter import simpledialog

        ano_mes = self.app.ano_mes_ativo()

        autor = simpledialog.askstring(
            "Exportar QTDs",
            "Identificação deste PC (opcional):",
            initialvalue="PC 1"
        ) or "PC"

        try:
            caminho = exportar_qtds(ano_mes, autor)
        except Exception as e:
            messagebox.showerror("Erro ao exportar", str(e))
            return

        messagebox.showinfo(
            "Exportado!",
            f"Arquivo gerado em:\n\n{caminho}\n\n"
            f"Envie este arquivo para o outro computador\n"
            f"e use o botão '📥 Importar QTDs de outro PC'."
        )

    def _importar_qtds(self):
        """Importa QTDs de um arquivo .json gerado em outro PC."""
        from core.sync_qtds import importar_qtds
        from tkinter import filedialog
        from pathlib import Path

        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo .json de QTDs do outro PC",
            filetypes=[
                ("Arquivo de QTDs", "*.json"),
                ("Todos os arquivos", "*.*"),
            ]
        )
        if not caminho:
            return

        try:
            resultado = importar_qtds(Path(caminho))
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e))
            return

        if not resultado.get("ok"):
            messagebox.showerror("Erro", resultado.get("erro") or "Falha desconhecida.")
            return

        msg = f"Importação concluída!\n\n"
        msg += f"Arquivo com {resultado['total_no_arquivo']} itens\n"
        msg += f"Mês: {resultado['ano_mes_arquivo']}\n\n"
        msg += f"✓ {resultado['inseridos']} itens novos\n"
        msg += f"✓ {resultado['atualizados']} itens atualizados\n"

        if resultado["produtos_nao_encontrados"]:
            msg += f"\n⚠ {len(resultado['produtos_nao_encontrados'])} códigos não encontrados"

        messagebox.showinfo("Importação", msg)

        self.recarregar()