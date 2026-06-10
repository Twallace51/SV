"""Tests for alumnos dialogs."""

import sqlite3
from pathlib import Path

from __init__ import reset_active_db_path, set_active_db_path
from dialogs.alumnos import EditAlumnoDialog, NuevoAlumnoDialog


def _create_alumnos_dialog_database(path: Path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE grados (id INTEGER PRIMARY KEY, grado TEXT)")
        connection.execute(
            "CREATE TABLE adultos ("
            "id INTEGER PRIMARY KEY, a_nombres TEXT, a_paterno TEXT, a_materno TEXT)"
        )
        connection.execute(
            "CREATE TABLE alumnos ("
            "id INTEGER PRIMARY KEY, nombres TEXT, paterno TEXT, materno TEXT, "
            "cumpleanos TEXT, rude TEXT, Carnet TEXT, id_grado TEXT, pension REAL, "
            "id_padre TEXT, id_madre TEXT)"
        )

        connection.executemany(
            "INSERT INTO grados (id, grado) VALUES (?, ?)",
            [(1, "Primero"), (2, "Segundo")],
        )
        connection.executemany(
            "INSERT INTO adultos (id, a_nombres, a_paterno, a_materno) VALUES (?, ?, ?, ?)",
            [
                (10, "Pedro", "Lopez", "Diaz"),
                (20, "Marta", "Lopez", "Rios"),
                (30, "Juan", "Perez", "Quispe"),
                (40, "Ana", "Perez", "Mamani"),
            ],
        )
        connection.execute(
            "INSERT INTO alumnos (id, nombres, paterno, materno, cumpleanos, rude, Carnet, id_grado, pension, id_padre, id_madre) "
            "VALUES (1, 'Ana', 'Lopez', 'Rios', '2010-01-15', 'R-1', 'C-1', '1', 300, '10', '20')"
        )


def test_edit_alumno_shows_parent_lookups(qapp, tmp_path):
    database = tmp_path / "alumnos_dialog.db"
    _create_alumnos_dialog_database(database)
    set_active_db_path(database)
    try:
        dialog = EditAlumnoDialog(1)

        assert dialog.id_padre.text() == "10"
        assert dialog.padre_lookup.text() == "Pedro Lopez Diaz"
        assert dialog.id_madre.text() == "20"
        assert dialog.madre_lookup.text() == "Marta Lopez Rios"
    finally:
        reset_active_db_path()


def test_nuevo_alumno_shows_parent_lookup_and_pension_format(qapp, tmp_path):
    database = tmp_path / "alumnos_dialog_new_fields.db"
    _create_alumnos_dialog_database(database)
    set_active_db_path(database)
    try:
        dialog = NuevoAlumnoDialog()

        assert dialog.pension.text() == "0"

        dialog.id_padre.setText("10")
        dialog.id_madre.setText("20")

        assert dialog.padre_lookup.text() == "Pedro Lopez Diaz"
        assert dialog.madre_lookup.text() == "Marta Lopez Rios"
    finally:
        reset_active_db_path()


def test_nuevo_alumno_save_persists_parent_ids_and_integer_pension(qapp, tmp_path, monkeypatch):
    database = tmp_path / "alumnos_dialog_new_save.db"
    _create_alumnos_dialog_database(database)
    set_active_db_path(database)
    try:
        monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *args, **kwargs: None)

        dialog = NuevoAlumnoDialog()
        dialog.nombres.setText("Lia")
        dialog.paterno.setText("Mora")
        dialog.id_padre.setText("10")
        dialog.id_madre.setText("20")
        dialog.pension.setText("450")
        dialog._save()

        with sqlite3.connect(database) as connection:
            row = connection.execute(
                "SELECT nombres, paterno, pension, id_padre, id_madre FROM alumnos WHERE nombres = 'Lia' AND paterno = 'Mora'"
            ).fetchone()

        assert row == ("Lia", "Mora", 450.0, "10", "20")
    finally:
        reset_active_db_path()


def test_edit_alumno_save_updates_parent_ids(qapp, tmp_path, monkeypatch):
    database = tmp_path / "alumnos_dialog_save.db"
    _create_alumnos_dialog_database(database)
    set_active_db_path(database)
    try:
        monkeypatch.setattr("dialogs.alumnos.QMessageBox.information", lambda *args, **kwargs: None)

        dialog = EditAlumnoDialog(1)
        dialog.id_padre.setText("30")
        dialog.id_madre.setText("40")
        dialog._save()

        with sqlite3.connect(database) as connection:
            row = connection.execute(
                "SELECT id_padre, id_madre FROM alumnos WHERE id = 1"
            ).fetchone()

        assert row == ("30", "40")
        assert dialog.padre_lookup.text() == "Juan Perez Quispe"
        assert dialog.madre_lookup.text() == "Ana Perez Mamani"
    finally:
        reset_active_db_path()


def test_edit_alumno_pension_is_non_negative_integer_with_default_zero(qapp, tmp_path):
    database = tmp_path / "alumnos_dialog_pension.db"
    _create_alumnos_dialog_database(database)
    set_active_db_path(database)
    try:
        dialog = EditAlumnoDialog(1)

        assert dialog.pension.text() == "300"

        dialog.pension.setText("")
        dialog._save()

        with sqlite3.connect(database) as connection:
            pension = connection.execute(
                "SELECT pension FROM alumnos WHERE id = 1"
            ).fetchone()[0]

        assert pension == 0
        assert dialog.pension.text() == "0"
    finally:
        reset_active_db_path()
