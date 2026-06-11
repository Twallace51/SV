"""Tests for alumnos dialogs: NuevoAlumnoDialog, EditAlumnoDialog."""

import sqlite3
from pathlib import Path

import pytest

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.alumnos import EditAlumnoDialog, NuevoAlumnoDialog


# ---------------------------------------------------------------------------
# Shared DB helpers
# ---------------------------------------------------------------------------

def _create_alumnos_db(path: Path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        conn.execute(
            "CREATE TABLE adultos "
            "(id INTEGER PRIMARY KEY, a_nombres TEXT, a_paterno TEXT, a_materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "cumpleanos TEXT, rude TEXT, Carnet TEXT, id_grado TEXT, pension REAL, "
            "id_padre TEXT, id_madre TEXT)"
        )
        conn.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)",
            [(1, "Primero"), (2, "Segundo")],
        )
        conn.executemany(
            "INSERT INTO adultos (id, a_nombres, a_paterno, a_materno) VALUES (?, ?, ?, ?)",
            [
                (10, "Pedro", "Lopez", "Diaz"),
                (20, "Marta", "Lopez", "Rios"),
                (30, "Juan",  "Perez", "Quispe"),
                (40, "Ana",   "Perez", "Mamani"),
            ],
        )
        conn.execute(
            "INSERT INTO alumnos "
            "(id, nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension, id_padre, id_madre) "
            "VALUES (1, 'Ana', 'Lopez', 'Rios', '2010-01-15', 'R-1', 'C-1', '1', 300, '10', '20')"
        )


def _create_duplicate_alumnos_db(path: Path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        conn.execute(
            "CREATE TABLE adultos "
            "(id INTEGER PRIMARY KEY, a_nombres TEXT, a_paterno TEXT, a_materno TEXT)"
        )
        conn.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "cumpleanos TEXT, rude TEXT, Carnet TEXT, id_grado TEXT, pension REAL, "
            "id_padre TEXT, id_madre TEXT)"
        )
        conn.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)", [(1, "Primero")]
        )
        conn.execute(
            "INSERT INTO adultos (id, a_nombres, a_paterno, a_materno) "
            "VALUES (10, 'Pedro', 'Lopez', 'Diaz')"
        )
        conn.executemany(
            "INSERT INTO alumnos "
            "(id, nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension, id_padre, id_madre) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "Ana",  "Lopez", "Rios", "2010-01-15", "R-1", "C-1", "1", 300, "10", None),
                (2, "Beto", "Perez", "Vega", "2011-02-20", "R-2", "C-2", "1", 200, "10", None),
            ],
        )


# ---------------------------------------------------------------------------
# EditAlumnoDialog – parent lookups
# ---------------------------------------------------------------------------

