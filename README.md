# COMP2090SEF Project - Pre-submission

**Group:** Group 103

**Members:** WONG Shing Chak (13881205),FAN Hang Lok (14257260),Li Vincent (13494788)

Preliminary code for both tasks.

## Task 1: OOP-based Ticket Selling System
- Folder: `Task_1/`
- Current: OOP ticket selling system with CLI and Flask API for GUI integration
- CLI Run: `python Task_1/cli_ui.py`

### Task 1 GUI + API Run
1. Install dependencies:
	- `python -m pip install flask pytest`
2. Build or refresh database:
	- `python Task_1/build_db.py`
3. Start Flask server (serves API and GUI):
	- `python Task_1/api_server.py`
4. Open in browser:
	- `http://127.0.0.1:5000/`

### GUI Features
- Single-page GUI matching CLI menu flow
- User and admin menu parity
- Real backend integration with SQLite data
- Live checkout countdown timer for pending booking payment
- Registration requires a 4-digit Payment PIN
- Checkout payment requires entering the correct Payment PIN
- Add-balance requires entering the correct Payment PIN
- GUI auto-refreshes once after successful payment
- Existing users created before this feature are assigned default PIN 0000 after migration

## Task 2: Self-study Data Structure + Algorithm
- Folder: `Task_2/`
- Preliminary: Circular Queue + Hierarchical Timing Wheels implementations  

