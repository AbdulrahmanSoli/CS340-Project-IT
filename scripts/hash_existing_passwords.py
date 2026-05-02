"""One-off migration: hash any plaintext values currently in users.passwordHash.

Run once after deploying the password-hashing changes:

    python scripts/hash_existing_passwords.py

Idempotent — rows that already start with a werkzeug hash prefix
('pbkdf2:', 'scrypt:', 'argon2') are left alone.

After this runs, the seeded users from the report log in with the literal
strings that were previously in the column ('hash_1', 'hash_2', ...).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkzeug.security import generate_password_hash
from db import get_connection

HASH_PREFIXES = ('pbkdf2:', 'scrypt:', 'argon2')

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT userID, passwordHash FROM users')
    rows = cur.fetchall()

    updated = 0
    skipped = 0
    for user_id, current in rows:
        if current and current.startswith(HASH_PREFIXES):
            skipped += 1
            continue
        cur.execute(
            'UPDATE users SET passwordHash = %s WHERE userID = %s',
            (generate_password_hash(current), user_id),
        )
        updated += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f'Hashed {updated} row(s); skipped {skipped} already-hashed row(s).')

if __name__ == '__main__':
    main()
