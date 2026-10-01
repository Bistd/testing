"""
Tela Início: banner + cards de módulos.
"""
import customtkinter as ctk

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_SUAVE,
    COR_VERDE, COR_VERDE_SUAVE,
    COR_ROXO, COR_ROXO_SUAVE,
    COR_LARANJA, COR_LARANJA_SUAVE,
    COR_VERMELHO, COR_VERMELHO_SUAVE,
    COR_CIANO,
    FONTE_TITULO, FONTE_SUBTITULO, FONTE_CARD_TITULO, FONTE_CARD_DESC,
)


class TelaInicio(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app

        self._montar_banner()
        self._montar_titulo_modulos()
        self._montar_cards()

    # ============================================================
    # BANNER
    # ============================================================
    def _montar_banner(self):
        banner = ctk.CTkFrame(self, height=140, corner_radius=16,
                              fg_color="#1e293b")
        banner.pack(fill="x", pady=(0, 25))
        banner.pack_propagate(False)

        # Ícone à esquerda
        ctk.CTkLabel(
            banner, text="🛒",
            font=("Segoe UI", 42),
            text_color="#ffffff"
        ).pack(side="left", padx=(30, 20), pady=20)

        # Texto
        texto_frame = ctk.CTkFrame(banner, fg_color="transparent")
        texto_frame.pack(side="left", pady=20)

        ctk.CTkLabel(
            texto_frame, text="Bem-vindo ao BISTECÃO",
            font=("Segoe UI", 24, "bold"),
            text_color="#ffffff"
        ).pack(anchor="w")

        ctk.CTkLabel(
            texto_frame, text="Sistema de gerenciamento de compras",
            font=("Segoe UI", 13),
            text_color="#cbd5e1"
        ).pack(anchor="w", pady=(4, 0))

        # Texto à direita
        ctk.CTkLabel(
            banner, text="Mais organização, melhores compras,\nmaior resultado.",
            font=("Segoe UI", 12),
            text_color="#93c5fd",
            justify="right"
        ).pack(side="right", padx=30)

    # ============================================================
    # TÍTULO
    # ============================================================
    def _montar_titulo_modulos(self):
        ctk.CTkLabel(
            self, text="Módulos do Sistema",
            font=("Segoe UI", 18, "bold"),
            text_color="#0f172a"
        ).pack(anchor="w", pady=(0, 15))

    # ============================================================
    # CARDS
    # ============================================================
    def _montar_cards(self):
        modulos = [
            ("📥", "Importação", "Importe os arquivos das notas dos fornecedores de forma simplificada.", COR_AZUL, COR_AZUL_SUAVE, "importacao"),
            ("💡", "Sugestão", "Veja as sugestões de compras e gerencie as quantidades necessárias.", COR_VERDE, COR_VERDE_SUAVE, "sugestao"),
            ("💲", "Cotação", "Gere a cotação com os fornecedores e envie para consulta.", COR_LARANJA, COR_LARANJA_SUAVE, "cotacao"),
            ("🔒", "Fechar Cotação", "Importe as respostas dos fornecedores e finalize a cotação.", COR_VERMELHO, COR_VERMELHO_SUAVE, "fechar"),
            ("🛒", "Pedidos", "Gere os pedidos de compra com base na cotação fechada.", COR_ROXO, COR_ROXO_SUAVE, "pedidos"),
            ("📊", "Análise", "Relatórios e análises detalhadas dos seus resultados.", COR_CIANO, "#cffafe", "analise"),
            ("📖", "Manual", "Acesse o manual do sistema e tire suas dúvidas.", "#64748b", "#f1f5f9", "manual"),
            ("⚙️", "Configurações", "Ajuste as preferências globais do seu sistema.", "#475569", "#e2e8f0", "config"),
        ]

        # Grid 4 colunas
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True)

        for i in range(4):
            grid.grid_columnconfigure(i, weight=1, uniform="card")

        for idx, (icone, titulo, desc, cor, cor_suave, chave) in enumerate(modulos):
            linha = idx // 4
            coluna = idx % 4
            card = self._criar_card(grid, icone, titulo, desc, cor, cor_suave, chave)
            card.grid(row=linha, column=coluna, padx=8, pady=8, sticky="nsew")

    def _criar_card(self, master, icone, titulo, desc, cor, cor_suave, chave):
        card = ctk.CTkFrame(master, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color="#e2e8f0")

        # Topo: ícone + seta
        topo = ctk.CTkFrame(card, fg_color="transparent")
        topo.pack(fill="x", padx=16, pady=(16, 8))

        # Ícone
        icone_frame = ctk.CTkFrame(topo, width=48, height=48,
                                    corner_radius=10, fg_color=cor_suave)
        icone_frame.pack(side="left")
        icone_frame.pack_propagate(False)

        ctk.CTkLabel(icone_frame, text=icone,
                     font=("Segoe UI", 22)).pack(expand=True)

        # Seta
        ctk.CTkLabel(topo, text="→", font=("Segoe UI", 18),
                     text_color=cor).pack(side="right")

        # Título
        ctk.CTkLabel(card, text=titulo,
                     font=FONTE_CARD_TITULO,
                     text_color="#0f172a").pack(anchor="w", padx=16)

        # Descrição
        ctk.CTkLabel(card, text=desc,
                     font=FONTE_CARD_DESC,
                     text_color="#64748b",
                     wraplength=200, justify="left").pack(anchor="w", padx=16, pady=(4, 16))

        # Hover + clique
        def on_enter(_):
            card.configure(border_color=cor)
        def on_leave(_):
            card.configure(border_color="#e2e8f0")
        def on_click(_):
            self.app.trocar_tela(chave)

        for widget in [card, topo, icone_frame]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", on_click)

        return card