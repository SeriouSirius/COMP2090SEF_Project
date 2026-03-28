class SeatManager:
    def __init__(self, rows=5, cols=5):
        self.rows = rows
        self.cols = cols
        self.seats = [[0 for _ in range(cols)] for _ in range(rows)]

    def display_seats(self):
        print("\n====== SEAT MAP ======")
        print("     " + "  ".join(f"{i+1}" for i in range(self.cols)))

        for i, row in enumerate(self.seats):
            row_label = chr(65 + i)
            row_display = []

            for seat in row:
                if seat == 0:
                    row_display.append("[O]")
                else:
                    row_display.append("[X]")

            print(f"{row_label}   " + " ".join(row_display))

        print("\nO = Available   X = Booked")

    def book_seat(self, row, col):
        if not self._valid(row, col):
            print("Invalid seat")
            return False

        if self.seats[row][col] == 0:
            self.seats[row][col] = 1
            return True
        return False

    def cancel_seat(self, row, col):
        if not self._valid(row, col):
            print("Invalid seat")
            return False

        if self.seats[row][col] == 1:
            self.seats[row][col] = 0
            return True
        return False

    def _valid(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols
    
    def display_with_selection(self, sel_row=None, sel_col=None):
        print("\n====== SEAT MAP ======")
        print("     " + "  ".join(f"{i+1}" for i in range(self.cols)))

        for i, row in enumerate(self.seats):
            row_label = chr(65 + i)
            row_display = []

            for j, seat in enumerate(row):
                if i == sel_row and j == sel_col:
                    row_display.append("[*]")
                elif seat == 0:
                    row_display.append("[O]")
                else:
                    row_display.append("[X]")

            print(f"{row_label}   " + " ".join(row_display))

        print("\nO = Available   X = Booked   * = Selected")