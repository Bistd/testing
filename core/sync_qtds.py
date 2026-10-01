"""
Exporta e importa QTDs entre computadores via arquivo JSON.
"""
import json
from datetime import datetime
from pathlib import Path

from core.database import conectar



def exportar_qtds(ano_mes: str, autor: str = "") -> Path:
    """
    Exporta todas as QTDs salvas (ambas as filiais) para um arquivo .json.
    Retorna o caminho do arquivo gerado.
    """
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT ci.filial_id, p.codigo_interno, ci.qtd_comprador
        FROM cotacao_itens ci
        JOIN produtos p ON p.id = ci.produto_id
        WHERE ci.ano_mes = ? AND ci.qtd_comprador > 0
        ORDER BY ci.filial_id, p.codigo_interno
    """, (ano_mes,))
    linhas = cur.fetchall()
    conn.close()

    qtds = [
        {
            "filial": r["filial_id"],
            "codigo_interno": r["codigo_interno"],
            "qtd": float(r["qtd_comprador"]),
        }
        for r in linhas
    ]

    pacote = {
        "versao": 1,
        "ano_mes": ano_mes,
        "data_exportacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "exportado_por": autor or "PC",
        "total_itens": len(qtds),
        "qtds": qtds,
    }

    # Nome do arquivo
    pasta = Path.home() / "Downloads"
    if not pasta.exists():
        pasta = Path.home()

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    nome = f"cotacao_qtds_{ano_mes}_{ts}.json"
    caminho = pasta / nome

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=2)

    return caminho


def importar_qtds(caminho: Path) -> dict:
    """
    Importa um arquivo .json com QTDs de outro PC.
    Merge: sobrescreve o que veio, mantém o resto.

    Retorna:
        {
            "ok": bool,
            "total_no_arquivo": N,
            "inseridos": N,
            "atualizados": N,
            "produtos_nao_encontrados": [...],
            "ano_mes_arquivo": "...",
        }
    """
    resultado = {
        "ok": False,
        "total_no_arquivo": 0,
        "inseridos": 0,
        "atualizados": 0,
        "produtos_nao_encontrados": [],
        "ano_mes_arquivo": None,
        "erro": None,
    }

    try:
        with open(caminho, "r", encoding="utf-8") as f:
            pacote = json.load(f)
    except Exception as e:
        resultado["erro"] = f"Não consegui ler o arquivo: {e}"
        return resultado

    # Validação
    if not isinstance(pacote, dict) or "qtds" not in pacote:
        resultado["erro"] = "Arquivo inválido (não é um pacote de cotação)."
        return resultado

    ano_mes = pacote.get("ano_mes")
    if not ano_mes:
        resultado["erro"] = "Arquivo sem 'ano_mes'. Não sei a que mês pertence."
        return resultado

    resultado["ano_mes_arquivo"] = ano_mes
    qtds = pacote.get("qtds", [])
    resultado["total_no_arquivo"] = len(qtds)

    if not qtds:
        resultado["ok"] = True
        return resultado

    conn = conectar()
    cur = conn.cursor()

    for item in qtds:
        try:
            filial = int(item["filial"])
            codigo = str(item["codigo_interno"]).strip()
            qtd = float(item["qtd"])
        except (KeyError, ValueError, TypeError):
            continue

        # Busca produto
        cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?", (codigo,))
        r = cur.fetchone()
        if not r:
            resultado["produtos_nao_encontrados"].append(codigo)
            continue

        produto_id = r[0]

        # Verifica se já existe
        cur.execute("""
            SELECT id FROM cotacao_itens
            WHERE filial_id = ? AND produto_id = ? AND ano_mes = ?
        """, (filial, produto_id, ano_mes))
        existe = cur.fetchone()

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if existe:
            cur.execute("""
                UPDATE cotacao_itens
                SET qtd_comprador = ?, data_atualizacao = ?
                WHERE id = ?
            """, (qtd, agora, existe[0]))
            resultado["atualizados"] += 1
        else:
            cur.execute("""
                INSERT INTO cotacao_itens
                (filial_id, produto_id, ano_mes, qtd_comprador, data_atualizacao)
                VALUES (?, ?, ?, ?, ?)
            """, (filial, produto_id, ano_mes, qtd, agora))
            resultado["inseridos"] += 1

    conn.commit()
    conn.close()

    resultado["ok"] = True
    return resultado