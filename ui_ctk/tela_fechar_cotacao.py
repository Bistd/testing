"""
Tela Fechar Cotação em CustomTkinter.
Importa respostas, lista fornecedores, exclui, abre análise.
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import sys
import subprocess
from ui_ctk.loading import LoadingOverlay
from pathlib import Path

from ui_ctk.tema import (
    COR_FUNDO, COR_CARD, COR_AZUL, COR_AZUL_HOVER,
    COR_VERDE, COR_VERDE_HOVER,
    COR_VERMELHO, COR_VERMELHO_HOVER,
    COR_LARANJA, COR_LARANJA_HOVER,
    COR_TEXTO, COR_TEXTO_SECUNDARIO, COR_BORDA,
    FONTE_TITULO, FONTE_SUBTITULO, FONTE_BOTAO,
)

from core.importador_respostas import ler_resposta_fornecedor
from core.cotacao import salvar_respostas
from core.analise import (
    calcular_totais_por_fornecedor,
    remover_respostas_fornecedor,
)
from core.database import conectar


class TelaFecharCotacao(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COR_FUNDO, **kwargs)
        self.app = app

        self._montar_titulo()
        self._montar_rodape()
        self._montar_lista()

        # Overlay
        self.loading = LoadingOverlay(self)

        self.recarregar()

    # ============================================================
    # TÍTULO
    # ============================================================
    def _montar_titulo(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            frame, text="🔒  Fechar Cotação",
            font=("Segoe UI", 22, "bold"),
            text_color=COR_TEXTO
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame, text="Importe as respostas dos fornecedores e analise os vencedores.",
            font=("Segoe UI", 13),
            text_color=COR_TEXTO_SECUNDARIO
        ).pack(anchor="w", pady=(2, 0))

    # ============================================================
    # RODAPÉ (BOTÕES)
    # ============================================================
    def _montar_rodape(self):
        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", pady=(12, 0))

        ctk.CTkButton(
            rodape, text="📂  Importar Excel Respondido",
            height=42, corner_radius=8,
            fg_color=COR_VERDE, hover_color=COR_VERDE_HOVER,
            font=FONTE_BOTAO, command=self._importar_excel
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            rodape, text="📊  Análise por Item",
            height=42, corner_radius=8,
            fg_color=COR_LARANJA, hover_color=COR_LARANJA_HOVER,
            font=FONTE_BOTAO, command=self._abrir_analise_itens
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            rodape, text="🔄  Recarregar",
            height=42, corner_radius=8,
            fg_color="#e2e8f0", hover_color="#cbd5e1",
            text_color=COR_TEXTO,
            font=FONTE_BOTAO, command=self.recarregar
        ).pack(side="left")

        self.lbl_info = ctk.CTkLabel(
            rodape, text="",
            font=("Segoe UI", 12, "bold"),
            text_color=COR_TEXTO_SECUNDARIO
        )
        self.lbl_info.pack(side="right")

    # ============================================================
    # LISTA
    # ============================================================
    def _montar_lista(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=COR_FUNDO,
            scrollbar_button_color="#cbd5e1",
            scrollbar_button_hover_color="#94a3b8"
        )
        self.scroll.pack(fill="both", expand=True)

    def recarregar(self):
        self.loading.mostrar("Carregando fornecedores...")
        self.update_idletasks()

        try:
            self._recarregar_interno()
        finally:
            self.loading.esconder()

    def _recarregar_interno(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        ano_mes = self.app._ano_mes_ativo()
        fornecedores = calcular_totais_por_fornecedor(ano_mes)

        if not fornecedores:
            ctk.CTkLabel(
                self.scroll,
                text="Nenhum fornecedor importado ainda.",
                font=("Segoe UI", 13),
                text_color="#94a3b8"
            ).pack(pady=60)
            self.lbl_info.configure(text="0 fornecedores")
            return

        nome_f1 = self.app.config.get("filiais", {}).get("1", {}).get("sigla", "F1")
        nome_f2 = self.app.config.get("filiais", {}).get("2", {}).get("sigla", "F2")

        for f in fornecedores:
            self._criar_card(f, nome_f1, nome_f2)

        self.lbl_info.configure(
            text=f"{len(fornecedores)} fornecedores  |  Mês: {ano_mes}"
        )

    def _criar_card(self, f, sigla_f1, sigla_f2):
        card = ctk.CTkFrame(self.scroll, corner_radius=12,
                            fg_color=COR_CARD, border_width=1, border_color=COR_BORDA)
        card.pack(fill="x", pady=5, padx=5)

        # Cabeçalho
        header = ctk.CTkFrame(card, fg_color="#1F4E79", corner_radius=0, height=38)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=f"Cód {f['fornecedor_codigo']} — {f['fornecedor_nome'][:50]}",
            font=("Segoe UI", 12, "bold"),
            text_color="white"
        ).pack(side="left", padx=15)

        # Corpo
        corpo = ctk.CTkFrame(card, fg_color="transparent")
        corpo.pack(fill="x", padx=15, pady=12)

        # Bloco F1
        b1 = ctk.CTkFrame(corpo, fg_color="transparent")
        b1.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(b1, text=f"Filial 1 ({sigla_f1})",
                     font=("Segoe UI", 10, "bold"),
                     text_color=COR_TEXTO_SECUNDARIO).pack(anchor="w")

        ctk.CTkLabel(b1,
                     text=f"R$ {f['filial_1_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                     font=("Segoe UI", 18, "bold"),
                     text_color=COR_AZUL).pack(anchor="w")

        ctk.CTkLabel(b1, text=f"{f['filial_1_itens']} itens",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack(anchor="w")

        ctk.CTkButton(b1, text="🗑️  Zerar Filial 1",
                       width=140, height=28, corner_radius=6,
                       fg_color="#F8CBAD", hover_color="#F4B183",
                       text_color="#333333",
                       font=("Segoe UI", 10, "bold"),
                       command=lambda cod=f["fornecedor_codigo"],
                                     nome=f["fornecedor_nome"]: self._zerar_filial(cod, nome, 1)
                       ).pack(anchor="w", pady=(6, 0))

        # Bloco F2
        b2 = ctk.CTkFrame(corpo, fg_color="transparent")
        b2.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(b2, text=f"Filial 2 ({sigla_f2})",
                     font=("Segoe UI", 10, "bold"),
                     text_color=COR_TEXTO_SECUNDARIO).pack(anchor="w")

        ctk.CTkLabel(b2,
                     text=f"R$ {f['filial_2_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                     font=("Segoe UI", 18, "bold"),
                     text_color=COR_AZUL).pack(anchor="w")

        ctk.CTkLabel(b2, text=f"{f['filial_2_itens']} itens",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack(anchor="w")

        ctk.CTkButton(b2, text="🗑️  Zerar Filial 2",
                       width=140, height=28, corner_radius=6,
                       fg_color="#F8CBAD", hover_color="#F4B183",
                       text_color="#333333",
                       font=("Segoe UI", 10, "bold"),
                       command=lambda cod=f["fornecedor_codigo"],
                                     nome=f["fornecedor_nome"]: self._zerar_filial(cod, nome, 2)
                       ).pack(anchor="w", pady=(6, 0))

        # Botões
        botoes = ctk.CTkFrame(corpo, fg_color="transparent")
        botoes.pack(side="right", padx=(15, 0))

        ctk.CTkButton(
            botoes, text="📂  Abrir Excel",
            width=130, height=32, corner_radius=6,
            fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
            font=("Segoe UI", 11, "bold"),
            command=lambda cod=f["fornecedor_codigo"]: self._abrir_excel(cod)
        ).pack(pady=(0, 6))

        ctk.CTkButton(
            botoes, text="❌  Excluir",
            width=130, height=32, corner_radius=6,
            fg_color=COR_VERMELHO, hover_color=COR_VERMELHO_HOVER,
            font=("Segoe UI", 11, "bold"),
            command=lambda cod=f["fornecedor_codigo"],
                          nome=f["fornecedor_nome"]: self._excluir(cod, nome)
        ).pack()

    # ============================================================
    # IMPORTAÇÃO
    # ============================================================
    def _importar_excel(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o Excel respondido pelo fornecedor",
            filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("Todos", "*.*")]
        )
        if not caminho:
            return

        caminho = Path(caminho)
        ano_mes = self.app._ano_mes_ativo()

        self.loading.mostrar("Lendo Excel do fornecedor...")
        self.update_idletasks()

        try:
            dados = ler_resposta_fornecedor(caminho)
        except Exception as e:
            self.loading.esconder()
            messagebox.showerror("Erro ao ler arquivo", str(e))
            return

        self.loading.esconder()

        if not dados["itens"]:
            messagebox.showwarning("Sem itens",
                f"Nenhum item com preço encontrado no arquivo.\n\n"
                f"Código lido da célula C3: {dados['codigo_fornecedor_c3']}")
            return

        codigo_c3 = dados.get("codigo_fornecedor_c3") or ""

        codigo = self._pedir_codigo_fornecedor(
            total_itens=dados["total_itens"],
            arquivo=caminho.name,
            sugestao=codigo_c3,
        )
        if not codigo:
            return

        # Converte códigos de barras em produto_id
        respostas = []
        nao_encontrados = []
        conn = conectar()
        cur = conn.cursor()

        for item in dados["itens"]:
            cur.execute("SELECT id FROM produtos WHERE codigo_barras = ?",
                        (item["codigo_barras"],))
            r = cur.fetchone()
            if r:
                respostas.append({"produto_id": r[0], "preco": item["preco"]})
            else:
                nao_encontrados.append(item["codigo_barras"])

        conn.close()

        if not respostas:
            messagebox.showwarning("Nada importado",
                f"Nenhum item reconhecido no cadastro.\n"
                f"Não encontrados: {len(nao_encontrados)}")
            return

        # Salva para as 2 filiais (o preço é o mesmo)
        try:
            for filial_id in [1, 2]:
                salvar_respostas(
                    filial_id=filial_id,
                    ano_mes=ano_mes,
                    fornecedor_codigo=codigo,
                    respostas=respostas,
                    arquivo_origem=caminho.name,
                )
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return

        msg = f"Fornecedor {codigo} importado!\n\n"
        msg += f"✓ {len(respostas)} itens salvos"
        if nao_encontrados:
            msg += f"\n⚠ {len(nao_encontrados)} códigos não encontrados"
        messagebox.showinfo("OK", msg)

        self.recarregar()

    # ============================================================
    # DIÁLOGO — código do fornecedor
    # ============================================================
    def _pedir_codigo_fornecedor(self, total_itens, arquivo, sugestao=""):
        resultado = {"codigo": None}

        janela = ctk.CTkToplevel(self)
        janela.title("Qual fornecedor respondeu?")
        janela.geometry("480x320")
        janela.transient(self)
        janela.grab_set()

        ctk.CTkLabel(janela, text="Qual fornecedor respondeu este arquivo?",
                     font=("Segoe UI", 14, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(janela, text=f"Arquivo: {arquivo}",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack()
        ctk.CTkLabel(janela, text=f"Itens com preço: {total_itens}",
                     font=("Segoe UI", 10),
                     text_color=COR_TEXTO_SECUNDARIO).pack()

        ctk.CTkLabel(janela, text="Código do fornecedor:",
                     font=("Segoe UI", 12)).pack(pady=(20, 5))

        var = ctk.StringVar(value=sugestao)
        entrada = ctk.CTkEntry(janela, textvariable=var,
                                font=("Segoe UI", 16),
                                justify="center", width=140, height=42)
        entrada.pack()
        entrada.focus_set()
        entrada.select_range(0, "end")

        lbl_nome = ctk.CTkLabel(janela, text="",
                                font=("Segoe UI", 12, "bold"))
        lbl_nome.pack(pady=(10, 0))

        def atualizar_nome(*args):
            cod = var.get().strip()
            if not cod:
                lbl_nome.configure(text="", text_color=COR_TEXTO_SECUNDARIO)
                return
            nome = self._buscar_nome_fornecedor(cod)
            if nome:
                lbl_nome.configure(text=f"✓ {nome}", text_color="#2E7D32")
            else:
                lbl_nome.configure(text="⚠ Fornecedor não encontrado",
                                    text_color=COR_VERMELHO)

        var.trace_add("write", atualizar_nome)
        atualizar_nome()

        def confirmar(_evt=None):
            cod = var.get().strip()
            if not cod:
                messagebox.showwarning("Aviso", "Digite o código do fornecedor.")
                return
            resultado["codigo"] = cod
            janela.destroy()

        def cancelar():
            janela.destroy()

        entrada.bind("<Return>", confirmar)

        botoes = ctk.CTkFrame(janela, fg_color="transparent")
        botoes.pack(pady=20)

        ctk.CTkButton(botoes, text="Confirmar",
                       width=120, height=38, corner_radius=8,
                       fg_color=COR_AZUL, hover_color=COR_AZUL_HOVER,
                       font=FONTE_BOTAO,
                       command=confirmar).pack(side="left", padx=5)

        ctk.CTkButton(botoes, text="Cancelar",
                       width=120, height=38, corner_radius=8,
                       fg_color="#e2e8f0", hover_color="#cbd5e1",
                       text_color=COR_TEXTO,
                       font=FONTE_BOTAO,
                       command=cancelar).pack(side="left", padx=5)

        self.wait_window(janela)
        return resultado["codigo"]

    def _buscar_nome_fornecedor(self, codigo):
        conn = conectar()
        cur = conn.cursor()
        cur.execute("SELECT nome FROM fornecedores WHERE codigo = ? LIMIT 1", (codigo,))
        r = cur.fetchone()
        conn.close()
        return r["nome"] if r else None

    # ============================================================
    # EXCLUIR
    # ============================================================
    def _excluir(self, codigo, nome):
        resp = messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir TODAS as respostas do fornecedor:\n\n"
            f"Cód {codigo} — {nome}\n\n"
            f"Os itens que ele ganhava vão passar pro 2º menor preço."
        )
        if not resp:
            return

        ano_mes = self.app._ano_mes_ativo()
        remover_respostas_fornecedor(ano_mes, codigo)
        self.recarregar()

    def _zerar_filial(self, codigo, nome, filial):
        """Remove as respostas desse fornecedor SOMENTE da filial escolhida."""
        resp = messagebox.askyesno(
            "Confirmar",
            f"Zerar a Filial {filial} do fornecedor:\n\n"
            f"Cód {codigo} — {nome}\n\n"
            f"Os itens que ele ganhava na Filial {filial} vão passar "
            f"pro 2º menor preço (só da Filial {filial}).\n\n"
            f"A Filial {'2' if filial == 1 else '1'} continua intacta.\n\n"
            f"Continuar?"
        )
        if not resp:
            return

        ano_mes = self.app._ano_mes_ativo()
        self._remover_respostas_fornecedor_filial(ano_mes, codigo, filial)
        self.recarregar()

    def _remover_respostas_fornecedor_filial(self, ano_mes, codigo, filial):
        """Remove respostas de um fornecedor específico numa filial específica."""
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM cotacao_respostas
            WHERE ano_mes = ? AND fornecedor_codigo = ? AND filial_id = ?
        """, (ano_mes, codigo, filial))
        conn.commit()
        conn.close()

    # ============================================================
    # ABRIR EXCEL DO FORNECEDOR
    # ============================================================
    def _abrir_excel(self, codigo):
        ano_mes = self.app._ano_mes_ativo()

        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT arquivo_origem FROM cotacao_respostas
            WHERE ano_mes = ? AND fornecedor_codigo = ?
            LIMIT 1
        """, (ano_mes, codigo))
        r = cur.fetchone()
        conn.close()

        nome_arquivo = r["arquivo_origem"] if r else ""

        caminho = filedialog.askopenfilename(
            title=f"Selecione o Excel do fornecedor {codigo}",
            initialfile=nome_arquivo,
            filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("Todos", "*.*")]
        )
        if not caminho:
            return

        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", caminho])
            else:
                subprocess.Popen(["xdg-open", caminho])
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    # ============================================================
    # ANÁLISE POR ITEM
    # ============================================================
    def _abrir_analise_itens(self):
        from ui_ctk.tela_analise_itens import abrir_janela_analise_itens
        abrir_janela_analise_itens(self.app)