class TestEditAlumnoParentLookups:
    def test_shows_padre_lookup_name(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = EditAlumnoDialog(1)
            assert dlg.id_padre.text() == "10"
            assert dlg.padre_lookup.text() == "Pedro Lopez Diaz"
        finally:
            reset_active_db_path()

    def test_shows_madre_lookup_name(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = EditAlumnoDialog(1)
            assert dlg.id_madre.text() == "20"
            assert dlg.madre_lookup.text() == "Marta Lopez Rios"
        finally:
            reset_active_db_path()

    def test_save_updates_parent_ids(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = EditAlumnoDialog(1)
            dlg.id_padre.setText("30")
            dlg.id_madre.setText("40")
            dlg._save()

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT id_padre, id_madre FROM alumnos WHERE id = 1"
                ).fetchone()
            assert row == ("30", "40")
            assert dlg.padre_lookup.text() == "Juan Perez Quispe"
            assert dlg.madre_lookup.text() == "Ana Perez Mamani"
        finally:
            reset_active_db_path()

    def test_save_allows_keeping_same_rude_and_carnet(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "dup.db"
        _create_duplicate_alumnos_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = EditAlumnoDialog(1)
            dlg._save()

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT rude, Carnet FROM alumnos WHERE id = 1"
                ).fetchone()
            assert row == ("R-1", "C-1")
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# EditAlumnoDialog – pension field
# ---------------------------------------------------------------------------

class TestEditAlumnoPension:
    def test_pension_loaded_correctly(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = EditAlumnoDialog(1)
            assert dlg.pension.text() == "300"
        finally:
            reset_active_db_path()

    def test_empty_pension_defaults_to_zero_on_save(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = EditAlumnoDialog(1)
            dlg.pension.setText("")
            dlg._save()

            with sqlite3.connect(db) as conn:
                pension = conn.execute(
                    "SELECT pension FROM alumnos WHERE id = 1"
                ).fetchone()[0]
            assert pension == 0
            assert dlg.pension.text() == "0"
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# NuevoAlumnoDialog – parent lookups and pension format
# ---------------------------------------------------------------------------

class TestNuevoAlumnoParentLookup:
    def test_pension_starts_at_zero(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoAlumnoDialog()
            assert dlg.pension.text() == "0"
        finally:
            reset_active_db_path()

    def test_padre_lookup_syncs_on_id_entry(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoAlumnoDialog()
            dlg.id_padre.setText("10")
            assert dlg.padre_lookup.text() == "Pedro Lopez Diaz"
        finally:
            reset_active_db_path()

    def test_madre_lookup_syncs_on_id_entry(self, qapp, tmp_path):
        db = tmp_path / "alumnos.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            dlg = NuevoAlumnoDialog()
            dlg.id_madre.setText("20")
            assert dlg.madre_lookup.text() == "Marta Lopez Rios"
        finally:
            reset_active_db_path()


# ---------------------------------------------------------------------------
# NuevoAlumnoDialog – save validation and persistence
# ---------------------------------------------------------------------------

class TestNuevoAlumnoSave:
    def test_save_persists_parent_ids_and_pension(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "save.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = NuevoAlumnoDialog()
            dlg.nombres.setText("Lia")
            dlg.paterno.setText("Mora")
            dlg.id_padre.setText("10")
            dlg.id_madre.setText("20")
            dlg.pension.setText("450")
            dlg._save()

            with sqlite3.connect(db) as conn:
                row = conn.execute(
                    "SELECT nombres, paterno, pension, id_padre, id_madre "
                    "FROM alumnos WHERE nombres = 'Lia' AND paterno = 'Mora'"
                ).fetchone()
            assert row == ("Lia", "Mora", 450.0, "10", "20")
        finally:
            reset_active_db_path()

    def test_save_rejects_missing_parent_id(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "bad_parent.db"
        _create_alumnos_db(db)
        set_active_db_path(db)
        try:
            warnings = []
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.warning", lambda *a: warnings.append(a))
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = NuevoAlumnoDialog()
            dlg.nombres.setText("Lia")
            dlg.paterno.setText("Mora")
            dlg.id_padre.setText("999")
            dlg.id_madre.setText("20")
            dlg._save()

            with sqlite3.connect(db) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM alumnos WHERE nombres = 'Lia'"
                ).fetchone()[0]
            assert count == 0
            assert warnings
            assert "ID de padre no existe" in warnings[0][2]
        finally:
            reset_active_db_path()

    def test_save_rejects_duplicate_rude_and_carnet(self, qapp, tmp_path, monkeypatch):
        db = tmp_path / "dup.db"
        _create_duplicate_alumnos_db(db)
        set_active_db_path(db)
        try:
            warnings = []
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.warning", lambda *a: warnings.append(a))
            monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *a, **kw: None)
            dlg = NuevoAlumnoDialog()
            dlg.nombres.setText("Lia")
            dlg.paterno.setText("Mora")
            dlg.rude.setText("R-1")
            dlg.carnet.setText("C-1")
            dlg.id_padre.setText("10")
            dlg._save()

            with sqlite3.connect(db) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM alumnos WHERE nombres = 'Lia'"
                ).fetchone()[0]
            assert count == 0
            assert warnings
            warning_text = warnings[0][2]
            assert "RUDE ya existe" in warning_text
            assert "Carnet ya existe" in warning_text
        finally:
            reset_active_db_path()

