class User:
    def __init__(self, name):
        self._name = name

    def get_name(self):
        return self._name


class Customer(User):
    def __init__(self, name, is_vip=False):
        super().__init__(name)
        self._is_vip = is_vip

    def is_vip(self):
        return self._is_vip


class Admin(User):
    def create_event(self, event):
        print(f"{self._name} created event {event.get_name()}")