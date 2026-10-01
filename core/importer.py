"""
Leitura dos arquivos .xls novos (cadastro + movimento) e gravação no banco.
"""
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import xlrd

from core.config import (
    RAIZ,
    caminho_pasta_entrada,
    caminho_pasta_produtos,
    caminho_pasta_fornecedores,
    caminho_pasta_movimento,
)
from core.database import conectar, fazer_backup
from core.util_meses import calcular_ano_mes, eh_pasta_de_mes
from core.importador_fornecedores import importar_fornecedores


# ============================================================
# PADRÕES DE NOME
# ============================================================

REGEX_CADASTRO = re.compile(r"8076-CADASTRO", re.IGNORECASE)
REGEX_MOVIMENTO = re.compile(r"8075-filial-(\d+)-([A-Z]{3})", re.IGNORECASE)


def detectar_tipo_arquivo(nome_arquivo: str) -> Optional[dict]:
    nome = Path(nome_arquivo).stem.upper().strip()

    if REGEX_CADASTRO.search(nome):
        return {"tipo": "cadastro"}

    m = REGEX_MOVIMENTO.search(nome)
    if m:
        return {"tipo": "movimento", "filial": int(m.group(1))}

    return None


# ============================================================
# LEITURA CRUA
# ============================================================

def ler_xls(caminho: Path) -> list:
    livro = xlrd.open_workbook(str(caminho))
    planilha = livro.sheet_by_index(0)

    linhas = []
    for i in range(planilha.nrows):
        linha = planilha.row_values(i)
        if all((c is None or str(c).strip() == "") for c in linha):
            continue
        linhas.append(linha)
    return linhas


