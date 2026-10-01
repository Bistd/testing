"""
Janela principal em CustomTkinter.
Menu lateral + área de conteúdo (sem topbar global).
"""
import customtkinter as ctk
import tkinter as tk

from ui_ctk.tema import (
    COR_SIDEBAR, COR_SIDEBAR_HOVER, COR_SIDEBAR_ATIVO,
    COR_SIDEBAR_TEXTO, COR_SIDEBAR_TEXTO_ATIVO,
    COR_FUNDO, COR_AZUL, COR_AZUL_HOVER,
    FONTE_TITULO, FONTE_SUBTITULO, FONTE_PADRAO,
    FONTE_MENU, LARGURA_SIDEBAR,
)


# ============================================================
# MENU LATERAL
# ============================================================

class MenuLateral(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, width=LARGURA_SIDEBAR,
                         corner_radius=0, fg_color=COR_SIDEBAR, **kwargs)
        self.pack_propagate(False)
        self.app = app
        self.botoes = {}

        self._montar_logo()
        self._montar_botoes()
        self._montar_rodape()

    def _montar_logo(self):
        frame = ctk.CTkFrame(self, fg_color="transparent", height=100)
        frame.pack(fill="x", pady=(20, 30), padx=20)

        ctk.CTkLabel(frame, text="BISTECÃO",
                     font=("Segoe UI", 20, "bold"),
                     text_color=COR_SIDEBAR_TEXTO_ATIVO).pack(anchor="w")

        ctk.CTkLabel(frame, text="Sistema de Compras",
                     font=("Segoe UI", 11),
                     text_color=COR_SIDEBAR_TEXTO).pack(anchor="w")

    def _montar_botoes(self):
        itens = [
            ("🏠", "Início", "inicio"),
            ("📥", "Importação", "importacao"),
            ("💡", "Sugestão", "sugestao"),
            ("💲", "Cotação", "cotacao"),
            ("🔒", "Fechar Cotação", "fechar"),
            ("🛒", "Pedidos", "pedidos"),
            ("📊", "Análise", "analise"),
            ("📖", "Manual", "manual"),
            ("⚙️", "Configurações", "config"),
        ]

        for icone, texto, chave in itens:
            btn = ctk.CTkButton(
                self,
                text=f"  {icone}   {texto}",
                anchor="w", height=42, corner_radius=8,
                font=FONTE_MENU,
                fg_color="transparent",
                hover_color=COR_SIDEBAR_HOVER,
                text_color=COR_SIDEBAR_TEXTO,
                command=lambda k=chave: self.app.trocar_tela(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.botoes[chave] = btn

        self.marcar_ativo("inicio")

    def marcar_ativo(self, chave):
        for k, btn in self.botoes.items():
            if k == chave:
                btn.configure(fg_color=COR_SIDEBAR_ATIVO,
                              text_color=COR_SIDEBAR_TEXTO_ATIVO)
            else:
                btn.configure(fg_color="transparent",
                              text_color=COR_SIDEBAR_TEXTO)

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=20, pady=20)

        ctk.CTkLabel(rodape, text="● Sistema Online",
                     font=("Segoe UI", 10),
                     text_color=COR_SIDEBAR_TEXTO).pack(anchor="w")

        ctk.CTkLabel(rodape, text="Versão 1.4.2",
                     font=("Segoe UI", 9),
                     text_color=COR_SIDEBAR_TEXTO).pack(anchor="w")


# ============================================================
# JANELA PRINCIPAL
# ============================================================

class JanelaPrincipalCTK(ctk.CTk):
    def __init__(self, config):
        super().__init__()
        self.config_app = config
        self.config = config

        self.title("Sistema de Compras — Cotação")
        self.minsize(1100, 700)

        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)
        self.after(100, lambda: self.state("zoomed"))

        self.tela_atual = None

        self._montar_layout()
        self.trocar_tela("inicio")

    def _montar_layout(self):
        # Sidebar (esquerda)
        self.menu = MenuLateral(self, self)
        self.menu.pack(side="left", fill="y")

        # Área direita (conteúdo)
        self.area_conteudo = ctk.CTkFrame(self, fg_color=COR_FUNDO, corner_radius=0)
        self.area_conteudo.pack(side="right", fill="both", expand=True, padx=20, pady=20)

    def trocar_tela(self, chave):
        """Troca a tela atual."""
        for widget in self.area_conteudo.winfo_children():
            widget.destroy()

        self.menu.marcar_ativo(chave)
        self.tela_atual = chave

        if chave == "inicio":
            from ui_ctk.tela_inicio import TelaInicio
            tela = TelaInicio(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        elif chave == "importacao":
            from ui_ctk.tela_importacao import TelaImportacao
            tela = TelaImportacao(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        elif chave == "sugestao":
            from ui_ctk.tela_sugestao import TelaSugestao
            tela = TelaSugestao(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        elif chave == "cotacao":
            from ui_ctk.tela_cotacao import TelaCotacao
            tela = TelaCotacao(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        elif chave == "fechar":
            from ui_ctk.tela_fechar_cotacao import TelaFecharCotacao
            tela = TelaFecharCotacao(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        elif chave == "pedidos":
            from ui_ctk.tela_pedidos import TelaPedidos
            tela = TelaPedidos(self.area_conteudo, self)
            tela.pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(
                self.area_conteudo,
                text=f"📌 Tela '{chave}' — em construção",
                font=("Segoe UI", 18, "bold"),
                text_color="#64748b"
            ).pack(expand=True)

    def recarregar_tela_atual(self):
        if self.tela_atual:
            self.trocar_tela(self.tela_atual)

    def _ano_mes_ativo(self):
        """Retorna o ano-mês ativo (YYYY-MM)."""
        from core.util_meses import calcular_ano_mes
        return calcular_ano_mes(self.config["mes_ativo"])

    def set_status(self, texto: str):
        print(f"[STATUS] {texto}")