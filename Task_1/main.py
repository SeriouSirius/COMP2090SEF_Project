import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Task_1.build_db import DB_path, DB, hash_pwd
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
    def __init__(self, booking_id, user_id, event_id, ticket_type_id, quantity, total_price, status, expire_time):
        self.booking_id = booking_id
        self.user_id = user_id
        self.event_id = event_id
        self.ticket_type_id = ticket_type_id
        self.quantity = quantity
        self.total_price = total_price
        self.status = status
        self.expire_time = expire_time


class Authsys:
    def __init__(self, db):
        self.db = db

    def register(self, username, pwd, payment_pin):
        # check if user already exists
        if self.db.fetchone("SELECT id FROM users WHERE username = ?", (username,)):
            return None, "Username already exists"

        if not payment_pin or not payment_pin.isdigit() or len(payment_pin) != 4:
            return None, "Payment PIN must be exactly 4 digits"

        pwdHash = self.hash_pwd(pwd)
        paymentPinHash = self.hash_pwd(payment_pin)
        cursor = self.db.execute(
            "INSERT INTO users (username, pwd_hash, payment_pin_hash, balance, is_admin) VALUES (?, ?, ?, ?, ?)",
            (username, pwdHash, paymentPinHash, 0.0, 0),
        )
        print(f"new user registered: {username}")
        return self.get_user_by_id(cursor.lastrowid), "Register success"

    def login(self, username, pwd):
        row = self.db.fetchone("SELECT * FROM users WHERE username = ?", (username,))
        if row is None:
            return None, "User not found"

        pwdHash = self.hash_pwd(pwd)
        # TODO: maybe add login attempt limit later
        if row["pwd_hash"] != pwdHash:
            return None, "Wrong password"

        print(f"user {username} logged in")
        return self._row_to_user(row), "Login success"

    def get_user_by_id(self, user_id):
        row = self.db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        if row is None:
            return None
        return self._row_to_user(row)

    def verify_payment_pin(self, user_id, payment_pin):
        if not payment_pin:
            return False, "Payment PIN is required"
        if not payment_pin.isdigit() or len(payment_pin) != 4:
            return False, "Payment PIN must be exactly 4 digits"

        row = self.db.fetchone(
            "SELECT payment_pin_hash FROM users WHERE id = ?",
            (user_id,),
        )
        if row is None:
            return False, "User not found"
        if not row["payment_pin_hash"]:
            return False, "Payment PIN is not set for this user"

        if row["payment_pin_hash"] != self.hash_pwd(payment_pin):
            return False, "Payment PIN is incorrect"
        return True, "Payment PIN verified"

    def hash_pwd(self, pwd):
        return hash_pwd(pwd)

    def _row_to_user(self, row):
        return User(
            row["id"],
            row["username"],
            row["balance"],
            bool(row["is_admin"]),
        )


class Event_sys:
    def __init__(self, db):
        self.db = db

    def list_events(self):
        rows = self.db.fetchall("SELECT * FROM events ORDER BY event_date, title")
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id):
        row = self.db.fetchone("SELECT * FROM events WHERE id = ?", (event_id,))
        if row is None:
            return None
        return self._row_to_event(row)

    def get_ticket_types(self, event_id):
        rows = self.db.fetchall(
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
        cursor = self.db.execute(
            "INSERT INTO events (title, description, location, event_date) VALUES (?, ?, ?, ?)",
            (title, description, location, event_date),
        )
        print("event added, id =", cursor.lastrowid)
        return cursor.lastrowid

    def add_ticket_type(self, event_id, name, price, stock):
        self.db.execute(
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


class Balance_sys:
    def __init__(self, db, auth_sys):
        self.db = db
        self.auth_sys = auth_sys

    def get_balance(self, user_id):
        row = self.db.fetchone("SELECT balance FROM users WHERE id = ?", (user_id,))
        return row["balance"] if row else 0.0

    def add_balance(self, user_id, amount):
        currentBalance = self.get_balance(user_id)
        new_balance = currentBalance + amount
        self.db.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )
        return new_balance

    def deduct_balance(self, user_id, amount):
        currentBalance = self.get_balance(user_id)
        if currentBalance < amount:
            return False, currentBalance

        new_balance = currentBalance - amount
        self.db.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (new_balance, user_id),
        )
        return True, new_balance


