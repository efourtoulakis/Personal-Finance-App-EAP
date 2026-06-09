"""
PDF export για μηνιαία οικονομική αναφορά.

Χρησιμοποιούμε fpdf2, γιατί είναι βιβλιοθήκη ειδικά για δημιουργία PDF reports.
Η οθόνη του GUI καλεί μόνο τη function export_month_to_pdf().

Σημαντικό για τα ελληνικά:
Τα PDF έχουν θέμα με τις απλές ενσωματωμένες γραμματοσειρές, γιατί δεν καλύπτουν
σωστά ελληνικούς χαρακτήρες. Γι' αυτό χρησιμοποιούμε Unicode γραμματοσειρά.
Προτιμάμε τη DejaVu Sans που συνήθως υπάρχει μαζί με τη matplotlib, την οποία
ήδη χρησιμοποιούμε για τα γραφήματα.
"""


# Η inspect χρησιμοποιείται για να ελέγξουμε δυναμικά
# ποιες παραμέτρους δέχεται η add_font().
# Έτσι ο κώδικας δουλεύει πιο σωστά με διαφορετικές εκδόσεις της fpdf/fpdf2.
import inspect


# Η os χρησιμοποιείται για χειρισμό αρχείων και paths.
# Εδώ τη χρειαζόμαστε για να ελέγχουμε αν υπάρχουν αρχεία γραμματοσειρών
# και για να διαγράφουμε προσωρινά αρχεία εικόνων μετά τη δημιουργία του PDF.
import os

# Η re χρησιμοποιείται για regular expressions.
# Εδώ τη χρησιμοποιούμε για να εντοπίζουμε και να κρύβουμε από το PDF
# το εσωτερικό marker των επαναλαμβανόμενων συναλλαγών, π.χ. [AUTO-REC:3]
import re

# Η tempfile χρησιμοποιείται για τη δημιουργία προσωρινών αρχείων.
# Εδώ τη χρησιμοποιούμε για να αποθηκεύσουμε προσωρινά το γράφημα ως εικόνα PNG,
# ώστε να μπορέσει να ενσωματωθεί μέσα στο PDF.
import tempfile

from fpdf import FPDF

from Db.database import (
    select_expenses_by_category,
    select_month_totals,
    select_transactions,
)

from datetime import datetime
from matplotlib.figure import Figure




AUTO_REC_MARKER_PATTERN = re.compile(r"\s*\[AUTO-REC:\d+\]\s*")


def date_to_greek(date_text):
    """Μετατρέπει ημερομηνία από YYYY-MM-DD σε DD-MM-YYYY για εμφάνιση στο PDF."""

    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d-%m-%Y")
    except (TypeError, ValueError):
        return date_text or ""


def description_to_display(description):
    """
    Κρύβει το εσωτερικό marker recurring από το PDF.

    Το marker μένει στη βάση για αποφυγή διπλοεγγραφών,
    αλλά δεν πρέπει να εμφανίζεται στον τελικό χρήστη.
    """

    if not description:
        return ""

    return AUTO_REC_MARKER_PATTERN.sub("", str(description)).strip()





# -----------------------------------------------------------------------------
# FONT HELPERS
# -----------------------------------------------------------------------------

def _find_unicode_font():
    """
    Βρίσκει γραμματοσειρά που υποστηρίζει ελληνικά.

    Πρώτα ψάχνουμε τη DejaVu Sans μέσω matplotlib, γιατί είναι πιο σταθερή
    για ελληνικά από το να βασιστούμε σε Arial/Calibri των Windows.
    Αν δεν βρεθεί από τη matplotlib, ελέγχουμε μερικά συνηθισμένα paths.
    """

    # 1. Προτιμάμε τη DejaVu Sans της matplotlib.
    # Η matplotlib υπάρχει ήδη στο project λόγω των γραφημάτων.
    try:
        from matplotlib import font_manager

        font_path = font_manager.findfont("DejaVu Sans", fallback_to_default=True)
        if font_path and os.path.exists(font_path):
            return font_path
    except Exception:
        # Αν για κάποιο λόγο δεν δουλέψει η matplotlib, συνεχίζουμε με manual paths.
        pass

    # 2. Εναλλακτικά γνωστά paths σε Linux / macOS / Windows.
    candidate_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        r"C:\Windows\Fonts\DejaVuSans.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]

    for font_path in candidate_fonts:
        if os.path.exists(font_path):
            return font_path

    raise RuntimeError(
        "Δεν βρέθηκε γραμματοσειρά Unicode για το PDF. "
        "Χρειάζεται διαθέσιμη γραμματοσειρά όπως DejaVu Sans ή Arial."
    )


