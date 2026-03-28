def show_menu():
    print("1. Book Ticket")
    print("2. Cancel Ticket")
    print("3. Exit")


def choose_seat():
    while True:
        row = input("Enter row (A-E): ").upper()
        col = int(input("Enter column (1-5): "))

        row_index = ord(row) - 65
        col_index = col - 1

        if 0 <= row_index < 5 and 0 <= col_index < 5:
            return row_index, col_index
        else:
            print("Invalid seat, try again.")