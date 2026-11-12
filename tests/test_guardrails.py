"""Testes dos guardrails: o que pode e o que nao pode virar SQL executavel.

Rodar com:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from guardrails import SqlInvalido, limpar_comentarios, validar_sql  # noqa: E402


class TestValidarSql(unittest.TestCase):
    def test_select_simples_passa(self):
        sql = validar_sql("SELECT nome FROM clientes")
        self.assertTrue(sql.startswith("SELECT nome FROM clientes"))
        self.assertIn("LIMIT", sql.upper())

    def test_select_com_limit_nao_duplica(self):
        sql = validar_sql("SELECT nome FROM clientes LIMIT 5")
        self.assertEqual(sql.upper().count("LIMIT"), 1)

    def test_with_cte_passa(self):
        sql = validar_sql("WITH t AS (SELECT 1 AS x) SELECT * FROM t")
        self.assertIn("WITH", sql.upper())

    def test_delete_bloqueado(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("DELETE FROM clientes")

    def test_drop_bloqueado(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("SELECT 1; DROP TABLE clientes")

    def test_dois_comandos_bloqueados(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("SELECT 1; SELECT 2")

    def test_comentario_nao_esconde_comando(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("SELECT 1 -- comentario\n; DELETE FROM produtos")

    def test_comentario_de_bloco_removido(self):
        self.assertEqual(limpar_comentarios("SELECT /* oi */ 1").split(), ["SELECT", "1"])

    def test_pragma_bloqueado(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("PRAGMA table_info(clientes)")

    def test_vazio_bloqueado(self):
        with self.assertRaises(SqlInvalido):
            validar_sql("   ")

    def test_ponto_e_virgula_final_e_aceito(self):
        sql = validar_sql("SELECT 1;")
        self.assertFalse(sql.rstrip().endswith(";"))


if __name__ == "__main__":
    unittest.main()
