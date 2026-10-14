-- =====================================================================
-- THE READING ROOM — LIBRARY OPERATIONS DATABASE SCHEMA & SEED DATA
-- Database Engine: SQLite / ANSI SQL Compatible
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. DROP EXISTING TABLES (In reverse dependency order)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS activity_ledger;
DROP TABLE IF EXISTS digital_access;
DROP TABLE IF EXISTS fines;
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS circulation;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS books;

-- ---------------------------------------------------------------------
-- 2. DDL: TABLE DEFINITIONS
-- ---------------------------------------------------------------------

-- Table 1: Books Catalog
CREATE TABLE books (
    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    isbn TEXT UNIQUE NOT NULL,
    genre TEXT NOT NULL,
    publication_year INTEGER,
    total_copies INTEGER NOT NULL DEFAULT 1,
    available_copies INTEGER NOT NULL DEFAULT 1,
    digital_available INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (total_copies >= 0),
    CHECK (available_copies <= total_copies)
);

-- Table 2: Library Members
CREATE TABLE members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    membership_no TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Suspended', 'Expired')),
    joined_date DATE NOT NULL
);

-- Table 3: Book Circulation (Loans & Returns)
CREATE TABLE circulation (
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

-- Table 4: Book Reservations / Holds
CREATE TABLE reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    reservation_date DATE NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('Waiting', 'Fulfilled', 'Cancelled')),
    notes TEXT,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

