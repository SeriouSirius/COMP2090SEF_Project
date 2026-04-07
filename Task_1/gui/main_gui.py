import customtkinter as ctk
from tkinter import messagebox
import sys
import os
import json
import qrcode
from pathlib import Path
from PIL import Image, ImageTk

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import Customer, Admin
from models.event import Event
from utils.seat_manager import SeatManager
from services.booking_service import BookingService
from services.payment_service import CreditCardPayment, PayPalPayment

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class EventTickPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EventTick Pro - Professional Ticketing System")
        self.geometry("1280x720")
        self.minsize(1100, 700)
        self.data_dir = Path(__file__).parent.parent / "data"
        os.makedirs(self.data_dir, exist_ok=True)

        self.users = {}
        self.events = []
        self.orders = {}
        self.booking_service = BookingService()

        self.current_username = None
        self.current_user = None

        self.load_all_data()

        self.create_sidebar()
        self.show_login_page()

    def load_all_data(self):
        try:
            with open(os.path.join(self.data_dir, "users.json"), "r", encoding="utf-8") as f:
                users_data = json.load(f)
                for u, d in users_data.items():
                    self.users[u] = d.copy()
                    if d["role"] == "customer":
                        self.users[u]["user_obj"] = Customer(d["name"], is_vip=d.get("is_vip", False))
                    else:
                        self.users[u]["user_obj"] = Admin(d["name"])
        except:
            pass

        if "admin" not in self.users:
            self.users["admin"] = {"password": "admin", "name": "System Administrator", "role": "admin", "is_vip": False}
            self.users["admin"]["user_obj"] = Admin("System Administrator")

        try:
            with open(os.path.join(self.data_dir, "events.json"), "r", encoding="utf-8") as f:
                events_data = json.load(f)
                for ed in events_data:
                    e = Event(ed["name"])
                    e._seat_manager = SeatManager(ed["rows"], ed["cols"])
                    e._seat_manager.seats = ed["seats"]
                    e.price = ed.get("price", 880.0)
                    e.vip_discount = ed.get("vip_discount", 0.0)
                    self.events.append(e)
        except:
            self.events = []

        try:
            with open(os.path.join(self.data_dir, "orders.json"), "r", encoding="utf-8") as f:
                self.orders = json.load(f)
        except:
            pass

    def save_all_data(self):
        users_to_save = {}
        for uname, data in self.users.items():
            users_to_save[uname] = {
                "password": data["password"],
                "name": data["name"],
                "role": data["role"],
                "is_vip": data.get("is_vip", False)
            }
        with open(os.path.join(self.data_dir, "users.json"), "w", encoding="utf-8") as f:
            json.dump(users_to_save, f, ensure_ascii=False, indent=2)

        events_data = []
        for e in self.events:
            sm = e.get_seat_manager()
            events_data.append({
                "name": e.get_name(),
                "rows": sm.rows,
                "cols": sm.cols,
                "seats": sm.seats,
                "price": getattr(e, "price", 880.0),
                "vip_discount": getattr(e, "vip_discount", 0.0)
            })
        with open(os.path.join(self.data_dir, "events.json"), "w", encoding="utf-8") as f:
            json.dump(events_data, f, ensure_ascii=False, indent=2)

        with open(os.path.join(self.data_dir, "orders.json"), "w", encoding="utf-8") as f:
            json.dump(self.orders, f, ensure_ascii=False, indent=2)

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(self.sidebar, text="EventTick Pro", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=30)

        self.user_label = ctk.CTkLabel(self.sidebar, text="", font=ctk.CTkFont(size=14))
        self.user_label.pack(pady=10)

        ctk.CTkButton(self.sidebar, text="Home", command=self.show_home_page, height=50, font=ctk.CTkFont(size=16)).pack(pady=8, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Browse Events", command=self.show_events_page, height=50, font=ctk.CTkFont(size=16)).pack(pady=8, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="My Orders", command=self.show_orders_page, height=50, font=ctk.CTkFont(size=16)).pack(pady=8, padx=20, fill="x")

        self.btn_admin = ctk.CTkButton(self.sidebar, text="Admin Panel", command=self.show_admin_page, height=50, font=ctk.CTkFont(size=16), fg_color="#27ae60")

        self.btn_account = ctk.CTkButton(self.sidebar, text="Login", command=self.toggle_login, height=50, fg_color="#27ae60", font=ctk.CTkFont(size=16))
        self.btn_account.pack(side="bottom", pady=30, padx=20, fill="x")

    def refresh_sidebar(self):
        if self.current_username:
            name = self.users[self.current_username]["name"]
            self.user_label.configure(text=f"{name}", text_color="#f1c40f")
            self.btn_account.configure(text="Logout", fg_color="#e74c3c")
            if self.current_username == "admin":
                self.btn_admin.pack(pady=8, padx=20, fill="x")
            else:
                self.btn_admin.pack_forget()
        else:
            self.user_label.configure(text="")
            self.btn_account.configure(text="Login", fg_color="#27ae60")
            self.btn_admin.pack_forget()

    def toggle_login(self):
        if self.current_username:
            self.logout()
        else:
            self.show_login_page()

    def show_login_page(self):
        self.clear_main_area()
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=40, pady=40)
        ctk.CTkLabel(frame, text="EventTick Pro", font=ctk.CTkFont(size=42, weight="bold")).pack(pady=30)
        ctk.CTkLabel(frame, text="Login to Your Account", font=ctk.CTkFont(size=20)).pack(pady=10)
        ctk.CTkLabel(frame, text="Username", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=60, pady=(20,5))
        self.username_entry = ctk.CTkEntry(frame, width=420, height=50, placeholder_text="Enter username")
        self.username_entry.pack(pady=8, padx=60)
        ctk.CTkLabel(frame, text="Password", font=ctk.CTkFont(size=16)).pack(anchor="w", padx=60, pady=(10,5))
        self.password_entry = ctk.CTkEntry(frame, width=420, height=50, placeholder_text="Password", show="•")
        self.password_entry.pack(pady=8, padx=60)
        ctk.CTkButton(frame, text="Login", command=self.login, width=420, height=55, font=ctk.CTkFont(size=18)).pack(pady=25, padx=60)
        ctk.CTkButton(frame, text="Register New Account", command=self.show_register_page, width=420, height=50, fg_color="#27ae60", font=ctk.CTkFont(size=18)).pack(pady=5, padx=60)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if username not in self.users or self.users[username]["password"] != password:
            messagebox.showerror("Login Failed", "Incorrect username or password!")
            return
        self.current_username = username
        self.current_user = self.users[username]["user_obj"]
        messagebox.showinfo("Login Successful", f"Welcome back, {self.users[username]['name']}!")
        self.refresh_sidebar()
        self.show_home_page()

    def logout(self):
        self.current_username = None
        self.current_user = None
        self.refresh_sidebar()
        self.show_login_page()

    def show_register_page(self):
        reg = ctk.CTkToplevel(self)
        reg.title("Register New Account")
        reg.geometry("520x480")
        reg.grab_set()
        ctk.CTkLabel(reg, text="Register New Account", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        ctk.CTkLabel(reg, text="Username").pack(anchor="w", padx=40, pady=(10,0))
        username_entry = ctk.CTkEntry(reg, width=400, height=45)
        username_entry.pack(pady=5, padx=40)
        ctk.CTkLabel(reg, text="Full Name").pack(anchor="w", padx=40, pady=(10,0))
        name_entry = ctk.CTkEntry(reg, width=400, height=45)
        name_entry.pack(pady=5, padx=40)
        ctk.CTkLabel(reg, text="Password").pack(anchor="w", padx=40, pady=(10,0))
        pw_entry = ctk.CTkEntry(reg, width=400, height=45, show="•")
        pw_entry.pack(pady=5, padx=40)
        def do_register():
            u = username_entry.get().strip()
            n = name_entry.get().strip()
            p = pw_entry.get().strip()
            if not u or not n or not p:
                messagebox.showwarning("Error", "Please fill in all fields")
                return
            if u in self.users:
                messagebox.showerror("Error", "Username already exists")
                return
            customer = Customer(n, is_vip=False)
            self.users[u] = {"password": p, "name": n, "role": "customer", "is_vip": False, "user_obj": customer}
            self.save_all_data()
            messagebox.showinfo("Registration Successful", f"Account {u} has been created!")
            reg.destroy()
        ctk.CTkButton(reg, text="Create Account", command=do_register, height=50, width=400).pack(pady=30)

    def show_admin_page(self):
        if self.current_username != "admin":
            return
        self.clear_main_area()
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=30, pady=20)
        ctk.CTkLabel(frame, text="Admin Panel", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=15)
        ctk.CTkLabel(frame, text="Add New Event", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=20, pady=(20,5))
        ctk.CTkLabel(frame, text="Event Name").pack(anchor="w", padx=40)
        self.new_event_name = ctk.CTkEntry(frame, width=500, height=40)
        self.new_event_name.pack(pady=5, padx=40)
        ctk.CTkLabel(frame, text="Seat Size (Rows x Columns)").pack(anchor="w", padx=40, pady=(10,5))
        size_frame = ctk.CTkFrame(frame)
        size_frame.pack(pady=5, padx=40)
        self.rows_entry = ctk.CTkEntry(size_frame, width=100, height=40, placeholder_text="Rows")
        self.rows_entry.pack(side="left", padx=5)
        self.cols_entry = ctk.CTkEntry(size_frame, width=100, height=40, placeholder_text="Columns")
        self.cols_entry.pack(side="left", padx=5)
        ctk.CTkLabel(frame, text="Ticket Price (HKD)").pack(anchor="w", padx=40, pady=(15,5))
        self.price_entry = ctk.CTkEntry(frame, width=500, height=40)
        self.price_entry.insert(0, "880")
        self.price_entry.pack(pady=5, padx=40)
        ctk.CTkLabel(frame, text="VIP Discount Rate (%)").pack(anchor="w", padx=40, pady=(10,5))
        self.discount_entry = ctk.CTkEntry(frame, width=500, height=40)
        self.discount_entry.insert(0, "15")
        self.discount_entry.pack(pady=5, padx=40)
        ctk.CTkButton(frame, text="Add Event", command=self.add_new_event, height=50, width=500).pack(pady=20)
        ctk.CTkLabel(frame, text="VIP Management", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=20, pady=(30,5))
        for uname, data in list(self.users.items()):
            if data["role"] == "customer":
                text = f"{uname} ({data['name']}) → {'VIP' if data.get('is_vip') else 'Make VIP'}"
                color = "#f1c40f" if data.get("is_vip") else "#27ae60"
                ctk.CTkButton(frame, text=text, command=lambda u=uname: self.promote_to_vip(u), fg_color=color).pack(pady=5, padx=40, fill="x")

    def add_new_event(self):
        name = self.new_event_name.get().strip()
        try:
            rows = int(self.rows_entry.get())
            cols = int(self.cols_entry.get())
            price = float(self.price_entry.get())
            vip_discount = float(self.discount_entry.get())
        except:
            messagebox.showerror("Error", "Please enter valid numbers")
            return
        if not name:
            messagebox.showerror("Error", "Please enter event name")
            return
        new_event = Event(name)
        new_event._seat_manager = SeatManager(rows, cols)
        new_event.price = price
        new_event.vip_discount = vip_discount
        self.events.append(new_event)
        self.save_all_data()
        messagebox.showinfo("Success", f"Event '{name}' has been added!")
        self.new_event_name.delete(0, "end")

    def promote_to_vip(self, username):
        if username in self.users:
            self.users[username]["is_vip"] = True
            self.users[username]["user_obj"]._is_vip = True
            self.save_all_data()
            messagebox.showinfo("Success", f"{username} is now a VIP member!")
            self.show_admin_page()

    def show_home_page(self):
        self.clear_main_area()
        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=40, pady=40)
        if self.current_username:
            ctk.CTkLabel(frame, text=f"Welcome back, {self.users[self.current_username]['name']}!", font=ctk.CTkFont(size=36, weight="bold")).pack(pady=100)
            if self.users[self.current_username].get("is_vip"):
                ctk.CTkLabel(frame, text="VIP Exclusive Benefits Activated", text_color="#f1c40f", font=ctk.CTkFont(size=22)).pack()
        else:
            ctk.CTkLabel(frame, text="Welcome to EventTick Pro", font=ctk.CTkFont(size=36, weight="bold")).pack(pady=100)
            ctk.CTkLabel(frame, text="Click Login in the sidebar to access full features", font=ctk.CTkFont(size=20)).pack(pady=20)

    def show_events_page(self):
        self.clear_main_area()
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(frame, text="Browse Events", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)
        if not self.events:
            ctk.CTkLabel(frame, text="No events available yet.\nAdmin can add new events.", font=ctk.CTkFont(size=20)).pack(pady=100)
            return
        for event in self.events:
            card = ctk.CTkFrame(frame)
            card.pack(fill="x", pady=12, padx=20)
            ctk.CTkLabel(card, text=event.get_name(), font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15, anchor="w", padx=30)
            seat_info = f"{event.get_seat_manager().rows}×{event.get_seat_manager().cols} seats"
            ctk.CTkLabel(card, text=seat_info).pack(anchor="w", padx=30)
            if self.current_username:
                ctk.CTkButton(card, text="Buy Tickets", command=lambda e=event: self.show_seat_map(e), width=180, height=50).pack(side="right", padx=30, pady=15)
            else:
                ctk.CTkButton(card, text="Login to Buy", command=self.toggle_login, width=180, height=50, fg_color="gray").pack(side="right", padx=30, pady=15)

    def show_seat_map(self, event):
        win = ctk.CTkToplevel(self)
        win.title(f"Seat Selection - {event.get_name()}")
        win.geometry("1100x750")
        win.grab_set()
        ctk.CTkLabel(win, text=f"{event.get_name()}\nSeat Map", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=15)
        sm = event.get_seat_manager()
        grid = ctk.CTkFrame(win)
        grid.pack(pady=20)
        self.temp_buttons = {}
        for r in range(sm.rows):
            for c in range(sm.cols):
                seat_num = f"{chr(65 + r)}{c + 1}"
                color = "#27ae60" if sm.seats[r][c] == 0 else "#e74c3c"
                btn = ctk.CTkButton(grid, text=seat_num, width=75, height=75, fg_color=color,
                                    command=lambda rr=r, cc=c, smm=sm, ev=event, w=win: self.confirm_order(rr, cc, smm, ev, w))
                btn.grid(row=r, column=c, padx=4, pady=4)
                self.temp_buttons[(r, c)] = btn
        ctk.CTkLabel(win, text="Available   Sold", font=ctk.CTkFont(size=16)).pack(pady=10)

    def confirm_order(self, row, col, seat_manager, event, window):
        if seat_manager.seats[row][col] != 0:
            messagebox.showerror("Error", "This seat has already been booked!")
            return
        confirm_win = ctk.CTkToplevel(self)
        confirm_win.title("Order Confirmation")
        confirm_win.geometry("600x550")
        confirm_win.grab_set()
        ctk.CTkLabel(confirm_win, text="Order Confirmation", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        ctk.CTkLabel(confirm_win, text=f"Event: {event.get_name()}", font=ctk.CTkFont(size=18)).pack(pady=5)
        seat_str = f"{chr(65 + row)}{col + 1}"
        ctk.CTkLabel(confirm_win, text=f"Seat: {seat_str}", font=ctk.CTkFont(size=18)).pack(pady=5)
        price = getattr(event, "price", 880.0)
        discount = getattr(event, "vip_discount", 0.0)
        final_price = price * (1 - discount / 100) if self.current_username and self.users[self.current_username].get("is_vip") else price
        ctk.CTkLabel(confirm_win, text=f"Price: HKD {final_price:.2f}", font=ctk.CTkFont(size=18)).pack(pady=5)
        if self.current_username and self.users[self.current_username].get("is_vip"):
            ctk.CTkLabel(confirm_win, text=f"VIP Discount: {discount}%", font=ctk.CTkFont(size=16), text_color="#f1c40f").pack(pady=5)
        ctk.CTkButton(confirm_win, text="Proceed to Payment", command=lambda: self.process_payment(row, col, seat_manager, event, window, confirm_win), height=50, width=400).pack(pady=30)

    def process_payment(self, row, col, seat_manager, event, seat_win, confirm_win):
        if messagebox.askyesno("Payment Method", "Pay with Credit Card?\n(No = PayPal)"):
            CreditCardPayment().pay(880)
        else:
            PayPalPayment().pay(880)
        seat_manager.book_seat(row, col)
        seat_str = f"{chr(65 + row)}{col + 1}"
        if self.current_username not in self.orders:
            self.orders[self.current_username] = []
        order_number = "TICKET-" + str(len(self.orders[self.current_username]) + 1000)
        self.orders[self.current_username].append((event.get_name(), seat_str, "Paid", order_number))
        self.save_all_data()
        confirm_win.destroy()
        seat_win.destroy()
        self.show_ticket_success(event.get_name(), seat_str, order_number)

    def show_ticket_success(self, event_name, seat_str, order_number):
        success = ctk.CTkToplevel(self)
        success.title("Purchase Successful")
        success.geometry("700x650")
        success.grab_set()
        ctk.CTkLabel(success, text="Purchase Successful!", font=ctk.CTkFont(size=32, weight="bold"), text_color="#27ae60").pack(pady=20)
        ctk.CTkLabel(success, text=f"Event: {event_name}", font=ctk.CTkFont(size=20)).pack(pady=5)
        ctk.CTkLabel(success, text=f"Seat: {seat_str}", font=ctk.CTkFont(size=20)).pack(pady=5)
        ctk.CTkLabel(success, text=f"Order Number: {order_number}", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        qr_data = f"EventTick Order: {order_number} | {event_name} | {seat_str}"
        qr = qrcode.make(qr_data)
        qr = qr.resize((300, 300))
        qr_img = ImageTk.PhotoImage(qr)
        qr_label = ctk.CTkLabel(success, text="")
        qr_label.image = qr_img
        qr_label.configure(image=qr_img)
        qr_label.pack(pady=20)
        ctk.CTkLabel(success, text="Scan QR Code for Ticket Verification", font=ctk.CTkFont(size=16)).pack(pady=5)
        ctk.CTkButton(success, text="Close", command=success.destroy, width=300, height=50).pack(pady=20)

    def show_orders_page(self):
        self.clear_main_area()
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=40, pady=20)
        ctk.CTkLabel(frame, text="My Orders", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)
        if self.current_username not in self.orders or not self.orders[self.current_username]:
            ctk.CTkLabel(frame, text="You have no orders yet", font=ctk.CTkFont(size=20)).pack(pady=100)
            return
        for order in self.orders[self.current_username]:
            card = ctk.CTkFrame(frame)
            card.pack(fill="x", pady=8, padx=20)
            ctk.CTkLabel(card, text=f"Event: {order[0]}\nSeat: {order[1]}\nStatus: {order[2]}\nTicket: {order[3]}", font=ctk.CTkFont(size=16), justify="left").pack(pady=15, padx=20, anchor="w")

    def clear_main_area(self):
        for widget in self.winfo_children():
            if widget != self.sidebar:
                widget.destroy()

    def destroy(self):
        self.save_all_data()
        super().destroy()

if __name__ == "__main__":
    app = EventTickPro()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()