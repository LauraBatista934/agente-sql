"""Acesso ao banco: conexao somente leitura, leitura do schema e execucao.

Toda consulta roda em uma conexao aberta em modo `ro` (read-only) do
SQLite. Mesmo se a validacao de SQL falhar, o banco nao aceita escrita
por esse caminho.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "loja.db"

MAX_ROWS = 50


class DatabaseError(RuntimeError):
    """Erro de banco com mensagem amigavel para o usuario."""


def connect_readonly() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise DatabaseError(
            f"Banco nao encontrado em {DB_PATH}. Rode: python seed.py"
        )
    uri = f"file:{DB_PATH.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema() -> str:
    """Devolve o DDL das tabelas, pronto para entrar no prompt do modelo."""
    conn = connect_readonly()
    try:
        rows = conn.execute(
            """
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return "\n\n".join(r["sql"].strip() + ";" for r in rows)
    finally:
        conn.close()


def get_sample_rows(por_tabela: int = 2) -> str:
    """Pequena amostra de cada tabela, para o modelo ver o formato dos dados."""
    conn = connect_readonly()
    blocos = []
    try:
        tabelas = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        for tabela in tabelas:
            cursor = conn.execute(f'SELECT * FROM "{tabela}" LIMIT {int(por_tabela)}')
            colunas = [d[0] for d in cursor.description]
            linhas = [tuple(r) for r in cursor.fetchall()]
            blocos.append(f"{tabela} {colunas} -> {linhas}")
    finally:
        conn.close()
    return "\n".join(blocos)


def run_query(sql: str) -> tuple[list[str], list[tuple]]:
    """Executa o SELECT ja validado e devolve colunas + linhas."""
    conn = connect_readonly()
    try:
        cursor = conn.execute(sql)
        colunas = [d[0] for d in cursor.description] if cursor.description else []
        linhas = [tuple(r) for r in cursor.fetchmany(MAX_ROWS)]
        return colunas, linhas
    except sqlite3.Error as exc:
        raise DatabaseError(f"O banco rejeitou a consulta: {exc}") from exc
    finally:
        conn.close()
