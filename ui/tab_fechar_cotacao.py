"""
Aba Fechar Cotação: importa respostas, lista fornecedores, exclui, e abre análise.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import subprocess
from pathlib import Path

from core.importador_respostas import ler_resposta_fornecedor
from core.cotacao import salvar_respostas, listar_respostas
from core.analise import (
    calcular_totais_por_fornecedor,
    listar_fornecedores_importados,
    remover_respostas_fornecedor,
)
from core.database import conectar


class TabFecharCotacao:
    def __init__(self, master, app):
        self.app = app
        self.frame = ttk.Frame(master, padding=10)

        self._montar_rodape()
        self._montar_lista()

    # ============================================================
    # RODAPÉ
    # ============================================================
    def _montar_rodape(self):
        rodape = ttk.Frame(self.frame)
        rodape.pack(side="bottom", fill="x", pady=(8, 0))

        ttk.Button(rodape, text="📂 Importar Excel Respondido",
                   command=self._importar_excel).pack(side="left", padx=(0, 8))
        ttk.Button(rodape, text="🔄 Recarregar",
                   command=self.recarregar).pack(side="left", padx=(0, 8))
        ttk.Button(rodape, text="📊 Análise por Item",
                   command=self._abrir_analise_itens).pack(side="left", padx=(0, 8))

        self.lbl_info = ttk.Label(rodape, text="", foreground="#555")
        self.lbl_info.pack(side="right")

    # ============================================================
    # LISTA DE FORNECEDORES
    # ============================================================
    def _montar_lista(self):
        ttk.Label(self.frame, text="Fornecedores Importados",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))

        # Frame com scroll
        container = ttk.Frame(self.frame)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scroll_y = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.frame_interno = ttk.Frame(canvas)

        self.frame_interno.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.frame_interno, anchor="nw")
        canvas.configure(yscrollcommand=scroll_y.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        # Guarda referência pro scroll do mouse
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"
        ))

    def recarregar(self):
        # Limpa
        for widget in self.frame_interno.winfo_children():
            widget.destroy()

        ano_mes = self.app.ano_mes_ativo()
        fornecedores = calcular_totais_por_fornecedor(ano_mes)

        if not fornecedores:
            ttk.Label(self.frame_interno,
                      text="Nenhum fornecedor importado ainda.",
                      foreground="#888").pack(pady=20)
            self.lbl_info.config(text="0 fornecedores")
            return

        nome_f1 = self.app.config.get("filiais", {}).get("1", {}).get("sigla", "F1")
        nome_f2 = self.app.config.get("filiais", {}).get("2", {}).get("sigla", "F2")

        for f in fornecedores:
            self._criar_card(f, nome_f1, nome_f2)

        self.lbl_info.config(
            text=f"{len(fornecedores)} fornecedores  |  Mês: {ano_mes}"
        )

    def _criar_card(self, f, nome_f1, nome_f2):
        card = ttk.LabelFrame(self.frame_interno,
                              text=f"Cód {f['fornecedor_codigo']} — {f['fornecedor_nome']}",
                              padding=10)
        card.pack(fill="x", pady=4, padx=4)

        corpo = ttk.Frame(card)
        corpo.pack(fill="x")

        # Bloco F1
        bloco1 = ttk.Frame(corpo)
        bloco1.pack(side="left", fill="x", expand=True)
        ttk.Label(bloco1, text=f"Filial 1 ({nome_f1})",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(bloco1,
                  text=f"R$ {f['filial_1_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                  font=("Segoe UI", 14), foreground="#1F4E79").pack(anchor="w")
        ttk.Label(bloco1, text=f"{f['filial_1_itens']} itens",
                  foreground="#555").pack(anchor="w")

        # Bloco F2
        bloco2 = ttk.Frame(corpo)
        bloco2.pack(side="left", fill="x", expand=True)
        ttk.Label(bloco2, text=f"Filial 2 ({nome_f2})",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(bloco2,
                  text=f"R$ {f['filial_2_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                  font=("Segoe UI", 14), foreground="#1F4E79").pack(anchor="w")
        ttk.Label(bloco2, text=f"{f['filial_2_itens']} itens",
                  foreground="#555").pack(anchor="w")

        # Botões
        botoes = ttk.Frame(corpo)
        botoes.pack(side="right", padx=(10, 0))

        ttk.Button(botoes, text="📂 Abrir Excel",
                   command=lambda cod=f["fornecedor_codigo"]: self._abrir_excel(cod)
                   ).pack(side="top", pady=2, fill="x")
        ttk.Button(botoes, text="❌ Excluir",
                   command=lambda cod=f["fornecedor_codigo"],
                                  nome=f["fornecedor_nome"]: self._excluir(cod, nome)
                   ).pack(side="top", pady=2, fill="x")

    # ============================================================
    # IMPORTAR EXCEL
    # ============================================================
    def _importar_excel(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o Excel respondido pelo fornecedor",
            filetypes=[
                ("Excel", "*.xlsx *.xlsm *.xls"),
                ("Todos os arquivos", "*.*"),
            ]
        )
        if not caminho:
            return

        caminho = Path(caminho)
        ano_mes = self.app.ano_mes_ativo()

        # 1. Lê o arquivo
        try:
            dados = ler_resposta_fornecedor(caminho)
        except Exception as e:
            messagebox.showerror("Erro ao ler arquivo", str(e))
            return

        if not dados["itens"]:
            messagebox.showwarning("Sem itens",
                f"Nenhum item com preço encontrado no arquivo.\n\n"
                f"Código lido da célula C3: {dados['codigo_fornecedor_c3']}\n"
                f"Erros: {dados['erros'][:3]}")
            return

        # 2. Pede o código do fornecedor
        codigo_c3 = dados.get("codigo_fornecedor_c3")
        sugestao = codigo_c3 if codigo_c3 else ""

        codigo = _pedir_codigo_fornecedor(
            self.app.root,
            total_itens=dados["total_itens"],
            arquivo=caminho.name,
            sugestao=sugestao,
            config=self.app.config
        )
        if not codigo:
            return

        # 3. Valida se o fornecedor existe no cadastro
        if not _fornecedor_existe(codigo):
            resp = messagebox.askyesno(
                "Fornecedor não cadastrado",
                f"O fornecedor {codigo} não está no cadastro.\n\n"
                f"Deseja importar mesmo assim?"
            )
            if not resp:
                return

        # 4. Converte códigos de barras em produto_id
        respostas = []
        nao_encontrados = []
        conn = conectar()
        cur = conn.cursor()

        for item in dados["itens"]:
            # Tenta pelo código de barras
            cur.execute("SELECT id FROM produtos WHERE codigo_barras = ?",
                        (item["codigo_barras"],))
            r = cur.fetchone()
            if r:
                respostas.append({
                    "produto_id": r[0],
                    "preco": item["preco"],
                })
            else:
                nao_encontrados.append(item["codigo_barras"])

        conn.close()

        if not respostas:
            messagebox.showwarning("Nada importado",
                f"Nenhum item foi reconhecido no cadastro.\n\n"
                f"Não encontrados: {len(nao_encontrados)}")
            return

        # 5. Salva no banco (faz pra cada filial)
        # O usuário importa uma vez, mas o arquivo pode conter itens das 2 filiais
        # Como o Excel cego tem os blocos separados, o preço se aplica à filial do item
        # Vamos salvar em ambas as filiais (o mesmo preço) e deixar a análise decidir
        # Aqui: salva na filial 1 e filial 2 (a análise filtra por filial)
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
        msg += f"✓ {len(respostas)} itens salvos\n"
        if nao_encontrados:
            msg += f"⚠ {len(nao_encontrados)} códigos não encontrados no cadastro"
        messagebox.showinfo("Importação concluída", msg)

        self.recarregar()

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

        ano_mes = self.app.ano_mes_ativo()
        remover_respostas_fornecedor(ano_mes, codigo)
        self.recarregar()

    # ============================================================
    # ABRIR EXCEL
    # ============================================================
    def _abrir_excel(self, codigo):
        ano_mes = self.app.ano_mes_ativo()

        # Pega o arquivo de origem do fornecedor
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            SELECT arquivo_origem FROM cotacao_respostas
            WHERE ano_mes = ? AND fornecedor_codigo = ?
            LIMIT 1
        """, (ano_mes, codigo))
        r = cur.fetchone()
        conn.close()

        if not r or not r["arquivo_origem"]:
            messagebox.showwarning("Aviso",
                "Não sei onde está o arquivo original desse fornecedor.")
            return

        nome_arquivo = r["arquivo_origem"]

        # Abre diálogo pro usuário localizar o arquivo (já que ele pode ter movido)
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
            messagebox.showerror("Erro ao abrir", str(e))

    # ============================================================
    # ANÁLISE POR ITEM
    # ============================================================
    def _abrir_analise_itens(self):
        from ui.tab_analise_itens import abrir_janela_analise_itens
        abrir_janela_analise_itens(self.app)


