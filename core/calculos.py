"""
Cálculos: estoque (novo modelo), CX, sugestão, regra dos 60%.
"""
from core.database import conectar
from core.util_meses import ultimos_n_meses


# ============================================================
# ESTOQUE — NOVA REGRA (acumulativa com zeragem)
# ============================================================

def calcular_estoque(filial_id: int, produto_id: int,
                     ano_mes_atual: str, meses: int = 12) -> float:
    """
    Estoque novo:
      saldo = 0
      Para cada mês (do mais antigo pro mais atual):
          saldo = saldo + entrada - saída - avaria
          se saldo < 0: saldo = 0
      return saldo
    """
    lista_meses = ultimos_n_meses(ano_mes_atual, meses)

    conn = conectar()
    cur = conn.cursor()
    ph = ",".join("?" * len(lista_meses))
    cur.execute(f"""
        SELECT ano_mes, qtd_entrada, qtd_venda, qtd_avaria
        FROM historico_mensal
        WHERE filial_id = ? AND produto_id = ?
          AND ano_mes IN ({ph})
    """, [filial_id, produto_id] + lista_meses)
    dados = {r["ano_mes"]: r for r in cur.fetchall()}
    conn.close()

    saldo = 0.0
    for m in lista_meses:
        r = dados.get(m)
        if r:
            saldo += (r["qtd_entrada"] or 0) - (r["qtd_venda"] or 0) - (r["qtd_avaria"] or 0)
            if saldo < 0:
                saldo = 0

    return round(saldo, 2)


# ============================================================
# CX = menor qtd_entrada MENSAL dos últimos 12 meses
# ============================================================

def calcular_cx(filial_id: int, produto_id: int,
                ano_mes_atual: str, meses: int = 12) -> int:
    """
    CX = menor `qtd_entrada` MENSAL (diferente de zero) dos últimos 12 meses.
    Se nunca entrou, retorna 1.
    """
    lista_meses = ultimos_n_meses(ano_mes_atual, meses)

    conn = conectar()
    cur = conn.cursor()
    ph = ",".join("?" * len(lista_meses))
    cur.execute(f"""
        SELECT qtd_entrada
        FROM historico_mensal
        WHERE filial_id = ? AND produto_id = ?
          AND ano_mes IN ({ph})
          AND qtd_entrada > 0
    """, [filial_id, produto_id] + lista_meses)
    valores = [r["qtd_entrada"] for r in cur.fetchall()]
    conn.close()

    if not valores:
        return 1
    return max(1, int(min(valores)))


# ============================================================
# VL UNIT (direto do banco)
# ============================================================

