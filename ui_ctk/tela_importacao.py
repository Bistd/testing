"""
Tela Importação em CustomTkinter.
Botões para importar dados + área de log.
"""
import customtkinter as ctk
import threading
import os
import sys
import subprocess
from tkinter import messagebox

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_BORDA,
    FONTE_TITULO, FONTE_SUBTITULO, FONTE_BOTAO,
)

from core.importer import reprocessar_mes_ativo, importar_historico_completo
from core.config import caminho_pasta_entrada


class TelaImportacao(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app

        self._montar_titulo()
        self._montar_botoes()
        self._montar_log()

    # ============================================================
    # TÍTULO
    # ============================================================
    def _montar_titulo(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            frame, text="📥  Importação",
            font=("Segoe UI", 22, "bold"),
            text_color=COR_TEXTO
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame, text="Importe os arquivos de cadastro, fornecedores e movimento.",
            font=("Segoe UI", 13),
            text_color=COR_TEXTO_SECUNDARIO
        ).pack(anchor="w", pady=(2, 0))

    # ============================================================
    # BOTÕES
    # ============================================================
    def _montar_botoes(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="x", pady=(0, 15))

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=20, pady=20)

        self.btn_reprocessar = ctk.CTkButton(
            linha, text="🔄  Reprocessar mês ativo",
            height=42, corner_radius=8,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=FONTE_BOTAO,
            command=self._on_reprocessar
        )
        self.btn_reprocessar.pack(side="left", padx=(0, 10))

        self.btn_historico = ctk.CTkButton(
            linha, text="📚  Importar histórico completo",
            height=42, corner_radius=8,
            fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
            font=FONTE_BOTAO,
            command=self._on_historico
        )
        self.btn_historico.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            linha, text="📂  Abrir pasta de entrada",
            height=42, corner_radius=8,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=FONTE_BOTAO,
            command=self._abrir_pasta
        ).pack(side="left")

    # ============================================================
    # LOG
    # ============================================================
    def _montar_log(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="both", expand=True)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            header, text="Relatório:",
            font=("Segoe UI", 14, "bold"),
            text_color=COR_TEXTO
        ).pack(side="left")

        ctk.CTkButton(
            header, text="🗑️ Limpar",
            width=90, height=26, corner_radius=6,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=("Segoe UI", 10),
            command=self._limpar_log
        ).pack(side="right")

        self.txt_log = ctk.CTkTextbox(
            card,
            font=("Consolas", 11),
            fg_color="#f8fafc",
            text_color=COR_TEXTO,
            corner_radius=8,
            wrap="word",
        )
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(5, 15))

    def _log(self, texto):
        self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")

    def _limpar_log(self):
        self.txt_log.delete("1.0", "end")

    # ============================================================
    # AÇÕES
    # ============================================================
    def _abrir_pasta(self):
        pasta = caminho_pasta_entrada(self.app.config)
        pasta.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(pasta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", pasta])
            else:
                subprocess.Popen(["xdg-open", pasta])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _on_reprocessar(self):
        if not messagebox.askyesno("Confirmar",
            f"Reprocessar arquivos do mês {self.app.config['mes_ativo']}?\n\n"
            "O app fará backup do banco e importará fornecedores + cadastro + movimento."):
            return
        self._executar_em_thread(reprocessar_mes_ativo, "Reprocessando mês ativo")

    def _on_historico(self):
        if not messagebox.askyesno("Confirmar",
            "Importar histórico COMPLETO de todas as pastas?\n\n"
            "Use isso na primeira execução. Pode demorar alguns minutos."):
            return
        self._executar_em_thread(importar_historico_completo, "Importando histórico completo")

    # ============================================================
    # EXECUÇÃO EM THREAD
    # ============================================================
    def _executar_em_thread(self, funcao, titulo):
        self.btn_reprocessar.configure(state="disabled")
        self.btn_historico.configure(state="disabled")
        self._limpar_log()
        self._log(f"=== {titulo} ===\n")
        self.app.set_status(f"{titulo}...")

        def worker():
            try:
                resultados = funcao(self.app.config)
                self.after(0, lambda: self._mostrar_resultados(resultados))
            except Exception as e:
                self.after(0, lambda: self._mostrar_erro(e))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_resultados(self, resultados):
        total_ins = 0
        total_at = 0
        total_er = 0

        for r in resultados:
            linha = self._formatar_resultado(r)
            self._log(linha)
            total_ins += r.get("inseridos", 0)
            total_at += r.get("atualizados", 0)
            total_er += r.get("erros", 0)

        self._log("\n" + "=" * 60)
        self._log(f"TOTAL: {len(resultados)} arquivos | "
                  f"inseridos: {total_ins} | atualizados: {total_at} | erros: {total_er}")

        self.btn_reprocessar.configure(state="normal")
        self.btn_historico.configure(state="normal")
        self.app.set_status("Importação concluída.")

    def _formatar_resultado(self, r) -> str:
        nome = r.get("arquivo", "?")
        tipo = r.get("tipo", "?")
        linhas = r.get("linhas", 0)
        ins = r.get("inseridos", 0)
        at = r.get("atualizados", 0)
        er = r.get("erros", 0)
        msg = r.get("mensagem_erro", "")
        filial = r.get("filial")
        ano_mes = r.get("ano_mes")

        extras = []
        if filial:
            extras.append(f"filial {filial}")
        if ano_mes:
            extras.append(ano_mes)
        extras_str = f" [{', '.join(extras)}]" if extras else ""

        linha = f"✓ {nome}{extras_str}\n"
        linha += f"    tipo={tipo} linhas={linhas} ins={ins} at={at} erros={er}"
        if msg:
            linha += f"\n    ⚠ {msg}"
        return linha

    def _mostrar_erro(self, e):
        self._log(f"\n❌ ERRO: {e}")
        self.btn_reprocessar.configure(state="normal")
        self.btn_historico.configure(state="normal")
        self.app.set_status("Erro na importação.")
        messagebox.showerror("Erro", str(e))