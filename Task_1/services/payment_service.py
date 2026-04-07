class Payment:
    def pay(self, amount):
        raise NotImplementedError


class CreditCardPayment(Payment):
    def pay(self, amount):
        #print(f"Paid {amount} by Credit Card")
        pass

class PayPalPayment(Payment):
    def pay(self, amount):
        #print(f"Paid {amount} by PayPal")
        pass