"""
Database layer για την εφαρμογή Personal Finance Manager.

Το αρχείο αυτό είναι το κεντρικό σημείο επικοινωνίας με τη SQLite βάση.
Το κρατάμε ξεχωριστά από το GUI για να είναι καθαρή η αρχιτεκτονική:
- Το GUI ασχολείται με κουμπιά, φόρμες και μηνύματα.
- Το database.py ασχολείται με πίνακες, INSERT, SELECT, UPDATE, DELETE και reports.

Σε κάθε function η σύνδεση με τη βάση κλείνει πάντα με finally.
Αυτό είναι σημαντικό  ώστε ακόμα και αν υπάρξει σφάλμα
π.χ. διπλή κατηγορία ή περιορισμός foreign key, να μη μείνει η SQLite κλειδωμένη.
"""

# Η sqlite3 είναι η ενσωματωμένη βιβλιοθήκη της Python για SQLite βάσεις.
import sqlite3

# Το os χρησιμοποιείται για να φτιάξουμε ασφαλές path προς το finance.db.
# Έτσι δεν εξαρτόμαστε από το από ποιον φάκελο άνοιξε ο χρήστης το terminal.
import os

# Το sys μάς βοηθά να καταλάβουμε αν η εφαρμογή τρέχει ως κανονικό .py
# ή ως executable που δημιουργήθηκε με PyInstaller.
import sys


def get_project_root():
    """
    Επιστρέφει τον φάκελο όπου θα αποθηκεύεται το finance.db.

    Υπάρχουν δύο περιπτώσεις:
    1. Κανονική εκτέλεση με Python:
       Παίρνουμε ως root τον κεντρικό φάκελο του project.
    2. Εκτέλεση ως .exe με PyInstaller:
       Παίρνουμε ως root τον φάκελο όπου βρίσκεται το executable.
    """

    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = get_project_root()
DB_NAME = os.path.join(PROJECT_ROOT, "finance.db")


# -----------------------------------------------------------------------------
# ΒΑΣΙΚΗ ΣΥΝΔΕΣΗ ΜΕ ΤΗ ΒΑΣΗ
# -----------------------------------------------------------------------------

def get_connection():
    """
    Ανοίγει σύνδεση με τη βάση δεδομένων.

    row_factory = sqlite3.Row:
    Διαβάζουμε πεδία με όνομα, π.χ. row["Category"].

    PRAGMA foreign_keys = ON:
    Ενεργοποιεί τους περιορισμούς foreign key σε κάθε νέα σύνδεση.

    busy_timeout:
    Δίνει λίγο χρόνο στη SQLite αν η βάση είναι προσωρινά απασχολημένη.
    """

    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


# -----------------------------------------------------------------------------
# ΔΗΜΙΟΥΡΓΙΑ SCHEMA
# -----------------------------------------------------------------------------

