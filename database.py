"""Data-access layer.

All SQLite access for the application lives here so the dialog code can stay
focused on the user interface. Each function opens a short-lived connection to
the database that is currently active for the session (see
``get_active_db_path``).

Read helpers swallow database errors and return a sensible empty default,
mirroring the resilient "best effort" behaviour the dialogs relied on before.
Write helpers (insert/update/delete) let exceptions propagate so the calling
dialog can show an error message to the user.
"""

import sqlite3

from __init__ import get_active_db_path


# --- Connection helpers ---------------------------------------------------

def connect() -> sqlite3.Connection:
    """Open a connection to the currently active database."""
    return sqlite3.connect(get_active_db_path())


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the set of column names for ``table``."""
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _table_names(conn: sqlite3.Connection) -> set[str]:
    """Return the set of table names defined in the database."""
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


# --- Grados ---------------------------------------------------------------

def list_grados() -> list[tuple]:
    """Return ``(id, grado)`` rows ordered by grade name."""
    try:
        conn = connect()
        try:
            return conn.execute(
                "SELECT id, grado FROM grados ORDER BY grado"
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return []


# --- Adultos (parientes) lookups ------------------------------------------

def fetch_adulto_lookup_name(adulto_id: int) -> tuple | None:
    """Return ``(a_nombres, a_paterno, a_materno)`` for an adulto, or None."""
    try:
        with connect() as conn:
            return conn.execute(
                "SELECT a_nombres, a_paterno, a_materno FROM adultos WHERE id = ?",
                (adulto_id,),
            ).fetchone()
    except Exception:
        return None


def fetch_adulto_name_pair(adulto_id: int) -> tuple | None:
    """Return ``(a_nombres, a_paterno)`` for an adulto, or None."""
    try:
        conn = connect()
        try:
            return conn.execute(
                "SELECT a_nombres, a_paterno FROM adultos WHERE id = ?",
                (adulto_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None


def adulto_exists(conn: sqlite3.Connection, adulto_id: int) -> bool:
    """Return True when an adulto with ``adulto_id`` exists."""
    return conn.execute(
        "SELECT 1 FROM adultos WHERE id = ?", (adulto_id,)
    ).fetchone() is not None


# --- Adultos (parientes) CRUD ---------------------------------------------

_ADULTO_FORM_COLUMNS = (
    "a_nombres", "a_paterno", "a_materno",
    "cell1", "cell2", "email", "a_carnet", "NIT",
)


def fetch_adulto(record_id: int) -> tuple | None:
    """Return the editable adulto columns for ``record_id``, or None."""
    try:
        conn = connect()
        try:
            return conn.execute(
                f"SELECT {', '.join(_ADULTO_FORM_COLUMNS)} FROM adultos WHERE id = ?",
                (record_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None


def insert_adulto(values: tuple) -> int:
    """Insert a new adulto and return its new row id."""
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO adultos (a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_adulto(record_id: int, values: tuple) -> None:
    """Update an existing adulto. ``values`` matches the insert column order."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE adultos SET a_nombres=?, a_paterno=?, a_materno=?,"
            " cell1=?, cell2=?, email=?, a_carnet=?, NIT=? WHERE id=?",
            (*values, record_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_adulto(record_id: int) -> None:
    """Delete an adulto by id."""
    conn = connect()
    try:
        conn.execute("DELETE FROM adultos WHERE id = ?", (record_id,))
        conn.commit()
    finally:
        conn.close()


def search_adultos(text: str) -> list[tuple]:
    """Search adultos by name/surname; returns full display rows."""
    like = f"%{text}%"
    try:
        conn = connect()
        try:
            return conn.execute(
                "SELECT id, a_nombres, a_paterno, a_materno, cell1, cell2, email, a_carnet, NIT"
                " FROM adultos"
                " WHERE a_nombres LIKE ? OR a_paterno LIKE ? OR a_materno LIKE ?"
                " ORDER BY a_paterno, a_nombres",
                (like, like, like),
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return []


# --- Alumnos lookups ------------------------------------------------------

def fetch_alumno_name_pair(alumno_id: int) -> tuple | None:
    """Return ``(paterno, nombres)`` for an alumno, or None."""
    try:
        conn = connect()
        try:
            return conn.execute(
                "SELECT paterno, nombres FROM alumnos WHERE id = ?",
                (alumno_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None


def validate_alumno(rude: str, carnet: str, id_padre, id_madre, current_id=None) -> list[str]:
    """Return a list of validation errors for related adults and unique fields.

    Checks that ``id_padre``/``id_madre`` reference existing adultos and that
    RUDE/Carnet are not already used by another alumno.
    """
    errors: list[str] = []
    conn = connect()
    try:
        for label, related_id in (("padre", id_padre), ("madre", id_madre)):
            if related_id is None:
                continue
            if not adulto_exists(conn, related_id):
                errors.append(f"El ID de {label} no existe en adultos.")

        for label, value, column_name in (
            ("RUDE", rude, "rude"),
            ("Carnet", carnet, "Carnet"),
        ):
            if not value:
                continue
            params = [value]
            query = f"SELECT 1 FROM alumnos WHERE {column_name} = ?"
            if current_id is not None:
                query += " AND id <> ?"
                params.append(current_id)
            if conn.execute(query, tuple(params)).fetchone():
                errors.append(f"{label} ya existe en otro alumno.")
    finally:
        conn.close()
    return errors


# --- Alumnos CRUD ---------------------------------------------------------

# Columns that always exist on the alumnos table.
_ALUMNO_BASE_COLUMNS = (
    "nombres", "paterno", "materno", "cumpleanos", "rude", "Carnet", "id_grado", "pension",
)


def fetch_alumno(record_id: int) -> dict | None:
    """Return an alumno as a column->value dict, or None if not found.

    Optional columns ``id_padre`` / ``id_madre`` are included only when the
    table actually defines them.
    """
    try:
        conn = connect()
        try:
            columns = table_columns(conn, "alumnos")
            select_columns = list(_ALUMNO_BASE_COLUMNS)
            if "id_padre" in columns:
                select_columns.append("id_padre")
            if "id_madre" in columns:
                select_columns.append("id_madre")
            row = conn.execute(
                f"SELECT {', '.join(select_columns)} FROM alumnos WHERE id = ?",
                (record_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None

    if row is None:
        return None
    return dict(zip(select_columns, row))


def _alumno_optional_columns(conn: sqlite3.Connection) -> tuple[bool, bool]:
    """Return whether the alumnos table has id_padre / id_madre columns."""
    columns = table_columns(conn, "alumnos")
    return "id_padre" in columns, "id_madre" in columns


def insert_alumno(data: dict) -> int:
    """Insert a new alumno from a field dict; returns the new row id.

    ``data`` may include ``id_padre`` / ``id_madre`` which are persisted only
    when those columns exist on the table.
    """
    conn = connect()
    try:
        has_id_padre, has_id_madre = _alumno_optional_columns(conn)
        fields = list(_ALUMNO_BASE_COLUMNS)
        values = [data[col] for col in _ALUMNO_BASE_COLUMNS]
        if has_id_padre:
            fields.append("id_padre")
            values.append(data.get("id_padre"))
        if has_id_madre:
            fields.append("id_madre")
            values.append(data.get("id_madre"))

        placeholders = ", ".join("?" for _ in fields)
        cur = conn.execute(
            f"INSERT INTO alumnos ({', '.join(fields)}) VALUES ({placeholders})",
            tuple(values),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_alumno(record_id: int, data: dict) -> None:
    """Update an existing alumno from a field dict."""
    conn = connect()
    try:
        has_id_padre, has_id_madre = _alumno_optional_columns(conn)
        fields = list(_ALUMNO_BASE_COLUMNS)
        values = [data[col] for col in _ALUMNO_BASE_COLUMNS]
        if has_id_padre:
            fields.append("id_padre")
            values.append(data.get("id_padre"))
        if has_id_madre:
            fields.append("id_madre")
            values.append(data.get("id_madre"))

        assignments = ", ".join(f"{field}=?" for field in fields)
        conn.execute(
            f"UPDATE alumnos SET {assignments} WHERE id=?",
            (*values, record_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_alumno(record_id: int) -> None:
    """Delete an alumno by id."""
    conn = connect()
    try:
        conn.execute("DELETE FROM alumnos WHERE id = ?", (record_id,))
        conn.commit()
    finally:
        conn.close()


def search_alumnos(text: str, only_inscritos: bool) -> list[tuple]:
    """Search alumnos, optionally limited to those with a real grade.

    Returns rows of ``(id, nombres, paterno, materno, rude, Carnet, grado,
    pension, id_grado)`` ordered by surname then name.
    """
    like = f"%{text}%"
    try:
        conn = connect()
        try:
            query = (
                "SELECT a.id, a.nombres, a.paterno, a.materno, a.rude, a.Carnet,"
                " g.grado, a.pension, a.id_grado"
                " FROM alumnos a"
                " LEFT JOIN grados g ON g.id = CASE"
                "   WHEN a.id_grado IS NULL THEN NULL"
                "   WHEN TRIM(CAST(a.id_grado AS TEXT)) = '' THEN NULL"
                "   WHEN LOWER(TRIM(CAST(a.id_grado AS TEXT))) IN ('null', 'none') THEN NULL"
                "   ELSE CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER)"
                " END"
                " WHERE (a.nombres LIKE ? OR a.paterno LIKE ? OR a.materno LIKE ?)"
            )
            params = [like, like, like]
            if only_inscritos:
                query += (
                    " AND a.id_grado IS NOT NULL"
                    " AND TRIM(CAST(a.id_grado AS TEXT)) <> ''"
                    " AND LOWER(TRIM(CAST(a.id_grado AS TEXT))) NOT IN ('null', 'none')"
                    " AND CAST(TRIM(CAST(a.id_grado AS TEXT)) AS INTEGER) > 0"
                )
            query += " ORDER BY a.paterno, a.nombres"
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()
    except Exception:
        return []


# --- Cuentas (accounts) CRUD ----------------------------------------------

def fetch_cuenta(record_id: int) -> tuple | None:
    """Return ``(id_alumno, id_creditor, debito, credito, aclaracion, fecha,
    factura)`` for a cuenta, or None."""
    try:
        conn = connect()
        try:
            return conn.execute(
                "SELECT id_alumno, id_creditor, debito, credito, aclaracion, fecha, factura"
                " FROM ctas WHERE id = ?",
                (record_id,),
            ).fetchone()
        finally:
            conn.close()
    except Exception:
        return None


def insert_cuenta(values: tuple) -> int:
    """Insert a new cuenta; ``values`` is (id_alumno, id_creditor, debito,
    credito, aclaracion, fecha, factura). Returns the new row id."""
    conn = connect()
    try:
        cur = conn.execute(
            "INSERT INTO ctas (id_alumno, id_creditor, debito, credito, aclaracion, fecha, factura)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_cuenta(record_id: int, values: tuple) -> None:
    """Update a cuenta. ``values`` matches the insert column order."""
    conn = connect()
    try:
        conn.execute(
            "UPDATE ctas SET id_alumno=?, id_creditor=?, debito=?, credito=?, aclaracion=?,"
            " fecha=?, factura=? WHERE id=?",
            (*values, record_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_cuenta(record_id: int) -> None:
    """Delete a cuenta by id."""
    conn = connect()
    try:
        conn.execute("DELETE FROM ctas WHERE id = ?", (record_id,))
        conn.commit()
    finally:
        conn.close()


def search_cuentas(alumno_search: str, creditor_search: str) -> list[tuple]:
    """Search cuentas joined to alumnos (and adultos when available).

    Returns rows of ``(cuenta_id, alumno_id, alumno_name, creditor_id,
    creditor_name, debito, credito, aclaracion, fecha, factura)``.
    """
    alumno_like = f"%{alumno_search}%"
    creditor_like = f"%{creditor_search}%"
    try:
        conn = connect()
        try:
            ctas_columns = table_columns(conn, "ctas")
            creditor_id_expr = "c.id_creditor" if "id_creditor" in ctas_columns else "NULL"
            tables = _table_names(conn)

            creditor_name_expr = "''"
            creditor_join = ""
            has_creditor_name = False
            if "adultos" in tables:
                adulto_columns = table_columns(conn, "adultos")
                name_parts = []
                if "a_paterno" in adulto_columns:
                    name_parts.append("COALESCE(ad.a_paterno, '')")
                if "a_nombres" in adulto_columns:
                    name_parts.append("COALESCE(ad.a_nombres, '')")
                if "a_materno" in adulto_columns:
                    name_parts.append("COALESCE(ad.a_materno, '')")
                if name_parts:
                    creditor_name_expr = "TRIM(" + " || ' ' || ".join(name_parts) + ")"
                    has_creditor_name = True
                creditor_join = (
                    f" LEFT JOIN adultos ad ON ad.id = CAST({creditor_id_expr} AS INTEGER)"
                )

            where_clauses = [
                "(CAST(a.id AS TEXT) LIKE ? OR a.nombres LIKE ? OR a.paterno LIKE ?)"
            ]
            params = [alumno_search, alumno_like, alumno_like]

            if creditor_search:
                creditor_filters = []
                if "id_creditor" in ctas_columns:
                    creditor_filters.append("CAST(c.id_creditor AS TEXT) LIKE ?")
                    params.append(creditor_search)
                if has_creditor_name:
                    creditor_filters.append(f"{creditor_name_expr} LIKE ?")
                    params.append(creditor_like)
                if creditor_filters:
                    where_clauses.append("(" + " OR ".join(creditor_filters) + ")")
                else:
                    where_clauses.append("1 = 0")

            return conn.execute(
                "SELECT c.id, a.id, a.paterno || ', ' || a.nombres,"
                f" {creditor_id_expr}, {creditor_name_expr},"
                " c.debito, c.credito, c.aclaracion, c.fecha, c.factura"
                " FROM ctas c JOIN alumnos a ON c.id_alumno = a.id"
                f"{creditor_join}"
                f" WHERE {' AND '.join(where_clauses)}"
                " ORDER BY c.fecha DESC",
                params,
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return []