def obter_vl_unit_ultima_entrada(filial_id: int, produto_id: int) -> float:
    """
    Preço unitário = vl_unit_ultima_entrada do mês MAIS RECENTE que tenha entrada.
    """
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT vl_unit_ultima_entrada
        FROM historico_mensal
        WHERE filial_id = ? AND produto_id = ?
          AND qtd_entrada > 0
        ORDER BY ano_mes DESC
        LIMIT 1
    """, (filial_id, produto_id))
    r = cur.fetchone()
    conn.close()
    if not r:
        return 0.0
    return round(r["vl_unit_ultima_entrada"] or 0, 2)


# ============================================================
# MOTOR DE SUGESTÃO
# ============================================================

def montar_sugestoes(filial_id: int, ano_mes_atual: str,
                     config: dict,
                     filtro_departamento: str = None,
                     filtro_fornecedor: str = None,
                     filtro_busca: str = None) -> list:
    """
    Monta a lista de sugestões com o NOVO modelo.
    """
    pct_regra = config.get("percentual_regra_sugestao", 0.60)
    meses_sug = config.get("meses_media_sugestao", 6)
    meses_est = config.get("meses_estoque", 12)

    lista_est = ultimos_n_meses(ano_mes_atual, meses_est)
    lista_sug = ultimos_n_meses(ano_mes_atual, meses_sug)

    conn = conectar()
    cur = conn.cursor()

    # 1. Buscar produtos
    sql = """
        SELECT id, codigo_interno, descricao, departamento,
               fornecedor_codigo, categoria, secao, fora_de_linha
        FROM produtos
        WHERE UPPER(COALESCE(fora_de_linha, '')) != 'FL'
    """
    params = []
    if filtro_departamento:
        sql += " AND departamento = ?"
        params.append(filtro_departamento)
    if filtro_fornecedor:
        sql += " AND fornecedor_codigo = ?"
        params.append(filtro_fornecedor)
    if filtro_busca:
        sql += " AND UPPER(descricao) LIKE UPPER(?)"
        params.append(filtro_busca.strip())
    sql += " ORDER BY descricao"

    cur.execute(sql, params)
    produtos = cur.fetchall()

    if not produtos:
        conn.close()
        return []

    # 2. Buscar todo o histórico dos últimos 12 meses (1 query)
    ph_est = ",".join("?" * len(lista_est))
    cur.execute(f"""
        SELECT produto_id, ano_mes, qtd_entrada, qtd_venda, qtd_avaria,
               vl_unit_ultima_entrada
        FROM historico_mensal
        WHERE filial_id = ? AND ano_mes IN ({ph_est})
    """, [filial_id] + lista_est)

    hist_por_produto = {}
    for r in cur.fetchall():
        pid = r["produto_id"]
        if pid not in hist_por_produto:
            hist_por_produto[pid] = {}
        hist_por_produto[pid][r["ano_mes"]] = {
            "qtd_entrada": r["qtd_entrada"] or 0,
            "qtd_venda": r["qtd_venda"] or 0,
            "qtd_avaria": r["qtd_avaria"] or 0,
            "vl_unit": r["vl_unit_ultima_entrada"] or 0,
        }

    conn.close()

    # 3. Processar em memória
    sugestoes = []
    set_est = set(lista_est)
    set_sug = set(lista_sug)

    for p in produtos:
        pid = p["id"]
        hist = hist_por_produto.get(pid, {})

        # ---- ESTOQUE (acumulativo com zeragem) ----
        saldo = 0.0
        for m in lista_est:
            h = hist.get(m)
            if h:
                saldo += h["qtd_entrada"] - h["qtd_venda"] - h["qtd_avaria"]
                if saldo < 0:
                    saldo = 0
        estoque = round(saldo, 2)

        # ---- CX = menor qtd_entrada mensal (últimos 12m) ----
        entradas = [hist[m]["qtd_entrada"] for m in lista_est
                    if m in hist and hist[m]["qtd_entrada"] > 0]
        cx = max(1, int(min(entradas))) if entradas else 1

        # ---- SUGESTÃO = média de venda dos últimos 6 meses ----
        soma_sug = sum(hist[m]["qtd_venda"] for m in lista_sug if m in hist)
        sugestao_bruta = soma_sug / meses_sug
        if cx <= 1:
            sugestao = int(sugestao_bruta)
        else:
            sugestao = int(sugestao_bruta // cx) * cx

        # ---- VL Unit (última entrada) ----
        vl_unit = 0.0
        ultimo_mes_entrada = None
        for m in sorted(hist.keys(), reverse=True):
            h = hist[m]
            if h["qtd_entrada"] > 0:
                vl_unit = h["vl_unit"]
                ultimo_mes_entrada = m
                break

        # ---- Regra dos 60% ----
        pct_vendido = 0.0
        if ultimo_mes_entrada:
            qtd_ult = hist[ultimo_mes_entrada]["qtd_entrada"]
            if qtd_ult > 0:
                vendido = sum(
                    hist[m]["qtd_venda"]
                    for m in hist
                    if ultimo_mes_entrada <= m <= ano_mes_atual
                )
                pct_vendido = vendido / qtd_ult

        # ---- Regra de inclusão ----
        # Se busca por texto: inclui TUDO (mesmo sem movimento)
        # Senão: aplica regra dos 60% + exige movimento nos últimos 12m
        incluir = True

        # Regra SEMPRE aplicada: precisa ter movimento nos últimos 12 meses
        tem_movimento = any(
            (hist[m]["qtd_entrada"] + hist[m]["qtd_venda"]) > 0
            for m in lista_est if m in hist
        )
        if not tem_movimento:
            incluir = False

        # Regra extra (só sem busca): aplica também a regra dos 60%
        if incluir and filtro_busca is None:
            if pct_vendido < pct_regra:
                incluir = False

        if incluir:
            sugestoes.append({
                "produto_id": pid,
                "codigo_interno": p["codigo_interno"],
                "descricao": p["descricao"],
                "departamento": p["departamento"],
                "fornecedor_codigo": p["fornecedor_codigo"],
                "categoria": p["categoria"],
                "secao": p["secao"],
                "fora_de_linha": p["fora_de_linha"],
                "estoque_atual": estoque,
                "cx": cx,
                "sugestao": sugestao,
                "vl_unit": vl_unit,
                "pct_vendido": round(pct_vendido * 100, 1),
                "qtd_comprador": 0.0,
            })

    return sugestoes