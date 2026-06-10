"""
Δημιουργεί έτοιμα demo δεδομένα για την παρουσίαση της εφαρμογής
Personal Finance Manager.

Στόχος:
- Να έχουμε καθαρές κατηγορίες, συναλλαγές και επαναλαμβανόμενες εγγραφές.
- Να υπάρχουν αρκετά δεδομένα για Συναλλαγές, Φίλτρα Από/Έως, Γραφήματα και Exports.
- Να μη χρειάζεται χειροκίνητη καταχώρηση πριν την παρουσίαση.

Σημαντικό:
Το script δημιουργεί πρώτα backup του υπάρχοντος DB_NAME.
Μετά καθαρίζει τα δεδομένα και εισάγει demo δεδομένα.

Εκτέλεση από τη ρίζα του project:
    python demo_data.py
"""

import os
import shutil
import sqlite3
from datetime import datetime

from Db.database import DB_NAME, initialize_database


# -----------------------------------------------------------------------------
# ΒΟΗΘΗΤΙΚΕΣ FUNCTIONS
# -----------------------------------------------------------------------------

def backup_database():
    """
    Δημιουργεί backup της υπάρχουσας βάσης πριν αλλάξουμε δεδομένα.

    Αν υπάρχει ήδη DB_NAME, το αντιγράφουμε με timestamp.
    Έτσι μπορούμε να επαναφέρουμε την παλιά βάση αν χρειαστεί.
    """

    if not os.path.exists(DB_NAME):
        return None

    project_root = os.path.dirname(DB_NAME)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"finance_backup_before_demo_{timestamp}.db"
    backup_path = os.path.join(project_root, backup_name)

    shutil.copy2(DB_NAME, backup_path)
    return backup_path


def get_connection():
    """
    Ανοίγει σύνδεση με τη SQLite.

    Ενεργοποιούμε foreign keys, γιατί η εφαρμογή βασίζεται σε αυτά
    για να προστατεύει τις σχέσεις ανάμεσα σε κατηγορίες και συναλλαγές.
    """

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def clear_existing_data(conn):
    """
    Καθαρίζει τα υπάρχοντα δεδομένα.

    Η σειρά είναι σημαντική:
    πρώτα διαγράφουμε child tables και μετά categories,
    γιατί οι συναλλαγές και οι recurring εγγραφές δείχνουν σε κατηγορίες.
    """

    cursor = conn.cursor()

    cursor.execute("DELETE FROM Transactions;")
    cursor.execute("DELETE FROM Recurring_Transactions;")
    cursor.execute("DELETE FROM Categories;")

    # Μηδενίζουμε τα autoincrement IDs για να είναι καθαρή η demo βάση.
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('Transactions', 'Recurring_Transactions', 'Categories');")

    conn.commit()


def insert_categories(conn):
    """
    Εισάγει demo κατηγορίες εσόδων και εξόδων.

    Κρατάμε απλές, κατανοητές κατηγορίες ώστε να φαίνονται ωραία
    και στα γραφήματα και στα exports.
    """

    categories = [
        ("Μισθός", "Σταθερό μηνιαίο εισόδημα", "income"),
        ("Freelance", "Έσοδα από ελεύθερη εργασία", "income"),
        ("Επίδομα", "Επίδομα ή άλλη οικονομική ενίσχυση", "income"),

        ("Ενοίκιο", "Μηνιαίο κόστος ενοικίου", "expense"),
        ("Τρόφιμα", "Αγορές super market και τρόφιμα", "expense"),
        ("Λογαριασμοί", "Ρεύμα, νερό, internet, τηλέφωνο", "expense"),
        ("Μεταφορές", "Καύσιμα, εισιτήρια, μετακινήσεις", "expense"),
        ("Ψυχαγωγία", "Έξοδοι, χόμπι και διασκέδαση", "expense"),
        ("Υγεία", "Φάρμακα, γιατροί και εξετάσεις", "expense"),
        ("Εκπαίδευση", "Μαθήματα, βιβλία και εκπαιδευτικό υλικό", "expense"),
    ]

    cursor = conn.cursor()

    cursor.executemany(
        """
        INSERT INTO Categories (Category, CategoryDescr, CategoryType)
        VALUES (?, ?, ?)
        """,
        categories,
    )

    conn.commit()


