from ..Task_2.algorithm import Algorithm as al
from ..Task_2.data_structure import DataStructure as dt


class Event:
    def __init__(self, name, date, time, location):
        self.name = name
        self.date = date
        self.time = time
        self.location = location

    def get_event_details(self):
        return f"Event: {self.name}, Date: {self.date}, Time: {self.time}, Location: {self.location}"
    

class Ticket(Event):
    def __init__(self, event, price, type, stock):
        self.event = event
        self.price = price
        self.type = type
        self.stock = stock


class User(Event):
    def __init__(self, username, email):
        self.username = username
        self.email = email
