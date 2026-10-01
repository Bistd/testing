"""
Importa os arquivos de fornecedores (FORNECEDORES.xls e FORNECEDORES_COTACAO.xls).
"""
from pathlib import Path
import xlrd

from core.database import conectar
from core.config import RAIZ


PASTA_FORNECEDORES = RAIZ / "dados_entrada" / "FORNECEDORES"


def importar_fornecedores() -> dict:
    """
    Importa os 2 arquivos de fornecedores:
    - FORNECEDORES.xls → tabela `fornecedores` (todos)
    - FORNECEDORES_COTACAO.xls → tabela `fornecedores` + marca `participa_cotacao = 1`
    """
    stats = {
        "geral": {"importados": 0, "erros": 0, "arquivo": None},
        "cotacao": {"importados": 0, "erros": 0, "arquivo": None},
    }

    # ---- 1. Todos os fornecedores ----
    arq_geral = PASTA_FORNECEDORES / "FORNECEDORES.xls"
    if arq_geral.exists():
        stats["geral"] = _importar_arquivo(arq_geral, participa_cotacao=False)
    else:
        stats["geral"]["erros"] = 1
        stats["geral"]["arquivo"] = str(arq_geral)

    # ---- 2. Só os que participam da cotação ----
    arq_cot = PASTA_FORNECEDORES / "FORNECEDORES_COTACAO.xls"
    if arq_cot.exists():
        stats["cotacao"] = _importar_arquivo(arq_cot, participa_cotacao=True)
    else:
        stats["cotacao"]["erros"] = 1
        stats["cotacao"]["arquivo"] = str(arq_cot)

    return stats


def _importar_arquivo(caminho: Path, participa_cotacao: bool) -> dict:
    """Importa um arquivo de fornecedores."""
    resultado = {
        "arquivo": str(caminho.name),
        "importados": 0,
        "erros": 0,
        "mensagem": None,
    }

    try:
        livro = xlrd.open_workbook(str(caminho))
        planilha = livro.sheet_by_index(0)
    except Exception as e:
        resultado["erros"] = 1
        resultado["mensagem"] = str(e)
        return resultado

    conn = conectar()
    cur = conn.cursor()

    # Limpa a tabela se for o geral (que é a base)
    # Se for o de cotação, só atualiza os que participam
    if not participa_cotacao:
        cur.execute("DELETE FROM fornecedores")

    for i in range(planilha.nrows):
        linha = planilha.row_values(i)
        if len(linha) < 2:
            resultado["erros"] += 1
            continue

        codigo = _limpar(linha[0])
        nome = _limpar(linha[1])

        if not codigo or not nome:
            resultado["erros"] += 1
            continue

        try:
            if participa_cotacao:
                # Marca o fornecedor como participante da cotação
                cur.execute("""
                    INSERT INTO fornecedores (codigo, nome, participa_cotacao, ativo)
                    VALUES (?, ?, 1, 1)
                    ON CONFLICT(codigo) DO UPDATE SET
                        nome = excluded.nome,
                        participa_cotacao = 1
                """, (codigo, nome))
            else:
                # Insere/atualiza
                cur.execute("""
                    INSERT INTO fornecedores (codigo, nome, participa_cotacao, ativo)
                    VALUES (?, ?, 0, 1)
                    ON CONFLICT(codigo) DO UPDATE SET
                        nome = excluded.nome
                """, (codigo, nome))

            resultado["importados"] += 1
        except Exception as e:
            resultado["erros"] += 1

    conn.commit()
    conn.close()
    return resultado


def _limpar(v) -> str:
    """Converte valor em string limpa."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def listar_fornecedores_cotacao() -> list:
    """Retorna só os fornecedores que participam da cotação."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT codigo, nome FROM fornecedores
        WHERE participa_cotacao = 1
        ORDER BY CAST(codigo AS INTEGER), codigo
    """)
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()
    return resultado


def listar_todos_fornecedores() -> list:
    """Retorna todos os fornecedores."""
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT codigo, nome FROM fornecedores
        WHERE ativo = 1
        ORDER BY CAST(codigo AS INTEGER), codigo
    """)
    resultado = [dict(r) for r in cur.fetchall()]
    conn.close()
    return resultado