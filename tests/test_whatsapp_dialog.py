"""Tests for WhatsApp dialog student-first template flow."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl

sys.path.insert(0, str(Path(__file__).parent.parent))
from dialogs.whatsapp import EnviarWhatsAppDialog


class TestEnviarWhatsAppDialogStudentFlow:
    def test_loads_linked_parents_for_selected_student(self, qapp, monkeypatch):
        monkeypatch.setattr(
            "dialogs.whatsapp.database.list_alumnos_para_whatsapp",
            lambda: [(1, "Lopez Ana Rios", "Primero")],
        )
        monkeypatch.setattr(
            "dialogs.whatsapp.database.get_whatsapp_targets_for_alumno",
            lambda alumno_id: (
                {
                    "student_name": "Lopez Ana Rios",
                    "grade": "Primero",
                    "balance": "+150",
                    "alumno_id": "1",
                    "date": "2026-06-27",
                },
                [
                    ("Perez Juan", "70123456"),
                    ("Perez Maria", "71112233"),
                ],
            ),
        )

        dlg = EnviarWhatsAppDialog()
        try:
            assert dlg.student_combo.count() == 1
            assert dlg.table.rowCount() == 2
            assert dlg.table.item(0, 1).text() == "Perez Juan"
            assert dlg.table.item(1, 1).text() == "Perez Maria"
        finally:
            dlg.close()

    def test_renders_placeholders_before_opening_chat(self, qapp, monkeypatch):
        monkeypatch.setattr(
            "dialogs.whatsapp.database.list_alumnos_para_whatsapp",
            lambda: [(1, "Lopez Ana Rios", "Primero")],
        )
        monkeypatch.setattr(
            "dialogs.whatsapp.database.get_whatsapp_targets_for_alumno",
            lambda alumno_id: (
                {
                    "student_name": "Lopez Ana Rios",
                    "grade": "Primero",
                    "balance": "+150",
                    "alumno_id": "1",
                    "date": "2026-06-27",
                },
                [("Perez Juan", "70123456")],
            ),
        )

        opened_urls = []

        def _open_url(url: QUrl):
            opened_urls.append(url.toString())
            return True

        monkeypatch.setattr("dialogs.whatsapp.QDesktopServices.openUrl", _open_url)

        dlg = EnviarWhatsAppDialog()
        try:
            dlg.message_edit.setPlainText(
                "Hola {parent_name}. Alumno: {student_name}. Grado: {grade}. "
                "Balance: {balance}. ID: {alumno_id}. Fecha: {date}."
            )

            dlg._open_next()

            assert len(opened_urls) == 1
            assert "Perez Juan" in opened_urls[0]
            assert "Lopez Ana Rios" in opened_urls[0]
            assert "Primero" in opened_urls[0]
            assert "%2B150" in opened_urls[0]
            assert "ID%3A 1" in opened_urls[0]
            assert "2026-06-27" in opened_urls[0]
        finally:
            dlg.close()

    def test_shows_empty_state_when_student_has_no_parent_phones(self, qapp, monkeypatch):
        monkeypatch.setattr(
            "dialogs.whatsapp.database.list_alumnos_para_whatsapp",
            lambda: [(1, "Lopez Ana Rios", "Primero")],
        )
        monkeypatch.setattr(
            "dialogs.whatsapp.database.get_whatsapp_targets_for_alumno",
            lambda alumno_id: (
                {
                    "student_name": "Lopez Ana Rios",
                    "grade": "Primero",
                    "balance": "+0",
                    "alumno_id": "1",
                    "date": "2026-06-27",
                },
                [],
            ),
        )

        dlg = EnviarWhatsAppDialog()
        try:
            assert dlg.table.rowCount() == 0
            assert "no tiene padres vinculados" in dlg.status_label.text().lower()
        finally:
            dlg.close()
