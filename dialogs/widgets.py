"""Shared custom widgets used by the dialog tables."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

# Dedicated role for an explicit numeric sort key. It is kept separate from
# Qt.UserRole so a cell can independently store unrelated data (such as a
# record id) under Qt.UserRole without affecting how the column sorts.
SORT_ROLE = Qt.ItemDataRole.UserRole + 1000


class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts numerically instead of alphabetically.

    Sorting prefers an explicit numeric key stored under ``SORT_ROLE`` when
    both items provide one; otherwise it interprets the visible text as an
    integer, and finally falls back to the default string comparison.
    """

    def __lt__(self, other):
        if isinstance(other, QTableWidgetItem):
            left_key = self.data(SORT_ROLE)
            right_key = other.data(SORT_ROLE)
            if left_key is not None and right_key is not None:
                try:
                    return int(left_key) < int(right_key)
                except (TypeError, ValueError):
                    return str(left_key) < str(right_key)
            try:
                return int(self.text()) < int(other.text())
            except (TypeError, ValueError):
                pass
        return super().__lt__(other)
