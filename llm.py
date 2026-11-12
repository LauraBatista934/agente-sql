"""Conversa com o Gemini: transforma a pergunta em SQL.

Usa apenas a biblioteca padrao (urllib), sem SDK, para o projeto rodar
com `python agent.py` sem instalar nada.

Variaveis de ambiente (ou arquivo .env):
    GEMINI_API_KEY  obrigatoria
    GEMINI_MODEL    opcional (padrao: gemini-2.5-flash)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

MODELO_PADRAO = "gemini-2.5-flash"

SYSTEM_PROMPT = """Voce e um assistente que traduz perguntas em portugues para SQL.
Responda SEMPRE com um objeto JSON valido, sem texto fora do JSON, no formato:

{"sql": "SELECT ...", "explicacao": "uma ou duas frases explicando o que a consulta faz"}

Regras obrigatorias:
- use apenas SELECT (ou WITH ... SELECT). Nunca INSERT, UPDATE, DELETE, DROP, PRAGMA ou CREATE;
- use exclusivamente as tabelas e colunas do schema informado;
- use o dialeto SQLite;
- para agrupamentos e ordenacoes, use apelidos claros em portugues;
- se a pergunta nao puder ser respondida com o schema, devolva
  {"sql": "", "explicacao": "explicando o que falta"}.
"""


class LLMError(RuntimeError):
    """Falha ao falar com a API ou ao interpretar a resposta."""


def carregar_env() -> None:
    """Le .env (se existir) e injeta no ambiente, sem sobrescrever o que ja existe."""
    if not ENV_PATH.exists():
        return
    for linha in ENV_PATH.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def _extrair_json(texto: str) -> dict:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio == -1 or fim == -1:
        raise LLMError(f"a resposta nao veio em JSON: {texto[:200]}")
    try:
        return json.loads(texto[inicio : fim + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"JSON invalido na resposta: {exc}") from exc


def gerar_sql(pergunta: str, schema: str, amostra: str = "") -> dict:
    """Devolve {'sql': str, 'explicacao': str}."""
    carregar_env()

    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        raise LLMError(
            "GEMINI_API_KEY nao definida. Copie .env.example para .env e cole sua chave "
            "(https://aistudio.google.com/apikey)."
        )

    modelo = os.environ.get("GEMINI_MODEL", MODELO_PADRAO).strip() or MODELO_PADRAO

    prompt = (
        f"Schema do banco:\n{schema}\n\n"
        + (f"Exemplos de linhas:\n{amostra}\n\n" if amostra else "")
        + f"Pergunta do usuario:\n{pergunta}"
    )

    corpo = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    requisicao = urllib.request.Request(
        ENDPOINT.format(model=modelo) + f"?key={chave}",
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=60) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")[:400]
        raise LLMError(f"a API respondeu {exc.code}: {detalhe}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"nao consegui conectar na API: {exc.reason}") from exc

    try:
        texto = dados["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"resposta inesperada da API: {str(dados)[:300]}") from exc

    resultado = _extrair_json(texto)
    return {
        "sql": str(resultado.get("sql", "")).strip(),
        "explicacao": str(resultado.get("explicacao", "")).strip(),
    }