class Booking_sys:
    def __init__(self, db, event_sys, balance_sys, auth_sys):
        self.db = db
        self.event_sys = event_sys
        self.balance_sys = balance_sys
        self.auth_sys = auth_sys
        self.timing_wheel = HierarchicalTimingWheel()
        self.pending_booking_ids = set()
        self.load_pending_bookings()

    def load_pending_bookings(self):
        rows = self.db.fetchall(
            "SELECT id, expire_time FROM bookings WHERE status = 'pending'"
        )
        current_time = datetime.now()
        for row in rows:
            expireTime = datetime.fromisoformat(row["expire_time"])
            remaining_seconds = int((expireTime - current_time).total_seconds())
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
        ticketRow = self.db.fetchone(
            "SELECT * FROM ticket_types WHERE id = ? AND event_id = ?",
            (ticket_type_id, event_id),
        )
        if ticketRow is None:
            return None, "Ticket type not found"

        if quantity <= 0:
            return None, "Quantity must be greater than 0"

        if ticketRow["stock"] < quantity:
            return None, "Not enough ticket stock"

        total_price = ticketRow["price"] * quantity
        self.db.execute(
            "UPDATE ticket_types SET stock = stock - ? WHERE id = ?",
            (quantity, ticket_type_id),
        )

        # calc expire time, 5 min window
        expireTime = datetime.now().timestamp() + PAYMENT_WINDOW_SECONDS
        expire_time_text = datetime.fromtimestamp(expireTime).isoformat(timespec="seconds")
        cursor = self.db.execute(
            """
            INSERT INTO bookings (user_id, event_id, ticket_type_id, quantity, total_price, status, expire_time, created_time)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                user_id,
                event_id,
                ticket_type_id,
                quantity,
                total_price,
                expire_time_text,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        booking_id = cursor.lastrowid
        self.timing_wheel.schedule(booking_id, PAYMENT_WINDOW_SECONDS)
        self.pending_booking_ids.add(booking_id)
        print(f"booking created: id={booking_id}, total={total_price}")
        return self.get_booking(booking_id), "Booking created. Please pay in 5 minutes."

    def pay_booking(self, booking_id, user_id, payment_pin):
        booking = self.get_booking(booking_id)
        if booking is None or booking.user_id != user_id:
            return False, "Booking not found"

        if booking.status != "pending":
            return False, f"Booking status is {booking.status}"

        pin_ok, pin_message = self.auth_sys.verify_payment_pin(user_id, payment_pin)
        if not pin_ok:
            return False, pin_message

        if datetime.now() > datetime.fromisoformat(booking.expire_time):
            self.expire_booking(booking.booking_id)
            return False, "Payment time is over"

        success, balance = self.balance_sys.deduct_balance(user_id, booking.total_price)
        if not success:
            return False, "Balance not enough to pay"

        self.db.execute(
            "UPDATE bookings SET status = 'paid' WHERE id = ?",
            (booking.booking_id,),
        )
        self.pending_booking_ids.discard(booking.booking_id)
        print("payment done for booking", booking_id)
        return True, f"Thank you for your purchase. New balance: {balance:.2f}"

    def expire_booking(self, booking_id):
        row = self.db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        if row is None or row["status"] != "pending":
            return

        self.db.execute(
            "UPDATE ticket_types SET stock = stock + ? WHERE id = ?",
            (row["quantity"], row["ticket_type_id"]),
        )
        self.db.execute(
            "UPDATE bookings SET status = 'expired' WHERE id = ?",
            (booking_id,),
        )
        self.pending_booking_ids.discard(booking_id)
        # TODO: maybe notify user that booking expired

    def get_user_bookings(self, user_id):
        rows = self.db.fetchall(
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
        row = self.db.fetchone("SELECT * FROM bookings WHERE id = ?", (booking_id,))
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
            row["expire_time"],
        )

    def get_booking_statuses(self):
        return self.db.fetchall(
            """
            SELECT b.id, u.username, e.title, tt.name AS ticket_type_name,
                   b.quantity, b.total_price, b.status, b.expire_time
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN events e ON b.event_id = e.id
            JOIN ticket_types tt ON b.ticket_type_id = tt.id
            ORDER BY b.id DESC
            """
        )


class TicketSystem:
    def __init__(self, DB_path=DB_path):
        self.db = DB(DB_path)
        self.auth_sys = Authsys(self.db)
        self.event_sys = Event_sys(self.db)
        self.balance_sys = Balance_sys(self.db, self.auth_sys)
        self.booking_sys = Booking_sys(
            self.db,
            self.event_sys,
            self.balance_sys,
            self.auth_sys,
        )
        self.current_user = None
        self.booking_sys.process_expired_bookings()

    def close(self):
        self.db.close()
