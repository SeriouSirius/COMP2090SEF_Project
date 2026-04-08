import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Task_1.build_db import DATABASE_PATH, DatabaseManager, hash_password
from Task_2.algorithm_data_structure import HierarchicalTimingWheel


PAYMENT_WINDOW_SECONDS = 300


class User:
    def __init__(self, user_id, username, balance, is_admin):
        self.user_id = user_id
        self.username = username
        self.balance = balance
        self.is_admin = is_admin


class Event:
    def __init__(self, event_id, title, description, location, event_date):
        self.event_id = event_id
        self.title = title
        self.description = description
        self.location = location
        self.event_date = event_date


class TicketType:
    def __init__(self, ticket_type_id, event_id, name, price, stock):
        self.ticket_type_id = ticket_type_id
        self.event_id = event_id
        self.name = name
        self.price = price
        self.stock = stock


class Booking:
    def __init__(self, booking_id, user_id, event_id, ticket_type_id, quantity, total_price, status, expires_at):
        self.booking_id = booking_id
        self.user_id = user_id
        self.event_id = event_id
        self.ticket_type_id = ticket_type_id
        self.quantity = quantity
        self.total_price = total_price
        self.status = status
        self.expires_at = expires_at


class AuthService:
    def __init__(self, database):
        self.database = database

    def register(self, username, password):
        if self.database.fetchone("SELECT id FROM users WHERE username = ?", (username,)):
            return None, "Username already exists"

        password_hash = self._hash_password(password)
        cursor = self.database.execute(
            "INSERT INTO users (username, password_hash, balance, is_admin) VALUES (?, ?, ?, ?)",
            (username, password_hash, 0.0, 0),
        )
        return self.get_user_by_id(cursor.lastrowid), "Register success"

    def login(self, username, password):
        row = self.database.fetchone("SELECT * FROM users WHERE username = ?", (username,))
        if row is None:
            return None, "User not found"

        password_hash = self._hash_password(password)
        if row["password_hash"] != password_hash:
            return None, "Wrong password"

        return self._row_to_user(row), "Login success"

    def get_user_by_id(self, user_id):
        row = self.database.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            return None
        return self._row_to_user(row)

    def _hash_password(self, password):
        return hash_password(password)

    def _row_to_user(self, row):
        return User(
            row["id"],
            row["username"],
            row["balance"],
            bool(row["is_admin"]),
        )


class EventService:
    def __init__(self, database):
        self.database = database

    def list_events(self):
        rows = self.database.fetchall("SELECT * FROM events ORDER BY event_date, title")
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id):
        row = self.database.fetchone("SELECT * FROM events WHERE id = ?", (event_id,))
        if row is None:
            return None
        return self._row_to_event(row)

    def get_ticket_types(self, event_id):
        rows = self.database.fetchall(
            "SELECT * FROM ticket_types WHERE event_id = ? ORDER BY id",
            (event_id,),
        )
        return [
            TicketType(
                row["id"],
                row["event_id"],
                row["name"],
                row["price"],
                row["stock"],
            )
            for row in rows
        ]

    def add_event(self, title, description, location, event_date):
        cursor = self.database.execute(
            "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
            (title, description, location, event_date),
        )
        return cursor.lastrowid

    def add_ticket_type(self, event_id, name, price, stock):
        self.database.execute(
            "INSERT INTO ticket_types (event_id, name, price, stock) VALUES (?, ?, ?, ?)",
            (event_id, name, price, stock),
        )

    def _row_to_event(self, row):
        return Event(
            row["id"],
            row["title"],
            row["description"],
            row["location"],
            row["event_date"],
        )


class BalanceService:
    def __init__(self, database, auth_service):
        self.database = database
        self.auth_service = auth_service

    def get_balance(self, user_id):
        row = self.database.fetchone("SELECT balance FROM users WHERE id = ?", (user_id,))
        return row["balance"] if row else 0.0

    def add_balance(self, user_id, amount):
        current_balance = self.get_balance(user_id)
        new_balance = current_balance + amount
        self.database.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )
        return new_balance

    def deduct_balance(self, user_id, amount):
        current_balance = self.get_balance(user_id)
        if current_balance < amount:
            return False, current_balance

        new_balance = current_balance - amount
        self.database.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )
        return True, new_balance