def _add_unicode_font(pdf, family, style, font_path):
    """
    Προσθέτει Unicode font στο PDF.

    Σημείωση:
    Η βιβλιοθήκη εγκαθίσταται ως fpdf2, αλλά γίνεται import ως fpdf.
    Σε κάποιους υπολογιστές μπορεί να υπάρχει παλιό πακέτο fpdf.
    Γι' αυτό ελέγχουμε αν η add_font() δέχεται παράμετρο uni=True.
    Έτσι ο κώδικας είναι πιο ανθεκτικός και στα δύο περιβάλλοντα.
    """

    params = inspect.signature(pdf.add_font).parameters

    if "uni" in params:
        # Παλιότερη βιβλιοθήκη fpdf/pyfpdf: θέλει uni=True για ελληνικά.
        pdf.add_font(family, style, font_path, uni=True)
    else:
        # fpdf2: τα Unicode fonts υποστηρίζονται χωρίς uni=True.
        pdf.add_font(family, style, font_path)


def _clean_text(value, max_chars=None):
    """
    Καθαρίζει κείμενο πριν μπει στο PDF.

    Αφαιρούμε αλλαγές γραμμής για να μη χαλάσει ο απλός πίνακας.
    Αν το κείμενο είναι μεγάλο, το κόβουμε ώστε να χωράει στη στήλη.
    """

    if value is None:
        text = ""
    else:
        text = str(value)

    text = text.replace("\n", " ").replace("\r", " ").strip()

    if max_chars is not None and len(text) > max_chars:
        text = text[: max_chars - 3] + "..."

    return text

def _create_expenses_chart_image(month, year):
    """
    Δημιουργεί προσωρινή εικόνα γραφήματος εξόδων ανά κατηγορία.

    Χρησιμοποιούμε οριζόντιο bar chart αντί για pie chart,
    γιατί στο PDF είναι πιο καθαρό όταν υπάρχουν πολλές κατηγορίες.
    """

    rows = select_expenses_by_category(month, year)

    if not rows:
        return None

    labels = [row["Category"] for row in rows]
    values = [float(row["TotalExpense"]) for row in rows]

    if sum(values) == 0:
        return None

    # Ταξινομούμε τα έξοδα ώστε το γράφημα να είναι πιο ευανάγνωστο.
    chart_data = sorted(zip(labels, values), key=lambda item: item[1])

    labels = [item[0] for item in chart_data]
    values = [item[1] for item in chart_data]

    fig = Figure(figsize=(8, 4.8), dpi=120)
    ax = fig.add_subplot(111)

    ax.barh(labels, values)

    ax.set_title(f"Έξοδα ανά κατηγορία - {month:02d}/{year}")
    ax.set_xlabel("Ποσό (€)")

    # Γράφουμε το ποσό δίπλα από κάθε μπάρα.
    # Δίνουμε έξτρα χώρο δεξιά στο γράφημα,
    # ώστε τα ποσά να μη πέφτουν πάνω στο όριο του πλαισίου.
    max_value = max(values)
    right_space = max_value * 0.20
    text_space = max_value * 0.02

    ax.set_xlim(0, max_value + right_space)

    # Εμφανίζουμε το ποσό λίγο δεξιά από κάθε μπάρα.
    for index, value in enumerate(values):
        ax.text(
            value + text_space,
            index,
            f"{value:.2f} €",
            va="center",
            fontsize=9,
        )

    fig.tight_layout()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    chart_path = temp_file.name
    temp_file.close()

    fig.savefig(chart_path, bbox_inches="tight")

    return chart_path


# -----------------------------------------------------------------------------
# PDF CLASS
# -----------------------------------------------------------------------------

class MonthlyReportPDF(FPDF):
    """
    Μικρή κλάση για το PDF report.

    Βάζουμε εδώ header/footer ώστε το κεντρικό export function να μείνει πιο καθαρό.
    """

    def header(self):
        """Header που εμφανίζεται στην κορυφή κάθε σελίδας."""

        self.set_font("ReportFont", "B", 12)
        self.cell(0, 8, "Personal Finance Manager", 0, 1, "C")
        self.ln(2)

    def footer(self):
        """Footer που εμφανίζεται στο κάτω μέρος κάθε σελίδας."""

        self.set_y(-15)
        self.set_font("ReportFont", "", 8)
        self.cell(0, 8, f"Σελίδα {self.page_no()}", 0, 0, "C")


# -----------------------------------------------------------------------------
# TABLE HELPERS
# -----------------------------------------------------------------------------

def _write_table_header(pdf, column_widths):
    """Γράφει την επικεφαλίδα του πίνακα συναλλαγών."""

    pdf.set_font("ReportFont", "B", 9)
    pdf.set_fill_color(230, 230, 230)

    headers = ["Ημερομηνία", "Κατηγορία", "Τύπος", "Ποσό", "Περιγραφή"]

    for header, width in zip(headers, column_widths):
        pdf.cell(width, 8, header, 1, 0, "C", True)

    pdf.ln(8)


