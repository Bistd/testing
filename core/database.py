"""
Criação e conexão com o banco SQLite.
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

from core.config import caminho_banco, RAIZ


def conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(caminho_banco())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco() -> None:
    """Cria todas as tabelas se não existirem."""
    conn = conectar()
    cur = conn.cursor()

    # ---------- FILIAIS ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS filiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER UNIQUE NOT NULL,
            nome TEXT
        )
    """)

    # ---------- PRODUTOS ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_interno TEXT UNIQUE NOT NULL,
            codigo_barras TEXT,
            descricao TEXT,
            departamento TEXT,
            secao TEXT,
            categoria TEXT,
            fornecedor_codigo TEXT,
            fora_de_linha TEXT,
            qtd_por_caixa INTEGER DEFAULT 1,
            data_atualizacao TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_depto ON produtos(departamento)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_forn ON produtos(fornecedor_codigo)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prod_desc ON produtos(descricao)")

    # ---------- HISTÓRICO MENSAL ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico_mensal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filial_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            ano_mes TEXT NOT NULL,
            qtd_entrada REAL DEFAULT 0,
            qtd_venda REAL DEFAULT 0,
            qtd_avaria REAL DEFAULT 0,
            vl_unit_ultima_entrada REAL DEFAULT 0,
            data_ultima_entrada TEXT,
            UNIQUE(filial_id, produto_id, ano_mes),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_filial_mes ON historico_mensal(filial_id, ano_mes)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hist_produto ON historico_mensal(produto_id)")

    # ---------- FORNECEDORES ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT,
            participa_cotacao INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_forn_cotacao ON fornecedores(participa_cotacao)")

    # ---------- CÓDIGOS DO FORNECEDOR (por produto) ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS codigos_fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            fornecedor_codigo TEXT NOT NULL,
            codigo_no_fornecedor TEXT,
            UNIQUE(produto_id, fornecedor_codigo),
            FOREIGN KEY (produto_id) REFERENCES produtos(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cod_forn ON codigos_fornecedores(produto_id, fornecedor_codigo)")

    # ---------- COTAÇÃO ITENS ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filial_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            ano_mes TEXT NOT NULL,
            qtd_comprador REAL DEFAULT 0,
            data_atualizacao TEXT,
            UNIQUE(filial_id, produto_id, ano_mes)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cot_item_filial_mes ON cotacao_itens(filial_id, ano_mes)")

    # ---------- COTAÇÃO RESPOSTAS ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cotacao_respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filial_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            ano_mes TEXT NOT NULL,
            fornecedor_codigo TEXT NOT NULL,
            preco_unitario REAL NOT NULL,
            data_importacao TEXT,
            arquivo_origem TEXT,
            UNIQUE(filial_id, produto_id, ano_mes, fornecedor_codigo)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cot_resp_chave ON cotacao_respostas(filial_id, ano_mes, produto_id)")

    # ---------- LOG DE IMPORTAÇÕES ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS arquivos_importados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caminho TEXT NOT NULL,
            tipo TEXT NOT NULL,
            filial_numero INTEGER,
            ano_mes TEXT,
            linhas_processadas INTEGER DEFAULT 0,
            inseridos INTEGER DEFAULT 0,
            atualizados INTEGER DEFAULT 0,
            erros INTEGER DEFAULT 0,
            data_importacao TEXT
        )
    """)

    # ---------- GARANTE AS 2 FILIAIS ----------
    cur.execute("INSERT OR IGNORE INTO filiais (numero, nome) VALUES (1, 'Filial 1')")
    cur.execute("INSERT OR IGNORE INTO filiais (numero, nome) VALUES (2, 'Filial 2')")

    conn.commit()
    conn.close()


def apagar_banco() -> None:
    caminho = caminho_banco()
    if caminho.exists():
        caminho.unlink()
    inicializar_banco()


def fazer_backup(manter: int = 5) -> Path:
    origem = caminho_banco()
    if not origem.exists():
        return None

    pasta_backup = RAIZ / "data" / "backups"
    pasta_backup.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = pasta_backup / f"compras_{ts}.db"
    shutil.copy2(origem, destino)

    backups = sorted(pasta_backup.glob("compras_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > manter:
        backups.pop(0).unlink()

    return destino