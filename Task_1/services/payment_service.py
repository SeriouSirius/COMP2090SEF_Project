class Payment:
    def pay(self, amount):
        raise NotImplementedError


class CreditCardPayment(Payment):
    def pay(self, amount):
        print(f"Paid {amount} by Credit Card")


class PayPalPayment(Payment):
    def pay(self, amount):
        print(f"Paid {amount} by PayPal")