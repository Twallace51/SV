# Generic Main Menu Application

## Using modules:
PySide6

## Features:

shortcut to bypass login as 'admin' - right click + wheel move
logging configured and enabled
checks for pip and module dependencies
docstrings for all modules and functions
login window for admin, user, trainee
trainee session has light red background
git installed with project .gitignore file
__init__.py  for global variables,  example project version
single instance lock to avoid concurrent runs
terminal clear when app starts
initial test modules - see tests/README.md
in addition to admin and user users,  trainee to allow user input that is discarded when session closes
manually edited to add folding regions

Usage:

General

Making changes to menu_window menubar
Describe the menu structure directly — plain English works well, example

    Add a 'Tools' menu between 'Edit' and 'Help', with actions 'Run (Ctrl+R)' and 'Settings'

Database

import sqlite3
create a database with representative data,  add to folder
create menus in menubar for each table,  with actions for 'New' and 'Search'
create crud modules for each table with paged, filtered and sorted options
create reports for tables and add print preview, print direct, export to csv or excel
add validations for user input
set user permissions, example Delete()
