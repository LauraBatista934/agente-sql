"""Agente SQL: pergunte em portugues, receba a resposta do banco.

Exemplos:
    python agent.py "Quais foram os 5 clientes que mais gastaram?"
    python agent.py "Receita por categoria, sem pedidos cancelados" --mostrar-sql
    python agent.py --schema
"""

from __future__ import annotations

import argparse
import sys

import database
import guardrails
import llm


def configurar_saida() -> None:
    """Evita erro de acento no terminal do Windows."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def formatar_tabela(colunas: list[str], linhas: list[tuple]) -> str:
    if not colunas:
        return "(a consulta nao retornou colunas)"

    def texto(valor) -> str:
        if valor is None:
            return "NULL"
        if isinstance(valor, float):
            return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(valor)

    corpo = [[texto(v) for v in linha] for linha in linhas]
    larguras = [
        max(len(colunas[i]), *(len(linha[i]) for linha in corpo)) if corpo else len(colunas[i])
        for i in range(len(colunas))
    ]

    def linha(valores: list[str]) -> str:
        return " | ".join(v.ljust(larguras[i]) for i, v in enumerate(valores))

    separador = "-+-".join("-" * w for w in larguras)
    partes = [linha(colunas), separador] + [linha(l) for l in corpo]
    if len(linhas) >= database.MAX_ROWS:
        partes.append(f"... limite de {database.MAX_ROWS} linhas atingido")
    return "\n".join(partes)


def main() -> int:
    configurar_saida()

    parser = argparse.ArgumentParser(description="Pergunte em portugues, receba SQL e o resultado.")
    parser.add_argument("pergunta", nargs="*", help="a pergunta em linguagem natural")
    parser.add_argument("--schema", action="store_true", help="mostra o schema do banco e sai")
    parser.add_argument("--mostrar-sql", action="store_true", help="mostra o SQL gerado")
    parser.add_argument("--nao-executar", action="store_true", help="gera o SQL mas nao roda")
    args = parser.parse_args()

    if args.schema:
        print(database.get_schema())
        return 0

    pergunta = " ".join(args.pergunta).strip()
    if not pergunta:
        parser.print_help()
        return 1

    print(f"Pergunta: {pergunta}\n")

    try:
        schema = database.get_schema()
        amostra = database.get_sample_rows()
    except database.DatabaseError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    try:
        resposta = llm.gerar_sql(pergunta, schema, amostra)
    except llm.LLMError as exc:
        print(f"Erro ao consultar o Gemini: {exc}", file=sys.stderr)
        return 1

    sql_bruto = resposta["sql"]
    if not sql_bruto:
        print(f"Nao consegui responder: {resposta['explicacao']}")
        return 2

    if resposta["explicacao"]:
        print(f"Explicacao: {resposta['explicacao']}\n")

    try:
        sql = guardrails.validar_sql(sql_bruto)
    except guardrails.SqlInvalido as exc:
        print(f"SQL bloqueado pelos guardrails: {exc}", file=sys.stderr)
        print(f"\nSQL sugerido pelo modelo:\n{sql_bruto}", file=sys.stderr)
        return 3

    if args.mostrar_sql or args.nao_executar:
        print(f"SQL:\n{sql}\n")

    if args.nao_executar:
        return 0

    try:
        colunas, linhas = database.run_query(sql)
    except database.DatabaseError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        print(f"\nSQL executado:\n{sql}", file=sys.stderr)
        return 4

    print(formatar_tabela(colunas, linhas))
    print(f"\n{len(linhas)} linha(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
