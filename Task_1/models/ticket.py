class Ticket:
    def __init__(self, event, row, col):
        self._event = event
        self._row = row
        self._col = col

    def display_ticket(self):
        print(f"Event: {self._event.get_name()}, Seat: {chr(65+self._row)}{self._col + 1}")