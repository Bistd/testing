"""
Funções para trabalhar com as pastas de mês (A-JAN, B-FEV, ...).
"""
from datetime import date
from typing import Optional
import re

# Mapa: sigla → número do mês
MESES_SIGLA = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
    "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
    "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

# Mapa: número do mês → sigla
MESES_NUMERO = {v: k for k, v in MESES_SIGLA.items()}

# Regex para reconhecer pastas de mês: A-JAN, B-FEV, etc.
REGEX_PASTA_MES = re.compile(r"^([A-L])-([A-Z]{3})$")


def eh_pasta_de_mes(nome: str) -> bool:
    """Verifica se o nome de pasta casa com o padrão A-JAN."""
    m = REGEX_PASTA_MES.match(nome.upper())
    if not m:
        return False
    return m.group(2) in MESES_SIGLA


def sigla_para_numero(sigla: str) -> int:
    """'SET' → 9"""
    return MESES_SIGLA[sigla.upper()]


def numero_para_sigla(numero: int) -> str:
    """9 → 'SET'"""
    return MESES_NUMERO[numero]


def calcular_ano_mes(pasta_mes: str, hoje: Optional[date] = None) -> str:
    """
    Dado o nome da pasta (ex: 'I-SET'), retorna o ano-mês real (ex: '2025-09').

    Regra:
      - Se o mês da pasta <= mês atual → é do ano atual.
      - Se o mês da pasta > mês atual → é do ano passado.
    """
    if hoje is None:
        hoje = date.today()

    m = REGEX_PASTA_MES.match(pasta_mes.upper())
    if not m:
        raise ValueError(f"Pasta inválida: {pasta_mes}")

    sigla = m.group(2)
    mes = sigla_para_numero(sigla)

    if mes <= hoje.month:
        ano = hoje.year
    else:
        ano = hoje.year - 1

    return f"{ano}-{mes:02d}"


def ultimos_n_meses(ano_mes_atual: str, n: int) -> list:
    """
    Retorna lista dos últimos N ano_mes (incluindo o atual), do mais antigo
    pro mais recente.

    Ex: ultimos_n_meses("2025-09", 6) → ['2025-04', ..., '2025-09']
    """
    ano, mes = map(int, ano_mes_atual.split("-"))
    resultado = []
    for _ in range(n):
        resultado.append(f"{ano}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes = 12
            ano -= 1
    return list(reversed(resultado))