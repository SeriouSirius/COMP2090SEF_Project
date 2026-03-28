from models.user import Customer, Admin
from models.event import Event
from models.order import Order
from services.booking_service import BookingService
from services.payment_service import CreditCardPayment
from services.queue_service import QueueService
import cli_ui


def main():
    print("=== Ticket Booking System ===")
    event_name = input("Enter event name: ")
    event = Event(event_name)

    admin = Admin("Admin")
    admin.create_event(event)

    queue = QueueService()

    print("\n--- Add Users to Queue ---")
    while True:
        name = input("Enter your name (or 'q' to stop): ")

        if name.lower() == 'q':
            break

        is_vip_input = input("VIP? (y/n): ")
        is_vip = is_vip_input.lower() == "y"

        priority = 1 if is_vip else 5

        queue.add_user(Customer(name, is_vip), priority)

    booking_service = BookingService()

    print("\n--- Start Serving Queue ---")

    while True:
        user = queue.get_next_user()
        if not user:
            print("No more users in queue.")
            break

        print(f"\nNow serving: {user.get_name()}")

        order = Order(user)

        while True:
            cli_ui.show_menu()
            choice = input("Choose: ")

            if choice == "1":
                seat_manager = event.get_seat_manager()

                seat_manager.display_seats()

                print("Tip: Choose seat like A1, B3")
                row, col = cli_ui.choose_seat()
                seat_manager.display_with_selection(row, col)

                ticket = booking_service.book_ticket(user, event, row, col)

                if ticket:
                    order.add_ticket(ticket)

                    payment = CreditCardPayment()
                    payment.pay(100)

                    order.show_order()

            elif choice == "2":
                row, col = cli_ui.choose_seat()
                booking_service.cancel_ticket(event, row, col)

            elif choice == "3":
                break

            else:
                print("Invalid choice")


if __name__ == "__main__":
    main()