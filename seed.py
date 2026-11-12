"""Cria o banco de exemplo (SQLite) usado pelo agente.

Uso:
    python seed.py

Gera o arquivo data/loja.db com quatro tabelas: clientes, produtos,
pedidos e itens_pedido. Os dados sao ficticios, criados apenas para
servir de base para as perguntas em linguagem natural.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "loja.db"

SCHEMA = """
CREATE TABLE clientes (
    id            INTEGER PRIMARY KEY,
    nome          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    cidade        TEXT NOT NULL,
    estado        TEXT NOT NULL,
    data_cadastro TEXT NOT NULL
);

CREATE TABLE produtos (
    id        INTEGER PRIMARY KEY,
    nome      TEXT NOT NULL,
    categoria TEXT NOT NULL,
    preco     REAL NOT NULL,
    estoque   INTEGER NOT NULL
);

CREATE TABLE pedidos (
    id          INTEGER PRIMARY KEY,
    cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
    data_pedido TEXT NOT NULL,
    status      TEXT NOT NULL,
    canal       TEXT NOT NULL
);

CREATE TABLE itens_pedido (
    id             INTEGER PRIMARY KEY,
    pedido_id      INTEGER NOT NULL REFERENCES pedidos(id),
    produto_id     INTEGER NOT NULL REFERENCES produtos(id),
    quantidade     INTEGER NOT NULL,
    preco_unitario REAL NOT NULL
);
"""

CLIENTES = [
    ("Ana Souza", "ana.souza@exemplo.com", "Porto Alegre", "RS", "2025-03-11"),
    ("Bruno Lima", "bruno.lima@exemplo.com", "Sao Paulo", "SP", "2025-05-02"),
    ("Carla Menezes", "carla.menezes@exemplo.com", "Curitiba", "PR", "2025-06-19"),
    ("Diego Rocha", "diego.rocha@exemplo.com", "Porto Alegre", "RS", "2025-07-08"),
    ("Elisa Prado", "elisa.prado@exemplo.com", "Belo Horizonte", "MG", "2025-09-23"),
    ("Felipe Nunes", "felipe.nunes@exemplo.com", "Recife", "PE", "2026-01-14"),
    ("Gabriela Dias", "gabriela.dias@exemplo.com", "Porto Alegre", "RS", "2026-02-06"),
    ("Henrique Alves", "henrique.alves@exemplo.com", "Sao Paulo", "SP", "2026-03-30"),
    ("Isabela Castro", "isabela.castro@exemplo.com", "Florianopolis", "SC", "2026-05-17"),
    ("Joao Pedro Ramos", "joao.ramos@exemplo.com", "Curitiba", "PR", "2026-08-01"),
]

PRODUTOS = [
    ("Teclado Mecanico", "Perifericos", 349.90, 42),
    ("Mouse Sem Fio", "Perifericos", 129.90, 120),
    ("Monitor 27 Polegadas", "Monitores", 1499.00, 18),
    ("Headset Gamer", "Audio", 289.50, 55),
    ("Cadeira Ergonomica", "Moveis", 1890.00, 9),
    ("Webcam Full HD", "Perifericos", 219.00, 33),
    ("Hub USB-C", "Acessorios", 159.90, 80),
    ("Suporte para Notebook", "Acessorios", 89.90, 64),
]

STATUS = ["entregue", "entregue", "entregue", "enviado", "pendente", "cancelado"]
CANAIS = ["site", "site", "app", "loja"]


def build_rows():
    """Monta pedidos e itens de forma deterministica (sem random)."""
    pedidos = []
    itens = []
    inicio = date(2026, 1, 6)
    pedido_id = 1
    item_id = 1

    for n in range(24):
        cliente_id = (n * 3) % len(CLIENTES) + 1
        data_pedido = inicio + timedelta(days=n * 11 + (n % 5))
        status = STATUS[n % len(STATUS)]
        canal = CANAIS[n % len(CANAIS)]
        pedidos.append((pedido_id, cliente_id, data_pedido.isoformat(), status, canal))

        for k in range(n % 3 + 1):
            produto = PRODUTOS[(n + k) % len(PRODUTOS)]
            quantidade = (n + k) % 3 + 1
            itens.append((item_id, pedido_id, (n + k) % len(PRODUTOS) + 1, quantidade, produto[2]))
            item_id += 1

        pedido_id += 1

    return pedidos, itens


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    pedidos, itens = build_rows()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO clientes (nome, email, cidade, estado, data_cadastro) VALUES (?, ?, ?, ?, ?)",
            CLIENTES,
        )
        conn.executemany(
            "INSERT INTO produtos (nome, categoria, preco, estoque) VALUES (?, ?, ?, ?)",
            PRODUTOS,
        )
        conn.executemany(
            "INSERT INTO pedidos (id, cliente_id, data_pedido, status, canal) VALUES (?, ?, ?, ?, ?)",
            pedidos,
        )
        conn.executemany(
            "INSERT INTO itens_pedido (id, pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?, ?)",
            itens,
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Banco criado em: {DB_PATH}")
    print(f"  clientes .... {len(CLIENTES)} linhas")
    print(f"  produtos .... {len(PRODUTOS)} linhas")
    print(f"  pedidos ..... {len(pedidos)} linhas")
    print(f"  itens_pedido  {len(itens)} linhas")


if __name__ == "__main__":
    main()
