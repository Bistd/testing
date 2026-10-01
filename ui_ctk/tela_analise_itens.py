"""
Janela de Análise por Item (CustomTkinter).
Mostra campeões, variação vs. última entrada, edita QTD.
"""
import customtkinter as ctk
from tkinter import messagebox
from ui_ctk.loading import LoadingOverlay

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_VERMELHO, COR_VERMELHO_HOVER,
    COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_BORDA,
    FONTE_TITULO, FONTE_BOTAO,
)

from core.analise import calcular_campeoes
from core.cotacao import salvar_qtd, carregar_qtds


ITENS_POR_PAGINA = 100


def abrir_janela_analise_itens(app):
    JanelaAnaliseItens(app)


class JanelaAnaliseItens:
    def __init__(self, app):
        self.app = app
        self.dados = []
        self.qtds_originais = {}
        self.pagina = 0

        self.janela = ctk.CTkToplevel(app)
        self.janela.title("📊 Análise por Item")
        self.janela.geometry("1400x750")
        self.janela.minsize(1000, 600)

        # Abre maximizada
        try:
            self.janela.state("zoomed")
        except Exception:
            pass
        self.janela.after(100, lambda: self.janela.state("zoomed"))

        self._montar_topo()
        self._montar_tabela()
        self._montar_rodape()

        # Overlay (usa a janela como parent)
        self.loading = LoadingOverlay(self.janela)

        self.recarregar()

    # ============================================================
    # TOPO
    # ============================================================
    def _montar_topo(self):
        topo = ctk.CTkFrame(self.janela, fg_color="transparent")
        topo.pack(fill="x", padx=15, pady=(15, 8))

        ctk.CTkLabel(topo, text="Filial:",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
        self.var_filial = ctk.StringVar(value="")
        ctk.CTkComboBox(topo, values=["", "Filial 1", "Filial 2"],
                         variable=self.var_filial,
                         width=140, command=lambda v: self.recarregar()
                         ).pack(side="left", padx=(0, 15))

        ctk.CTkLabel(topo, text="Ordenar por:",
                     font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 5))
        self.var_ordem = ctk.StringVar(value="Maior aumento %")
        ctk.CTkComboBox(topo,
                         values=["Maior aumento %", "Maior queda %",
                                 "Maior valor R$", "Produto"],
                         variable=self.var_ordem,
                         width=180, command=lambda v: self.recarregar()
                         ).pack(side="left", padx=(0, 15))

        ctk.CTkButton(topo, text="🔄  Recarregar",
                       width=120, height=32, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO,
                       command=self.recarregar).pack(side="left")

        self.lbl_info = ctk.CTkLabel(topo, text="",
                                      font=("Segoe UI", 11),
                                      text_color=COR_TEXTO_SECUNDARIO)
        self.lbl_info.pack(side="right")

    # ============================================================
    # TABELA
    # ============================================================
    def _montar_tabela(self):
        card = ctk.CTkFrame(self.janela, corner_radius=12,
                            fg_color=COR_CARD, border_width=1, border_color=COR_BORDA)
        card.pack(fill="both", expand=True, padx=15, pady=(0, 8))

        header = ctk.CTkFrame(card, fg_color="#f8fafc", height=36)
        header.pack(fill="x")
        header.pack_propagate(False)

        cols = [
            ("Código", 90), ("Produto", 300), ("Depto", 55),
            ("Filial", 55), ("VL Compra", 95), ("VL Ant", 95),
            ("Var %", 80), ("Campeão", 140), ("QTD", 80),
        ]
        for titulo, largura in cols:
            anchor = "w" if titulo == "Produto" else "center"
            ctk.CTkLabel(header, text=titulo,
                          font=("Segoe UI", 10, "bold"),
                          text_color=COR_TEXTO,
                          width=largura, anchor=anchor
                          ).pack(side="left", padx=(6, 0), pady=6)

        self.scroll = ctk.CTkScrollableFrame(
            card, fg_color="transparent",
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)

    # ============================================================
    # RODAPÉ
    # ============================================================
    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self.janela, fg_color="transparent")
        rodape.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(rodape, text="💾  Salvar Alterações",
                       width=180, height=40, corner_radius=8,
                       fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
                       font=FONTE_BOTAO,
                       command=self._salvar).pack(side="left", padx=(0, 8))

        ctk.CTkButton(rodape, text="✅  Salvar e Fechar",
                       width=180, height=40, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO,
                       command=self._salvar_e_fechar).pack(side="left", padx=(0, 8))

        ctk.CTkButton(rodape, text="❌  Fechar sem Salvar",
                       width=180, height=40, corner_radius=8,
                       fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER,
                       font=FONTE_BOTAO,
                       command=self._fechar_sem_salvar).pack(side="right")

        # Paginação no centro
        pag_frame = ctk.CTkFrame(rodape, fg_color="transparent")
        pag_frame.pack(side="left", padx=30)

        self.btn_ant = ctk.CTkButton(pag_frame, text="◀",
                                       width=40, height=32, corner_radius=6,
                                       fg_color="#e2e8f0", hover_color="#cbd5e1",
                                       text_color=COR_TEXTO,
                                       command=self._pag_anterior)
        self.btn_ant.pack(side="left")

        self.lbl_pag = ctk.CTkLabel(pag_frame, text="Página 1 de 1",
                                     font=("Segoe UI", 11),
                                     text_color=COR_TEXTO_SECUNDARIO,
                                     width=140)
        self.lbl_pag.pack(side="left", padx=8)

        self.btn_prox = ctk.CTkButton(pag_frame, text="▶",
                                        width=40, height=32, corner_radius=6,
                                        fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                                        command=self._pag_proxima)
        self.btn_prox.pack(side="left")

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        filtro = self.var_filial.get()

        if not filtro or filtro not in ("Filial 1", "Filial 2"):
            self.dados = []
            self.qtds_originais = {}
            self.pagina = 0
            self._popular()
            self.lbl_info.configure(text="Escolha uma filial para analisar")
            return

        self.loading.mostrar("Carregando análise...")
        self.janela.update_idletasks()

        try:
            self._recarregar_interno()
        finally:
            self.loading.esconder()

    def _recarregar_interno(self):
        filtro = self.var_filial.get()
        filial_id = 1 if filtro == "Filial 1" else 2
        ano_mes = self.app._ano_mes_ativo()

        filial_id = 1 if filtro == "Filial 1" else 2
        ano_mes = self.app._ano_mes_ativo()

        try:
            campeoes = calcular_campeoes(ano_mes, filial_id)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            campeoes = []

        qtds = carregar_qtds(filial_id, ano_mes)

        for c in campeoes:
            c["qtd_comprador"] = qtds.get(c["produto_id"], 0)

        # Ordena
        ordem = self.var_ordem.get()
        if ordem == "Maior aumento %":
            campeoes.sort(key=lambda x: x.get("variacao_pct") if x.get("variacao_pct") is not None else -9999, reverse=True)
        elif ordem == "Maior queda %":
            campeoes.sort(key=lambda x: x.get("variacao_pct") if x.get("variacao_pct") is not None else 9999)
        elif ordem == "Maior valor R$":
            campeoes.sort(key=lambda x: (x.get("preco_unitario") or 0) * (x.get("qtd_comprador") or 0), reverse=True)
        elif ordem == "Produto":
            campeoes.sort(key=lambda x: x.get("descricao", ""))

        self.dados = campeoes
        self.qtds_originais = {
            c["produto_id"]: c.get("qtd_comprador", 0)
            for c in campeoes
        }
        self.pagina = 0
        self._popular()

    def _popular(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        total = len(self.dados)
        total_pags = max(1, (total + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)

        if self.pagina >= total_pags:
            self.pagina = total_pags - 1

        inicio = self.pagina * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        pagina = self.dados[inicio:fim]

        for idx, c in enumerate(pagina):
            var = c.get("variacao_pct")
            if var is None:
                var_str = "—"
                bg = "#FFF2CC"
            else:
                var_str = f"{var:+.1f}%"
                if var < -10:
                    bg = "#E2EFDA"
                elif var <= 10:
                    bg = "#FFF2CC"
                elif var <= 20:
                    bg = "#FFE699"
                else:
                    bg = "#F8CBAD"

            linha = ctk.CTkFrame(self.scroll, fg_color=bg, height=32, corner_radius=0)
            linha.pack(fill="x", pady=1)
            linha.pack_propagate(False)

            filial_str = "F1" if c["filial_id"] == 1 else "F2"
            nome_forn = c.get("fornecedor_nome") or f"Forn {c['fornecedor_codigo']}"

            vals = [
                (str(c.get("codigo_interno", ""))[:15], 90, "w"),
                (c.get("descricao", "")[:45], 300, "w"),
                (c.get("departamento", "") or "", 55, "center"),
                (filial_str, 55, "center"),
                (f"R$ {c.get('preco_unitario', 0):.2f}", 95, "center"),
                (f"R$ {c.get('vl_ant', 0):.2f}" if c.get('vl_ant') else "—", 95, "center"),
                (var_str, 80, "center"),
                (nome_forn[:20], 140, "center"),
            ]
            for texto, largura, anchor in vals:
                ctk.CTkLabel(linha, text=texto,
                              font=("Segoe UI", 10),
                              text_color=COR_TEXTO,
                              width=largura, anchor=anchor
                              ).pack(side="left", padx=(6, 0), pady=6)

            ctk.CTkButton(
                linha, text=f"{c.get('qtd_comprador', 0):.0f}",
                width=80, height=24, corner_radius=6,
                fg_color="#FFF2CC", hover_color="#FFE699",
                text_color="#333333",
                font=("Segoe UI", 10, "bold"),
                command=lambda x=c: self._editar_qtd(x)
            ).pack(side="left", padx=(0, 0), pady=3)

        self.lbl_pag.configure(text=f"Página {self.pagina + 1} de {total_pags}  ({total} itens)")
        self.btn_ant.configure(state="normal" if self.pagina > 0 else "disabled")
        self.btn_prox.configure(state="normal" if self.pagina < total_pags - 1 else "disabled")

        if total > 0:
            self.lbl_info.configure(text=f"{total} itens campeões")
        elif self.var_filial.get() in ("Filial 1", "Filial 2"):
            self.lbl_info.configure(text="Nenhum item nesta filial")

    def _pag_anterior(self):
        if self.pagina > 0:
            self.pagina -= 1
            self._popular()

    def _pag_proxima(self):
        total_pags = max(1, (len(self.dados) + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
        if self.pagina < total_pags - 1:
            self.pagina += 1
            self._popular()

    # ============================================================
    # EDITAR QTD
    # ============================================================
    def _editar_qtd(self, item):
        valor_atual = item.get("qtd_comprador", 0)

        popup = ctk.CTkToplevel(self.janela)
        popup.title("Editar QTD")
        popup.geometry("400x250")
        popup.transient(self.janela)
        popup.grab_set()

        ctk.CTkLabel(popup, text=item["descricao"][:45],
                     font=("Segoe UI", 12, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(popup, text=f"Campeão: {item.get('fornecedor_nome', '')[:30]}",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack()

        ctk.CTkLabel(popup, text="Quantidade:",
                     font=("Segoe UI", 11)).pack(pady=(15, 5))

        var = ctk.StringVar(value=f"{valor_atual:.0f}")
        entrada = ctk.CTkEntry(popup, textvariable=var,
                                font=("Segoe UI", 16),
                                justify="center", width=140, height=42)
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
            item["qtd_comprador"] = novo
            popup.destroy()
            self._popular()

        entrada.bind("<Return>", confirmar)

        ctk.CTkButton(popup, text="Confirmar",
                       width=120, height=38, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO,
                       command=confirmar).pack(pady=15)

    # ============================================================
    # SALVAR
    # ============================================================
    def _salvar(self, silencioso=False):
        filtro = self.var_filial.get()
        if not filtro or filtro not in ("Filial 1", "Filial 2"):
            return 0

        filial_id = 1 if filtro == "Filial 1" else 2
        ano_mes = self.app._ano_mes_ativo()
        alterados = 0

        try:
            for c in self.dados:
                qtd_antiga = self.qtds_originais.get(c["produto_id"], 0)
                qtd_nova = c.get("qtd_comprador", 0)
                if abs(qtd_nova - qtd_antiga) > 0.001:
                    salvar_qtd(filial_id, c["produto_id"], ano_mes, qtd_nova)
                    alterados += 1
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return 0

        self.qtds_originais = {
            c["produto_id"]: c.get("qtd_comprador", 0)
            for c in self.dados
        }

        if not silencioso:
            if alterados == 0:
                messagebox.showinfo("Nada a salvar", "Nenhuma alteração detectada.")
            else:
                messagebox.showinfo("Salvo", f"{alterados} quantidades atualizadas!")

        return alterados

    def _salvar_e_fechar(self):
        self._salvar(silencioso=True)
        self.janela.destroy()

    def _fechar_sem_salvar(self):
        tem_alteracoes = False
        for c in self.dados:
            qtd_antiga = self.qtds_originais.get(c["produto_id"], 0)
            qtd_nova = c.get("qtd_comprador", 0)
            if abs(qtd_nova - qtd_antiga) > 0.001:
                tem_alteracoes = True
                break

        if tem_alteracoes:
            resp = messagebox.askyesno("Alterações não salvas",
                "Existem alterações não salvas.\nDeseja sair mesmo assim?")
            if not resp:
                return

        self.janela.destroy()