from ..Task_2.demo import Combine as alds


class Event:
    def __init__(self, name, date, time, location):
        self.name = name
        self.date = date
        self.time = time
        self.location = location

class ticket(Event):
    def __init__(self, event, price, type, stock):
        self.event = event
        self.price = price
        self.type = type
        self.stock = stock


class User(Event):
    def __init__(self, username, email):
        self.username = username
        self.email = email