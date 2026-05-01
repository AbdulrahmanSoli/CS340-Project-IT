import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def query(sql, params=None, raise_errors=False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        try:
            return cur.fetchall()
        except Exception:
            return []
    except Exception:
        conn.rollback()
        if raise_errors:
            raise
        return None
    finally:
        cur.close()
        conn.close()

def tx(statements):
    """Run several (sql, params) pairs in one transaction.
    Rolls back on any error and re-raises so the caller can match on the
    psycopg2 error class."""
    conn = get_connection()
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
        conn.close()