class BookingService:
    def __init__(self, database, event_service, balance_service):
        self.database = database
        self.event_service = event_service
        self.balance_service = balance_service
        self.timing_wheel = HierarchicalTimingWheel()
        self.pending_booking_ids = set()
        self._load_pending_bookings()

    def _load_pending_bookings(self):
        rows = self.database.fetchall(
            "SELECT id, expires_at FROM bookings WHERE status = 'pending'"
        )
        current_time = datetime.now()
        for row in rows:
            expires_at = datetime.fromisoformat(row["expires_at"])
            remaining_seconds = int((expires_at - current_time).total_seconds())
            if remaining_seconds <= 0:
                self.expire_booking(row["id"])
            else:
                self.timing_wheel.schedule(row["id"], remaining_seconds)
                self.pending_booking_ids.add(row["id"])

    def process_expired_bookings(self):
        due_booking_ids = self.timing_wheel.advance_to_now()
        for booking_id in due_booking_ids:
            if booking_id in self.pending_booking_ids:
                self.expire_booking(booking_id)

    def create_booking(self, user_id, event_id, ticket_type_id, quantity):
        ticket_row = self.database.fetchone(
            "SELECT * FROM ticket_types WHERE id = ? AND event_id = ?",
            (ticket_type_id, event_id),
        )
        if ticket_row is None:
            return None, "Ticket type not found"

        if quantity <= 0:
            return None, "Quantity must be greater than 0"

        if ticket_row["stock"] < quantity:
            return None, "Not enough ticket stock"

        total_price = ticket_row["price"] * quantity
        self.database.execute(
            "UPDATE ticket_types SET stock = stock - ? WHERE id = ?",
            (quantity, ticket_type_id),
        )

        expires_at = datetime.now().timestamp() + PAYMENT_WINDOW_SECONDS
        expires_at_text = datetime.fromtimestamp(expires_at).isoformat(timespec="seconds")
        cursor = self.database.execute(
            """
            INSERT INTO bookings (user_id, event_id, ticket_type_id, quantity, total_price, status, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                user_id,
                event_id,
                ticket_type_id,
                quantity,
                total_price,
                expires_at_text,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        booking_id = cursor.lastrowid
        self.timing_wheel.schedule(booking_id, PAYMENT_WINDOW_SECONDS)
        self.pending_booking_ids.add(booking_id)
        return self.get_booking(booking_id), "Booking created. Please pay in 5 minutes."

    def pay_booking(self, booking_id, user_id):
        booking = self.get_booking(booking_id)
        if booking is None or booking.user_id != user_id:
            return False, "Booking not found"

        if booking.status != "pending":
            return False, f"Booking status is {booking.status}"

        if datetime.now() > datetime.fromisoformat(booking.expires_at):
            self.expire_booking(booking.booking_id)
            return False, "Payment time is over"

        success, balance = self.balance_service.deduct_balance(user_id, booking.total_price)
        if not success:
            return False, "Balance not enough to pay"

        self.database.execute(
            "UPDATE bookings SET status = 'paid' WHERE id = ?",
            (booking.booking_id,),
        )
        self.pending_booking_ids.discard(booking.booking_id)
        return True, f"Thank you for your purchase. New balance: {balance:.2f}"

    def expire_booking(self, booking_id):
        row = self.database.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        if row is None or row["status"] != "pending":
            return

        self.database.execute(
            "UPDATE ticket_types SET stock = stock + ? WHERE id = ?",
            (row["quantity"], row["ticket_type_id"]),
        )
        self.database.execute(
            "UPDATE bookings SET status = 'expired' WHERE id = ?",
            (booking_id,),
        )
        self.pending_booking_ids.discard(booking_id)

    def get_user_bookings(self, user_id):
        rows = self.database.fetchall(
            """
            SELECT b.*, e.title, e.description, e.location, e.event_date, tt.name AS ticket_type_name
            FROM bookings b
            JOIN events e ON b.event_id = e.id
            JOIN ticket_types tt ON b.ticket_type_id = tt.id
            WHERE b.user_id = ?
            ORDER BY b.id DESC
            """,
            (user_id,),
        )
        return rows

    def get_booking(self, booking_id):
        row = self.database.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        if row is None:
            return None
        return Booking(
            row["id"],
            row["user_id"],
            row["event_id"],
            row["ticket_type_id"],
            row["quantity"],
            row["total_price"],
            row["status"],
            row["expires_at"],
        )

    def get_all_booking_statuses(self):
        return self.database.fetchall(
            """
            SELECT b.id, u.username, e.title, tt.name AS ticket_type_name,
                   b.quantity, b.total_price, b.status, b.expires_at
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN events e ON b.event_id = e.id
            JOIN ticket_types tt ON b.ticket_type_id = tt.id
            ORDER BY b.id DESC
            """
        )


class TicketSystem:
    def __init__(self):
        self.database = DatabaseManager(DATABASE_PATH)
        self.auth_service = AuthService(self.database)
        self.event_service = EventService(self.database)
        self.balance_service = BalanceService(self.database, self.auth_service)
        self.booking_service = BookingService(
            self.database,
            self.event_service,
            self.balance_service,
        )
        self.current_user = None
        self.booking_service.process_expired_bookings()

    def close(self):
        self.database.close()
