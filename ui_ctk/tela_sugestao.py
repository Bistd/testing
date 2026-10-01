"""
Tela Sugestão em CustomTkinter.
Seletor de filial/mês + filtros + tabela + botões de ação.
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import sys
import subprocess
from pathlib import Path

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_ROXO, COR_ROXO_HOVER,
    COR_LARANJA, COR_LARANJA_HOVER,
    COR_VERMELHO, COR_VERMELHO_HOVER,
    FONTE_TITULO, FONTE_BOTAO, COR_BORDA,
    COR_TEXTO, COR_TEXTO_SECUNDARIO,
)

from core.calculos import montar_sugestoes
from core.cotacao import salvar_qtds_em_lote, carregar_qtds, zerar_qtds
from core.excel_cotacao import (
    gerar_excel_trabalho, ler_excel_trabalho,
    fazer_backup_excel, PASTA_TRABALHO,
)
from core.database import conectar
from core.config import salvar_config
from core.util_meses import eh_pasta_de_mes
from core.config import caminho_pasta_entrada
from ui_ctk.loading import LoadingOverlay


ARQUIVO_TRABALHO = PASTA_TRABALHO / "cotacao_trabalho.xlsx"
ARQUIVO_CEGO = PASTA_TRABALHO / "cotacao_cego.xlsx"


class TelaSugestao(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app
        self.dados = []
        self.pagina_atual = 0
        self.itens_por_pagina = 100

        self._montar_cabecalho()
        self._montar_filtros()
        self._montar_tabela()
        self._montar_rodape()

        # Overlay de carregando (fica por cima de tudo)
        self.loading = LoadingOverlay(self)

        # Carrega inicial (sem overlay — é rápido o suficiente)
        self.recarregar()

    # ============================================================
    # CABEÇALHO — Filial + Mês
    # ============================================================
    def _montar_cabecalho(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="x", pady=(0, 12))

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=15, pady=10)

        # Filial
        ctk.CTkLabel(linha, text="🏪 Filial:",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
        self.var_filial = ctk.StringVar(value=f"Filial {self.app.config['filial_ativa']}")
        combo_filial = ctk.CTkComboBox(
            linha, values=["Filial 1", "Filial 2"],
            variable=self.var_filial, width=120, height=32,
            command=self._on_filial_change
        )
        combo_filial.pack(side="left", padx=(0, 20))

        # Mês
        ctk.CTkLabel(linha, text="📅 Mês ativo:",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
        self.var_mes = ctk.StringVar(value=self.app.config["mes_ativo"])
        valores = self._listar_meses_disponiveis()
        combo_mes = ctk.CTkComboBox(
            linha, values=valores,
            variable=self.var_mes, width=120, height=32,
            command=self._on_mes_change
        )
        combo_mes.pack(side="left", padx=(0, 20))

        # Atualizar
        ctk.CTkButton(linha, text="🔄  Atualizar",
                       width=120, height=32, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=("Segoe UI", 12, "bold"),
                       command=self.recarregar).pack(side="left")

    def _listar_meses_disponiveis(self):
        pasta = caminho_pasta_entrada(self.app.config) / "MOVIMENTO"
        if not pasta.exists():
            return [self.app.config["mes_ativo"]]
        meses = [p.name for p in pasta.iterdir() if p.is_dir() and eh_pasta_de_mes(p.name)]
        meses.sort()
        return meses or [self.app.config["mes_ativo"]]

    def _on_filial_change(self, valor):
        num = 1 if valor.endswith("1") else 2
        self.app.config["filial_ativa"] = num
        salvar_config(self.app.config)
        self.recarregar()

    def _on_mes_change(self, valor):
        self.app.config["mes_ativo"] = valor
        salvar_config(self.app.config)
        self.recarregar()

    # ============================================================
    # TÍTULO + FILTROS
    # ============================================================
    def _montar_filtros(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="x", pady=(0, 12))

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=15, pady=12)

        # Departamento
        ctk.CTkLabel(linha, text="Departamento",
                     font=("Segoe UI", 10, "bold"),
                     text_color=COR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 5))
        self.var_depto = ctk.StringVar(value="Todos")
        self.combo_depto = ctk.CTkComboBox(
            linha, values=["Todos"], variable=self.var_depto,
            width=120, height=32
        )
        self.combo_depto.pack(side="left", padx=(0, 15))

        # Fornecedor
        ctk.CTkLabel(linha, text="Fornecedor",
                     font=("Segoe UI", 10, "bold"),
                     text_color=COR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 5))
        self.var_forn = ctk.StringVar(value="Todos")
        self.combo_forn = ctk.CTkComboBox(
            linha, values=["Todos"], variable=self.var_forn,
            width=120, height=32
        )
        self.combo_forn.pack(side="left", padx=(0, 15))

        # Busca
        ctk.CTkLabel(linha, text="Buscar",
                     font=("Segoe UI", 10, "bold"),
                     text_color=COR_TEXTO_SECUNDARIO).pack(side="left", padx=(0, 5))
        self.var_busca = ctk.StringVar()
        self.entrada_busca = ctk.CTkEntry(
            linha, textvariable=self.var_busca,
            placeholder_text="ex: sor%melan%500%",
            width=280, height=32
        )
        self.entrada_busca.pack(side="left", padx=(0, 15))
        self.entrada_busca.bind("<Return>", lambda e: self.recarregar())

        # Botões
        ctk.CTkButton(
            linha, text="🔍  Filtrar",
            width=100, height=32, corner_radius=8,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=("Segoe UI", 12, "bold"),
            command=self.recarregar
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            linha, text="♻  Limpar",
            width=100, height=32, corner_radius=8,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=("Segoe UI", 12, "bold"),
            command=self._limpar_filtros
        ).pack(side="left")

    def _limpar_filtros(self):
        self.var_depto.set("Todos")
        self.var_forn.set("Todos")
        self.var_busca.set("")
        self.recarregar()

    # ============================================================
    # TABELA
    # ============================================================
    def _montar_tabela(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="both", expand=True, pady=(0, 12))

        header = ctk.CTkFrame(card, fg_color="#f8fafc", height=40)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        colunas = [
            ("Código", 110),
            ("Produto", 400),
            ("Departamento", 120),
            ("Fornecedor", 100),
            ("% Vend.", 100),
        ]
        for titulo, largura in colunas:
            ctk.CTkLabel(
                header, text=titulo,
                font=("Segoe UI", 11, "bold"),
                text_color=COR_TEXTO,
                width=largura, anchor="w"
            ).pack(side="left", padx=(15, 0), pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(
            card, fg_color="transparent",
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def _popular_tabela(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        total = len(self.dados)
        inicio = self.pagina_atual * self.itens_por_pagina
        fim = inicio + self.itens_por_pagina
        pagina = self.dados[inicio:fim]

        for idx, d in enumerate(pagina):
            cor_fundo = "#f8fafc" if idx % 2 == 0 else "#ffffff"
            linha = ctk.CTkFrame(self.scroll_frame, fg_color=cor_fundo,
                                  height=36, corner_radius=0)
            linha.pack(fill="x", pady=1)
            linha.pack_propagate(False)

            vals = [
                (d["codigo_interno"], 110, "w"),
                (d["descricao"][:60], 400, "w"),
                (d["departamento"] or "", 120, "w"),
                (d["fornecedor_codigo"] or "", 100, "w"),
                (f"{d['pct_vendido']:.1f}%", 100, "w"),
            ]
            for valor, largura, anchor in vals:
                ctk.CTkLabel(
                    linha, text=valor,
                    font=("Consolas" if valor == d["codigo_interno"] else "Segoe UI", 11),
                    text_color=COR_TEXTO,
                    width=largura, anchor=anchor
                ).pack(side="left", padx=(15, 0), pady=6)

        self._atualizar_paginacao()

    def _atualizar_paginacao(self):
        total = len(self.dados)
        total_paginas = max(1, (total + self.itens_por_pagina - 1) // self.itens_por_pagina)

        if self.pagina_atual >= total_paginas:
            self.pagina_atual = total_paginas - 1
        if self.pagina_atual < 0:
            self.pagina_atual = 0

        inicio = self.pagina_atual * self.itens_por_pagina + 1
        fim = min((self.pagina_atual + 1) * self.itens_por_pagina, total)

        texto = f"Mostrando {inicio} a {fim} de {total} produtos" if total else "Nenhum produto"
        self.lbl_total_tabela.configure(text=texto)

        if hasattr(self, "btn_pag_ant"):
            self.btn_pag_ant.configure(state="normal" if self.pagina_atual > 0 else "disabled")
            self.btn_pag_prox.configure(state="normal" if self.pagina_atual < total_paginas - 1 else "disabled")
            self.lbl_pagina.configure(text=f"Página {self.pagina_atual + 1} de {total_paginas}")

    def _pagina_anterior(self):
        if self.pagina_atual > 0:
            self.pagina_atual -= 1
            self._popular_tabela()

    def _pagina_proxima(self):
        total_paginas = (len(self.dados) + self.itens_por_pagina - 1) // self.itens_por_pagina
        if self.pagina_atual < total_paginas - 1:
            self.pagina_atual += 1
            self._popular_tabela()

    # ============================================================
    # RODAPÉ
    # ============================================================
    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x")

        linha_info = ctk.CTkFrame(rodape, fg_color="transparent")
        linha_info.pack(fill="x", pady=(0, 8))

        self.lbl_total_tabela = ctk.CTkLabel(
            linha_info, text="",
            font=("Segoe UI", 12, "bold"),
            text_color=COR_TEXTO_SECUNDARIO
        )
        self.lbl_total_tabela.pack(side="left")

        self.btn_pag_prox = ctk.CTkButton(
            linha_info, text="Próxima ▶",
            width=100, height=30, corner_radius=6,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=("Segoe UI", 11, "bold"),
            command=self._pagina_proxima
        )
        self.btn_pag_prox.pack(side="right", padx=(8, 0))

        self.lbl_pagina = ctk.CTkLabel(
            linha_info, text="Página 1 de 1",
            font=("Segoe UI", 11),
            text_color=COR_TEXTO_SECUNDARIO
        )
        self.lbl_pagina.pack(side="right", padx=(0, 8))

        self.btn_pag_ant = ctk.CTkButton(
            linha_info, text="◀ Anterior",
            width=100, height=30, corner_radius=6,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=("Segoe UI", 11, "bold"),
            command=self._pagina_anterior
        )
        self.btn_pag_ant.pack(side="right")

        # Linha 1 — ações principais
        l1 = ctk.CTkFrame(rodape, fg_color="transparent")
        l1.pack(fill="x", pady=(0, 6))

        ctk.CTkButton(l1, text="📤  Enviar para Excel",
                       height=38, corner_radius=8,
                       fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
                       font=FONTE_BOTAO, command=self._enviar_excel).pack(side="left", padx=(0, 8))

        ctk.CTkButton(l1, text="📂  Abrir Excel",
                       height=38, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO, command=self._abrir_excel).pack(side="left", padx=(0, 8))

        ctk.CTkButton(l1, text="💾  Salvar quantidades",
                       height=38, corner_radius=8,
                       fg_color=COR_ROXO, hover_color=COR_ROXO_HOVER,
                       font=FONTE_BOTAO, command=self._salvar_qtds).pack(side="left", padx=(0, 8))

        # Linha 2 — sync + nova cotação
        l2 = ctk.CTkFrame(rodape, fg_color="transparent")
        l2.pack(fill="x")

        ctk.CTkButton(l2, text="📤  Exportar QTDs",
                       height=38, corner_radius=8,
                       fg_color="#06b6d4", hover_color="#0891b2",
                       font=FONTE_BOTAO, command=self._exportar_qtds).pack(side="left", padx=(0, 8))

        ctk.CTkButton(l2, text="📥  Importar QTDs",
                       height=38, corner_radius=8,
                       fg_color=COR_LARANJA, hover_color=COR_LARANJA_HOVER,
                       font=FONTE_BOTAO, command=self._importar_qtds).pack(side="left", padx=(0, 8))

        ctk.CTkButton(l2, text="🆕  Nova Cotação",
                       height=38, corner_radius=8,
                       fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER,
                       font=FONTE_BOTAO, command=self._nova_cotacao).pack(side="right")

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        # Mostra overlay e desabilita cliques
        self.loading.mostrar("Carregando sugestões...")
        self.update_idletasks()

        try:
            self._recarregar_interno()
        finally:
            self.loading.esconder()

    def _recarregar_interno(self):
        filial = self.app.config["filial_ativa"]
        ano_mes = self.app._ano_mes_ativo()

        depto = self.var_depto.get()
        forn = self.var_forn.get()
        busca = self.entrada_busca.get().strip()

        depto = None if depto in ("Todos", "") else depto
        forn = None if forn in ("Todos", "") else forn
        busca = None if not busca else busca

        try:
            self.dados = montar_sugestoes(
                filial_id=filial,
                ano_mes_atual=ano_mes,
                config=self.app.config,
                filtro_departamento=depto,
                filtro_fornecedor=forn,
                filtro_busca=busca,
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            self.dados = []

        qtds = carregar_qtds(filial, ano_mes)
        for d in self.dados:
            d["qtd_comprador"] = qtds.get(d["produto_id"], 0)

        self.pagina_atual = 0
        self._popular_tabela()
        self._atualizar_combos()

    def _atualizar_combos(self):
        deptos = sorted({d["departamento"] for d in self.dados if d["departamento"]})
        forns = sorted({d["fornecedor_codigo"] for d in self.dados if d["fornecedor_codigo"]})
        self.combo_depto.configure(values=["Todos"] + deptos)
        self.combo_forn.configure(values=["Todos"] + forns)

    # ============================================================
    # AÇÕES
    # ============================================================
    def _enviar_excel(self):
        if not self.dados:
            messagebox.showwarning("Aviso", "Sem produtos na tela.")
            return

        filial = self.app.config["filial_ativa"]
        ano_mes = self.app._ano_mes_ativo()

        if ARQUIVO_TRABALHO.exists():
            resp = messagebox.askyesno("Backup",
                "Já existe um Excel de trabalho. Fazer backup antes?")
            if resp:
                try:
                    fazer_backup_excel(ARQUIVO_TRABALHO, "antes_gerar")
                except Exception:
                    pass

        self.loading.mostrar("Gerando Excel de trabalho...")
        self.update_idletasks()
        try:
            produtos_excel = self._montar_produtos_para_excel(filial, ano_mes)
            gerar_excel_trabalho(produtos_excel, ano_mes, ARQUIVO_TRABALHO, self.app.config)
            messagebox.showinfo("OK", f"Excel gerado com {len(produtos_excel)} produtos.")
        except Exception as e:
            messagebox.showerror("Erro ao gerar Excel", str(e))
        finally:
            self.loading.esconder()

    def _montar_produtos_para_excel(self, filial_id, ano_mes):
        from core.util_meses import ultimos_n_meses
        lista_meses = ultimos_n_meses(ano_mes, 12)
        ph = ",".join("?" * len(lista_meses))

        ids = [d["produto_id"] for d in self.dados]
        if not ids:
            return []

        conn = conectar()
        cur = conn.cursor()

        ph_ids = ",".join("?" * len(ids))
        cur.execute(f"""
            SELECT produto_id, ano_mes, qtd_entrada, qtd_venda, qtd_avaria
            FROM historico_mensal
            WHERE filial_id = ?
              AND produto_id IN ({ph_ids})
              AND ano_mes IN ({ph})
        """, [filial_id] + ids + lista_meses)

        hist_por_produto = {}
        for r in cur.fetchall():
            pid = r["produto_id"]
            if pid not in hist_por_produto:
                hist_por_produto[pid] = {}
            hist_por_produto[pid][r["ano_mes"]] = {
                "qtd_entrada": r["qtd_entrada"] or 0,
                "qtd_venda": r["qtd_venda"] or 0,
                "qtd_avaria": r["qtd_avaria"] or 0,
            }

        cur.execute(f"SELECT id, codigo_barras FROM produtos WHERE id IN ({ph_ids})", ids)
        barras = {r["id"]: (r["codigo_barras"] or "") for r in cur.fetchall()}

        conn.close()

        produtos = []
        for d in self.dados:
            pid = d["produto_id"]
            produtos.append({
                "codigo_interno": d["codigo_interno"],
                "codigo_barras": barras.get(pid, ""),
                "descricao": d["descricao"],
                "vl_unit": d["vl_unit"],
                "estoque": d["estoque_atual"],
                "cx": d.get("cx", 1),
                "hist": hist_por_produto.get(pid, {}),
            })

        return produtos

    def _abrir_excel(self):
        if not ARQUIVO_TRABALHO.exists():
            messagebox.showwarning("Aviso", "Gere o Excel primeiro.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(ARQUIVO_TRABALHO)
            else:
                subprocess.Popen(["xdg-open", str(ARQUIVO_TRABALHO)])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _salvar_qtds(self):
        if not ARQUIVO_TRABALHO.exists():
            messagebox.showwarning("Aviso", "Gere o Excel primeiro.")
            return

        filial = self.app.config["filial_ativa"]
        ano_mes = self.app._ano_mes_ativo()

        self.loading.mostrar("Lendo Excel e salvando quantidades...")
        self.update_idletasks()

        try:
            linhas = ler_excel_trabalho(ARQUIVO_TRABALHO)
        except Exception as e:
            self.loading.esconder()
            messagebox.showerror("Erro ao ler", str(e))
            return

        conn = conectar()
        cur = conn.cursor()
        salvar = []
        for linha in linhas:
            cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?",
                        (linha["codigo_interno"],))
            r = cur.fetchone()
            if r:
                salvar.append({"produto_id": r[0], "qtd": linha["qtd"]})
        conn.close()

        try:
            n = salvar_qtds_em_lote(filial, ano_mes, salvar)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        fazer_backup_excel(ARQUIVO_TRABALHO, f"salvo_{filial}_{ano_mes}")
        self.loading.esconder()
        messagebox.showinfo("OK", f"{n} QTDs salvas!")
        self.recarregar()

    def _exportar_qtds(self):
        from core.sync_qtds import exportar_qtds
        from tkinter import simpledialog
        ano_mes = self.app._ano_mes_ativo()
        autor = simpledialog.askstring("Exportar", "Identificação:", initialvalue="PC") or "PC"
        try:
            caminho = exportar_qtds(ano_mes, autor)
            messagebox.showinfo("Exportado", f"Arquivo gerado em:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _importar_qtds(self):
        from core.sync_qtds import importar_qtds
        caminho = filedialog.askopenfilename(
            title="Selecione o arquivo .json",
            filetypes=[("Arquivo QTDs", "*.json"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            r = importar_qtds(Path(caminho))
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        if not r.get("ok"):
            messagebox.showerror("Erro", r.get("erro") or "Falha")
            return
        messagebox.showinfo("Importado",
            f"{r['total_no_arquivo']} itens\n"
            f"{r['inseridos']} novos | {r['atualizados']} atualizados")
        self.recarregar()

    def _nova_cotacao(self):
        ano_mes = self.app._ano_mes_ativo()

        resp = messagebox.askyesno(
            "Nova Cotação",
            "Isso vai apagar TUDO desta cotação (as 2 filiais):\n\n"
            "• QTDs salvas (Filial 1 + Filial 2)\n"
            "• Excel de trabalho\n"
            "• Excel cego\n"
            "• Respostas importadas dos fornecedores\n\n"
            "Começar do zero?"
        )
        if not resp:
            return

        # 1. Zera QTDs das 2 filiais
        for f in [1, 2]:
            zerar_qtds(f, ano_mes)

        # 2. Apaga Excel de trabalho (com backup)
        if ARQUIVO_TRABALHO.exists():
            try:
                fazer_backup_excel(ARQUIVO_TRABALHO, f"nova_cot_{ano_mes}")
                ARQUIVO_TRABALHO.unlink()
            except Exception:
                pass

        # 3. Apaga Excel cego (com backup)
        if ARQUIVO_CEGO.exists():
            try:
                fazer_backup_excel(ARQUIVO_CEGO, f"nova_cot_cego_{ano_mes}")
                ARQUIVO_CEGO.unlink()
            except Exception:
                pass

        # 4. Apaga respostas importadas (das 2 filiais)
        try:
            conn = conectar()
            cur = conn.cursor()
            cur.execute("DELETE FROM cotacao_respostas WHERE ano_mes = ?", (ano_mes,))
            conn.commit()
            conn.close()
        except Exception:
            pass

        messagebox.showinfo("Nova Cotação", "Tudo zerado nas 2 filiais!")
        self.recarregar()