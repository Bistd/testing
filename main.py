"""
Ponto de entrada do aplicativo de compras.
"""
import sys
import os
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import carregar_config
from core.database import inicializar_banco
from core.migracoes import aplicar_migracoes
from ui.janela_principal import JanelaPrincipal


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

    root = tk.Tk()
    app = JanelaPrincipal(root, config)
    root.mainloop()


if __name__ == "__main__":
    main()