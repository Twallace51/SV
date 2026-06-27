"""Database tests for WhatsApp student selection filters."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from __init__ import reset_active_db_path, set_active_db_path
from modules import database


def test_list_alumnos_para_whatsapp_only_returns_valid_id_grado(tmp_path):
    db = tmp_path / "wa.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, id_grado TEXT)"
        )
        conn.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        conn.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)",
            [
                (1, "Primero"),
                (2, "Segundo"),
            ],
        )
        conn.executemany(
            "INSERT INTO alumnos (id, nombres, paterno, materno, id_grado) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "Ana", "Lopez", "Rios", "1"),
                (2, "Beto", "Perez", "", "0"),
                (3, "Celia", "Vega", "Mora", ""),
                (4, "Dario", "Mendez", "", None),
                (5, "Elena", "Flores", "", "none"),
                (6, "Fabio", "Quispe", "", "null"),
                (7, "Gina", "Arce", "", "2"),
            ],
        )

    set_active_db_path(db)
    try:
        rows = database.list_alumnos_para_whatsapp()
        ids = [row[0] for row in rows]
        assert ids == [1, 7]
    finally:
        reset_active_db_path()
