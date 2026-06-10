"""
Validation helpers για τις φόρμες της εφαρμογής.

Στόχος του αρχείου είναι να μη γεμίσουμε το GUI με πολλούς ελέγχους.
Το GUI καλεί αυτές τις συναρτήσεις και παίρνει καθαρό αποτέλεσμα ή σφάλμα.
"""

from datetime import datetime


class ValidationError(Exception):
    """Δικό μας exception για λάθη εισαγωγής από τον χρήστη."""


def validate_required(value, field_name):
    """Ελέγχει ότι ένα πεδίο δεν είναι κενό."""

    if value is None or str(value).strip() == "":
        raise ValidationError(f"Το πεδίο '{field_name}' είναι υποχρεωτικό.")

    return str(value).strip()


def validate_amount(value):
    """Μετατρέπει το ποσό σε float και ελέγχει ότι είναι θετικό."""

    value = validate_required(value, "Ποσό")

    try:
        amount = float(value.replace(",", "."))
    except ValueError as exc:
        raise ValidationError("Το ποσό πρέπει να είναι αριθμός.") from exc

    if amount <= 0:
        raise ValidationError("Το ποσό πρέπει να είναι μεγαλύτερο από το μηδέν.")

    return amount


def validate_date(value):
    """Ελέγχει ημερομηνία στη μορφή YYYY-MM-DD."""

    value = validate_required(value, "Ημερομηνία")

    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("Η ημερομηνία πρέπει να έχει μορφή YYYY-MM-DD.") from exc

    return value


def validate_category_name(value):
    """Ελέγχει όνομα κατηγορίας."""

    name = validate_required(value, "Κατηγορία")

    if len(name) < 2:
        raise ValidationError("Το όνομα κατηγορίας πρέπει να έχει τουλάχιστον 2 χαρακτήρες.")

    return name


def validate_category_type(value):
    """Ελέγχει ότι ο τύπος κατηγορίας είναι ένας από τους δύο επιτρεπτούς."""

    if value not in ("income", "expense"):
        raise ValidationError("Ο τύπος κατηγορίας πρέπει να είναι income ή expense.")

    return value


def validate_month(value):
    """Ελέγχει μήνα από 1 έως 12."""

    try:
        month = int(value)
    except ValueError as exc:
        raise ValidationError("Ο μήνας πρέπει να είναι αριθμός από 1 έως 12.") from exc

    if month < 1 or month > 12:
        raise ValidationError("Ο μήνας πρέπει να είναι από 1 έως 12.")

    return month


def validate_year(value):
    """Ελέγχει έτος σε απλό λογικό εύρος."""

    try:
        year = int(value)
    except ValueError as exc:
        raise ValidationError("Το έτος πρέπει να είναι αριθμός.") from exc

    if year < 2000 or year > 2100:
        raise ValidationError("Το έτος πρέπει να είναι ανάμεσα στο 2000 και στο 2100.")

    return year


def handle_error(error):
    """Επιστρέφει φιλικό μήνυμα σφάλματος για εμφάνιση στο GUI."""

    if isinstance(error, ValidationError):
        return str(error)

    return f"Παρουσιάστηκε σφάλμα: {error}"
