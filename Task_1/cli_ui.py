# Run MEEEEEEEEEEEEEEEEEEEEEEEEEEEE

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Task_1.build_db import build_database
from Task_1.main import TicketSystem


class TicketSystemCLI:
    def __init__(self):
        self.system = TicketSystem()

    def run(self):
        while True:
            self.system.booking_service.process_expired_bookings()
            if self.system.current_user is None:
                if not self.show_auth_menu():
                    break
            else:
                self.show_main_menu()

    def show_auth_menu(self):
        print("\n=== Event Ticket Selling System ===")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            self.handle_login()
        elif choice == "2":
            self.handle_register()
        elif choice == "3":
            self.system.close()
            return False
        else:
            print("Invalid choice")
        return True

    def handle_login(self):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        user, message = self.system.auth_service.login(username, password)
        print(message)
        if user:
            self.system.current_user = user

    def handle_register(self):
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        payment_pin = input("Payment PIN (4 digits): ").strip()
        user, message = self.system.auth_service.register(username, password, payment_pin)
        print(message)
        if user:
            self.system.current_user = user

    def show_main_menu(self):
        current_user = self.system.current_user
        print(f"\n=== Main Menu ({current_user.username}) ===")
        print("1. Browse events")
        print("2. Check balance")
        print("3. Check tickets")
        print("4. Logout")
        if current_user.is_admin:
            print("5. Add events")
            print("6. Check bookings status")

        choice = input("Choose: ").strip()
        if choice == "1":
            self.browse_events()
        elif choice == "2":
            self.show_balance_menu()
        elif choice == "3":
            self.show_tickets_menu()
        elif choice == "4":
            self.system.current_user = None
            print("Logout success")
        elif choice == "5" and current_user.is_admin:
            self.add_event_menu()
        elif choice == "6" and current_user.is_admin:
            self.show_booking_status_menu()
        else:
            print("Invalid choice")

    def browse_events(self):
        events = self.system.event_service.list_events()
        if not events:
            print("No events found")
            return

        print("\n=== Events ===")
        for index, event in enumerate(events, start=1):
            print(f"{index}. {event.title} | {event.location} | {event.event_date}")

        choice = input("Choose event number or B to back: ").strip()
        if choice.lower() == "b":
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(events):
            print("Invalid event choice")
            return

        event = events[int(choice) - 1]
        self.show_event_detail_menu(event)

    def show_event_detail_menu(self, event):
        print("\n=== Event Detail ===")
        print(f"Title: {event.title}")
        print(f"Description: {event.description}")
        print(f"Location: {event.location}")
        print(f"Date: {event.event_date}")

        ticket_types = self.system.event_service.get_ticket_types(event.event_id)
        if not ticket_types:
            print("No ticket types for this event")
            return

        print("\nTicket Types:")
        for index, ticket_type in enumerate(ticket_types, start=1):
            print(
                f"{index}. {ticket_type.name} | Price: {ticket_type.price:.2f} | "
                f"Stock: {ticket_type.stock}"
            )

        ticket_choice = input("Choose ticket type number or B to back: ").strip()
        if ticket_choice.lower() == "b":
            return
        if not ticket_choice.isdigit() or int(ticket_choice) < 1 or int(ticket_choice) > len(ticket_types):
            print("Invalid ticket type choice")
            return

        quantity_text = input("Enter quantity: ").strip()
        if not quantity_text.isdigit():
            print("Quantity must be a number")
            return

        quantity = int(quantity_text)
        ticket_type = ticket_types[int(ticket_choice) - 1]
        booking, message = self.system.booking_service.create_booking(
            self.system.current_user.user_id,
            event.event_id,
            ticket_type.ticket_type_id,
            quantity,
        )
        print(message)
        if booking is None:
            return

        pay_now = input("Pay now? (y/n): ").strip().lower()
        if pay_now == "y":
            payment_pin = input("Enter Payment PIN: ").strip()
            _, payment_message = self.system.booking_service.pay_booking(
                booking.booking_id,
                self.system.current_user.user_id,
                payment_pin,
            )
            print(payment_message)
            self.system.current_user = self.system.auth_service.get_user_by_id(
                self.system.current_user.user_id
            )

    def show_balance_menu(self):
        self.system.current_user = self.system.auth_service.get_user_by_id(
            self.system.current_user.user_id
        )
        print(f"\nCurrent balance: {self.system.current_user.balance:.2f}")
        print("1. Add balance")
        print("2. Back to menu")
        choice = input("Choose: ").strip()

        if choice == "1":
            amount_text = input("Enter amount: ").strip()
            try:
                amount = float(amount_text)
            except ValueError:
                print("Amount must be a number")
                return

            if amount <= 0:
                print("Amount must be greater than 0")
                return

            payment_pin = input("Enter Payment PIN: ").strip()
            pin_ok, pin_message = self.system.auth_service.verify_payment_pin(
                self.system.current_user.user_id,
                payment_pin,
            )
            if not pin_ok:
                print(pin_message)
                return

            new_balance = self.system.balance_service.add_balance(
                self.system.current_user.user_id,
                amount,
            )
            self.system.current_user = self.system.auth_service.get_user_by_id(
                self.system.current_user.user_id
            )
            print("Add balance success")
            print(f"New balance: {new_balance:.2f}")
        elif choice == "2":
            return
        else:
            print("Invalid choice")

    def show_tickets_menu(self):
        bookings = self.system.booking_service.get_user_bookings(
            self.system.current_user.user_id
        )
        if not bookings:
            print("No tickets bought yet")
            return

        print("\n=== My Tickets ===")
        for index, booking in enumerate(bookings, start=1):
            print(
                f"{index}. {booking['title']} | {booking['ticket_type_name']} | Quantity: {booking['quantity']} | "
                f"Total: {booking['total_price']:.2f} | Status: {booking['status']}"
            )

        choice = input("Choose ticket number or B to back: ").strip()
        if choice.lower() == "b":
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(bookings):
            print("Invalid choice")
            return

        booking = bookings[int(choice) - 1]
        print("\n=== Ticket Detail ===")
        print(f"Event: {booking['title']}")
        print(f"Description: {booking['description']}")
        print(f"Location: {booking['location']}")
        print(f"Date: {booking['event_date']}")
        print(f"Ticket Type: {booking['ticket_type_name']}")
        print(f"Quantity: {booking['quantity']}")
        print(f"Status: {booking['status']}")
        print(f"Total: {booking['total_price']:.2f}")
        if booking["status"] == "pending":
            print(f"Pay before: {booking['expires_at']}")
            pay_now = input("Pay now? (y/n): ").strip().lower()
            if pay_now == "y":
                payment_pin = input("Enter Payment PIN: ").strip()
                _, payment_message = self.system.booking_service.pay_booking(
                    booking["id"],
                    self.system.current_user.user_id,
                    payment_pin,
                )
                print(payment_message)
                self.system.current_user = self.system.auth_service.get_user_by_id(
                    self.system.current_user.user_id
                )
        else:
            print(f"Total Paid: {booking['total_price']:.2f}")

    def add_event_menu(self):
        print("\n=== Add Event ===")
        title = input("Title: ").strip()
        description = input("Description: ").strip()
        location = input("Location: ").strip()
        event_date = input("Date and time (YYYY-MM-DD HH:MM): ").strip()

        if not title or not description or not location or not event_date:
            print("All event fields are required")
            return

        event_id = self.system.event_service.add_event(
            title,
            description,
            location,
            event_date,
        )
        while True:
            ticket_name = input("Ticket type name (or B to finish): ").strip()
            if ticket_name.lower() == "b":
                break

            price_text = input("Ticket price: ").strip()
            stock_text = input("Ticket stock: ").strip()
            try:
                price = float(price_text)
                stock = int(stock_text)
            except ValueError:
                print("Price must be a number and stock must be an integer")
                continue

            self.system.event_service.add_ticket_type(
                event_id,
                ticket_name,
                price,
                stock,
            )
            print("Ticket type added")

        print("Event added successfully")

    def show_booking_status_menu(self):
        bookings = self.system.booking_service.get_all_booking_statuses()
        if not bookings:
            print("No bookings found")
            return

        print("\n=== Booking Status ===")
        for booking in bookings:
            print(
                f"Booking #{booking['id']} | User: {booking['username']} | Event: {booking['title']} | "
                f"Ticket: {booking['ticket_type_name']} | Qty: {booking['quantity']} | "
                f"Total: {booking['total_price']:.2f} | Status: {booking['status']} | Expires: {booking['expires_at']}"
            )

    def close(self):
        self.system.close()


def run_cli():
    build_database()
    cli = TicketSystemCLI()
    try:
        cli.run()
    finally:
        cli.close()


if __name__ == "__main__":
    run_cli()
