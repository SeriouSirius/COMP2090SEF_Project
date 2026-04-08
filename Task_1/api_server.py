import atexit
import html
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Task_1.build_db import (
    DATABASE_PATH,
    DatabaseManager,
    create_tables,
    seed_sample_events,
    seed_super_admin,
)
from Task_1.main import TicketSystem


def initialize_database(database_path, seed_data=True):
    database = DatabaseManager(database_path)
    try:
        create_tables(database)
        seed_super_admin(database)
        if seed_data:
            seed_sample_events(database)
    finally:
        database.close()


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def make_json(success, message, data=None, error_code=None):
    payload = {
        "success": success,
        "message": message,
        "data": data if data is not None else {},
    }
    if error_code:
        payload["error_code"] = error_code
    return jsonify(payload)


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def serialize_user(user):
    return {
        "user_id": user.user_id,
        "username": user.username,
        "balance": user.balance,
        "is_admin": user.is_admin,
    }


def serialize_event(event):
    return {
        "event_id": event.event_id,
        "title": event.title,
        "description": event.description,
        "location": event.location,
        "event_date": event.event_date,
    }


def serialize_ticket_type(ticket_type):
    return {
        "ticket_type_id": ticket_type.ticket_type_id,
        "event_id": ticket_type.event_id,
        "name": ticket_type.name,
        "price": ticket_type.price,
        "stock": ticket_type.stock,
    }


def serialize_booking(booking):
    return {
        "id": booking.booking_id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "ticket_type_id": booking.ticket_type_id,
        "quantity": booking.quantity,
        "total_price": booking.total_price,
        "status": booking.status,
        "expires_at": booking.expires_at,
    }


