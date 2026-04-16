# Run MEEEEEEEEEEEEEEEEEEEEEEEEEEEE

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Task_1.build_db import build_db
from Task_1.main import TicketSystem


class TicketSystemCLIUI:
    def __init__(self):
        self.system = TicketSystem()
        # TODO: add color support maybe

    def run(self):
        while True:
            self.system.booking_sys.process_expired_bookings()
            if self.system.current_user is None:
                if not self.auth_menu():
                    break
            else:
                self.main_menu()

    def auth_menu(self):
        print("\n=== Event Ticket Selling System ===")
        print("1. Login")
        print("2. Register")
        print("3. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            self.login()
        elif choice == "2":
            self.register()
        elif choice == "3":
            self.system.close()
            return False
        else:
            print("Invalid choice")
        return True

    def login(self):
        username = input("Username: ").strip()
        pwd = input("Password: ").strip()
        print("checking login...")
        user, message = self.system.auth_sys.login(username, pwd)
        print(message)
        if user:
            self.system.current_user = user

    def register(self):
        username = input("Username: ").strip()
        pwd = input("Password: ").strip()
        paymentPin = input("Payment PIN (4 digits): ").strip()
        user, message = self.system.auth_sys.register(username, pwd, paymentPin)
        print(message)
        if user:
            self.system.current_user = user

    def main_menu(self):
        currentUser = self.system.current_user
        print(f"\n=== Main Menu ({currentUser.username}) ===")
        print("1. Browse events")
        print("2. Check balance")
        print("3. Check tickets")
        print("4. Logout")
        if currentUser.is_admin:
            print("5. Add events")
            print("6. Check bookings status")

        choice = input("Choose: ").strip()
        if choice == "1":
            self.browse_events()
        elif choice == "2":
            self.balance_menu()
        elif choice == "3":
            self.ticket_menu()
        elif choice == "4":
            self.system.current_user = None
            print("Logout success")
        elif choice == "5" and currentUser.is_admin:
            self.add_event_menu()
        elif choice == "6" and currentUser.is_admin:
            self.booking_status_menu()
        else:
            print("Invalid choice")

    def browse_events(self):
        events = self.system.event_sys.list_events()
        if not events:
            print("No events found")
            return

        print("\n=== Events ===")
        for index, event in enumerate(events, start=1):
            print(f"{index}. {event.title} | {event.location} | {event.event_date}")

        choice = input("Choose event number or B to back: ").strip()
        if choice == "b" or choice == "B":
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(events):
            print("Invalid event choice")
            return

        event = events[int(choice) - 1]
        self.event_detail_menu(event)

    def event_detail_menu(self, event):
        print("\n=== Event Detail ===")
        print(f"Title: {event.title}")
        print(f"Description: {event.description}")
        print(f"Location: {event.location}")
        print(f"Date: {event.event_date}")

        ticketTypes = self.system.event_sys.get_ticket_types(event.event_id)
        if not ticketTypes:
            print("No ticket types for this event")
            return

        print("\nTicket Types:")
        for index, ticket_type in enumerate(ticketTypes, start=1):
            print(
                f"{index}. {ticket_type.name} | Price: {ticket_type.price:.2f} | "
                f"Stock: {ticket_type.stock}"
            )

        ticket_choice = input("Choose ticket type number or B to back: ").strip()
        if ticket_choice == "b" or ticket_choice == "B":
            return
        if not ticket_choice.isdigit() or int(ticket_choice) < 1 or int(ticket_choice) > len(ticketTypes):
            print("Invalid ticket type choice")
            return

        quantityText = input("Enter quantity: ").strip()
        if not quantityText.isdigit():
            print("Quantity must be a number")
            return

        quantity = int(quantityText)
        ticket_type = ticketTypes[int(ticket_choice) - 1]
        booking, message = self.system.booking_sys.create_booking(
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
            paymentPin = input("Enter Payment PIN: ").strip()
            _, paymentMsg = self.system.booking_sys.pay_booking(
                booking.booking_id,
                self.system.current_user.user_id,
                paymentPin,
            )
            print(paymentMsg)
            self.system.current_user = self.system.auth_sys.get_user_by_id(
                self.system.current_user.user_id
            )

    def balance_menu(self):
        self.system.current_user = self.system.auth_sys.get_user_by_id(
            self.system.current_user.user_id
        )
        print(f"\nCurrent balance: {self.system.current_user.balance:.2f}")
        print("1. Add balance")
        print("2. Back to menu")
        choice = input("Choose: ").strip()

        if choice == "1":
            amountText = input("Enter amount: ").strip()
            try:
                amount = float(amountText)
            except ValueError:
                print("Amount must be a number")
                return

            if amount <= 0:
                print("Amount must be greater than 0")
                return

            paymentPin = input("Enter Payment PIN: ").strip()
            pin_ok, pin_message = self.system.auth_sys.verify_payment_pin(
                self.system.current_user.user_id,
                paymentPin,
            )
            if not pin_ok:
                print(pin_message)
                return

            newBalance = self.system.balance_sys.add_balance(
                self.system.current_user.user_id,
                amount,
            )
            self.system.current_user = self.system.auth_sys.get_user_by_id(
                self.system.current_user.user_id
            )
            print("Add balance success")
            print(f"New balance: {newBalance:.2f}")
        elif choice == "2":
            return
        else:
            print("Invalid choice")

    def ticket_menu(self):
        bookings = self.system.booking_sys.get_user_bookings(
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
        if choice == "b" or choice == "B":
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
            print(f"Pay before: {booking['expire_time']}")
            pay_now = input("Pay now? (y/n): ").strip().lower()
            if pay_now == "y":
                paymentPin = input("Enter Payment PIN: ").strip()
                _, paymentMsg = self.system.booking_sys.pay_booking(
                    booking["id"],
                    self.system.current_user.user_id,
                    paymentPin,
                )
                print(paymentMsg)
                self.system.current_user = self.system.auth_sys.get_user_by_id(
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
            print("All event fields are required to fill in")
            return

        eventId = self.system.event_sys.add_event(
            title,
            description,
            location,
            event_date,
        )
        while True:
            ticket_name = input("Ticket type name (or B to finish): ").strip()
            if ticket_name.lower() == "b":
                break

            set_price = input("Ticket price: ").strip()
            set_stock = input("Ticket stock: ").strip()
            try:
                price = float(set_price)
                stock = int(set_stock)
            except ValueError:
                print("Price must be a floating number and stock must be an integer")
                continue

            self.system.event_sys.add_ticket_type(
                eventId,
                ticket_name,
                price,
                stock,
            )
            print("Ticket type added")

        print("Event added successfully")

    def booking_status_menu(self):
        bookings = self.system.booking_sys.get_booking_statuses()
        if not bookings:
            print("No bookings found")
            return

        print("\n=== Booking Status ===")
        for booking in bookings:
            print(
                f"Booking #{booking['id']} | User: {booking['username']} | Event: {booking['title']} | "
                f"Ticket: {booking['ticket_type_name']} | Qty: {booking['quantity']} | "
                f"Total: {booking['total_price']:.2f} | Status: {booking['status']} | Expires: {booking['expire_time']}"
            )

    def close(self):
        self.system.close()


def run_cli():
    build_db()
    cli = TicketSystemCLIUI()
    try:
        cli.run()
    finally:
        cli.close()


if __name__ == "__main__":
    run_cli()
