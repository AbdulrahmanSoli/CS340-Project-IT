import psycopg2
import os
from dotenv import load_dotenv
from flask import g, has_app_context

load_dotenv()

def get_connection():
    """Open a fresh connection. Use this from scripts and migrations."""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def _conn():
    """Per-request connection inside Flask, fresh otherwise."""
    if has_app_context():
        if 'db' not in g:
            g.db = psycopg2.connect(os.getenv('DATABASE_URL'))
        return g.db
    return get_connection()

def close_connection(exception=None):
    if not has_app_context():
        return
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query(sql, params=None):
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        try:
            return cur.fetchall()
        except psycopg2.ProgrammingError:
            return []
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        if not has_app_context():
            conn.close()

def tx(statements):
    """Run several (sql, params) pairs in one transaction."""
    conn = _conn()
    cur = conn.cursor()
    try:
        for sql, params in statements:
            cur.execute(sql, params or ())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        if not has_app_context():
            conn.close()