# ============================================================
# DIÁLOGO: pedir código do fornecedor
# ============================================================

def _pedir_codigo_fornecedor(parent, total_itens, arquivo, sugestao, config):
    """Abre diálogo pra digitar o código do fornecedor."""
    resultado = {"codigo": None}

    janela = tk.Toplevel(parent)
    janela.title("Qual fornecedor respondeu?")
    janela.geometry("420x260")
    janela.transient(parent)
    janela.grab_set()

    ttk.Label(janela, text="Qual fornecedor respondeu este arquivo?",
              font=("Segoe UI", 11, "bold")).pack(pady=(15, 5))
    ttk.Label(janela, text=f"Arquivo: {arquivo}",
              foreground="#666").pack()
    ttk.Label(janela, text=f"Itens com preço: {total_itens}",
              foreground="#666").pack()

    ttk.Label(janela, text="Código do fornecedor:",
              font=("Segoe UI", 10)).pack(pady=(15, 5))

    var = tk.StringVar(value=sugestao)
    entrada = ttk.Entry(janela, textvariable=var,
                        font=("Segoe UI", 14), justify="center", width=10)
    entrada.pack()
    entrada.focus_set()
    entrada.select_range(0, "end")

    # Mostra nome do fornecedor conforme digita
    lbl_nome = ttk.Label(janela, text="", foreground="#1F4E79",
                         font=("Segoe UI", 10, "bold"))
    lbl_nome.pack(pady=(8, 0))

    def atualizar_nome(*args):
        cod = var.get().strip()
        if not cod:
            lbl_nome.config(text="")
            return
        nome = _buscar_nome_fornecedor(cod)
        if nome:
            lbl_nome.config(text=f"✓ {nome}", foreground="#2E7D32")
        else:
            lbl_nome.config(text="⚠ Fornecedor não encontrado", foreground="#C00000")

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

    botoes = ttk.Frame(janela)
    botoes.pack(pady=15)
    ttk.Button(botoes, text="Confirmar", command=confirmar).pack(side="left", padx=5)
    ttk.Button(botoes, text="Cancelar", command=cancelar).pack(side="left", padx=5)

    parent.wait_window(janela)
    return resultado["codigo"]


def _buscar_nome_fornecedor(codigo):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT nome FROM fornecedores
        WHERE codigo = ? AND filial_id IS NULL
        LIMIT 1
    """, (codigo,))
    r = cur.fetchone()
    conn.close()
    return r["nome"] if r else None


def _fornecedor_existe(codigo):
    return _buscar_nome_fornecedor(codigo) is not None