def create_app(database_path=None, seed_data=True):
    resolved_database_path = Path(database_path) if database_path is not None else DATABASE_PATH
    initialize_database(resolved_database_path, seed_data=seed_data)

    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "GUI"),
        static_url_path="",
    )

    system = TicketSystem(database_path=resolved_database_path)
    app.config["ticket_system"] = system

    def require_user(payload):
        user_id = to_int((payload or {}).get("user_id"))
        if user_id is None:
            return None
        return system.auth_service.get_user_by_id(user_id)

    def require_admin(payload):
        user = require_user(payload)
        if user is None or not user.is_admin:
            return None
        return user

    def process_expiries():
        system.booking_service.process_expired_bookings()

    @app.get("/")
    def home_page():
        return app.send_static_file("index.html")

    @app.get("/ticket/verify/<int:booking_id>")
    def ticket_verify(booking_id):
        row = system.database.fetchone(
            """
            SELECT b.id, b.status, b.quantity, b.total_price,
                   u.username,
                   e.title, e.location, e.event_date,
                   tt.name AS ticket_type_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN events e ON b.event_id = e.id
            JOIN ticket_types tt ON b.ticket_type_id = tt.id
            WHERE b.id = ?
            """,
            (booking_id,),
        )

        if row is None:
            not_found_html = """
            <!DOCTYPE html>
            <html lang=\"en\">
            <head>
                <meta charset=\"UTF-8\" />
                <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
                <title>Ticket not found</title>
            </head>
            <body style=\"font-family: sans-serif; padding: 1.5rem;\">
                <h1>Ticket not found</h1>
                <p>The ticket ID is invalid or no longer available.</p>
            </body>
            </html>
            """
            return not_found_html, 404, {"Content-Type": "text/html; charset=utf-8"}

        data = dict(row)
        safe = {key: html.escape(str(value)) for key, value in data.items()}
        ticket_html = f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
            <meta charset=\"UTF-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
            <title>Ticket #{safe['id']}</title>
        </head>
        <body style=\"font-family: sans-serif; background: #f4efe8; padding: 1.2rem;\">
            <div style=\"max-width: 560px; margin: 0 auto; background: #fffdf9; border: 1px solid #d8cbbd; border-radius: 12px; padding: 1rem;\">
                <h1 style=\"margin-top: 0;\">Ticket Verification</h1>
                <p><strong>Holder:</strong> {safe['username']}</p>
                <p><strong>Event:</strong> {safe['title']}</p>
                <p><strong>Location:</strong> {safe['location']}</p>
                <p><strong>Date:</strong> {safe['event_date']}</p>
                <p><strong>Ticket Type:</strong> {safe['ticket_type_name']}</p>
                <p><strong>Quantity:</strong> {safe['quantity']}</p>
                <p><strong>Status:</strong> {safe['status']}</p>
                <p><strong>Total:</strong> {safe['total_price']}</p>
                <p><strong>Ticket ID:</strong> {safe['id']}</p>
            </div>
        </body>
        </html>
        """
        return ticket_html, 200, {"Content-Type": "text/html; charset=utf-8"}

    @app.post("/api/auth/login")
    def api_auth_login():
        payload = request.get_json(silent=True) or {}
        user, message = system.auth_service.login(
            payload.get("username", ""),
            payload.get("password", ""),
        )
        if user is None:
            return make_json(False, message, error_code="AUTH_FAILED"), 400
        return make_json(True, message, data=serialize_user(user))

    @app.post("/api/auth/register")
    def api_auth_register():
        payload = request.get_json(silent=True) or {}
        user, message = system.auth_service.register(
            payload.get("username", ""),
            payload.get("password", ""),
            str(payload.get("payment_pin", "")).strip(),
        )
        if user is None:
            return make_json(False, message, error_code="REGISTER_FAILED"), 400
        return make_json(True, message, data=serialize_user(user))

    @app.post("/api/user/profile")
    def api_user_profile():
        user = require_user(request.get_json(silent=True) or {})
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401
        return make_json(True, "Profile loaded", data=serialize_user(user))

    @app.post("/api/user/logout")
    def api_user_logout():
        user = require_user(request.get_json(silent=True) or {})
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401
        return make_json(True, "Logout success", data={"user_id": user.user_id})

    @app.post("/api/events/list")
    def api_events_list():
        user = require_user(request.get_json(silent=True) or {})
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401
        process_expiries()
        events = [serialize_event(event) for event in system.event_service.list_events()]
        return make_json(True, "Events loaded", data=events)

    @app.post("/api/events/detail")
    def api_events_detail():
        payload = request.get_json(silent=True) or {}
        user = require_user(payload)
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        event_id = to_int(payload.get("event_id"))
        if event_id is None:
            return make_json(False, "Invalid event id", error_code="INVALID_EVENT_ID"), 400

        event = system.event_service.get_event(event_id)
        if event is None:
            return make_json(False, "Event not found", error_code="EVENT_NOT_FOUND"), 404

        ticket_types = [
            serialize_ticket_type(ticket_type)
            for ticket_type in system.event_service.get_ticket_types(event_id)
        ]
        return make_json(
            True,
            "Event detail loaded",
            data={
                "event": serialize_event(event),
                "ticket_types": ticket_types,
            },
        )

    @app.post("/api/bookings/create")
    def api_bookings_create():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        user = require_user(payload)
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        event_id = to_int(payload.get("event_id"))
        ticket_type_id = to_int(payload.get("ticket_type_id"))
        quantity = to_int(payload.get("quantity"))
        if event_id is None or ticket_type_id is None or quantity is None:
            return make_json(False, "Invalid booking payload", error_code="INVALID_BOOKING_PAYLOAD"), 400

        booking, message = system.booking_service.create_booking(
            user.user_id,
            event_id,
            ticket_type_id,
            quantity,
        )
        if booking is None:
            return make_json(False, message, error_code="BOOKING_CREATE_FAILED"), 400

        return make_json(
            True,
            message,
            data={
                **serialize_booking(booking),
                "server_now": now_text(),
            },
        )

    @app.post("/api/bookings/pay")
    def api_bookings_pay():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        user = require_user(payload)
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        booking_id = to_int(payload.get("booking_id"))
        if booking_id is None:
            return make_json(False, "Invalid booking id", error_code="INVALID_BOOKING_ID"), 400

        payment_pin = str(payload.get("payment_pin", "")).strip()
        success, message = system.booking_service.pay_booking(
            booking_id,
            user.user_id,
            payment_pin,
        )
        if not success:
            return make_json(False, message, error_code="PAYMENT_FAILED"), 400

        fresh_user = system.auth_service.get_user_by_id(user.user_id)
        return make_json(
            True,
            message,
            data={
                "booking_id": booking_id,
                "balance": fresh_user.balance if fresh_user else 0,
            },
        )

    @app.post("/api/balance/get")
    def api_balance_get():
        process_expiries()
        user = require_user(request.get_json(silent=True) or {})
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        balance = system.balance_service.get_balance(user.user_id)
        return make_json(True, "Balance loaded", data={"balance": balance})

    @app.post("/api/balance/add")
    def api_balance_add():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        user = require_user(payload)
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        amount = to_float(payload.get("amount"))
        if amount is None or amount <= 0:
            return make_json(False, "Amount must be greater than 0", error_code="INVALID_AMOUNT"), 400

        payment_pin = str(payload.get("payment_pin", "")).strip()
        pin_ok, pin_message = system.auth_service.verify_payment_pin(
            user.user_id,
            payment_pin,
        )
        if not pin_ok:
            return make_json(False, pin_message, error_code="PIN_VERIFY_FAILED"), 400

        new_balance = system.balance_service.add_balance(user.user_id, amount)
        return make_json(True, "Add balance success", data={"new_balance": new_balance})

    @app.post("/api/bookings/my")
    def api_bookings_my():
        process_expiries()
        user = require_user(request.get_json(silent=True) or {})
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        now = now_text()
        rows = []
        for row in system.booking_service.get_user_bookings(user.user_id):
            row_data = dict(row)
            if row_data.get("status") == "pending":
                row_data["server_now"] = now
            rows.append(row_data)
        return make_json(True, "Bookings loaded", data=rows)

    @app.post("/api/bookings/detail")
    def api_bookings_detail():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        user = require_user(payload)
        if user is None:
            return make_json(False, "User not found", error_code="USER_NOT_FOUND"), 401

        booking_id = to_int(payload.get("booking_id"))
        if booking_id is None:
            return make_json(False, "Invalid booking id", error_code="INVALID_BOOKING_ID"), 400

        row = system.database.fetchone(
            """
            SELECT b.*, e.title, e.description, e.location, e.event_date, tt.name AS ticket_type_name
            FROM bookings b
            JOIN events e ON b.event_id = e.id
            JOIN ticket_types tt ON b.ticket_type_id = tt.id
            WHERE b.id = ? AND b.user_id = ?
            """,
            (booking_id, user.user_id),
        )
        if row is None:
            return make_json(False, "Booking not found", error_code="BOOKING_NOT_FOUND"), 404

        data = dict(row)
        if data.get("status") == "pending":
            data["server_now"] = now_text()
        return make_json(True, "Booking detail loaded", data=data)

    @app.post("/api/admin/events/add")
    def api_admin_events_add():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        admin = require_admin(payload)
        if admin is None:
            return make_json(False, "Admin permission required", error_code="FORBIDDEN"), 403

        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        location = (payload.get("location") or "").strip()
        event_date = (payload.get("event_date") or "").strip()

        if not title or not description or not location or not event_date:
            return make_json(False, "All event fields are required", error_code="INVALID_EVENT_PAYLOAD"), 400

        event_id = system.event_service.add_event(title, description, location, event_date)
        return make_json(True, "Event added successfully", data={"event_id": event_id})

    @app.post("/api/admin/ticket-types/add")
    def api_admin_ticket_types_add():
        process_expiries()
        payload = request.get_json(silent=True) or {}
        admin = require_admin(payload)
        if admin is None:
            return make_json(False, "Admin permission required", error_code="FORBIDDEN"), 403

        event_id = to_int(payload.get("event_id"))
        name = (payload.get("name") or "").strip()
        price = to_float(payload.get("price"))
        stock = to_int(payload.get("stock"))

        if event_id is None or not name or price is None or stock is None:
            return make_json(False, "Invalid ticket type payload", error_code="INVALID_TICKET_TYPE_PAYLOAD"), 400

        if price < 0 or stock < 0:
            return make_json(False, "Price and stock must be non-negative", error_code="INVALID_TICKET_VALUES"), 400

        event = system.event_service.get_event(event_id)
        if event is None:
            return make_json(False, "Event not found", error_code="EVENT_NOT_FOUND"), 404

        system.event_service.add_ticket_type(event_id, name, price, stock)
        return make_json(True, "Ticket type added")

    @app.post("/api/admin/bookings/status")
    def api_admin_bookings_status():
        process_expiries()
        admin = require_admin(request.get_json(silent=True) or {})
        if admin is None:
            return make_json(False, "Admin permission required", error_code="FORBIDDEN"), 403

        rows = [dict(row) for row in system.booking_service.get_all_booking_statuses()]
        return make_json(True, "Booking status loaded", data=rows)

    return app


if __name__ == "__main__":
    app = create_app()
    atexit.register(app.config["ticket_system"].close)
    app.run(host="127.0.0.1", port=5000, debug=True)
