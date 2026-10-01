"""
Aba de importação: botões para reprocessar o mês ativo ou importar todo o histórico.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading

from core.config import caminho_pasta_entrada
from core.importer import reprocessar_mes_ativo, importar_historico_completo


class TabImportacao:
    def __init__(self, master, app):
        self.app = app
        self.frame = ttk.Frame(master, padding=10)

        self._montar_botoes()
        self._montar_area_log()

    def _montar_botoes(self):
        topo = ttk.Frame(self.frame)
        topo.pack(fill="x", pady=(0, 10))

        self.btn_reprocessar = ttk.Button(
            topo, text="🔄 Reprocessar arquivos do mês ativo",
            command=self._on_reprocessar
        )
        self.btn_reprocessar.pack(side="left", padx=(0, 10))

        self.btn_historico = ttk.Button(
            topo, text="📚 Importar histórico completo (todas as pastas)",
            command=self._on_historico
        )
        self.btn_historico.pack(side="left", padx=(0, 10))

        ttk.Button(
            topo, text="📂 Abrir pasta de entrada",
            command=self._abrir_pasta
        ).pack(side="left", padx=(0, 10))

    def _montar_area_log(self):
        ttk.Label(self.frame, text="Relatório:", style="Titulo.TLabel").pack(anchor="w")
        container = ttk.Frame(self.frame)
        container.pack(fill="both", expand=True, pady=(4, 0))

        self.txt = tk.Text(container, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(container, command=self.txt.yview)
        self.txt.configure(yscrollcommand=scroll.set)
        self.txt.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ============================================================
    # AÇÕES
    # ============================================================
    def _abrir_pasta(self):
        import os, subprocess, sys
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
            "O app fará backup do banco e importará o cadastro + movimento."):
            return
        self._executar_em_thread(reprocessar_mes_ativo, "Reprocessando mês ativo")

    def _on_historico(self):
        if not messagebox.askyesno("Confirmar",
            "Importar histórico COMPLETO de todas as pastas de mês?\n\n"
            "Use isso só na primeira execução. Pode demorar."):
            return
        self._executar_em_thread(importar_historico_completo, "Importando histórico completo")

    def _executar_em_thread(self, funcao, titulo):
        self.btn_reprocessar.config(state="disabled")
        self.btn_historico.config(state="disabled")
        self._limpar_log()
        self._log(f"=== {titulo} ===\n")
        self.app.set_status(f"{titulo}...")

        def worker():
            try:
                resultados = funcao(self.app.config)
                self.app.root.after(0, lambda: self._mostrar_resultados(resultados))
            except Exception as e:
                self.app.root.after(0, lambda: self._mostrar_erro(e))

        threading.Thread(target=worker, daemon=True).start()

    def _mostrar_resultados(self, resultados):
        total_ins = total_at = total_er = 0
        for r in resultados:
            linha = self._formatar_resultado(r)
            self._log(linha)
            total_ins += r.get("inseridos", 0)
            total_at += r.get("atualizados", 0)
            total_er += r.get("erros", 0)

        self._log("\n" + "=" * 60)
        self._log(f"TOTAL: {len(resultados)} arquivos | "
                  f"inseridos: {total_ins} | atualizados: {total_at} | erros: {total_er}")

        self.btn_reprocessar.config(state="normal")
        self.btn_historico.config(state="normal")
        self.app.set_status("Importação concluída.")

        # Recarrega a aba de sugestão
        try:
            self.app.tab_sugestao.recarregar()
        except Exception:
            pass

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
        return linha + "\n"

    def _mostrar_erro(self, e):
        self._log(f"\n❌ ERRO: {e}")
        self.btn_reprocessar.config(state="normal")
        self.btn_historico.config(state="normal")
        self.app.set_status("Erro na importação.")
        messagebox.showerror("Erro", str(e))

    def _log(self, texto):
        self.txt.insert("end", texto + "\n")
        self.txt.see("end")

    def _limpar_log(self):
        self.txt.delete("1.0", "end")