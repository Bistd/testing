"""
Gerencia as QTDs decididas pelo comprador e as respostas dos fornecedores.
"""
from datetime import datetime
from core.database import conectar


# ============================================================
# QTDs do comprador
# ============================================================

def salvar_qtd(filial_id: int, produto_id: int, ano_mes: str, qtd: float):
    """Salva/atualiza a QTD de um produto."""
    conn = conectar()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO cotacao_itens (filial_id, produto_id, ano_mes, qtd_comprador, data_atualizacao)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(filial_id, produto_id, ano_mes)
        DO UPDATE SET qtd_comprador = excluded.qtd_comprador,
                      data_atualizacao = excluded.data_atualizacao
    """, (filial_id, produto_id, ano_mes, qtd, agora))
    conn.commit()
    conn.close()


def salvar_qtds_em_lote(filial_id: int, ano_mes: str, lista: list):
    """
    lista = [{"produto_id": X, "qtd": Y}, ...]
    Salva tudo numa transação só.
    """
    conn = conectar()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0
    for item in lista:
        cur.execute("""
            INSERT INTO cotacao_itens (filial_id, produto_id, ano_mes, qtd_comprador, data_atualizacao)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(filial_id, produto_id, ano_mes)
            DO UPDATE SET qtd_comprador = excluded.qtd_comprador,
                          data_atualizacao = excluded.data_atualizacao
        """, (filial_id, item["produto_id"], ano_mes, item["qtd"], agora))
        count += 1
    conn.commit()
    conn.close()
    return count


def carregar_qtds(filial_id: int, ano_mes: str) -> dict:
    """Retorna {produto_id: qtd}."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT produto_id, qtd_comprador FROM cotacao_itens
        WHERE filial_id = ? AND ano_mes = ?
    """, (filial_id, ano_mes))
    resultado = {r["produto_id"]: r["qtd_comprador"] for r in cur.fetchall()}
    conn.close()
    return resultado


def zerar_qtds(filial_id: int, ano_mes: str):
    """Apaga todas as QTDs salvas para a filial/mês."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM cotacao_itens WHERE filial_id = ? AND ano_mes = ?",
                (filial_id, ano_mes))
    conn.commit()
    conn.close()


def listar_itens_com_qtd(filial_id: int, ano_mes: str) -> list:
    """
    Retorna todos os itens com QTD > 0, com dados do produto prontos pra Excel.
    """
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            ci.qtd_comprador AS qtd,
            p.codigo_interno,
            p.codigo_barras,
            p.descricao,
            p.departamento,
            p.fornecedor_codigo
        FROM cotacao_itens ci
        JOIN produtos p ON p.id = ci.produto_id
        WHERE ci.filial_id = ? AND ci.ano_mes = ? AND ci.qtd_comprador > 0
        ORDER BY p.descricao
    """, (filial_id, ano_mes))
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()
    return resultado


# ============================================================
# Respostas dos fornecedores
# ============================================================

def salvar_respostas(filial_id: int, ano_mes: str, fornecedor_codigo: str,
                     respostas: list, arquivo_origem: str = ""):
    """
    respostas = [{"produto_id": X, "preco": Y}, ...]
    """
    conn = conectar()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    count = 0

    for r in respostas:
        cur.execute("""
            INSERT INTO cotacao_respostas
            (filial_id, produto_id, ano_mes, fornecedor_codigo,
             preco_unitario, data_importacao, arquivo_origem)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filial_id, produto_id, ano_mes, fornecedor_codigo)
            DO UPDATE SET preco_unitario = excluded.preco_unitario,
                          data_importacao = excluded.data_importacao,
                          arquivo_origem = excluded.arquivo_origem
        """, (filial_id, r["produto_id"], ano_mes, fornecedor_codigo,
              r["preco"], agora, arquivo_origem))
        count += 1

    conn.commit()
    conn.close()
    return count


def limpar_respostas(filial_id: int, ano_mes: str):
    """Apaga todas as respostas da filial/mês."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM cotacao_respostas WHERE filial_id = ? AND ano_mes = ?",
                (filial_id, ano_mes))
    conn.commit()
    conn.close()


def listar_respostas(filial_id: int, ano_mes: str) -> list:
    """Retorna todas as respostas da filial/mês."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            cr.fornecedor_codigo,
            cr.preco_unitario,
            cr.data_importacao,
            p.id AS produto_id,
            p.codigo_interno,
            p.descricao,
            p.codigo_barras
        FROM cotacao_respostas cr
        JOIN produtos p ON p.id = cr.produto_id
        WHERE cr.filial_id = ? AND cr.ano_mes = ?
    """, (filial_id, ano_mes))
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()
    return resultado

# ============================================================
# PREVIEW PARA ABA COTAÇÃO
# ============================================================

def listar_itens_para_preview(filial_id: int, ano_mes: str) -> list:
    """
    Retorna itens com QTD > 0 para preview na aba Cotação.
    Junta dados do produto + QTD + VL Unit.
    """
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            ci.produto_id,
            ci.qtd_comprador,
            p.codigo_interno,
            p.codigo_barras,
            p.descricao,
            p.departamento
        FROM cotacao_itens ci
        JOIN produtos p ON p.id = ci.produto_id
        WHERE ci.filial_id = ? AND ci.ano_mes = ? AND ci.qtd_comprador > 0
        ORDER BY p.descricao
    """, (filial_id, ano_mes))
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Enriquece com VL Unit (última entrada)
    from core.calculos import obter_vl_unit_ultima_entrada
    for item in resultado:
        item["vl_unit"] = obter_vl_unit_ultima_entrada(filial_id, item["produto_id"])

    return resultado