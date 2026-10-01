"""
Janela de Análise por Item: mostra todos os produtos campeões com comparação
com a última entrada, permite editar QTD, e salvar.
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.analise import calcular_campeoes
from core.cotacao import salvar_qtd, carregar_qtds


def abrir_janela_analise_itens(app):
    """Abre a janela de análise por item (modal)."""
    JanelaAnaliseItens(app)


class JanelaAnaliseItens:
    def __init__(self, app):
        self.app = app

        self.janela = tk.Toplevel(app.root)
        self.janela.title("📊 Análise por Item")
        self.janela.geometry("1400x750")
        # Permite maximizar/minimizar (nativo do Windows)
        self.janela.resizable(True, True)
        self.janela.minsize(800, 500)

        self.dados = []
        self.qtds_originais = {}

        self._montar_topo()
        self._montar_tabela()
        self._montar_rodape()

        self.recarregar()

    # ============================================================
    # TOPO — filtros
    # ============================================================
    def _montar_topo(self):
        topo = ttk.Frame(self.janela, padding=(10, 8))
        topo.pack(fill="x")

        ttk.Label(topo, text="Filial:", font=("Segoe UI", 10)).pack(side="left")
        self.var_filial = tk.StringVar(value="Todas")
        combo = ttk.Combobox(topo, textvariable=self.var_filial,
                             values=["Todas", "Filial 1", "Filial 2"],
                             state="readonly", width=12)
        combo.pack(side="left", padx=(4, 15))
        combo.bind("<<ComboboxSelected>>", lambda e: self.recarregar())

        ttk.Label(topo, text="Ordenar por:", font=("Segoe UI", 10)).pack(side="left")
        self.var_ordem = tk.StringVar(value="Maior aumento %")
        combo2 = ttk.Combobox(topo, textvariable=self.var_ordem,
                              values=["Maior aumento %", "Maior queda %",
                                      "Maior valor R$", "Produto"],
                              state="readonly", width=18)
        combo2.pack(side="left", padx=(4, 15))
        combo2.bind("<<ComboboxSelected>>", lambda e: self.recarregar())

        ttk.Button(topo, text="🔄 Recarregar",
                   command=self.recarregar).pack(side="left", padx=5)

        self.lbl_info = ttk.Label(topo, text="", foreground="#555")
        self.lbl_info.pack(side="right")

    


    # ============================================================
    # TABELA
    # ============================================================
    def _montar_tabela(self):
        container = ttk.Frame(self.janela)
        container.pack(fill="both", expand=True, padx=10)

        colunas = ("codigo", "descricao", "depto", "filial",
                   "vl_compra", "vl_ant", "variacao", "campeao", "qtd")
        self.tree = ttk.Treeview(container, columns=colunas, show="headings")

        headers = {
            "codigo": ("Código", 90),
            "descricao": ("Produto", 320),
            "depto": ("Depto", 55),
            "filial": ("Filial", 60),
            "vl_compra": ("VL Compra", 100),
            "vl_ant": ("VL Ant", 100),
            "variacao": ("Var %", 80),
            "campeao": ("Campeão", 130),
            "qtd": ("Qtd", 80),
        }
        for col, (titulo, largura) in headers.items():
            self.tree.heading(col, text=titulo)
            self.tree.column(col, width=largura,
                             anchor="center" if col != "descricao" else "w")

        # Tags pra cores
        self.tree.tag_configure("verde", background="#E2EFDA")   # queda > 10%
        self.tree.tag_configure("amarelo", background="#FFF2CC")  # -10% a +10%
        self.tree.tag_configure("vermelho", background="#F8CBAD")  # +20%
        self.tree.tag_configure("laranja", background="#FFE699")   # +10% a +20%

        scroll_y = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        # Duplo clique na QTD edita
        self.tree.bind("<Double-1>", self._editar_qtd)

    # ============================================================
    # RODAPÉ
    # ============================================================
    def _montar_rodape(self):
        rodape = ttk.Frame(self.janela, padding=(10, 8))
        rodape.pack(fill="x")

        ttk.Button(rodape, text="💾 Salvar Alterações",
                   command=self._salvar).pack(side="left", padx=(0, 8))
        ttk.Button(rodape, text="🔄 Descartar Alterações",
                   command=self.recarregar).pack(side="left", padx=(0, 8))

        ttk.Button(rodape, text="✅ Salvar e Fechar",
                   command=self._salvar_e_fechar).pack(side="left", padx=(20, 8))

        ttk.Button(rodape, text="❌ Fechar sem Salvar",
                   command=self._fechar_sem_salvar).pack(side="right")

        # Legenda
        legenda = ttk.Frame(rodape)
        legenda.pack(side="right", padx=20)
        ttk.Label(legenda, text="🟢 Queda >10%   ",
                  background="#E2EFDA", padding=3).pack(side="left", padx=2)
        ttk.Label(legenda, text="🟡 -10% a +10%   ",
                  background="#FFF2CC", padding=3).pack(side="left", padx=2)
        ttk.Label(legenda, text="🟠 +10% a +20%   ",
                  background="#FFE699", padding=3).pack(side="left", padx=2)
        ttk.Label(legenda, text="🔴 Aumento >20%",
                  background="#F8CBAD", padding=3).pack(side="left", padx=2)

    # ============================================================
    # RECARREGAR
    # ============================================================
    def recarregar(self):
        ano_mes = self.app.ano_mes_ativo()

        try:
            campeoes = calcular_campeoes(ano_mes)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao calcular campeões: {e}")
            campeoes = []

        # Carrega QTDs já salvas
        qtds_f1 = carregar_qtds(1, ano_mes)
        qtds_f2 = carregar_qtds(2, ano_mes)

        # Filtra por filial
        filtro = self.var_filial.get()
        if filtro == "Filial 1":
            campeoes = [c for c in campeoes if c["filial_id"] == 1]
        elif filtro == "Filial 2":
            campeoes = [c for c in campeoes if c["filial_id"] == 2]

        # Enriquece com QTD atual
        for c in campeoes:
            qtds = qtds_f1 if c["filial_id"] == 1 else qtds_f2
            c["qtd_comprador"] = qtds.get(c["produto_id"], 0)

        # Ordena
        ordem = self.var_ordem.get()
        if ordem == "Maior aumento %":
            campeoes.sort(
                key=lambda x: x.get("variacao_pct") if x.get("variacao_pct") is not None else -9999,
                reverse=True
            )
        elif ordem == "Maior queda %":
            campeoes.sort(
                key=lambda x: x.get("variacao_pct") if x.get("variacao_pct") is not None else 9999
            )
        elif ordem == "Maior valor R$":
            campeoes.sort(
                key=lambda x: (x.get("preco_unitario") or 0) * (x.get("qtd_comprador") or 0),
                reverse=True
            )
        elif ordem == "Produto":
            campeoes.sort(key=lambda x: x.get("descricao", ""))

        self.dados = campeoes
        self.qtds_originais = {
            (c["filial_id"], c["produto_id"]): c.get("qtd_comprador", 0)
            for c in campeoes
        }

        self._popular()

    def _popular(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for c in self.dados:
            var = c.get("variacao_pct")
            if var is None:
                var_str = "—"
                tag = "amarelo"
            else:
                var_str = f"{var:+.1f}%"
                if var < -10:
                    tag = "verde"
                elif var <= 10:
                    tag = "amarelo"
                elif var <= 20:
                    tag = "laranja"
                else:
                    tag = "vermelho"

            filial_str = "F1" if c["filial_id"] == 1 else "F2"
            nome_forn = c.get("fornecedor_nome") or f"Fornecedor {c['fornecedor_codigo']}"

            self.tree.insert(
                "", "end",
                iid=str(c["produto_id"] * 10 + c["filial_id"]),  # id único
                values=(
                    c.get("codigo_interno", ""),
                    c.get("descricao", "")[:60],
                    c.get("departamento", "") or "",
                    filial_str,
                    f"R$ {c.get('preco_unitario', 0):.2f}",
                    f"R$ {c.get('vl_ant', 0):.2f}" if c.get('vl_ant') else "—",
                    var_str,
                    nome_forn[:20],
                    f"{c.get('qtd_comprador', 0):.0f}",
                ),
                tags=(tag,)
            )

        self.lbl_info.config(
            text=f"{len(self.dados)} itens campeões  |  Mês: {self.app.ano_mes_ativo()}"
        )

    # ============================================================
    # EDITAR QTD
    # ============================================================
    def _editar_qtd(self, evt):
        item = self.tree.identify_row(evt.y)
        col = self.tree.identify_column(evt.x)
        if not item or col != "#9":   # coluna QTD
            return

        idx = item.split("_") if "_" in item else None
        try:
            iid = int(item)
        except ValueError:
            return

        # Recupera o dado
        produto_id = iid // 10
        filial_id = iid % 10

        # Encontra nos dados
        alvo = None
        for c in self.dados:
            if c["produto_id"] == produto_id and c["filial_id"] == filial_id:
                alvo = c
                break
        if not alvo:
            return

        valor_atual = alvo.get("qtd_comprador", 0)

        # Popup
        popup = tk.Toplevel(self.janela)
        popup.title("Editar QTD")
        popup.geometry("320x180")
        popup.transient(self.janela)
        popup.grab_set()

        ttk.Label(popup, text=alvo["descricao"][:40],
                  font=("Segoe UI", 10, "bold")).pack(pady=(15, 5))
        ttk.Label(popup, text=f"Campeão: {alvo.get('fornecedor_nome', '')[:30]}",
                  foreground="#555").pack()

        ttk.Label(popup, text="Quantidade:", font=("Segoe UI", 10)).pack(pady=(10, 5))
        var = tk.StringVar(value=f"{valor_atual:.0f}")
        entrada = ttk.Entry(popup, textvariable=var,
                            font=("Segoe UI", 14), justify="center", width=10)
        entrada.pack()
        entrada.focus_set()
        entrada.select_range(0, "end")

        def confirmar(_evt=None):
            try:
                novo = float(var.get().replace(",", "."))
                if novo < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erro", "Digite um número válido.")
                return

            alvo["qtd_comprador"] = novo

            # Atualiza a linha
            valores = list(self.tree.item(str(iid), "values"))
            valores[8] = f"{novo:.0f}"
            self.tree.item(str(iid), values=valores)

            popup.destroy()

        entrada.bind("<Return>", confirmar)
        ttk.Button(popup, text="Confirmar", command=confirmar).pack(pady=10)

    # ============================================================
    # SALVAR
    # ============================================================
    def _salvar(self, silencioso=False):
        ano_mes = self.app.ano_mes_ativo()
        alterados = 0

        try:
            for c in self.dados:
                chave = (c["filial_id"], c["produto_id"])
                qtd_antiga = self.qtds_originais.get(chave, 0)
                qtd_nova = c.get("qtd_comprador", 0)
                if abs(qtd_nova - qtd_antiga) > 0.001:
                    salvar_qtd(c["filial_id"], c["produto_id"], ano_mes, qtd_nova)
                    alterados += 1
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return 0

        # Atualiza o snapshot
        self.qtds_originais = {
            (c["filial_id"], c["produto_id"]): c.get("qtd_comprador", 0)
            for c in self.dados
        }

        if not silencioso:
            if alterados == 0:
                messagebox.showinfo("Nada a salvar", "Nenhuma alteração detectada.")
            else:
                messagebox.showinfo("Salvo", f"{alterados} quantidades atualizadas!")

        # Recarrega a aba Sugestão
        try:
            if hasattr(self.app, "tab_sugestao"):
                self.app.tab_sugestao.recarregar()
        except Exception:
            pass

        return alterados

    def _salvar_e_fechar(self):
        """Salva e fecha a janela."""
        n = self._salvar(silencioso=True)
        if n >= 0:  # sempre fecha, mesmo se nada mudou
            self.janela.destroy()

    def _fechar_sem_salvar(self):
        """Fecha a janela (pergunta se tem alterações pendentes)."""
        # Verifica se tem alterações não salvas
        tem_alteracoes = False
        for c in self.dados:
            chave = (c["filial_id"], c["produto_id"])
            qtd_antiga = self.qtds_originais.get(chave, 0)
            qtd_nova = c.get("qtd_comprador", 0)
            if abs(qtd_nova - qtd_antiga) > 0.001:
                tem_alteracoes = True
                break

        if tem_alteracoes:
            resp = messagebox.askyesno(
                "Alterações não salvas",
                "Existem alterações não salvas.\n\nDeseja sair mesmo assim?"
            )
            if not resp:
                return

        self.janela.destroy()