def _limpar(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return 0.0
    s = s.replace("R$", "").replace(" ", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _tratar_codigo_barras(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        try:
            return str(int(v))
        except (ValueError, OverflowError):
            return str(v)
    s = str(v).strip()
    if "E" in s.upper() or "e" in s:
        try:
            return str(int(float(s.replace(",", "."))))
        except (ValueError, OverflowError):
            pass
    return s


# ============================================================
# IMPORTAÇÃO DE CADASTRO
# ============================================================

def importar_cadastro(caminho: Path) -> dict:
    stats = {
        "arquivo": caminho.name, "tipo": "cadastro",
        "linhas": 0, "inseridos": 0, "atualizados": 0, "erros": 0,
    }

    try:
        linhas = ler_xls(caminho)
    except Exception as e:
        stats["erros"] = 1
        stats["mensagem_erro"] = str(e)
        return stats

    conn = conectar()
    cur = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for linha in linhas:
        stats["linhas"] += 1
        try:
            if len(linha) < 8:
                stats["erros"] += 1
                continue

            codigo = _limpar(linha[0])
            if not codigo:
                stats["erros"] += 1
                continue

            codigo_barras = _tratar_codigo_barras(linha[1])
            descricao = _limpar(linha[2])
            departamento = _limpar(linha[3])
            secao = _limpar(linha[4])
            categoria = _limpar(linha[5])
            fornecedor = _limpar(linha[6])
            fora_de_linha = _limpar(linha[7]).upper()

            cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?", (codigo,))
            existe = cur.fetchone()

            if existe:
                cur.execute("""
                    UPDATE produtos SET
                        codigo_barras = ?, descricao = ?, departamento = ?,
                        secao = ?, categoria = ?, fornecedor_codigo = ?,
                        fora_de_linha = ?, data_atualizacao = ?
                    WHERE codigo_interno = ?
                """, (codigo_barras, descricao, departamento, secao, categoria,
                      fornecedor, fora_de_linha, agora, codigo))
                stats["atualizados"] += 1
            else:
                cur.execute("""
                    INSERT INTO produtos
                    (codigo_interno, codigo_barras, descricao, departamento,
                     secao, categoria, fornecedor_codigo, fora_de_linha,
                     qtd_por_caixa, data_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (codigo, codigo_barras, descricao, departamento, secao,
                      categoria, fornecedor, fora_de_linha, agora))
                stats["inseridos"] += 1

        except Exception:
            stats["erros"] += 1

    conn.commit()
    conn.close()

    _registrar_importacao(caminho, "cadastro", None, None, stats)
    return stats


# ============================================================
# IMPORTAÇÃO DE MOVIMENTO
# ============================================================

def importar_movimento(caminho: Path, filial_numero: int, ano_mes: str) -> dict:
    info = detectar_tipo_arquivo(caminho.name)
    if not info or info["tipo"] != "movimento":
        return {"arquivo": caminho.name, "erros": 1,
                "mensagem_erro": "Não é arquivo de movimento"}

    stats = {
        "arquivo": caminho.name, "tipo": "movimento",
        "filial": filial_numero, "ano_mes": ano_mes,
        "linhas": 0, "inseridos": 0, "atualizados": 0, "erros": 0,
    }

    try:
        linhas = ler_xls(caminho)
    except Exception as e:
        stats["erros"] = 1
        stats["mensagem_erro"] = str(e)
        return stats

    stats["linhas"] = len(linhas)

    conn = conectar()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO filiais (numero, nome) VALUES (?, ?)",
                (filial_numero, f"Filial {filial_numero}"))
    conn.commit()

    cur.execute("SELECT id FROM filiais WHERE numero = ?", (filial_numero,))
    r = cur.fetchone()
    if not r:
        conn.close()
        stats["erros"] = 1
        stats["mensagem_erro"] = f"Filial {filial_numero} não encontrada"
        return stats
    filial_id = r[0]

    ins = 0
    atu = 0
    err = 0

    for linha in linhas:
        try:
            if len(linha) < 7:
                err += 1
                continue

            codigo = _limpar(linha[1])
            if not codigo:
                err += 1
                continue

            data_ult_entrada = _limpar(linha[2])
            vl_unit_ult = _to_float(linha[3])
            qtd_entrada = _to_float(linha[4])
            qtd_venda = _to_float(linha[5])
            qtd_avaria = _to_float(linha[6])

            cur.execute("SELECT id FROM produtos WHERE codigo_interno = ?", (codigo,))
            r = cur.fetchone()
            if not r:
                err += 1
                continue
            produto_id = r[0]

            cur.execute("""
                SELECT id FROM historico_mensal
                WHERE filial_id = ? AND produto_id = ? AND ano_mes = ?
            """, (filial_id, produto_id, ano_mes))
            existe = cur.fetchone()

            if existe:
                cur.execute("""
                    UPDATE historico_mensal SET
                        qtd_entrada = ?, qtd_venda = ?, qtd_avaria = ?,
                        vl_unit_ultima_entrada = ?, data_ultima_entrada = ?
                    WHERE id = ?
                """, (qtd_entrada, qtd_venda, qtd_avaria, vl_unit_ult,
                      data_ult_entrada, existe[0]))
                atu += 1
            else:
                cur.execute("""
                    INSERT INTO historico_mensal
                    (filial_id, produto_id, ano_mes,
                     qtd_entrada, qtd_venda, qtd_avaria,
                     vl_unit_ultima_entrada, data_ultima_entrada)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (filial_id, produto_id, ano_mes,
                      qtd_entrada, qtd_venda, qtd_avaria,
                      vl_unit_ult, data_ult_entrada))
                ins += 1

        except Exception:
            err += 1

    stats["inseridos"] = ins
    stats["atualizados"] = atu
    stats["erros"] = err

    conn.commit()
    conn.close()

    _registrar_importacao(caminho, "movimento", filial_numero, ano_mes, stats)
    return stats


# ============================================================
# IMPORTAÇÃO DE CÓDIGOS DE FORNECEDORES
# ============================================================

def importar_codigos_fornecedores(caminho: Path) -> dict:
    """Importa CODIGOS_FORNECEDORES.xls
    Colunas: produto_id (nosso) | fornecedor_codigo | codigo_no_fornecedor
    """
    stats = {
        "arquivo": caminho.name,
        "tipo": "codigos_fornecedores",
        "linhas": 0,
        "inseridos": 0,
        "atualizados": 0,
        "erros": 0,
        "produtos_nao_encontrados": 0,
    }

    if not caminho.exists():
        stats["erros"] = 1
        stats["mensagem_erro"] = "Arquivo não encontrado"
        return stats

    try:
        linhas = ler_xls(caminho)
    except Exception as e:
        stats["erros"] = 1
        stats["mensagem_erro"] = str(e)
        return stats

    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT id, codigo_interno FROM produtos")
    mapa_produtos = {r["codigo_interno"]: r["id"] for r in cur.fetchall()}

    for linha in linhas:
        stats["linhas"] += 1
        try:
            if len(linha) < 3:
                stats["erros"] += 1
                continue

            codigo_interno = _limpar(linha[0])
            fornecedor = _limpar(linha[1])
            codigo_forn = _limpar(linha[2])

            if not codigo_interno or not fornecedor:
                stats["erros"] += 1
                continue

            produto_id = mapa_produtos.get(codigo_interno)
            if not produto_id:
                stats["produtos_nao_encontrados"] += 1
                continue

            cur.execute("""
                INSERT INTO codigos_fornecedores
                (produto_id, fornecedor_codigo, codigo_no_fornecedor)
                VALUES (?, ?, ?)
                ON CONFLICT(produto_id, fornecedor_codigo)
                DO UPDATE SET codigo_no_fornecedor = excluded.codigo_no_fornecedor
            """, (produto_id, fornecedor, codigo_forn))
            stats["inseridos"] += 1

        except Exception:
            stats["erros"] += 1

    conn.commit()
    conn.close()

    _registrar_importacao(caminho, "codigos_fornecedores", None, None, stats)
    return stats


def buscar_codigo_no_fornecedor(produto_id: int, fornecedor_codigo: str) -> str:
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        SELECT codigo_no_fornecedor FROM codigos_fornecedores
        WHERE produto_id = ? AND fornecedor_codigo = ?
        LIMIT 1
    """, (produto_id, fornecedor_codigo))
    r = cur.fetchone()
    conn.close()
    return r["codigo_no_fornecedor"] if r and r["codigo_no_fornecedor"] else ""


# ============================================================
# ORQUESTRAÇÃO
# ============================================================

def reprocessar_mes_ativo(config: dict) -> list:
    resultados = []
    fazer_backup(config.get("backup_manter", 5))

    # 1. Fornecedores
    try:
        r = importar_fornecedores()
        resultados.append({
            "arquivo": "FORNECEDORES", "tipo": "fornecedores",
            "linhas": r["geral"]["importados"] + r["cotacao"]["importados"],
            "inseridos": r["geral"]["importados"] + r["cotacao"]["importados"],
            "atualizados": 0,
            "erros": r["geral"]["erros"] + r["cotacao"]["erros"],
        })
    except Exception as e:
        resultados.append({"arquivo": "FORNECEDORES", "erros": 1,
                           "mensagem_erro": str(e)})

    # 1.5. Códigos de fornecedores
    arq_codigos = caminho_pasta_fornecedores(config) / "CODIGOS_FORNECEDORES.xls"
    if arq_codigos.exists():
        resultados.append(importar_codigos_fornecedores(arq_codigos))

    # 2. Cadastro
    pasta_prod = caminho_pasta_produtos(config)
    if pasta_prod.exists():
        for arq in pasta_prod.iterdir():
            if arq.suffix.lower() != ".xls":
                continue
            info = detectar_tipo_arquivo(arq.name)
            if info and info["tipo"] == "cadastro":
                resultados.append(importar_cadastro(arq))

    # 3. Movimento do mês ativo
    pasta_mes = caminho_pasta_movimento(config) / config["mes_ativo"]
    if not pasta_mes.exists():
        resultados.append({"arquivo": str(pasta_mes), "erros": 1,
                           "mensagem_erro": f"Pasta {config['mes_ativo']} não existe"})
        return resultados

    ano_mes = calcular_ano_mes(config["mes_ativo"])

    for arq in pasta_mes.iterdir():
        if arq.suffix.lower() != ".xls":
            continue
        info = detectar_tipo_arquivo(arq.name)
        if not info or info["tipo"] != "movimento":
            continue
        resultados.append(importar_movimento(arq, info["filial"], ano_mes))

    return resultados


def importar_historico_completo(config: dict) -> list:
    resultados = []
    fazer_backup(config.get("backup_manter", 5))

    # 1. Fornecedores
    try:
        r = importar_fornecedores()
        resultados.append({
            "arquivo": "FORNECEDORES", "tipo": "fornecedores",
            "linhas": r["geral"]["importados"] + r["cotacao"]["importados"],
            "inseridos": r["geral"]["importados"] + r["cotacao"]["importados"],
            "atualizados": 0,
            "erros": r["geral"]["erros"] + r["cotacao"]["erros"],
        })
    except Exception as e:
        resultados.append({"arquivo": "FORNECEDORES", "erros": 1,
                           "mensagem_erro": str(e)})

    # 1.5. Códigos de fornecedores
    arq_codigos = caminho_pasta_fornecedores(config) / "CODIGOS_FORNECEDORES.xls"
    if arq_codigos.exists():
        resultados.append(importar_codigos_fornecedores(arq_codigos))

    # 2. Cadastro
    pasta_prod = caminho_pasta_produtos(config)
    if pasta_prod.exists():
        for arq in pasta_prod.iterdir():
            if arq.suffix.lower() != ".xls":
                continue
            info = detectar_tipo_arquivo(arq.name)
            if info and info["tipo"] == "cadastro":
                resultados.append(importar_cadastro(arq))

    # 3. Todos os meses
    pasta_mov = caminho_pasta_movimento(config)
    if not pasta_mov.exists():
        return resultados

    for item in sorted(pasta_mov.iterdir()):
        if not item.is_dir():
            continue
        if not eh_pasta_de_mes(item.name):
            continue

        ano_mes = calcular_ano_mes(item.name)

        for arq in item.iterdir():
            if arq.suffix.lower() != ".xls":
                continue
            info = detectar_tipo_arquivo(arq.name)
            if not info or info["tipo"] != "movimento":
                continue
            resultados.append(importar_movimento(arq, info["filial"], ano_mes))

    return resultados


# ============================================================
# LOG
# ============================================================

def _registrar_importacao(caminho: Path, tipo: str, filial: Optional[int],
                          ano_mes: Optional[str], stats: dict):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO arquivos_importados
            (caminho, tipo, filial_numero, ano_mes,
             linhas_processadas, inseridos, atualizados, erros, data_importacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(caminho), tipo, filial, ano_mes,
            stats.get("linhas", 0), stats.get("inseridos", 0),
            stats.get("atualizados", 0), stats.get("erros", 0),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass