"""
Tela Pedidos: gera PDF + Excel de cada fornecedor campeão, por filial.
"""
import customtkinter as ctk
from tkinter import messagebox
import os
import sys
import subprocess
import threading
from pathlib import Path

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_VERMELHO, COR_VERMELHO_HOVER,
    COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_BORDA,
    FONTE_TITULO, FONTE_BOTAO,
)

from core.gerador_pedidos import listar_pedidos_por_fornecedor
from core.gerador_xml import gerar_xml_pedido
from core.gerador_pdf import gerar_excel_pedido, exportar_pdf
from core.config import RAIZ


PASTA_PEDIDOS = RAIZ / "pedidos"


class TelaPedidos(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app

        self._montar_titulo()
        self._montar_resumo()
        self._montar_log()
        self._montar_rodape()

    def _limpar_pastas(self):
        """Apaga todos os PDFs e XLSX das 4 pastas de pedidos."""
        resp = messagebox.askyesno(
            "Confirmar",
            "Apagar TODOS os arquivos das pastas:\n\n"
            "• pedidos/PDF_F1/\n"
            "• pedidos/PDF_F2/\n"
            "• pedidos/XML_F1/\n"
            "• pedidos/XML_F2/\n\n"
            "Continuar?"
        )
        if not resp:
            return

        apagados = 0
        erros = 0

        for sub in ["PDF_F1", "PDF_F2", "XML_F1", "XML_F2"]:
            pasta = PASTA_PEDIDOS / sub
            if not pasta.exists():
                continue
            for arquivo in pasta.iterdir():
                if arquivo.is_file():
                    try:
                        arquivo.unlink()
                        apagados += 1
                    except Exception:
                        erros += 1

        msg = f"{apagados} arquivos apagados."
        if erros:
            msg += f"\n{erros} arquivos não puderam ser apagados (talvez abertos)."
        messagebox.showinfo("Limpeza concluída", msg)
        self._log(f"\n🗑️ {msg}")

    def _montar_titulo(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(frame, text="🛒  Pedidos",
                     font=("Segoe UI", 22, "bold"),
                     text_color=COR_TEXTO).pack(anchor="w")
        ctk.CTkLabel(frame, text="Gera PDF (pros fornecedores) e Excel (pro seu ERP).",
                     font=("Segoe UI", 13),
                     text_color=COR_TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

    def _montar_resumo(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(card, text="Fornecedores vencedores:",
                     font=("Segoe UI", 12, "bold"),
                     text_color=COR_TEXTO).pack(anchor="w", padx=15, pady=(12, 5))

        self.lbl_resumo = ctk.CTkLabel(
            card, text="(clique em 'Atualizar' para ver)",
            font=("Consolas", 11),
            text_color=COR_TEXTO_SECUNDARIO,
            justify="left"
        )
        self.lbl_resumo.pack(anchor="w", padx=15, pady=(0, 12))

    def _montar_log(self):
        card = ctk.CTkFrame(self, corner_radius=12, fg_color=COR_CARD,
                            border_width=1, border_color=COR_BORDA)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(card, text="Relatório:",
                     font=("Segoe UI", 12, "bold"),
                     text_color=COR_TEXTO).pack(anchor="w", padx=15, pady=(12, 5))

        self.txt_log = ctk.CTkTextbox(
            card, font=("Consolas", 11),
            fg_color="#f8fafc", text_color=COR_TEXTO, corner_radius=8
        )
        self.txt_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _log(self, texto):
        self.txt_log.insert("end", texto + "\n")
        self.txt_log.see("end")

    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(fill="x", pady=(12, 0))

        self.btn_gerar = ctk.CTkButton(
            rodape, text="📋  Gerar Pedidos",
            height=44, corner_radius=8,
            fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
            font=FONTE_BOTAO, command=self._gerar
        )
        self.btn_gerar.pack(side="left", padx=(0, 10))

        ctk.CTkButton(rodape, text="🔄  Atualizar",
                       height=44, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO, command=self.recarregar).pack(side="left", padx=(0, 10))

        ctk.CTkButton(rodape, text="🗑️  Limpar pastas",
                       height=44, corner_radius=8,
                       fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER,
                       font=FONTE_BOTAO, command=self._limpar_pastas).pack(side="left", padx=(0, 10))

        ctk.CTkButton(rodape, text="📂  Abrir pasta",
                       height=44, corner_radius=8,
                       fg_color="#e2e8f0", hover_color="#cbd5e1",
                       text_color=COR_TEXTO,
                       font=FONTE_BOTAO, command=self._abrir_pasta).pack(side="left")

    def _abrir_pasta(self):
        PASTA_PEDIDOS.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(PASTA_PEDIDOS)
            else:
                subprocess.Popen(["xdg-open", str(PASTA_PEDIDOS)])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def recarregar(self):
        ano_mes = self.app._ano_mes_ativo()
        try:
            pedidos = listar_pedidos_por_fornecedor(ano_mes)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        linhas = []
        total_f1 = 0
        total_f2 = 0
        for cod, d in sorted(pedidos.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            n1 = len(d["filial_1"])
            n2 = len(d["filial_2"])
            v1 = sum(i["total"] for i in d["filial_1"])
            v2 = sum(i["total"] for i in d["filial_2"])
            total_f1 += v1
            total_f2 += v2
            linhas.append(f"Cód {cod:>5}  |  F1: {n1:>3} itens (R$ {v1:>10.2f})  |  F2: {n2:>3} itens (R$ {v2:>10.2f})")

        if not linhas:
            self.lbl_resumo.configure(text="Nenhum pedido pronto. Importe respostas na aba Fechar Cotação.")
        else:
            texto = "\n".join(linhas)
            texto += f"\n\nTOTAL F1: R$ {total_f1:,.2f}   |   TOTAL F2: R$ {total_f2:,.2f}"
            self.lbl_resumo.configure(text=texto)

    def _gerar(self):
        resp = messagebox.askyesno(
            "Confirmar",
            "Gerar PDF e XML de todos os fornecedores vencedores?\n\n"
            "Os arquivos serão salvos em:\n"
            "pedidos/PDF_F1, pedidos/PDF_F2, pedidos/XML_F1, pedidos/XML_F2"
        )
        if not resp:
            return

        self.btn_gerar.configure(state="disabled")
        self.txt_log.delete("1.0", "end")
        self._log("=== Gerando pedidos ===\n")

        def worker():
            try:
                self._gerar_sync()
            except Exception as e:
                self.after(0, lambda: self._log(f"\n❌ ERRO: {e}"))
            finally:
                self.after(0, lambda: self.btn_gerar.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _buscar_nome_fornecedor(self, codigo):
        from core.database import conectar
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT nome FROM fornecedores WHERE codigo = ? LIMIT 1", (codigo,))
        r = cur.fetchone()
        conn.close()
        return r["nome"] if r and r["nome"] else f"Fornecedor {codigo}"

    def _enriquecer_codigos(self, itens, fornecedor_codigo):
        """Adiciona codigo_no_fornecedor em cada item."""
        from core.database import conectar
        from core.importer import buscar_codigo_no_fornecedor

        conn = conectar()
        cur = conn.cursor()
        for item in itens:
            cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?",
                        (item["codigo_interno"],))
            r = cur.fetchone()
            if r:
                item["codigo_no_fornecedor"] = buscar_codigo_no_fornecedor(r[0], fornecedor_codigo)
            else:
                item["codigo_no_fornecedor"] = ""
        conn.close()

    def _gerar_sync(self):
        ano_mes = self.app._ano_mes_ativo()
        pedidos = listar_pedidos_por_fornecedor(ano_mes)

        if not pedidos:
            self.after(0, lambda: self._log("Nenhum pedido pra gerar."))
            return

        for sub in ["PDF_F1", "PDF_F2", "XML_F1", "XML_F2"]:
            (PASTA_PEDIDOS / sub).mkdir(parents=True, exist_ok=True)

        total_arq = 0

        for cod, d in sorted(pedidos.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            nome_forn = self._buscar_nome_fornecedor(cod)

            # Enriquece códigos dos itens
            self._enriquecer_codigos(d["filial_1"], cod)
            self._enriquecer_codigos(d["filial_2"], cod)

            # -------- FILIAL 1 --------
            if d["filial_1"]:
                itens = d["filial_1"]
                try:
                    gerar_xml_pedido(itens, PASTA_PEDIDOS / "XML_F1" / f"{cod}-F1.xlsx")
                    self.after(0, lambda c=cod: self._log(f"✓ XML {c}-F1.xlsx"))
                    total_arq += 1
                except Exception as e:
                    self.after(0, lambda c=cod, err=e: self._log(f"❌ XML {c}-F1: {err}"))

                try:
                    temp_xlsx = PASTA_PEDIDOS / "PDF_F1" / f"{cod}-F1.xlsx"
                    gerar_excel_pedido(itens, cod, nome_forn, 1, self.app.config, temp_xlsx)
                    exportar_pdf(temp_xlsx, PASTA_PEDIDOS / "PDF_F1" / f"{cod}-F1.pdf")
                    temp_xlsx.unlink()
                    self.after(0, lambda c=cod: self._log(f"✓ PDF {c}-F1.pdf"))
                    total_arq += 1
                except Exception as e:
                    self.after(0, lambda c=cod, err=e: self._log(f"❌ PDF {c}-F1: {err}"))

            # -------- FILIAL 2 --------
            if d["filial_2"]:
                itens = d["filial_2"]
                try:
                    gerar_xml_pedido(itens, PASTA_PEDIDOS / "XML_F2" / f"{cod}-F2.xlsx")
                    self.after(0, lambda c=cod: self._log(f"✓ XML {c}-F2.xlsx"))
                    total_arq += 1
                except Exception as e:
                    self.after(0, lambda c=cod, err=e: self._log(f"❌ XML {c}-F2: {err}"))

                try:
                    temp_xlsx = PASTA_PEDIDOS / "PDF_F2" / f"{cod}-F2.xlsx"
                    gerar_excel_pedido(itens, cod, nome_forn, 2, self.app.config, temp_xlsx)
                    exportar_pdf(temp_xlsx, PASTA_PEDIDOS / "PDF_F2" / f"{cod}-F2.pdf")
                    temp_xlsx.unlink()
                    self.after(0, lambda c=cod: self._log(f"✓ PDF {c}-F2.pdf"))
                    total_arq += 1
                except Exception as e:
                    self.after(0, lambda c=cod, err=e: self._log(f"❌ PDF {c}-F2: {err}"))

        self.after(0, lambda: self._log(f"\n=== Pronto! {total_arq} arquivos gerados ==="))