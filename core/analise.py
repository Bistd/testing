"""
Análise de cotações: campeões (menor preço por item), variação vs. última entrada.
"""
from core.database import conectar
from core.calculos import obter_vl_unit_ultima_entrada


def calcular_campeoes(ano_mes: str, filial_id: int) -> list:
    """
    Para cada produto DA FILIAL ESCOLHIDA, encontra o fornecedor com MENOR preço
    entre aqueles que responderam E onde o comprador decidiu QTD > 0.
    """
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cr.filial_id,
            cr.produto_id,
            cr.fornecedor_codigo,
            cr.preco_unitario,
            p.codigo_interno,
            p.codigo_barras,
            p.descricao,
            p.departamento,
            f.nome AS fornecedor_nome,
            ci.qtd_comprador
        FROM cotacao_respostas cr
        JOIN produtos p ON p.id = cr.produto_id
        JOIN cotacao_itens ci
            ON ci.produto_id = cr.produto_id
            AND ci.filial_id = cr.filial_id
            AND ci.ano_mes = cr.ano_mes
            AND ci.qtd_comprador > 0
        LEFT JOIN fornecedores f
            ON f.codigo = cr.fornecedor_codigo
        WHERE cr.ano_mes = ? AND cr.filial_id = ?
    """, (ano_mes, filial_id))

    todas = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not todas:
        return []

    # Agrupa por produto_id e pega o menor preço
    grupos = {}
    for r in todas:
        pid = r["produto_id"]
        if pid not in grupos or r["preco_unitario"] < grupos[pid]["preco_unitario"]:
            grupos[pid] = r

    campeoes = list(grupos.values())

    # Enriquece com VL Ant (última entrada)
    for c in campeoes:
        vl_ant = obter_vl_unit_ultima_entrada(c["filial_id"], c["produto_id"])
        c["vl_ant"] = vl_ant
        if vl_ant and vl_ant > 0:
            c["variacao_pct"] = round(
                (c["preco_unitario"] - vl_ant) / vl_ant * 100, 2
            )
        else:
            c["variacao_pct"] = None

    return campeoes


def calcular_totais_por_fornecedor(ano_mes: str) -> list:
    """
    Calcula total que cada fornecedor 'ganhou', separado por filial.
    """
    campeoes_f1 = calcular_campeoes(ano_mes, filial_id=1)
    campeoes_f2 = calcular_campeoes(ano_mes, filial_id=2)

    # Pega qtd de cada produto/filial
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT filial_id, produto_id, qtd_comprador
        FROM cotacao_itens
        WHERE ano_mes = ?
    """, (ano_mes,))
    qtds = {(r["filial_id"], r["produto_id"]): r["qtd_comprador"] for r in cur.fetchall()}
    conn.close()

    resultado = {}

    for c in campeoes_f1 + campeoes_f2:
        cod = c["fornecedor_codigo"]
        if cod not in resultado:
            resultado[cod] = {
                "fornecedor_codigo": cod,
                "fornecedor_nome": c.get("fornecedor_nome") or f"Fornecedor {cod}",
                "filial_1_total": 0.0,
                "filial_1_itens": 0,
                "filial_2_total": 0.0,
                "filial_2_itens": 0,
            }
        qtd = qtds.get((c["filial_id"], c["produto_id"]), 0)
        subtotal = (c["preco_unitario"] or 0) * (qtd or 0)

        if c["filial_id"] == 1:
            resultado[cod]["filial_1_total"] += subtotal
            resultado[cod]["filial_1_itens"] += 1
        elif c["filial_id"] == 2:
            resultado[cod]["filial_2_total"] += subtotal
            resultado[cod]["filial_2_itens"] += 1

    lista = list(resultado.values())
    for item in lista:
        item["total_geral"] = item["filial_1_total"] + item["filial_2_total"]
    lista.sort(key=lambda x: x["total_geral"], reverse=True)

    return lista


def listar_fornecedores_importados(ano_mes: str) -> list:
    """Retorna fornecedores que já tiveram respostas importadas."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT fornecedor_codigo, arquivo_origem
        FROM cotacao_respostas
        WHERE ano_mes = ?
        ORDER BY CAST(fornecedor_codigo AS INTEGER)
    """, (ano_mes,))
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()
    return resultado


def remover_respostas_fornecedor(ano_mes: str, fornecedor_codigo: str):
    """Remove todas as respostas de um fornecedor."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM cotacao_respostas
        WHERE ano_mes = ? AND fornecedor_codigo = ?
    """, (ano_mes, fornecedor_codigo))
    conn.commit()
    conn.close()