def initialize_database():
    """Δημιουργεί τους πίνακες της εφαρμογής αν δεν υπάρχουν ήδη."""

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories
        (
            CategoryID INTEGER PRIMARY KEY AUTOINCREMENT,
            Category TEXT NOT NULL UNIQUE,
            CategoryDescr TEXT,
            CategoryType TEXT NOT NULL CHECK (CategoryType IN ('income','expense'))
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transactions
        (
            TranID INTEGER PRIMARY KEY AUTOINCREMENT,
            TranCategoryID INTEGER NOT NULL,
            TranAmount REAL NOT NULL CHECK (TranAmount > 0),
            TranRegDate TEXT NOT NULL,
            TranDescr TEXT,

            FOREIGN KEY (TranCategoryID)
                REFERENCES Categories(CategoryID)
                ON DELETE RESTRICT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Recurring_Transactions
        (
            RecTranID INTEGER PRIMARY KEY AUTOINCREMENT,
            RecTranCategoryID INTEGER NOT NULL,
            RecTranAmount REAL NOT NULL CHECK (RecTranAmount > 0),
            RecTranStartDate TEXT NOT NULL,
            RecTranDescr TEXT,
            RecTranActive INTEGER NOT NULL CHECK (RecTranActive IN (0,1)),

            FOREIGN KEY (RecTranCategoryID)
                REFERENCES Categories(CategoryID)
                ON DELETE RESTRICT
        )
        """)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# ΑΡΧΙΚΑ ΔΕΔΟΜΕΝΑ ΓΙΑ DEMO / ΠΡΩΤΗ ΕΚΚΙΝΗΣΗ
# -----------------------------------------------------------------------------

def seed_default_categories():
    """
    Προσθέτει μερικές βασικές κατηγορίες μόνο αν δεν υπάρχουν.

    Χρησιμοποιούμε INSERT OR IGNORE για να μη δημιουργούνται διπλές εγγραφές.
    """

    default_categories = [
        ("Μισθός", "Σταθερό μηνιαίο εισόδημα", "income"),
        ("Επίδομα", "Επίδομα ή άλλη οικονομική ενίσχυση", "income"),
        ("Freelance", "Έσοδα από ελεύθερη εργασία", "income"),
        ("Τρόφιμα", "Αγορές super market και τρόφιμα", "expense"),
        ("Ενοίκιο", "Μηνιαίο κόστος ενοικίου", "expense"),
        ("Λογαριασμοί", "Ρεύμα, νερό, internet, τηλέφωνο", "expense"),
        ("Μεταφορές", "Καύσιμα, εισιτήρια, μετακινήσεις", "expense"),
        ("Ψυχαγωγία", "Έξοδοι, χόμπι και διασκέδαση", "expense"),
    ]

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR IGNORE INTO Categories (Category, CategoryDescr, CategoryType)
            VALUES (?, ?, ?)
        """, default_categories)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# CRUD ΚΑΤΗΓΟΡΙΩΝ
# -----------------------------------------------------------------------------

def insert_category(category, category_descr, category_type):
    """Εισάγει νέα κατηγορία εσόδου ή εξόδου."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Categories (Category, CategoryDescr, CategoryType)
            VALUES (?, ?, ?)
        """, (category, category_descr, category_type))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def select_categories(category_type=None):
    """Επιστρέφει όλες τις κατηγορίες ή μόνο income/expense αν δοθεί φίλτρο."""

    conn = get_connection()

    try:
        cursor = conn.cursor()

        if category_type:
            cursor.execute("""
                SELECT CategoryID, Category, CategoryDescr, CategoryType
                FROM Categories
                WHERE CategoryType = ?
                ORDER BY Category
            """, (category_type,))
        else:
            cursor.execute("""
                SELECT CategoryID, Category, CategoryDescr, CategoryType
                FROM Categories
                ORDER BY CategoryType, Category
            """)

        return cursor.fetchall()
    finally:
        conn.close()


