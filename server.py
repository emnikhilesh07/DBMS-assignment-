import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse
from datetime import datetime, timedelta

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

class LibraryRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(body)
            except Exception:
                return {}
        return {}

    def log_activity(self, conn, member_name, action_text, category):
        cur = conn.cursor()
        now_time = datetime.now().strftime("%I:%M %p")
        cur.execute(
            "INSERT INTO activity_ledger (member_name, action_text, category, event_time) VALUES (?, ?, ?, ?)",
            (member_name, action_text, category, now_time)
        )

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        if not path.startswith("/api/"):
            return super().do_GET()

        conn = get_db()
        cur = conn.cursor()

        try:
            if path == "/api/stats":
                # Real-time stats calculation matching the dashboard
                cur.execute("SELECT COUNT(*) as titles, COALESCE(SUM(total_copies), 0) as total_copies, COALESCE(SUM(available_copies), 0) as available_copies FROM books")
                books_stat = cur.fetchone()

                cur.execute("SELECT COUNT(*) as active_loans FROM circulation WHERE status IN ('Active', 'Overdue')")
                active_loans = cur.fetchone()["active_loans"]

                cur.execute("SELECT COUNT(*) as overdue_loans FROM circulation WHERE status = 'Overdue'")
                overdue_loans = cur.fetchone()["overdue_loans"]

                cur.execute("SELECT COUNT(*) as active_members FROM members WHERE status = 'Active'")
                active_members = cur.fetchone()["active_members"]

                cur.execute("SELECT COUNT(*) as waiting_holds FROM reservations WHERE status = 'Waiting'")
                waiting_holds = cur.fetchone()["waiting_holds"]

                cur.execute("SELECT COALESCE(SUM(amount), 0.0) as outstanding_fines FROM fines WHERE status = 'Outstanding'")
                fines_stat = cur.fetchone()["outstanding_fines"]

                cur.execute("SELECT COUNT(*) as digital_visits FROM digital_access")
                digital_visits = cur.fetchone()["digital_visits"]

                cur.execute("SELECT COUNT(*) as total_reservations FROM reservations")
                total_reservations = cur.fetchone()["total_reservations"]

                data = {
                    "titles_count": books_stat["titles"],
                    "total_copies": books_stat["total_copies"],
                    "available_copies": books_stat["available_copies"],
                    "active_loans": active_loans,
                    "overdue_loans": overdue_loans,
                    "active_members": active_members,
                    "waiting_holds": waiting_holds,
                    "outstanding_fines": float(fines_stat),
                    "digital_visits": digital_visits,
                    "total_reservations": total_reservations
                }
                self.send_json(200, {"success": True, "data": data})

            elif path == "/api/activity":
                cur.execute("SELECT * FROM activity_ledger ORDER BY ledger_id DESC LIMIT 30")
                rows = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": rows})

            elif path == "/api/books":
                search = query_params.get("q", [""])[0].strip()
                genre = query_params.get("genre", [""])[0].strip()
                sql = "SELECT * FROM books WHERE 1=1"
                params = []
                if search:
                    sql += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
                    term = f"%{search}%"
                    params.extend([term, term, term])
                if genre:
                    sql += " AND genre LIKE ?"
                    params.append(f"%{genre}%")
                sql += " ORDER BY book_id ASC"
                cur.execute(sql, params)
                books = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": books})

            elif path == "/api/members":
                cur.execute("""
                    SELECT m.*,
                        (SELECT COUNT(*) FROM circulation c WHERE c.member_id = m.member_id AND c.status IN ('Active', 'Overdue')) as active_loans_count,
                        (SELECT COALESCE(SUM(f.amount), 0) FROM fines f WHERE f.member_id = m.member_id AND f.status = 'Outstanding') as outstanding_fine_total
                    FROM members m
                    ORDER BY m.member_id ASC
                """)
                members = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": members})

            elif path == "/api/circulation":
                cur.execute("""
                    SELECT c.*, b.title as book_title, b.author as book_author, m.full_name as member_name, m.membership_no
                    FROM circulation c
                    JOIN books b ON c.book_id = b.book_id
                    JOIN members m ON c.member_id = m.member_id
                    ORDER BY c.loan_id DESC
                """)
                records = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": records})

            elif path == "/api/reservations":
                cur.execute("""
                    SELECT r.*, b.title as book_title, m.full_name as member_name, m.membership_no
                    FROM reservations r
                    JOIN books b ON r.book_id = b.book_id
                    JOIN members m ON r.member_id = m.member_id
                    ORDER BY r.reservation_id DESC
                """)
                reservations = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": reservations})

            elif path == "/api/fines":
                cur.execute("""
                    SELECT f.*, m.full_name as member_name, m.membership_no, b.title as book_title
                    FROM fines f
                    JOIN members m ON f.member_id = m.member_id
                    LEFT JOIN circulation c ON f.loan_id = c.loan_id
                    LEFT JOIN books b ON c.book_id = b.book_id
                    ORDER BY f.fine_id DESC
                """)
                fines = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": fines})

            elif path == "/api/digital-access":
                cur.execute("""
                    SELECT d.*, b.title as book_title, b.author as book_author, m.full_name as member_name
                    FROM digital_access d
                    JOIN books b ON d.book_id = b.book_id
                    JOIN members m ON d.member_id = m.member_id
                    ORDER BY d.access_id DESC
                """)
                logs = [dict(r) for r in cur.fetchall()]
                self.send_json(200, {"success": True, "data": logs})

            elif path == "/api/schema":
                # Return SQL database tables and columns info for DBMS review
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
                tables = [r["name"] for r in cur.fetchall()]
                schema_info = {}
                for t in tables:
                    cur.execute(f"PRAGMA table_info({t})")
                    schema_info[t] = [dict(col) for col in cur.fetchall()]
                self.send_json(200, {"success": True, "tables": tables, "schema": schema_info})

            else:
                self.send_json(404, {"error": "API route not found"})
        except Exception as e:
            self.send_json(500, {"error": str(e)})
        finally:
            conn.close()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_body()
        conn = get_db()
        cur = conn.cursor()

        try:
            if path == "/api/books":
                title = body.get("title", "").strip()
                author = body.get("author", "").strip()
                isbn = body.get("isbn", "").strip()
                genre = body.get("genre", "General").strip()
                year = int(body.get("publication_year", 2024))
                copies = int(body.get("total_copies", 1))

                if not title or not author or not isbn:
                    self.send_json(400, {"error": "Title, Author, and ISBN are required."})
                    return

                cur.execute("""
                    INSERT INTO books (title, author, isbn, genre, publication_year, total_copies, available_copies, digital_available)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """, (title, author, isbn, genre, year, copies, copies))
                new_id = cur.lastrowid
                self.log_activity(conn, "Desk Librarian", f"added '{title}' to catalog", "Loan")
                conn.commit()
                self.send_json(201, {"success": True, "book_id": new_id, "message": "Book added successfully."})

            elif path == "/api/members":
                full_name = body.get("full_name", "").strip()
                email = body.get("email", "").strip()
                phone = body.get("phone", "").strip()
                if not full_name or not email:
                    self.send_json(400, {"error": "Name and email are required."})
                    return

                # Generate membership number
                cur.execute("SELECT COUNT(*) as cnt FROM members")
                count = cur.fetchone()["cnt"] + 1
                membership_no = f"LIB-2024-{str(count).zfill(3)}"
                today_str = datetime.now().strftime("%Y-%m-%d")

                cur.execute("""
                    INSERT INTO members (full_name, membership_no, email, phone, status, joined_date)
                    VALUES (?, ?, ?, ?, 'Active', ?)
                """, (full_name, membership_no, email, phone, today_str))
                new_id = cur.lastrowid
                self.log_activity(conn, full_name, f"enrolled as a new library member ({membership_no})", "Loan")
                conn.commit()
                self.send_json(201, {"success": True, "member_id": new_id, "membership_no": membership_no})

            elif path == "/api/circulation/borrow":
                book_id = int(body.get("book_id", 0))
                member_id = int(body.get("member_id", 0))
                days = int(body.get("days", 14))

                # Check book availability
                cur.execute("SELECT title, available_copies FROM books WHERE book_id = ?", (book_id,))
                book = cur.fetchone()
                if not book or book["available_copies"] <= 0:
                    self.send_json(400, {"error": "Book is currently unavailable for borrowing."})
                    return

                cur.execute("SELECT full_name FROM members WHERE member_id = ?", (member_id,))
                member = cur.fetchone()
                if not member:
                    self.send_json(404, {"error": "Member not found."})
                    return

                today_str = datetime.now().strftime("%Y-%m-%d")
                due_date_str = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

                # Insert loan
                cur.execute("""
                    INSERT INTO circulation (book_id, member_id, loan_date, due_date, status)
                    VALUES (?, ?, ?, ?, 'Active')
                """, (book_id, member_id, today_str, due_date_str))
                loan_id = cur.lastrowid

                # Decrement available copies
                cur.execute("UPDATE books SET available_copies = available_copies - 1 WHERE book_id = ?", (book_id,))

                # Log activity
                self.log_activity(conn, member["full_name"], f"checked out {book['title']}", "Loan")
                conn.commit()
                self.send_json(201, {"success": True, "loan_id": loan_id, "message": f"{book['title']} checked out successfully."})

            elif path == "/api/circulation/return":
                loan_id = int(body.get("loan_id", 0))
                cur.execute("""
                    SELECT c.*, b.title as book_title, m.full_name as member_name
                    FROM circulation c
                    JOIN books b ON c.book_id = b.book_id
                    JOIN members m ON c.member_id = m.member_id
                    WHERE c.loan_id = ?
                """, (loan_id,))
                loan = cur.fetchone()
                if not loan:
                    self.send_json(404, {"error": "Loan record not found."})
                    return

                if loan["status"] == "Returned":
                    self.send_json(400, {"error": "Book is already marked returned."})
                    return

                today_str = datetime.now().strftime("%Y-%m-%d")

                # Check if overdue and calculate fine (₹5 per day overdue)
                due_dt = datetime.strptime(loan["due_date"], "%Y-%m-%d")
                today_dt = datetime.strptime(today_str, "%Y-%m-%d")
                overdue_days = (today_dt - due_dt).days
                fine_generated = 0

                if overdue_days > 0:
                    fine_generated = overdue_days * 5.0
                    cur.execute("""
                        INSERT INTO fines (loan_id, member_id, amount, status, reason, issued_date)
                        VALUES (?, ?, ?, 'Outstanding', ?, ?)
                    """, (loan_id, loan["member_id"], fine_generated, f"Overdue return ({overdue_days} days @ ₹5/day)", today_str))

                # Update loan record
                cur.execute("UPDATE circulation SET return_date = ?, status = 'Returned' WHERE loan_id = ?", (today_str, loan_id))
                # Increment book available copies
                cur.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = ?", (loan["book_id"],))

                # Log activity
                self.log_activity(conn, loan["member_name"], f"returned {loan['book_title']}", "Return")
                conn.commit()

                self.send_json(200, {
                    "success": True,
                    "message": f"Successfully returned {loan['book_title']}.",
                    "fine_generated": fine_generated
                })

            elif path == "/api/reservations":
                book_id = int(body.get("book_id", 0))
                member_id = int(body.get("member_id", 0))
                notes = body.get("notes", "Member hold request")

                cur.execute("SELECT title FROM books WHERE book_id = ?", (book_id,))
                book = cur.fetchone()
                cur.execute("SELECT full_name FROM members WHERE member_id = ?", (member_id,))
                member = cur.fetchone()

                if not book or not member:
                    self.send_json(404, {"error": "Book or Member not found."})
                    return

                today_str = datetime.now().strftime("%Y-%m-%d")
                cur.execute("""
                    INSERT INTO reservations (book_id, member_id, reservation_date, status, notes)
                    VALUES (?, ?, ?, 'Waiting', ?)
                """, (book_id, member_id, today_str, notes))
                res_id = cur.lastrowid

                self.log_activity(conn, member["full_name"], f"placed a reservation for {book['title']}", "Reservation")
                conn.commit()
                self.send_json(201, {"success": True, "reservation_id": res_id, "message": "Reservation recorded."})

            elif path.startswith("/api/reservations/") and path.endswith("/status"):
                parts = path.split("/")
                res_id = int(parts[3])
                status = body.get("status", "Fulfilled")
                cur.execute("UPDATE reservations SET status = ? WHERE reservation_id = ?", (status, res_id))
                conn.commit()
                self.send_json(200, {"success": True, "message": f"Reservation updated to {status}."})

            elif path.startswith("/api/fines/") and path.endswith("/pay"):
                parts = path.split("/")
                fine_id = int(parts[3])
                today_str = datetime.now().strftime("%Y-%m-%d")
                cur.execute("""
                    SELECT f.*, m.full_name as member_name
                    FROM fines f
                    JOIN members m ON f.member_id = m.member_id
                    WHERE f.fine_id = ?
                """, (fine_id,))
                fine = cur.fetchone()
                if not fine:
                    self.send_json(404, {"error": "Fine record not found."})
                    return

                cur.execute("UPDATE fines SET status = 'Paid', paid_date = ? WHERE fine_id = ?", (today_str, fine_id))
                self.log_activity(conn, fine["member_name"], f"settled fine of ₹{fine['amount']:.2f}", "Fine")
                conn.commit()
                self.send_json(200, {"success": True, "message": "Fine settled successfully."})

            elif path == "/api/digital-access":
                book_id = int(body.get("book_id", 0))
                member_id = int(body.get("member_id", 0))
                device = body.get("device_type", "Web Reader")

                cur.execute("SELECT title FROM books WHERE book_id = ?", (book_id,))
                book = cur.fetchone()
                cur.execute("SELECT full_name FROM members WHERE member_id = ?", (member_id,))
                member = cur.fetchone()

                if not book or not member:
                    self.send_json(404, {"error": "Book or Member not found."})
                    return

                cur.execute("""
                    INSERT INTO digital_access (book_id, member_id, device_type, session_minutes)
                    VALUES (?, ?, ?, 30)
                """, (book_id, member_id, device))

                self.log_activity(conn, member["full_name"], f"opened the digital edition of {book['title']}", "Digital Access")
                conn.commit()
                self.send_json(201, {"success": True, "message": "Digital access session launched."})

            elif path == "/api/raw-query":
                # DBMS Review SQL Console: Run custom SQL queries safely
                raw_sql = body.get("query", "").strip()
                if not raw_sql:
                    self.send_json(400, {"error": "Empty SQL query."})
                    return

                # Disallow harmful system calls
                disallowed = ["attach", "detach", "pragma writable_schema"]
                if any(d in raw_sql.lower() for d in disallowed):
                    self.send_json(403, {"error": "System level operations not allowed."})
                    return

                start_time = datetime.now()
                is_select = raw_sql.strip().lower().startswith("select") or raw_sql.strip().lower().startswith("pragma")

                if is_select:
                    cur.execute(raw_sql)
                    columns = [d[0] for d in cur.description] if cur.description else []
                    rows = [dict(zip(columns, r)) for r in cur.fetchall()]
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    self.send_json(200, {
                        "success": True,
                        "type": "SELECT",
                        "columns": columns,
                        "rows": rows,
                        "rowCount": len(rows),
                        "executionTimeMs": round(elapsed_ms, 2)
                    })
                else:
                    cur.execute(raw_sql)
                    conn.commit()
                    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                    self.send_json(200, {
                        "success": True,
                        "type": "EXECUTE",
                        "affectedRows": cur.rowcount,
                        "executionTimeMs": round(elapsed_ms, 2),
                        "message": f"Query executed successfully. {cur.rowcount} row(s) affected."
                    })

            elif path == "/api/reset-db":
                import init_db
                conn.close()
                init_db.init_database()
                self.send_json(200, {"success": True, "message": "Database reseeded to default state."})
                return

            else:
                self.send_json(404, {"error": "API endpoint not found."})
        except Exception as e:
            conn.rollback()
            self.send_json(500, {"error": str(e)})
        finally:
            conn.close()

def run_server():
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with socketserver.TCPServer(("", PORT), LibraryRequestHandler) as httpd:
        print(f"Library Operations server running on http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
