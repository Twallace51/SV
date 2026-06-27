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


def test_list_alumnos_para_whatsapp_only_pending_filters_negative_balance(tmp_path):
    db = tmp_path / "wa_pending.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, id_grado TEXT)"
        )
        conn.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        conn.execute(
            "CREATE TABLE ctas ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, id_alumno INTEGER, debito REAL, credito REAL, "
            "aclaracion TEXT, fecha TEXT, factura TEXT)"
        )
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
                (2, "Beto", "Perez", "", "2"),
                (3, "Celia", "Vega", "", "2"),
            ],
        )
        conn.executemany(
            "INSERT INTO ctas (id_alumno, debito, credito, aclaracion, fecha, factura) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 200, 50, "pension", "2026-06-01", ""),
                (2, 100, 100, "pension", "2026-06-01", ""),
                (3, 100, 200, "pension", "2026-06-01", ""),
            ],
        )

    set_active_db_path(db)
    try:
        rows = database.list_alumnos_para_whatsapp(only_pending=True)
        ids = [row[0] for row in rows]
        assert ids == [1]
    finally:
        reset_active_db_path()