def select_category_by_id(category_id):
    """Επιστρέφει μία κατηγορία με βάση το CategoryID."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT CategoryID, Category, CategoryDescr, CategoryType
            FROM Categories
            WHERE CategoryID = ?
        """, (category_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def update_category(category_id, category, category_descr, category_type):
    """Ενημερώνει τα στοιχεία μίας υπάρχουσας κατηγορίας."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Categories
            SET Category = ?, CategoryDescr = ?, CategoryType = ?
            WHERE CategoryID = ?
        """, (category, category_descr, category_type, category_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_category(category_id):
    """
    Διαγράφει μία κατηγορία.

    Παραδοχή εργασίας:
    Αν η κατηγορία χρησιμοποιείται από συναλλαγές, δεν επιτρέπουμε διαγραφή.
    Αυτό γίνεται από το foreign key με ON DELETE RESTRICT.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Categories WHERE CategoryID = ?", (category_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# CRUD ΣΥΝΑΛΛΑΓΩΝ
# -----------------------------------------------------------------------------

def insert_transaction(tran_category_id, tran_amount, tran_reg_date, tran_descr):
    """Εισάγει νέα συναλλαγή στον πίνακα Transactions."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Transactions (TranCategoryID, TranAmount, TranRegDate, TranDescr)
            VALUES (?, ?, ?, ?)
        """, (tran_category_id, tran_amount, tran_reg_date, tran_descr))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def select_transactions(month=None, year=None, category_id=None, date_from=None, date_to=None):
    """
    Επιστρέφει συναλλαγές μαζί με το όνομα και τον τύπο της κατηγορίας.

    Χρησιμοποιούμε JOIN γιατί στο Transactions υπάρχει μόνο το TranCategoryID.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
            SELECT
                t.TranID,
                t.TranCategoryID,
                c.Category,
                c.CategoryType,
                t.TranAmount,
                t.TranRegDate,
                t.TranDescr
            FROM Transactions t
            INNER JOIN Categories c ON t.TranCategoryID = c.CategoryID
            WHERE 1 = 1
        """

        params = []

        if month and year:
            sql += " AND substr(t.TranRegDate, 1, 7) = ?"
            params.append(f"{int(year):04d}-{int(month):02d}")

        # Φίλτρο ημερομηνίας από.
        # Η βάση κρατάει τις ημερομηνίες ως YYYY-MM-DD,
        # άρα η σύγκριση κειμένου δουλεύει σωστά.
        if date_from:
            sql += " AND t.TranRegDate >= ?"
            params.append(date_from)

        # Φίλτρο ημερομηνίας έως.
        if date_to:
            sql += " AND t.TranRegDate <= ?"
            params.append(date_to)
        

        if category_id:
            sql += " AND t.TranCategoryID = ?"
            params.append(category_id)

        sql += " ORDER BY t.TranRegDate DESC, t.TranID DESC"

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def select_transaction_by_id(tran_id):
    """Επιστρέφει μία συναλλαγή με βάση το TranID."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                t.TranID,
                t.TranCategoryID,
                c.Category,
                c.CategoryType,
                t.TranAmount,
                t.TranRegDate,
                t.TranDescr
            FROM Transactions t
            INNER JOIN Categories c ON t.TranCategoryID = c.CategoryID
            WHERE t.TranID = ?
        """, (tran_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def update_transaction(tran_id, tran_category_id, tran_amount, tran_reg_date, tran_descr):
    """Ενημερώνει μία υπάρχουσα συναλλαγή."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Transactions
            SET TranCategoryID = ?,
                TranAmount = ?,
                TranRegDate = ?,
                TranDescr = ?
            WHERE TranID = ?
        """, (tran_category_id, tran_amount, tran_reg_date, tran_descr, tran_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_transaction(tran_id):
    """Διαγράφει μία συναλλαγή με βάση το TranID."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Transactions WHERE TranID = ?", (tran_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# CRUD ΕΠΑΝΑΛΑΜΒΑΝΟΜΕΝΩΝ ΣΥΝΑΛΛΑΓΩΝ
# -----------------------------------------------------------------------------

def insert_recurring_transaction(rec_tran_category_id, rec_tran_amount, rec_tran_start_date, rec_tran_descr, rec_tran_active=1):
    """Εισάγει νέα επαναλαμβανόμενη συναλλαγή."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Recurring_Transactions
            (RecTranCategoryID, RecTranAmount, RecTranStartDate, RecTranDescr, RecTranActive)
            VALUES (?, ?, ?, ?, ?)
        """, (rec_tran_category_id, rec_tran_amount, rec_tran_start_date, rec_tran_descr, rec_tran_active))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def select_recurring_transactions(active_only=False):
    """Επιστρέφει τις επαναλαμβανόμενες συναλλαγές."""

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
            SELECT
                r.RecTranID,
                r.RecTranCategoryID,
                c.Category,
                c.CategoryType,
                r.RecTranAmount,
                r.RecTranStartDate,
                r.RecTranDescr,
                r.RecTranActive
            FROM Recurring_Transactions r
            INNER JOIN Categories c ON r.RecTranCategoryID = c.CategoryID
            WHERE 1 = 1
        """

        params = []

        if active_only:
            sql += " AND r.RecTranActive = 1"

        sql += " ORDER BY r.RecTranStartDate, r.RecTranID"

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def select_recurring_by_id(rec_tran_id):
    """Επιστρέφει μία επαναλαμβανόμενη εγγραφή με βάση το RecTranID."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                r.RecTranID,
                r.RecTranCategoryID,
                c.Category,
                c.CategoryType,
                r.RecTranAmount,
                r.RecTranStartDate,
                r.RecTranDescr,
                r.RecTranActive
            FROM Recurring_Transactions r
            INNER JOIN Categories c ON r.RecTranCategoryID = c.CategoryID
            WHERE r.RecTranID = ?
        """, (rec_tran_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def update_recurring_transaction(rec_tran_id, rec_tran_category_id, rec_tran_amount, rec_tran_start_date, rec_tran_descr, rec_tran_active):
    """Ενημερώνει μία επαναλαμβανόμενη συναλλαγή."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Recurring_Transactions
            SET RecTranCategoryID = ?,
                RecTranAmount = ?,
                RecTranStartDate = ?,
                RecTranDescr = ?,
                RecTranActive = ?
            WHERE RecTranID = ?
        """, (rec_tran_category_id, rec_tran_amount, rec_tran_start_date, rec_tran_descr, rec_tran_active, rec_tran_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_recurring_transaction(rec_tran_id):
    """Διαγράφει μία επαναλαμβανόμενη συναλλαγή."""

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Recurring_Transactions WHERE RecTranID = ?", (rec_tran_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# REPORTS / ΣΥΝΟΨΕΙΣ / ΓΡΑΦΗΜΑΤΑ
# -----------------------------------------------------------------------------

def select_month_totals(month, year):
    """Υπολογίζει σύνολο εσόδων, εξόδων και υπόλοιπο για συγκεκριμένο μήνα."""

    rows = select_transactions(month, year)

    income = 0.0
    expense = 0.0

    for row in rows:
        if row["CategoryType"] == "income":
            income += float(row["TranAmount"])
        else:
            expense += float(row["TranAmount"])

    return {
        "income": income,
        "expense": expense,
        "balance": income - expense,
    }


def select_expenses_by_category(month=None, year=None, date_from=None, date_to=None):
    """
    Επιστρέφει σύνολο εξόδων ανά κατηγορία.

    Μπορεί να φιλτράρει:
    - είτε με μήνα/έτος για τα μηνιαία exports,
    - είτε με date_from/date_to για τα φίλτρα γραφημάτων Από / Έως.

    Οι ημερομηνίες στη βάση είναι σε μορφή YYYY-MM-DD,
    άρα οι συγκρίσεις κειμένου δουλεύουν σωστά.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
            SELECT
                c.Category,
                SUM(t.TranAmount) AS TotalExpense
            FROM Transactions t
            INNER JOIN Categories c ON t.TranCategoryID = c.CategoryID
            WHERE c.CategoryType = 'expense'
        """

        params = []

        # Συμβατότητα με την παλιά μηνιαία λογική των exports.
        if month and year:
            sql += " AND substr(t.TranRegDate, 1, 7) = ?"
            params.append(f"{int(year):04d}-{int(month):02d}")

        # Φίλτρο ημερομηνίας Από για τα γραφήματα.
        if date_from:
            sql += " AND t.TranRegDate >= ?"
            params.append(date_from)

        # Φίλτρο ημερομηνίας Έως για τα γραφήματα.
        if date_to:
            sql += " AND t.TranRegDate <= ?"
            params.append(date_to)

        sql += " GROUP BY c.Category ORDER BY TotalExpense DESC"

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()

def select_income_by_category(month=None, year=None, date_from=None, date_to=None):
    """
    Επιστρέφει σύνολο εσόδων ανά κατηγορία.

    Μπορεί να φιλτράρει:
    - είτε με μήνα/έτος,
    - είτε με date_from/date_to για τα φίλτρα γραφημάτων.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
            SELECT
                c.Category,
                SUM(t.TranAmount) AS TotalIncome
            FROM Transactions t
            INNER JOIN Categories c ON t.TranCategoryID = c.CategoryID
            WHERE c.CategoryType = 'income'
        """

        params = []

        # Συμβατότητα με την υπάρχουσα μηνιαία λογική.
        if month and year:
            sql += " AND substr(t.TranRegDate, 1, 7) = ?"
            params.append(f"{int(year):04d}-{int(month):02d}")

        # Φίλτρο ημερομηνίας Από.
        if date_from:
            sql += " AND t.TranRegDate >= ?"
            params.append(date_from)

        # Φίλτρο ημερομηνίας Έως.
        if date_to:
            sql += " AND t.TranRegDate <= ?"
            params.append(date_to)

        sql += " GROUP BY c.Category ORDER BY TotalIncome DESC"

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()

def select_monthly_summary(date_from=None, date_to=None):
    """
    Επιστρέφει μηνιαία σύνοψη εσόδων, εξόδων και υπολοίπου.

    Χρησιμοποιείται στα γραφήματα:
    - Μηνιαία σύνοψη εσόδων / εξόδων
    - Υπόλοιπο ανά μήνα

    Αν δοθούν date_from/date_to, περιορίζει τα δεδομένα στο επιλεγμένο διάστημα.
    """

    conn = get_connection()

    try:
        cursor = conn.cursor()

        sql = """
            SELECT
                substr(t.TranRegDate, 1, 7) AS Month,
                SUM(CASE WHEN c.CategoryType = 'income' THEN t.TranAmount ELSE 0 END) AS TotalIncome,
                SUM(CASE WHEN c.CategoryType = 'expense' THEN t.TranAmount ELSE 0 END) AS TotalExpense,
                ROUND(
                    SUM(CASE WHEN c.CategoryType = 'income' THEN t.TranAmount ELSE 0 END) -
                    SUM(CASE WHEN c.CategoryType = 'expense' THEN t.TranAmount ELSE 0 END),
                    2
                ) AS Balance
            FROM Transactions t
            INNER JOIN Categories c ON t.TranCategoryID = c.CategoryID
            WHERE 1 = 1
        """

        params = []

        # Φίλτρο ημερομηνίας Από.
        if date_from:
            sql += " AND t.TranRegDate >= ?"
            params.append(date_from)

        # Φίλτρο ημερομηνίας Έως.
        if date_to:
            sql += " AND t.TranRegDate <= ?"
            params.append(date_to)

        sql += """
            GROUP BY substr(t.TranRegDate, 1, 7)
            ORDER BY Month
        """

        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()

def recurring_transaction_exists_for_month(rec_tran_id, month, year):
    """
    Ελέγχει αν έχει ήδη δημιουργηθεί συναλλαγή για recurring εγγραφή στον μήνα.

    Ο έλεγχος γίνεται με marker στην περιγραφή, π.χ. [AUTO-REC:3].
    """

    marker = f"[AUTO-REC:{rec_tran_id}]"
    month_key = f"{int(year):04d}-{int(month):02d}"

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) AS Cnt
            FROM Transactions
            WHERE substr(TranRegDate, 1, 7) = ?
              AND TranDescr LIKE ?
        """, (month_key, f"%{marker}%"))

        count = cursor.fetchone()["Cnt"]
        return count > 0
    finally:
        conn.close()
