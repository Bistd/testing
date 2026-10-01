"""
Monta os pedidos a partir dos campeões (menor preço por item × filial).
"""
from core.database import conectar


def listar_pedidos_por_fornecedor(ano_mes: str) -> dict:
    """
    Retorna:
        {
            "4": {
                "filial_1": [ {codigo_interno, codigo_barras, descricao, qtd, preco, total}, ... ],
                "filial_2": [ ... ],
            },
            "53": { ... },
        }
    Só inclui itens com qtd > 0 e que tenham preço cadastrado.
    """
    conn = conectar()
    cur = conn.cursor()

    # 1. Pega campeões (menor preço por produto × filial)
    cur.execute("""
        SELECT
            cr.filial_id,
            cr.produto_id,
            cr.fornecedor_codigo,
            cr.preco_unitario,
            p.codigo_interno,
            p.codigo_barras,
            p.descricao
        FROM cotacao_respostas cr
        JOIN produtos p ON p.id = cr.produto_id
        WHERE cr.ano_mes = ?
    """, (ano_mes,))
    todas = [dict(r) for r in cur.fetchall()]

    # Agrupa e pega o menor preço
    campeoes = {}
    for r in todas:
        chave = (r["filial_id"], r["produto_id"])
        if chave not in campeoes or r["preco_unitario"] < campeoes[chave]["preco_unitario"]:
            campeoes[chave] = r

    # 2. Pega QTDs
    cur.execute("""
        SELECT filial_id, produto_id, qtd_comprador
        FROM cotacao_itens
        WHERE ano_mes = ?
    """, (ano_mes,))
    qtds = {(r["filial_id"], r["produto_id"]): r["qtd_comprador"] for r in cur.fetchall()}

    conn.close()

    # 3. Monta estrutura por fornecedor
    pedidos = {}
    for chave, c in campeoes.items():
        qtd = qtds.get(chave, 0)
        if not qtd or qtd <= 0:
            continue

        cod = str(c["fornecedor_codigo"])
        filial = c["filial_id"]

        if cod not in pedidos:
            pedidos[cod] = {"filial_1": [], "filial_2": []}

        item = {
            "codigo_interno": c["codigo_interno"],
            "codigo_barras": c["codigo_barras"] or "",
            "descricao": c["descricao"] or "",
            "qtd": float(qtd),
            "preco": float(c["preco_unitario"] or 0),
            "total": round(float(qtd) * float(c["preco_unitario"] or 0), 2),
        }

        if filial == 1:
            pedidos[cod]["filial_1"].append(item)
        elif filial == 2:
            pedidos[cod]["filial_2"].append(item)

    # Ordena itens por descrição em cada filial
    for cod in pedidos:
        pedidos[cod]["filial_1"].sort(key=lambda x: x["descricao"])
        pedidos[cod]["filial_2"].sort(key=lambda x: x["descricao"])

    return pedidos