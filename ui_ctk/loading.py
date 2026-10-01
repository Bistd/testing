"""
Overlay de "Carregando..." reutilizável pra todas as telas.
"""
import customtkinter as ctk

from ui_ctk.tema import (
    COR_CARD, COR_AZUL, COR_TEXTO, COR_TEXTO_SECUNDARIO,
)


class LoadingOverlay(ctk.CTkFrame):
    """
    Overlay que aparece por cima da tela com uma mensagem + spinner.
    Uso:
        self.loading = LoadingOverlay(self)
        self.loading.mostrar("Carregando produtos...")
        ...
        self.loading.esconder()
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._master = master
        self._visivel = False

        # Container central
        self.card = ctk.CTkFrame(self, corner_radius=16, fg_color=COR_CARD,
                                  border_width=2, border_color="#cbd5e1")
        self.card.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_spinner = ctk.CTkLabel(
            self.card, text="⏳",
            font=("Segoe UI", 42),
        )
        self.lbl_spinner.pack(padx=60, pady=(30, 10))

        self.lbl_msg = ctk.CTkLabel(
            self.card, text="Carregando...",
            font=("Segoe UI", 14, "bold"),
            text_color=COR_TEXTO,
        )
        self.lbl_msg.pack(padx=60, pady=(0, 30))

        self._animando = False
        self._frames = ["⏳", "⌛"]
        self._idx = 0

    def mostrar(self, mensagem="Carregando..."):
        if self._visivel:
            return
        self.lbl_msg.configure(text=mensagem)
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()
        self._visivel = True
        self._animando = True
        self._animar()

    def esconder(self):
        if not self._visivel:
            return
        self._animando = False
        self.place_forget()
        self._visivel = False

    def _animar(self):
        if not self._animando:
            return
        self._idx = (self._idx + 1) % len(self._frames)
        self.lbl_spinner.configure(text=self._frames[self._idx])
        self.after(400, self._animar)