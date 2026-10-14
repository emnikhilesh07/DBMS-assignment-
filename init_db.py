import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")

def init_database():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Books table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        book_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT UNIQUE NOT NULL,
        genre TEXT NOT NULL,
        publication_year INTEGER,
        total_copies INTEGER NOT NULL DEFAULT 1,
        available_copies INTEGER NOT NULL DEFAULT 1,
        digital_available INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Members table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        member_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        membership_no TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        status TEXT NOT NULL DEFAULT 'Active',
        joined_date DATE NOT NULL
    );
    """)

    # 3. Circulation (Loans & Returns) table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS circulation (
        loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        loan_date DATE NOT NULL,
        due_date DATE NOT NULL,
        return_date DATE,
        status TEXT NOT NULL CHECK(status IN ('Active', 'Returned', 'Overdue')),
        FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
    );
    """)

    # 4. Reservations (Holds) table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        reservation_date DATE NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Waiting', 'Fulfilled', 'Cancelled')),
        notes TEXT,
        FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
    );
    """)

    # 5. Fines table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fines (
        fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Outstanding', 'Paid', 'Waived')),
        reason TEXT NOT NULL,
        issued_date DATE NOT NULL,
        paid_date DATE,
        FOREIGN KEY (loan_id) REFERENCES circulation(loan_id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
    );
    """)

    # 6. Digital Access table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS digital_access (
        access_id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        device_type TEXT DEFAULT 'Web Reader',
        session_minutes INTEGER DEFAULT 25,
        FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
    );
    """)

    # 7. Activity Ledger table (Audit trail for the live feed shown in the UI)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_ledger (
        ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_name TEXT NOT NULL,
        action_text TEXT NOT NULL,
        category TEXT NOT NULL CHECK(category IN ('Loan', 'Return', 'Reservation', 'Digital Access', 'Fine')),
        event_time TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed initial data matching the exact UI in the screenshot
    # Screenshot stats:
    # Titles in catalog: 6 (12 copies across editions)
    # Available to borrow: 10 (2 active loans: 1 active, 1 overdue)
    # Active members: 4 (2 holds waiting)
    # Outstanding fines: ₹30.00 (1 overdue loan)
    
    books_data = [
        ("Atomic Habits", "James Clear", "978-0735211292", "Self-Help / Psychology", 2018, 2, 1, 1),
        ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "978-0062316097", "History / Anthropology", 2014, 2, 2, 1),
        ("1984", "George Orwell", "978-0451524935", "Dystopian Classic", 1949, 2, 1, 1),
        ("The Psychology of Money", "Morgan Housel", "978-0857197689", "Finance & Behaviour", 2020, 2, 2, 1),
        ("Deep Work", "Cal Newport", "978-1455586691", "Productivity", 2016, 2, 2, 1),
        ("To Kill a Mockingbird", "Harper Lee", "978-0061120084", "Classic Fiction", 1960, 2, 2, 1)
    ]
    cursor.executemany("""
        INSERT INTO books (title, author, isbn, genre, publication_year, total_copies, available_copies, digital_available)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, books_data)

    members_data = [
        ("Aarav Mehta", "LIB-2024-001", "aarav.mehta@readingroom.org", "+91 98765 43210", "Active", "2024-01-15"),
        ("Riya Patel", "LIB-2024-002", "riya.patel@readingroom.org", "+91 98765 43211", "Active", "2024-02-10"),
        ("Kabir Varma", "LIB-2024-003", "kabir.varma@readingroom.org", "+91 98765 43212", "Active", "2024-03-01"),
        ("Priya Sharma", "LIB-2024-004", "priya.sharma@readingroom.org", "+91 98765 43213", "Active", "2024-04-18")
    ]
    cursor.executemany("""
        INSERT INTO members (full_name, membership_no, email, phone, status, joined_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, members_data)

    # Circulation data:
    # 1 overdue copy of Atomic Habits (Aarav Mehta)
    # 1 active loan of 1984 (Priya Sharma)
    # 1 returned copy of Sapiens (Kabir Varma)
    today = datetime.now()
    two_weeks_ago = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    overdue_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    due_in_future = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    circulation_data = [
        (1, 1, two_weeks_ago, overdue_date, None, 'Overdue'), # Aarav Mehta, Atomic Habits
        (3, 4, today_str, due_in_future, None, 'Active'),      # Priya Sharma, 1984
        (2, 3, two_weeks_ago, today_str, today_str, 'Returned') # Kabir Varma, Sapiens
    ]
    cursor.executemany("""
        INSERT INTO circulation (book_id, member_id, loan_date, due_date, return_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, circulation_data)

    # Fines data: Aarav Mehta has an overdue fine of ₹30.00
    cursor.execute("""
        INSERT INTO fines (loan_id, member_id, amount, status, reason, issued_date, paid_date)
        VALUES (1, 1, 30.00, 'Outstanding', 'Overdue: Atomic Habits (6 days @ ₹5/day)', ?, NULL)
    """, (today_str,))

    # Reservations data: 2 holds waiting (Riya Patel for Sapiens, Kabir Varma for Atomic Habits)
    reservations_data = [
        (2, 2, today_str, 'Waiting', 'Preferred hardcover edition'),
        (1, 3, today_str, 'Waiting', 'Waiting for Aarav return')
    ]
    cursor.executemany("""
        INSERT INTO reservations (book_id, member_id, reservation_date, status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, reservations_data)

    # Digital access data:
    # 2 digital visits today
    digital_data = [
        (3, 4, f"{today_str} 13:40:00", "Web Reader", 35),
        (1, 2, f"{today_str} 10:15:00", "Tablet App", 20)
    ]
    cursor.executemany("""
        INSERT INTO digital_access (book_id, member_id, accessed_at, device_type, session_minutes)
        VALUES (?, ?, ?, ?, ?)
    """, digital_data)

    # Activity ledger matching the exact timeline entries in screenshot:
    # 1. Aarav Mehta has an overdue copy of Atomic Habits (Loan / Overdue) 01:53 PM
    # 2. Riya Patel placed a reservation for Sapiens (Reservation) 01:53 PM
    # 3. Kabir Varma returned Sapiens (Loan / Return) 01:52 PM
    # 4. Priya Sharma opened the digital edition of 1984 (Digital Access) 01:40 PM
    # 5. Priya Sharma checked out 1984 (Loan) 01:38 PM
    activities = [
        ("Aarav Mehta", "has an overdue copy of Atomic Habits", "Loan", "01:53 PM"),
        ("Riya Patel", "placed a reservation for Sapiens", "Reservation", "01:53 PM"),
        ("Kabir Varma", "returned Sapiens", "Return", "01:52 PM"),
        ("Priya Sharma", "opened the digital edition of 1984", "Digital Access", "01:40 PM"),
        ("Priya Sharma", "checked out 1984", "Loan", "01:38 PM")
    ]
    cursor.executemany("""
        INSERT INTO activity_ledger (member_name, action_text, category, event_time)
        VALUES (?, ?, ?, ?)
    """, activities)

    conn.commit()
    conn.close()
    print("Database library.db successfully initialized with schema and seed data.")

if __name__ == "__main__":
    init_database()
