"""
Tela Cotação em CustomTkinter.
Duas tabelas lado a lado (MJZ e SZ) + geração do Excel cego.
"""
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import subprocess

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_BORDA,
    FONTE_TITULO, FONTE_SUBTITULO, FONTE_BOTAO,
)

from core.cotacao import listar_itens_para_preview, salvar_qtd
from core.excel_cotacao import (
    gerar_excel_cego,
    listar_fornecedores_do_banco,
    fazer_backup_excel,
    PASTA_TRABALHO,
)


ARQUIVO_CEGO = PASTA_TRABALHO / "cotacao_cega.xlsx"
ITENS_POR_PAGINA = 50


class TelaCotacao(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app

        # Estado independente por filial
        self.pagina_f1 = 0
        self.pagina_f2 = 0
        self.itens_f1 = []
        self.itens_f2 = []

        self._montar_titulo()
        self._montar_tabelas()
        self._montar_rodape()

        self.recarregar()

    # ============================================================
    # TÍTULO
    # ============================================================
    def _montar_titulo(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            frame, text="💲  Cotação",
            font=("Segoe UI", 22, "bold"),
            text_color=COR_TEXTO
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame, text="Itens com QTD > 0 — revisar antes de gerar o Excel cego.",
            font=("Segoe UI", 13),
            text_color=COR_TEXTO_SECUNDARIO
        ).pack(anchor="w", pady=(2, 0))

    # ============================================================
    # TABELAS LADO A LADO
    # ============================================================
    def _montar_tabelas(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, pady=(0, 12))
        container.grid_columnconfigure(0, weight=1, uniform="col")
        container.grid_columnconfigure(1, weight=1, uniform="col")
        container.grid_rowconfigure(0, weight=1)

        nome_f1 = self.app.config.get("filiais", {}).get("1", {}).get("nome", "FILIAL 1")
        nome_f2 = self.app.config.get("filiais", {}).get("2", {}).get("nome", "FILIAL 2")

        # F1
        self.card_f1 = self._criar_card(container, nome_f1, filial=1)
        self.card_f1.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        # F2
        self.card_f2 = self._criar_card(container, nome_f2, filial=2)
        self.card_f2.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

    def _criar_card(self, parent, nome_filial, filial):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)

        # Cabeçalho
        header = ctk.CTkFrame(card, fg_color="#1F4E79", corner_radius=0, height=36)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=nome_filial,
            font=("Segoe UI", 12, "bold"),
            text_color="white"
        ).pack(side="left", padx=15)

        # Total (QTD × VL Unit) — atualizado dinamicamente
        lbl_total = ctk.CTkLabel(
            header, text="Total: R$ 0,00",
            font=("Segoe UI", 11, "bold"),
            text_color="#86efac"  # verde claro
        )
        lbl_total.pack(side="right", padx=(0, 15))

        lbl_info = ctk.CTkLabel(
            header, text="0 itens",
            font=("Segoe UI", 10),
            text_color="#cbd5e1"
        )
        lbl_info.pack(side="right", padx=(0, 15))

        # Cabeçalho da tabela
        cols_header = ctk.CTkFrame(card, fg_color="#f8fafc", height=32)
        cols_header.pack(fill="x")
        cols_header.pack_propagate(False)

        for titulo, largura in [("Código", 90), ("Produto", 220), ("QTD", 70), ("VL Unit", 85)]:
            anchor = "w" if titulo == "Produto" else "center"
            ctk.CTkLabel(
                cols_header, text=titulo,
                font=("Segoe UI", 10, "bold"),
                text_color=COR_TEXTO,
                width=largura, anchor=anchor
            ).pack(side="left", padx=(8, 0), pady=6)

        # Área com scroll
        scroll_frame = ctk.CTkScrollableFrame(
            card, fg_color="transparent",
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        scroll_frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Rodapé (paginação)
        rodape = ctk.CTkFrame(card, fg_color="transparent", height=38)
        rodape.pack(fill="x", padx=8, pady=(0, 6))
        rodape.pack_propagate(False)

        lbl_pag = ctk.CTkLabel(
            rodape, text="Página 1 de 1",
            font=("Segoe UI", 10),
            text_color=COR_TEXTO_SECUNDARIO
        )
        lbl_pag.pack(side="left")

        btn_prox = ctk.CTkButton(
            rodape, text="▶",
            width=38, height=28, corner_radius=6,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=("Segoe UI", 11, "bold"),
            command=lambda f=filial: self._proxima_pagina(f)
        )
        btn_prox.pack(side="right", padx=(4, 0))

        btn_ant = ctk.CTkButton(
            rodape, text="◀",
            width=38, height=28, corner_radius=6,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=("Segoe UI", 11, "bold"),
            command=lambda f=filial: self._pagina_anterior(f)
        )
        btn_ant.pack(side="right")

        # Guarda referências
        if filial == 1:
            self.scroll_f1 = scroll_frame
            self.lbl_info_f1 = lbl_info
            self.lbl_total_f1 = lbl_total
            self.lbl_pag_f1 = lbl_pag
            self.btn_ant_f1 = btn_ant
            self.btn_prox_f1 = btn_prox
        else:
            self.scroll_f2 = scroll_frame
            self.lbl_info_f2 = lbl_info
            self.lbl_total_f2 = lbl_total
            self.lbl_pag_f2 = lbl_pag
            self.btn_ant_f2 = btn_ant
            self.btn_prox_f2 = btn_prox

        return card

    # ============================================================
    # RODAPÉ — BOTÕES
    # ============================================================
    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x")

        ctk.CTkButton(
            rodape, text="📋  Gerar Excel Cego",
            height=42, corner_radius=8,
            fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
            font=FONTE_BOTAO,
            command=self._gerar_excel_cego
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            rodape, text="📂  Abrir Excel Cego",
            height=42, corner_radius=8,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=FONTE_BOTAO,
            command=self._abrir_excel_cego
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            rodape, text="🔄  Recarregar",
            height=42, corner_radius=8,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=FONTE_BOTAO,
            command=self.recarregar
        ).pack(side="left")

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        ano_mes = self.app._ano_mes_ativo()

        self.itens_f1 = listar_itens_para_preview(1, ano_mes)
        self.itens_f2 = listar_itens_para_preview(2, ano_mes)

        self.pagina_f1 = 0
        self.pagina_f2 = 0

        self._popular(1)
        self._popular(2)

    def _popular(self, filial):
        if filial == 1:
            scroll, itens, lbl_info, lbl_pag, btn_ant, btn_prox = (
                self.scroll_f1, self.itens_f1, self.lbl_info_f1,
                self.lbl_pag_f1, self.btn_ant_f1, self.btn_prox_f1
            )
            pagina = self.pagina_f1
        else:
            scroll, itens, lbl_info, lbl_pag, btn_ant, btn_prox = (
                self.scroll_f2, self.itens_f2, self.lbl_info_f2,
                self.lbl_pag_f2, self.btn_ant_f2, self.btn_prox_f2
            )
            pagina = self.pagina_f2

        # Limpa
        for w in scroll.winfo_children():
            w.destroy()

        total = len(itens)
        total_pags = max(1, (total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)

        if pagina >= total_pags:
            pagina = total_pags - 1
            if filial == 1:
                self.pagina_f1 = pagina
            else:
                self.pagina_f2 = pagina

        inicio = pagina * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        pagina_itens = itens[inicio:fim]

        for idx, it in enumerate(pagina_itens):
            cor = "#f8fafc" if idx % 2 == 0 else "#ffffff"
            linha = ctk.CTkFrame(scroll, fg_color=cor, height=30, corner_radius=0)
            linha.pack(fill="x", pady=1)
            linha.pack_propagate(False)

            cod = str(it["codigo_interno"])[:15]
            desc = (it["descricao"] or "")[:30]
            qtd = it.get("qtd_comprador", 0)
            vl = it.get("vl_unit", 0)

            ctk.CTkLabel(linha, text=cod,
                         font=("Consolas", 10), text_color=COR_TEXTO,
                         width=90, anchor="w").pack(side="left", padx=(8, 0), pady=6)
            ctk.CTkLabel(linha, text=desc,
                         font=("Segoe UI", 10), text_color=COR_TEXTO,
                         width=220, anchor="w").pack(side="left", padx=(0, 0), pady=6)

            # QTD editável (botão que abre popup)
            btn_qtd = ctk.CTkButton(
                linha, text=f"{qtd:.0f}",
                width=70, height=24, corner_radius=6,
                fg_color="#FFF2CC", hover_color="#FFE699",
                text_color="#333333",
                font=("Segoe UI", 10, "bold"),
                command=lambda i=it, f=filial: self._editar_qtd(i, f)
            )
            btn_qtd.pack(side="left", padx=(0, 0), pady=3)

            ctk.CTkLabel(linha, text=f"R$ {vl:.2f}",
                         font=("Segoe UI", 10), text_color=COR_TEXTO,
                         width=85, anchor="center").pack(side="left", pady=6)

        # Atualiza info
        total_reais = sum(
            (it.get("qtd_comprador", 0) or 0) * (it.get("vl_unit", 0) or 0)
            for it in itens
        )

        # Atualiza info
        lbl_info.configure(text=f"{total} itens")
        lbl_pag.configure(text=f"Página {pagina + 1} de {total_pags}")

        # Atualiza total
        lbl_total = self.lbl_total_f1 if filial == 1 else self.lbl_total_f2
        lbl_total.configure(text=f"Total: R$ {total_reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        btn_ant.configure(state="normal" if pagina > 0 else "disabled")
        btn_prox.configure(state="normal" if pagina < total_pags - 1 else "disabled")

    def _pagina_anterior(self, filial):
        if filial == 1 and self.pagina_f1 > 0:
            self.pagina_f1 -= 1
            self._popular(1)
        elif filial == 2 and self.pagina_f2 > 0:
            self.pagina_f2 -= 1
            self._popular(2)

    def _proxima_pagina(self, filial):
        itens = self.itens_f1 if filial == 1 else self.itens_f2
        total_pags = max(1, (len(itens) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
        if filial == 1 and self.pagina_f1 < total_pags - 1:
            self.pagina_f1 += 1
            self._popular(1)
        elif filial == 2 and self.pagina_f2 < total_pags - 1:
            self.pagina_f2 += 1
            self._popular(2)

    # ============================================================
    # EDITAR QTD
    # ============================================================
    def _editar_qtd(self, item, filial):
        ano_mes = self.app._ano_mes_ativo()
        valor_atual = item.get("qtd_comprador", 0)

        popup = ctk.CTkToplevel(self)
        popup.title("Editar QTD")
        popup.geometry("380x220")
        popup.transient(self)
        popup.grab_set()

        ctk.CTkLabel(popup, text=item["descricao"][:40],
                     font=("Segoe UI", 12, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=f"Filial {'1 (MJZ)' if filial == 1 else '2 (SZ)'}",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack()

        ctk.CTkLabel(popup, text="Quantidade:",
                     font=("Segoe UI", 11)).pack(pady=(15, 5))

        var = ctk.StringVar(value=f"{valor_atual:.0f}")
        entrada = ctk.CTkEntry(popup, textvariable=var,
                                font=("Segoe UI", 16),
                                justify="center", width=120, height=40)
        entrada.pack()
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

            salvar_qtd(filial, item["produto_id"], ano_mes, novo)
            item["qtd_comprador"] = novo
            popup.destroy()
            self._popular(filial)

        entrada.bind("<Return>", confirmar)

        ctk.CTkButton(popup, text="Confirmar",
                       height=38, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO,
                       command=confirmar).pack(pady=15)

    # ============================================================
    # GERAR EXCEL CEGO
    # ============================================================
    def _gerar_excel_cego(self):
        if not self.itens_f1 and not self.itens_f2:
            messagebox.showwarning("Aviso",
                "Nenhum item com QTD > 0.\nDecida as quantidades primeiro.")
            return

        # Monta produtos (só cód. barras + descrição)
        produtos_f1 = [
            {"codigo_barras": it.get("codigo_barras") or it["codigo_interno"],
             "descricao": it["descricao"]}
            for it in self.itens_f1
        ]
        produtos_f2 = [
            {"codigo_barras": it.get("codigo_barras") or it["codigo_interno"],
             "descricao": it["descricao"]}
            for it in self.itens_f2
        ]

        fornecedores = listar_fornecedores_do_banco()

        if not fornecedores:
            messagebox.showwarning("Aviso",
                "Nenhum fornecedor cadastrado para participar da cotação.\n\n"
                "Confira o arquivo FORNECEDORES_COTACAO.xls e reimporte.")
            return

        # Backup do anterior
        if ARQUIVO_CEGO.exists():
            resp = messagebox.askyesno("Backup",
                "Já existe um Excel cego. Fazer backup antes?")
            if resp:
                try:
                    fazer_backup_excel(ARQUIVO_CEGO, "cego_antes_gerar")
                except Exception:
                    pass

        try:
            gerar_excel_cego(
                produtos_f1=produtos_f1,
                produtos_f2=produtos_f2,
                fornecedores=fornecedores,
                config=self.app.config,
                caminho_destino=ARQUIVO_CEGO,
            )
            messagebox.showinfo("Excel Cego gerado",
                f"Arquivo criado:\n\n"
                f"• MJZ: {len(produtos_f1)} itens\n"
                f"• SZ:  {len(produtos_f2)} itens\n"
                f"• Fornecedores: {len(fornecedores)}\n\n"
                f"{ARQUIVO_CEGO}")
        except Exception as e:
            messagebox.showerror("Erro ao gerar Excel cego", str(e))

    def _abrir_excel_cego(self):
        if not ARQUIVO_CEGO.exists():
            messagebox.showwarning("Aviso",
                "Gere o Excel cego primeiro.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(ARQUIVO_CEGO)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ARQUIVO_CEGO])
            else:
                subprocess.Popen(["xdg-open", ARQUIVO_CEGO])
        except Exception as e:
            messagebox.showerror("Erro", str(e))