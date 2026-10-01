"""
Tema centralizado do app (cores, fontes, espaçamentos).
Baseado no Figma.
"""
import customtkinter as ctk


# ============================================================
# CORES
# ============================================================

# Sidebar / fundo escuro
COR_SIDEBAR = "#0f172a"
COR_SIDEBAR_HOVER = "#1e293b"
COR_SIDEBAR_ATIVO = "#3b82f6"
COR_SIDEBAR_TEXTO = "#e2e8f0"
COR_SIDEBAR_TEXTO_ATIVO = "#ffffff"

# Fundo principal
COR_FUNDO = "#f1f5f9"
COR_CARD = "#ffffff"
COR_BORDA = "#e2e8f0"

# Textos
COR_TEXTO = "#0f172a"
COR_TEXTO_SECUNDARIO = "#64748b"
COR_TEXTO_TERCIARIO = "#94a3b8"

# Cores de destaque (botões, cards)
COR_AZUL = "#3b82f6"
COR_AZUL_HOVER = "#2563eb"
COR_AZUL_SUAVE = "#dbeafe"

COR_VERDE = "#10b981"
COR_VERDE_HOVER = "#059669"
COR_VERDE_SUAVE = "#d1fae5"

COR_ROXO = "#8b5cf6"
COR_ROXO_HOVER = "#7c3aed"
COR_ROXO_SUAVE = "#ede9fe"

COR_LARANJA = "#f59e0b"
COR_LARANJA_HOVER = "#d97706"
COR_LARANJA_SUAVE = "#fef3c7"

COR_VERMELHO = "#ef4444"
COR_VERMELHO_HOVER = "#dc2626"
COR_VERMELHO_SUAVE = "#fee2e2"

COR_CIANO = "#06b6d4"
COR_CIANO_HOVER = "#0891b2"

# ============================================================
# FONTES
# ============================================================

FONTE_TITULO = ("Segoe UI", 22, "bold")
FONTE_SUBTITULO = ("Segoe UI", 14)
FONTE_PADRAO = ("Segoe UI", 12)
FONTE_PEQUENA = ("Segoe UI", 10)
FONTE_MENU = ("Segoe UI", 13, "bold")
FONTE_CARD_TITULO = ("Segoe UI", 15, "bold")
FONTE_CARD_DESC = ("Segoe UI", 11)
FONTE_BOTAO = ("Segoe UI", 12, "bold")

# ============================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================

def aplicar_tema():
    """Aplica o tema global do CustomTkinter."""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


# ============================================================
# DIMENSÕES
# ============================================================

LARGURA_SIDEBAR = 220
ALTURA_TOPBAR = 80
PADDING_PADRAO = 20
RAIO_CARD = 12
RAIO_BOTAO = 8