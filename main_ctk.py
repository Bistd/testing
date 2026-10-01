"""
Ponto de entrada da versão CustomTkinter do app.
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import carregar_config
from core.database import inicializar_banco
from core.migracoes import aplicar_migracoes

from ui_ctk.tema import aplicar_tema
from ui_ctk.janela_principal import JanelaPrincipalCTK


def main():
    try:
        config = carregar_config()
    except Exception as e:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Erro ao carregar config", str(e))
        return

    try:
        inicializar_banco()
        aplicar_migracoes()
    except Exception as e:
        root = tk.Tk(); root.withdraw()
        messagebox.showerror("Erro ao inicializar banco", str(e))
        return

    aplicar_tema()

    app = JanelaPrincipalCTK(config)
    app.mainloop()


if __name__ == "__main__":
    main()