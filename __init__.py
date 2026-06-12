"""Package metadata for this application."""

from pathlib import Path

PROJECT_NAME = "Sendas de Vida Menu"
VERSION = "1.3"

DB_PATH = Path(__file__).parent / "SV-1.3.db"
_ACTIVE_DB_PATH = DB_PATH


def get_active_db_path() -> Path:
	"""Return the database path currently active for this app session."""
	return _ACTIVE_DB_PATH


def set_active_db_path(path: Path) -> None:
	"""Set the database path to use for subsequent DB operations."""
	global _ACTIVE_DB_PATH
	_ACTIVE_DB_PATH = Path(path)


def reset_active_db_path() -> None:
	"""Reset database path selection back to the default production DB."""
	global _ACTIVE_DB_PATH
	_ACTIVE_DB_PATH = DB_PATH