def get_category_ids(conn):
    """
    Επιστρέφει λεξικό με όνομα κατηγορίας -> CategoryID.

    Αυτό μας βοηθά να εισάγουμε συναλλαγές χωρίς να γράφουμε χειροκίνητα IDs.
    """

    cursor = conn.cursor()
    cursor.execute("SELECT CategoryID, Category FROM Categories;")

    return {
        row["Category"]: row["CategoryID"]
        for row in cursor.fetchall()
    }


def insert_transactions(conn, category_ids):
    """
    Εισάγει demo συναλλαγές για 6 μήνες.

    Τα ποσά αποθηκεύονται θετικά στη βάση.
    Το αν είναι έσοδο ή έξοδο προκύπτει από τον τύπο της κατηγορίας.
    """

    demo_transactions = [
        # Ιανουάριος 2026
        ("Μισθός", 1200, "2026-01-01", "Μισθός Ιανουαρίου"),
        ("Freelance", 180, "2026-01-12", "Μικρή εργασία πελάτη"),
        ("Ενοίκιο", 450, "2026-01-02", "Ενοίκιο Ιανουαρίου"),
        ("Τρόφιμα", 260, "2026-01-08", "Super market"),
        ("Λογαριασμοί", 135, "2026-01-15", "Ρεύμα και internet"),
        ("Μεταφορές", 90, "2026-01-20", "Καύσιμα και εισιτήρια"),
        ("Ψυχαγωγία", 75, "2026-01-25", "Έξοδος με φίλους"),

        # Φεβρουάριος 2026
        ("Μισθός", 1200, "2026-02-01", "Μισθός Φεβρουαρίου"),
        ("Επίδομα", 100, "2026-02-10", "Οικονομική ενίσχυση"),
        ("Ενοίκιο", 450, "2026-02-02", "Ενοίκιο Φεβρουαρίου"),
        ("Τρόφιμα", 285, "2026-02-09", "Super market"),
        ("Λογαριασμοί", 120, "2026-02-14", "Λογαριασμοί μήνα"),
        ("Μεταφορές", 80, "2026-02-19", "Μετακινήσεις"),
        ("Υγεία", 45, "2026-02-22", "Φάρμακα"),

        # Μάρτιος 2026
        ("Μισθός", 1200, "2026-03-01", "Μισθός Μαρτίου"),
        ("Freelance", 250, "2026-03-11", "Έσοδο από project"),
        ("Ενοίκιο", 450, "2026-03-02", "Ενοίκιο Μαρτίου"),
        ("Τρόφιμα", 310, "2026-03-07", "Αγορές τροφίμων"),
        ("Λογαριασμοί", 150, "2026-03-16", "Ρεύμα"),
        ("Μεταφορές", 95, "2026-03-18", "Καύσιμα"),
        ("Εκπαίδευση", 60, "2026-03-23", "Βιβλία και σημειώσεις"),

        # Απρίλιος 2026
        ("Μισθός", 1200, "2026-04-01", "Μισθός Απριλίου"),
        ("Ενοίκιο", 450, "2026-04-02", "Ενοίκιο Απριλίου"),
        ("Τρόφιμα", 295, "2026-04-08", "Super market"),
        ("Λογαριασμοί", 110, "2026-04-15", "Internet και τηλέφωνο"),
        ("Μεταφορές", 20, "2026-04-20", "Καύσιμα"),
        ("Ψυχαγωγία", 120, "2026-04-26", "Σινεμά και έξοδος"),

        # Μάιος 2026
        ("Μισθός", 1200, "2026-05-01", "Μισθός Μαΐου"),
        ("Freelance", 300, "2026-05-13", "Freelance εργασία"),
        ("Ενοίκιο", 450, "2026-05-02", "Ενοίκιο Μαΐου"),
        ("Τρόφιμα", 325, "2026-05-09", "Super market"),
        ("Λογαριασμοί", 140, "2026-05-16", "Λογαριασμοί"),
        ("Μεταφορές", 20, "2026-05-21", "Μετακινήσεις"),
        ("Υγεία", 70, "2026-05-24", "Ιατρικά έξοδα"),

        # Ιούνιος 2026
        ("Μισθός", 1200, "2026-06-01", "Μισθός Ιουνίου"),
        ("Ενοίκιο", 450, "2026-06-02", "Ενοίκιο Ιουνίου"),
        ("Τρόφιμα", 300, "2026-06-08", "Super market"),
        ("Λογαριασμοί", 125, "2026-06-15", "Λογαριασμοί Ιουνίου"),
        ("Μεταφορές", 90, "2026-06-20", "Καύσιμα"),
        ("Ψυχαγωγία", 20, "2026-06-22", "Έξοδος"),
        ("Εκπαίδευση", 55, "2026-06-25", "Εκπαιδευτικό υλικό"),
    ]

    rows = [
        (
            category_ids[category],
            amount,
            tran_date,
            description,
        )
        for category, amount, tran_date, description in demo_transactions
    ]

    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO Transactions (TranCategoryID, TranAmount, TranRegDate, TranDescr)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )

    conn.commit()


