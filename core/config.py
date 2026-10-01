"""
Leitura e gravação do config.json.
"""
import json
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CONFIG = RAIZ / "config.json"

DEFAULTS = {
    "pasta_entrada": "dados_entrada",
    "filial_ativa": 1,
    "mes_ativo": "I-SET",
    "percentual_regra_sugestao": 0.60,
    "meses_media_sugestao": 6,
    "meses_estoque": 12,
    "backup_manter": 5,
}


def carregar_config() -> dict:
    """Carrega o config.json. Se não existir, cria com defaults."""
    if not ARQUIVO_CONFIG.exists():
        salvar_config(DEFAULTS)
        return dict(DEFAULTS)

    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        # Se o arquivo estiver corrompido, recria
        salvar_config(DEFAULTS)
        return dict(DEFAULTS)

    # Preenche chaves faltantes com defaults
    for k, v in DEFAULTS.items():
        dados.setdefault(k, v)
    return dados


def salvar_config(config: dict) -> None:
    """Grava o config.json."""
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def caminho_pasta_entrada(config: dict) -> Path:
    """Retorna o Path absoluto da pasta de entrada."""
    return RAIZ / config["pasta_entrada"]

def caminho_pasta_produtos(config: dict) -> Path:
    """Pasta dos arquivos de cadastro."""
    return caminho_pasta_entrada(config) / "PRODUTOS"


def caminho_pasta_fornecedores(config: dict) -> Path:
    """Pasta dos arquivos de fornecedores."""
    return caminho_pasta_entrada(config) / "FORNECEDORES"


def caminho_pasta_movimento(config: dict) -> Path:
    """Pasta dos arquivos de movimento (com subpastas A-JAN, etc)."""
    return caminho_pasta_entrada(config) / "MOVIMENTO"


def caminho_banco() -> Path:
    """Retorna o Path absoluto do banco."""
    p = RAIZ / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p / "compras.db"


def caminho_logs() -> Path:
    """Retorna o Path absoluto da pasta de logs."""
    p = RAIZ / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p