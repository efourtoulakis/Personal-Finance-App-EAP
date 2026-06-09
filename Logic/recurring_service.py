"""
Λογική για επαναλαμβανόμενες μηνιαίες συναλλαγές.

Το project ζητά να μπορεί ο χρήστης να χαρακτηρίσει μία κίνηση ως μηνιαία.
Εδώ υλοποιούμε το πρακτικό κομμάτι: από τις ενεργές recurring εγγραφές
δημιουργούμε πραγματικές συναλλαγές για έναν επιλεγμένο μήνα.
"""

from datetime import datetime

from Db.database import (
    insert_transaction,
    recurring_transaction_exists_for_month,
    select_recurring_transactions,
)


def _month_key(year, month):
    """
    Φτιάχνει κείμενο μορφής YYYY-MM για σύγκριση μηνών.

    Παράδειγμα:
    year=2026, month=6 -> "2026-06"
    Το χρησιμοποιούμε για να συγκρίνουμε αν ένας μήνας είναι πριν ή μετά
    από τον μήνα έναρξης μιας recurring εγγραφής.
    """

    return f"{int(year):04d}-{int(month):02d}"


def _get_start_month_key(start_date_text):
    """
    Παίρνει την ημερομηνία έναρξης μιας recurring εγγραφής και επιστρέφει YYYY-MM.

    Η βάση κρατά την ημερομηνία ως κείμενο YYYY-MM-DD.
    Αν για οποιονδήποτε λόγο υπάρχει λάθος τιμή, επιστρέφουμε None
    ώστε να παραλείψουμε την εγγραφή χωρίς να σπάσει όλη η διαδικασία.
    """

    try:
        start_date = datetime.strptime(start_date_text, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None

    return f"{start_date.year:04d}-{start_date.month:02d}"


def generate_monthly_transactions(month, year):
    """
    Δημιουργεί συναλλαγές μήνα από τις ενεργές recurring εγγραφές.

    Παραδοχή:
    Μία recurring εγγραφή δημιουργεί συναλλαγές από τον μήνα έναρξής της και μετά.
    Για απλότητα, η αυτόματη συναλλαγή μπαίνει στην πρώτη ημέρα του μήνα.

    Παράδειγμα:
    Αν recurring εγγραφή ξεκινά στις 2026-06-15, τότε δεν δημιουργείται για 05/2026,
    αλλά μπορεί να δημιουργηθεί για 06/2026 και για τους επόμενους μήνες.
    """

    created_count = 0
    skipped_count = 0

    # Ο μήνας για τον οποίο ζητήθηκε δημιουργία recurring συναλλαγών.
    target_month_key = _month_key(year, month)

    # Διαβάζουμε μόνο τις ενεργές recurring εγγραφές.
    recurring_rows = select_recurring_transactions(active_only=True)

    # Η ημερομηνία της αυτόματης εγγραφής μπαίνει στην πρώτη ημέρα του μήνα.
    transaction_date = f"{int(year):04d}-{int(month):02d}-01"

    for row in recurring_rows:
        rec_id = row["RecTranID"]

        # Ελέγχουμε από ποιον μήνα και μετά επιτρέπεται να δημιουργηθεί.
        start_month_key = _get_start_month_key(row["RecTranStartDate"])

        # Αν η ημερομηνία έναρξης είναι χαλασμένη ή ο μήνας στόχος είναι πριν
        # από τον μήνα έναρξης, δεν δημιουργούμε συναλλαγή.
        if start_month_key is None or target_month_key < start_month_key:
            skipped_count += 1
            continue

        # Αποφεύγουμε διπλές αυτόματες εγγραφές στον ίδιο μήνα.
        if recurring_transaction_exists_for_month(rec_id, month, year):
            skipped_count += 1
            continue

        # Βάζουμε marker στην περιγραφή για να ξέρουμε από ποιο recurring δημιουργήθηκε.
        # Αυτό βοηθάει και στον έλεγχο διπλοεγγραφών.
        description = row["RecTranDescr"] or "Επαναλαμβανόμενη συναλλαγή"
        description = f"{description} [AUTO-REC:{rec_id}]"

        # Δημιουργούμε κανονική συναλλαγή στον πίνακα Transactions.
        insert_transaction(
            row["RecTranCategoryID"],
            row["RecTranAmount"],
            transaction_date,
            description,
        )

        created_count += 1

    return {
        "created": created_count,
        "skipped": skipped_count,
    }