def insert_recurring_transactions(conn, category_ids):
    """
    Εισάγει demo επαναλαμβανόμενες εγγραφές.

    Περιλαμβάνει και μία ανενεργή εγγραφή, ώστε στην παρουσίαση να φανεί
    ότι οι ανενεργές recurring εγγραφές δεν δημιουργούν συναλλαγές.
    """

    recurring_rows = [
        (category_ids["Μισθός"], 1200, "2026-07-01", "Μηνιαίος μισθός", 1),
        (category_ids["Ενοίκιο"], 450, "2026-07-01", "Μηνιαίο ενοίκιο", 1),
        (category_ids["Λογαριασμοί"], 125, "2026-07-01", "Σταθεροί λογαριασμοί", 1),
        (category_ids["Μεταφορές"], 80, "2026-07-01", "Κάρτα μετακινήσεων", 1),
        (category_ids["Ψυχαγωγία"], 25, "2026-07-01", "Συνδρομή streaming ανενεργή", 0),
    ]

    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO Recurring_Transactions
        (RecTranCategoryID, RecTranAmount, RecTranStartDate, RecTranDescr, RecTranActive)
        VALUES (?, ?, ?, ?, ?)
        """,
        recurring_rows,
    )

    conn.commit()


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def main():
    """
    Κεντρική ροή του demo script.

    Ζητάμε επιβεβαίωση από τον χρήστη, γιατί το script καθαρίζει τα υπάρχοντα δεδομένα.
    """

    print("Personal Finance Manager — Demo Data Setup")
    print("-" * 50)
    print(f"Βάση δεδομένων: {DB_NAME}")
    print()
    print("ΠΡΟΣΟΧΗ: Θα δημιουργηθεί backup και μετά θα αντικατασταθούν τα δεδομένα με demo δεδομένα.")
    print("Για να συνεχίσετε, γράψτε YES και πατήστε Enter.")
    confirmation = input("> ").strip()

    if confirmation != "YES":
        print("Ακύρωση. Δεν έγινε καμία αλλαγή.")
        return

    # Δημιουργούμε τους πίνακες αν δεν υπάρχουν ήδη.
    initialize_database()

    # Backup πριν από οποιαδήποτε αλλαγή.
    backup_path = backup_database()

    conn = get_connection()

    try:
        clear_existing_data(conn)
        insert_categories(conn)
        category_ids = get_category_ids(conn)
        insert_transactions(conn, category_ids)
        insert_recurring_transactions(conn, category_ids)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    print()
    print("Τα demo δεδομένα δημιουργήθηκαν επιτυχώς.")

    if backup_path:
        print(f"Backup παλιάς βάσης: {backup_path}")

    print()
    print("Μπορείτε τώρα να ανοίξετε την εφαρμογή με:")
    print("python main.py")


if __name__ == "__main__":
    main()
