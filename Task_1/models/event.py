from utils.seat_manager import SeatManager

class Event:
    def __init__(self, name):
        self._name = name
        self._seat_manager = SeatManager()

    def get_name(self):
        return self._name

    def get_seat_manager(self):
        return self._seat_manager