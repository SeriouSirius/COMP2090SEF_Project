class Order:
    def __init__(self, customer):
        self._customer = customer
        self._tickets = []

    def add_ticket(self, ticket):
        self._tickets.append(ticket)

    def remove_ticket(self, index):
        if 0 <= index < len(self._tickets):
            return self._tickets.pop(index)

    def show_order(self):
        print(f"Order for {self._customer.get_name()}")
        for i, t in enumerate(self._tickets):
            print(f"{i}: ", end="")
            t.display_ticket()