def _write_transaction_row(pdf, transaction, column_widths):
    """Γράφει μία γραμμή συναλλαγής στον πίνακα."""

    is_income = transaction["CategoryType"] == "income"
    transaction_type = "Έσοδο" if is_income else "Έξοδο"

    # Το ποσό στη βάση αποθηκεύεται πάντα θετικό.
    # Στο PDF όμως θέλουμε τα έξοδα να εμφανίζονται με αρνητικό πρόσημο.
    amount = float(transaction["TranAmount"])

    if not is_income:
        amount = -amount

    row_values = [
        _clean_text(date_to_greek(transaction["TranRegDate"]), 12),
        _clean_text(transaction["Category"], 18),
        transaction_type,
        f"{amount:.2f} €",
        _clean_text(description_to_display(transaction["TranDescr"]), 36),
    ]

    pdf.set_font("ReportFont", "", 8)

    for value, width in zip(row_values, column_widths):
        pdf.cell(width, 7, value, 1, 0)

    pdf.ln(7)

# -----------------------------------------------------------------------------
# EXPORT FUNCTION
# -----------------------------------------------------------------------------

def export_month_to_pdf(month, year, file_path):
    """
    Δημιουργεί PDF αρχείο με σύνοψη και συναλλαγές συγκεκριμένου μήνα.

    Αυτή είναι η function που καλεί το GUI.
    Κρατάμε ίδιο όνομα με πριν, ώστε το charts_export.py να μη χρειαστεί αλλαγή.
    """

    month = int(month)
    year = int(year)

    # Διαβάζουμε δεδομένα από το database layer.
    transactions = select_transactions(month, year)
    totals = select_month_totals(month, year)
    
    # Δημιουργούμε προσωρινό γράφημα εξόδων ανά κατηγορία.
    # Αν δεν υπάρχουν έξοδα, η function επιστρέφει None.
    chart_path = _create_expenses_chart_image(month, year)

    # Βρίσκουμε και φορτώνουμε Unicode γραμματοσειρά.
    font_path = _find_unicode_font()

    pdf = MonthlyReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Βάζουμε την ίδια γραμματοσειρά και για normal και για bold.
    # Για φοιτητική εργασία είναι αρκετό και κρατάει τον κώδικα απλό.
    _add_unicode_font(pdf, "ReportFont", "", font_path)
    _add_unicode_font(pdf, "ReportFont", "B", font_path)

    pdf.add_page()

    # Τίτλος αναφοράς.
    pdf.set_font("ReportFont", "B", 15)
    pdf.cell(0, 10, f"Αναφορά οικονομικών κινήσεων - {month:02d}/{year}", 0, 1, "C")
    pdf.ln(5)

    # Σύνοψη μήνα.
    pdf.set_font("ReportFont", "", 11)
    pdf.cell(0, 7, f"Σύνολο εσόδων: {totals['income']:.2f} €", 0, 1)
    pdf.cell(0, 7, f"Σύνολο εξόδων: {-totals['expense']:.2f} €", 0, 1)
    pdf.cell(0, 7, f"Υπόλοιπο: {totals['balance']:.2f} €", 0, 1)
    pdf.cell(0, 7, f"Πλήθος συναλλαγών: {len(transactions)}", 0, 1)
    pdf.ln(6)

    # Τίτλος πίνακα.
    pdf.set_font("ReportFont", "B", 11)
    pdf.cell(0, 8, "Συναλλαγές μήνα", 0, 1)

    # Πλάτη στηλών ώστε να χωράει ο πίνακας σε Α4.
    column_widths = [28, 42, 23, 26, 71]

    if not transactions:
        pdf.set_font("ReportFont", "", 10)
        pdf.cell(0, 8, "Δεν υπάρχουν συναλλαγές για τον επιλεγμένο μήνα.", 0, 1)
    else:
        _write_table_header(pdf, column_widths)

        for transaction in transactions:
            # Αν φτάνουμε χαμηλά στη σελίδα, ανοίγουμε νέα σελίδα
            # και ξαναγράφουμε την επικεφαλίδα του πίνακα.
            if pdf.get_y() > 265:
                pdf.add_page()
                _write_table_header(pdf, column_widths)

            _write_transaction_row(pdf, transaction, column_widths)

    
    # Αν δημιουργήθηκε γράφημα, το προσθέτουμε σε νέα σελίδα στο τέλος του PDF.
    if chart_path:
        pdf.add_page()

        pdf.set_font("ReportFont", "B", 13)
        pdf.cell(0, 10, "Γράφημα εξόδων ανά κατηγορία", 0, 1, "C")
        pdf.ln(5)

        # Τοποθετούμε την εικόνα στο PDF.
        # x=20 σημαίνει λίγο περιθώριο αριστερά.
        # w=170 σημαίνει ότι θα χωράει όμορφα σε σελίδα A4.
        pdf.image(chart_path, x=20, w=170)

    # Αποθήκευση στο path που επέλεξε ο χρήστης.
    pdf.output(file_path)

    # Διαγράφουμε το προσωρινό αρχείο εικόνας για να μη μένει άχρηστο αρχείο στον δίσκο.
    if chart_path and os.path.exists(chart_path):
        os.remove(chart_path)

    return file_path   
    
    
 