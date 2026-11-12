"""Guardrails: o modelo sugere SQL, esta camada decide o que pode rodar.

Regras aplicadas antes de qualquer execucao:
  1. apenas uma instrucao (sem `;` no meio);
  2. precisa comecar com SELECT ou WITH;
  3. nenhuma palavra-chave de escrita/administracao (INSERT, DROP, PRAGMA...);
  4. comentarios sao removidos (para nao esconder comandos);
  5. se nao houver LIMIT, aplica um limite padrao.

Alem disso, a conexao do banco e aberta em modo somente leitura
(read-only), como segunda barreira.
"""

from __future__ import annotations

import re

LIMITE_PADRAO = 100

PALAVRAS_PROIBIDAS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "replace",
    "truncate",
    "attach",
    "detach",
    "pragma",
    "vacuum",
    "reindex",
    "grant",
    "revoke",
    "begin",
    "commit",
    "rollback",
    "savepoint",
)

_RE_PROIBIDAS = re.compile(r"\b(" + "|".join(PALAVRAS_PROIBIDAS) + r")\b", re.IGNORECASE)
_RE_COMENTARIO_LINHA = re.compile(r"--[^\n]*")
_RE_COMENTARIO_BLOCO = re.compile(r"/\*.*?\*/", re.DOTALL)


class SqlInvalido(ValueError):
    """SQL rejeitado pelos guardrails."""


def limpar_comentarios(sql: str) -> str:
    sql = _RE_COMENTARIO_BLOCO.sub(" ", sql)
    sql = _RE_COMENTARIO_LINHA.sub(" ", sql)
    return sql


def validar_sql(sql: str) -> str:
    """Valida e normaliza a consulta. Levanta SqlInvalido se algo estiver errado."""
    if not sql or not sql.strip():
        raise SqlInvalido("a consulta veio vazia")

    limpo = limpar_comentarios(sql).strip().rstrip(";").strip()

    if not limpo:
        raise SqlInvalido("a consulta veio vazia")

    if ";" in limpo:
        raise SqlInvalido("apenas uma instrucao por vez (encontrei mais de um ';')")

    if not re.match(r"^(select|with)\b", limpo, re.IGNORECASE):
        raise SqlInvalido("a consulta precisa comecar com SELECT ou WITH")

    proibida = _RE_PROIBIDAS.search(limpo)
    if proibida:
        raise SqlInvalido(
            f"a palavra '{proibida.group(0).upper()}' nao e permitida (somente leitura)"
        )

    if not re.search(r"\blimit\b", limpo, re.IGNORECASE):
        limpo = f"{limpo}\nLIMIT {LIMITE_PADRAO}"

    return limpo
