"""Central place for application constants and tunable values.

Keeping these literals in one module makes them easy to find and change
without hunting through the UI code.
"""

# --- Authentication -------------------------------------------------------

# Built-in demo credentials. Replace with real authentication when available.
LOGIN_CREDENTIALS = {
    "admin": "admin",
    "user": "user",
    "trainee": "trainee",
}

# --- Session behaviour ----------------------------------------------------

# Automatically log the user out after this much inactivity (milliseconds).
INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000

# --- Cuentas (accounts) ---------------------------------------------------

# Preset "Aclaración" options offered for debit and credit movements.
DEBITO_ACLARACIONES = ["Pension", "Comedor", "Insumos"]
CREDITO_ACLARACIONES = ["Efectivo", "Deposito"]

# --- Monthly pension automation -------------------------------------------

# Spanish month names, indexed 0 (enero) .. 11 (diciembre).
MONTH_NAMES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Monthly pension charges are generated for months in this inclusive range
# (February through November).
PENSION_FIRST_MONTH = 2
PENSION_LAST_MONTH = 11
