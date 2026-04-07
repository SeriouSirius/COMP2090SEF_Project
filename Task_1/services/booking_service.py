from models.ticket import Ticket

class BookingService:
    def book_ticket(self, customer, event, row, col):
        seat_manager = event.get_seat_manager()

        if seat_manager.book_seat(row, col):
            #print(f"Booking successful for {customer.get_name()}")
            return Ticket(event, row, col)
        else:
            #rint("Seat already taken")
            return None

    def cancel_ticket(self, event, row, col):
        seat_manager = event.get_seat_manager()

        if seat_manager.cancel_seat(row, col):
            #print("Refund successful")
            pass
        else:
           #print("Cancel failed")
           pass