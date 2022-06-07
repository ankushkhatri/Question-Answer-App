
import sqlite3
from flask import g

# --------------------------------------------------------------------------
# Connecting to DB


def connect_db():
    sql = sqlite3.connect('D:/Flask/Q&A_App/questions.db')
    # The results will be returned as dictionaries instead of tuples
    sql.row_factory = sqlite3.Row
    return sql


def get_db():
    if not hasattr(g, 'sqlite3'):
        # it will if this object(sqlite_db) exists in their,
        g.sqlite_db = connect_db()
    # if it doesn't it will add it and connect to db and return results
    return g.sqlite_db

# --------------------------------------------------------------------------