-- Table 5: Fines & Penalties (Overdue fines in INR ₹)
CREATE TABLE fines (
    fine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0),
    status TEXT NOT NULL CHECK(status IN ('Outstanding', 'Paid', 'Waived')),
    reason TEXT NOT NULL,
    issued_date DATE NOT NULL,
    paid_date DATE,
    FOREIGN KEY (loan_id) REFERENCES circulation(loan_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

-- Table 6: Digital Library Access Logs
CREATE TABLE digital_access (
    access_id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    device_type TEXT DEFAULT 'Web Reader',
    session_minutes INTEGER DEFAULT 25,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

-- Table 7: Activity Ledger (Live Desk Audit Trail)
CREATE TABLE activity_ledger (
    ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name TEXT NOT NULL,
    action_text TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Loan', 'Return', 'Reservation', 'Digital Access', 'Fine')),
    event_time TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 3. DML: SEED DATA (Exact match to "The Reading Room" Daily Desk state)
-- ---------------------------------------------------------------------

-- Insert Books (6 titles, 12 total physical copies)
INSERT INTO books (book_id, title, author, isbn, genre, publication_year, total_copies, available_copies, digital_available)
VALUES 
    (1, 'Atomic Habits', 'James Clear', '978-0735211292', 'Self-Help / Psychology', 2018, 2, 1, 1),
    (2, 'Sapiens: A Brief History of Humankind', 'Yuval Noah Harari', '978-0062316097', 'History / Anthropology', 2014, 2, 2, 1),
    (3, '1984', 'George Orwell', '978-0451524935', 'Dystopian Classic', 1949, 2, 1, 1),
    (4, 'The Psychology of Money', 'Morgan Housel', '978-0857197689', 'Finance & Behaviour', 2020, 2, 2, 1),
    (5, 'Deep Work', 'Cal Newport', '978-1455586691', 'Productivity', 2016, 2, 2, 1),
    (6, 'To Kill a Mockingbird', 'Harper Lee', '978-0061120084', 'Classic Fiction', 1960, 2, 2, 1);

-- Insert Members (4 active patrons)
INSERT INTO members (member_id, full_name, membership_no, email, phone, status, joined_date)
VALUES 
    (1, 'Aarav Mehta', 'LIB-2024-001', 'aarav.mehta@readingroom.org', '+91 98765 43210', 'Active', '2024-01-15'),
    (2, 'Riya Patel', 'LIB-2024-002', 'riya.patel@readingroom.org', '+91 98765 43211', 'Active', '2024-02-10'),
    (3, 'Kabir Varma', 'LIB-2024-003', 'kabir.varma@readingroom.org', '+91 98765 43212', 'Active', '2024-03-01'),
    (4, 'Priya Sharma', 'LIB-2024-004', 'priya.sharma@readingroom.org', '+91 98765 43213', 'Active', '2024-04-18');

-- Insert Circulation Records (2 active loans: 1 overdue, 1 regular active; 1 returned)
INSERT INTO circulation (loan_id, book_id, member_id, loan_date, due_date, return_date, status)
VALUES 
    (1, 1, 1, '2026-09-22', '2026-10-06', NULL, 'Overdue'),
    (2, 3, 4, '2026-10-12', '2026-10-26', NULL, 'Active'),
    (3, 2, 3, '2026-09-22', '2026-10-12', '2026-10-12', 'Returned');

-- Insert Outstanding Fine (₹30.00 for Aarav Mehta's overdue loan of Atomic Habits)
INSERT INTO fines (fine_id, loan_id, member_id, amount, status, reason, issued_date, paid_date)
VALUES 
    (1, 1, 1, 30.00, 'Outstanding', 'Overdue: Atomic Habits (6 days @ ₹5/day)', '2026-10-12', NULL);

-- Insert Reservations (2 holds waiting)
INSERT INTO reservations (reservation_id, book_id, member_id, reservation_date, status, notes)
VALUES 
    (1, 2, 2, '2026-10-12', 'Waiting', 'Preferred hardcover edition'),
    (2, 1, 3, '2026-10-12', 'Waiting', 'Waiting for Aarav return');

-- Insert Digital Access Logs (2 digital visits today)
INSERT INTO digital_access (access_id, book_id, member_id, accessed_at, device_type, session_minutes)
VALUES 
    (1, 3, 4, '2026-10-12 13:40:00', 'Web Reader', 35),
    (2, 1, 2, '2026-10-12 10:15:00', 'Tablet App', 20);

-- Insert Activity Ledger (Timeline Feed matching screenshot)
INSERT INTO activity_ledger (ledger_id, member_name, action_text, category, event_time)
VALUES 
    (1, 'Aarav Mehta', 'has an overdue copy of Atomic Habits', 'Loan', '01:53 PM'),
    (2, 'Riya Patel', 'placed a reservation for Sapiens', 'Reservation', '01:53 PM'),
    (3, 'Kabir Varma', 'returned Sapiens', 'Return', '01:52 PM'),
    (4, 'Priya Sharma', 'opened the digital edition of 1984', 'Digital Access', '01:40 PM'),
    (5, 'Priya Sharma', 'checked out 1984', 'Loan', '01:38 PM');

-- ---------------------------------------------------------------------
-- 4. DBMS REVIEW QUERIES (Joins, Aggregations, Analytics)
-- ---------------------------------------------------------------------

-- Query 1: Active & Overdue Loans with Book and Borrower Info (INNER JOIN)
-- SELECT c.loan_id, b.title, m.full_name, m.membership_no, c.loan_date, c.due_date, c.status
-- FROM circulation c
-- JOIN books b ON c.book_id = b.book_id
-- JOIN members m ON c.member_id = m.member_id
-- WHERE c.status IN ('Active', 'Overdue');

-- Query 2: Outstanding Fines summary with Member Details (JOIN + WHERE)
-- SELECT f.fine_id, m.full_name, m.email, b.title, f.amount, f.reason, f.status
-- FROM fines f
-- JOIN members m ON f.member_id = m.member_id
-- LEFT JOIN circulation c ON f.loan_id = c.loan_id
-- LEFT JOIN books b ON c.book_id = b.book_id
-- WHERE f.status = 'Outstanding';

-- Query 3: Book Borrowing Frequency & Popularity (LEFT JOIN + GROUP BY)
-- SELECT b.book_id, b.title, b.author, COUNT(c.loan_id) AS total_borrows, b.available_copies
-- FROM books b
-- LEFT JOIN circulation c ON b.book_id = c.book_id
-- GROUP BY b.book_id
-- ORDER BY total_borrows DESC;

-- Query 4: Daily Desk Live KPI Aggregates (Aggregations)
-- SELECT 
--     (SELECT COUNT(*) FROM books) AS titles_in_catalog,
--     (SELECT SUM(total_copies) FROM books) AS total_physical_copies,
--     (SELECT SUM(available_copies) FROM books) AS available_to_borrow,
--     (SELECT COUNT(*) FROM circulation WHERE status IN ('Active', 'Overdue')) AS active_loans,
--     (SELECT COUNT(*) FROM members WHERE status = 'Active') AS active_members,
--     (SELECT COUNT(*) FROM reservations WHERE status = 'Waiting') AS waiting_holds,
--     (SELECT COALESCE(SUM(amount), 0.0) FROM fines WHERE status = 'Outstanding') AS outstanding_fines;
