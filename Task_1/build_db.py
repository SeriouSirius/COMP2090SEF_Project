import hashlib
import sqlite3
import sys
import threading
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DB_path = BASE_DIR / "database" / "db.db"
ADMIN_USERNAME = "admin"
ADMIN_PWD = "admin123"
ADMIN_PAYMENT_PIN = "0000"
# admin pin default is 0000, maybe change later idk


class DB:
    def __init__(self, db_path=DB_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()

    def execute(self, query, parameters=()):
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(query, parameters)
            self.connection.commit()
            return cursor

    def fetchone(self, query, parameters=()):
        with self._lock:
            cursor = self.connection.cursor()
            cursor.execute(query, parameters)
            return cursor.fetchone()

    def fetchall(self, query, parameters=()):
        with self._lock:
          cursor = self.connection.cursor()
          cursor.execute(query, parameters)
          return cursor.fetchall()

    def close(self):
        with self._lock:
            self.connection.close()


def hash_pwd(pwd):
    # sha256 should be fine for now
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def ensure_users_table_schema(db):
    columns = {row["name"] for row in db.fetchall("PRAGMA table_info(users)")}
    if "payment_pin_hash" not in columns:
        db.execute(
            "ALTER TABLE users ADD COLUMN payment_pin_hash TEXT NOT NULL DEFAULT ''"
        )

    db.execute(
        "UPDATE users SET payment_pin_hash = ? WHERE payment_pin_hash IS NULL OR payment_pin_hash = ''",
        (hash_pwd(ADMIN_PAYMENT_PIN),),
    )


def create_tables(db):
    # create users table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pwd_hash TEXT NOT NULL,
            payment_pin_hash TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS events 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            event_date TEXT NOT NULL
        )
        """
    )
    # ticket types table
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_types 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            ticket_type_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT NOT NULL,
            expire_time TEXT,
            created_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (ticket_type_id) REFERENCES ticket_types(id)
        )
        """
    )
    ensure_users_table_schema(db)


def seed_admin(db):
    existingRow = db.fetchone(
        "SELECT id, payment_pin_hash FROM users WHERE username = ?",
        (ADMIN_USERNAME,),
    )
    if existingRow:
        if not existingRow["payment_pin_hash"]:
            db.execute(
                "UPDATE users SET payment_pin_hash = ? WHERE id = ?",
                (hash_pwd(ADMIN_PAYMENT_PIN), existingRow["id"]),
            )
        return

    db.execute(
        "INSERT INTO users (username, pwd_hash, payment_pin_hash, balance, is_admin) VALUES (?, ?, ?, ?, ?)",
        (
            ADMIN_USERNAME,
            hash_pwd(ADMIN_PWD),
            hash_pwd(ADMIN_PAYMENT_PIN),
            0.0,
            1,
        ),
    )
    print("admin user created")


def seed_sample_events(db):
    row = db.fetchone("SELECT COUNT(*) AS count FROM events")
    if row["count"] > 0:
        # already have data, skip
        return

    concertCursor = db.execute(
        "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
        (
            "Campus Music Night",
            "Enjoy live band performances with your friends.",
            "University Hall",
            "2026-04-20 19:00",
        ),
    )
    concert_id = concertCursor.lastrowid
    db.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (concert_id, "Standard", 120.0, 50),
    )
    db.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (concert_id, "VIP", 250.0, 20),
    )

    techTalkCursor = db.execute(
        "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
        (
            "Tech Innovation Forum",
            "Learn about new technology and startup ideas.",
            "Conference Room A",
            "2026-05-02 14:00",
        ),
    )
    tech_talk_id = techTalkCursor.lastrowid
    db.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (tech_talk_id, "Standard", 80.0, 80),
    )
    db.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (tech_talk_id, "Front Row", 150.0, 30),
    )
    print("sample events added")


def build_db():
    db = DB()
    try:
        create_tables(db)
        seed_admin(db)
        seed_sample_events(db)
    finally:
        db.close()


if __name__ == "__main__":
    build_db()
    print("db setup and seed data complete.")
