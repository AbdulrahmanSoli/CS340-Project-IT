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