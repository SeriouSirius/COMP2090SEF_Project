import hashlib
import sqlite3
import sys
import threading
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

DATABASE_PATH = BASE_DIR / "database" / "db.db"
SUPER_ADMIN_USERNAME = "admin"
SUPER_ADMIN_PASSWORD = "admin123"
SUPER_ADMIN_PAYMENT_PIN = "0000"


class DatabaseManager:
    def __init__(self, db_path=DATABASE_PATH):
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


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ensure_users_table_schema(database):
    columns = {row["name"] for row in database.fetchall("PRAGMA table_info(users)")}
    if "payment_pin_hash" not in columns:
        database.execute(
            "ALTER TABLE users ADD COLUMN payment_pin_hash TEXT NOT NULL DEFAULT ''"
        )

    database.execute(
        "UPDATE users SET payment_pin_hash = ? WHERE payment_pin_hash IS NULL OR payment_pin_hash = ''",
        (hash_password(SUPER_ADMIN_PAYMENT_PIN),),
    )


def create_tables(database):
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS users 
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            payment_pin_hash TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    database.execute(
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
    database.execute(
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
    database.execute(
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
            expires_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id),
            FOREIGN KEY (ticket_type_id) REFERENCES ticket_types(id)
        )
        """
    )
    ensure_users_table_schema(database)


def seed_super_admin(database):
    existing_row = database.fetchone(
        "SELECT id, payment_pin_hash FROM users WHERE username = ?",
        (SUPER_ADMIN_USERNAME,),
    )
    if existing_row:
        if not existing_row["payment_pin_hash"]:
            database.execute(
                "UPDATE users SET payment_pin_hash = ? WHERE id = ?",
                (hash_password(SUPER_ADMIN_PAYMENT_PIN), existing_row["id"]),
            )
        return

    database.execute(
        "INSERT INTO users (username, password_hash, payment_pin_hash, balance, is_admin) VALUES (?, ?, ?, ?, ?)",
        (
            SUPER_ADMIN_USERNAME,
            hash_password(SUPER_ADMIN_PASSWORD),
            hash_password(SUPER_ADMIN_PAYMENT_PIN),
            0.0,
            1,
        ),
    )


def seed_sample_events(database):
    row = database.fetchone("SELECT COUNT(*) AS count FROM events")
    if row["count"] > 0:
        return

    concert_cursor = database.execute(
        "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
        (
            "Campus Music Night",
            "Enjoy live band performances with your friends.",
            "University Hall",
            "2026-04-20 19:00",
        ),
    )
    concert_id = concert_cursor.lastrowid
    database.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (concert_id, "Standard", 120.0, 50),
    )
    database.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (concert_id, "VIP", 250.0, 20),
    )

    tech_talk_cursor = database.execute(
        "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
        (
            "Tech Innovation Forum",
            "Learn about new technology and startup ideas.",
            "Conference Room A",
            "2026-05-02 14:00",
        ),
    )
    tech_talk_id = tech_talk_cursor.lastrowid
    database.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (tech_talk_id, "Standard", 80.0, 80),
    )
    database.execute(
        "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
        (tech_talk_id, "Front Row", 150.0, 30),
    )


def build_database():
    database = DatabaseManager()
    try:
        create_tables(database)
        seed_super_admin(database)
        seed_sample_events(database)
    finally:
        database.close()


if __name__ == "__main__":
    build_database()
    print("Database setup and seed data complete.")
