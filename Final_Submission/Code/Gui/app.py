"""Personal Finance Manager - GUI (Dark Theme)

Το αρχείο αυτό περιέχει το βασικό γραφικό περιβάλλον της εφαρμογής.
Η εφαρμογή είναι χωρισμένη σε επίπεδα, ώστε ο κώδικας να παραμένει καθαρός:

- Το GUI εμφανίζει φόρμες, πίνακες, κουμπιά και μηνύματα στον χρήστη.
- Το Db/database.py χειρίζεται τη σύνδεση με τη SQLite και τις SQL εντολές.
- Το Logic/ περιέχει βοηθητική λογική, όπως recurring συναλλαγές και validation.
- Το Exports_Pdf_Excel/ περιέχει την εξαγωγή αρχείων.

Βασική ροή λειτουργίας:
ο χρήστης πατάει κουμπί -> καλείται function του GUI -> καλείται function του database layer -> ενημερώνεται η SQLite.

Στο GUI δεν γράφονται SQL queries. Αυτό βοηθάει ώστε κάθε μέρος της εφαρμογής
να έχει ξεκάθαρη ευθύνη και να είναι πιο εύκολη η συντήρηση του project.
"""

# Η tkinter χρησιμοποιείται για το βασικό GUI της εφαρμογής.
import tkinter as tk

# Το ttk δίνει πιο έτοιμα widgets, όπως Combobox και Treeview.
# Το messagebox εμφανίζει απλά ενημερωτικά / προειδοποιητικά παράθυρα.
from tkinter import ttk, messagebox

# Το Calendar εμφανίζει popup ημερολόγιο.
# Δεν χρησιμοποιούμε DateEntry εδώ, γιατί σε κάποια Windows περιβάλλοντα
# κλείνει όταν ο χρήστης πατάει τα βελάκια αλλαγής μήνα/έτους.
from tkcalendar import Calendar


class CalendarPopupEntry(tk.Frame):
    """
    Σταθερό πεδίο ημερομηνίας με popup ημερολόγιο.

    Γιατί το φτιάχνουμε έτσι:
    Το tkcalendar DateEntry κλείνει σε κάποια Windows περιβάλλοντα όταν ο χρήστης
    πατάει τα βελάκια αλλαγής μήνα/έτους. Για να μη βασιζόμαστε στα εσωτερικά
    focus events του DateEntry, φτιάχνουμε δικό μας μικρό widget:
    - ένα απλό Entry για το κείμενο της ημερομηνίας,
    - ένα κουμπί ▼ που ανοίγει Calendar σε Toplevel,
    - το popup κλείνει μόνο όταν επιλεγεί ημερομηνία ή όταν ανοίξει άλλο calendar.

    Έτσι το ημερολόγιο μένει σταθερό όταν ο χρήστης αλλάζει μήνα/έτος.
    Δεν αλλάζει καθόλου η μορφή ημερομηνίας: ο χρήστης βλέπει DD-MM-YYYY.
    """

    _active_picker = None

    def __init__(
        self,
        parent,
        textvariable,
        width=12,
        colors=None,
        font=None,
        date_pattern="dd-mm-yyyy",
        locale="el_GR",
    ):
        self.colors = colors or {}
        self.variable = textvariable
        self.date_pattern = date_pattern
        self.locale = locale
        self._popup = None
        self._calendar = None

        # Παίρνουμε το background από τον parent, ώστε να δένει με το dark theme.
        try:
            parent_bg = parent.cget("bg")
        except Exception:
            parent_bg = self.colors.get("card", "#22263a")

        super().__init__(parent, bg=parent_bg)

        self.entry = tk.Entry(
            self,
            textvariable=self.variable,
            width=width,
            bg=self.colors.get("entry_bg", "#181c2e"),
            fg=self.colors.get("text", "#e8eaf6"),
            insertbackground=self.colors.get("accent", "#4f8ef7"),
            relief="flat",
            font=font,
            highlightthickness=1,
            highlightbackground=self.colors.get("border", "#2e3250"),
            highlightcolor=self.colors.get("accent", "#4f8ef7"),
        )
        self.entry.pack(side="left")

        # Το κουμπί λειτουργεί σαν το βελάκι του DateEntry, αλλά χωρίς τα focus bugs του.
        self.button = tk.Button(
            self,
            text="▼",
            command=self._toggle_calendar,
            width=2,
            bg=self.colors.get("accent", "#4f8ef7"),
            fg="white",
            relief="flat",
            font=font,
            cursor="hand2",
            activebackground=self.colors.get("hover", "#2d3149"),
            activeforeground="white",
            bd=0,
        )
        self.button.pack(side="left", padx=(2, 0))

    # Οι παρακάτω μέθοδοι κάνουν το custom widget να συμπεριφέρεται σαν Entry/DateEntry
    # στα σημεία όπου ήδη το χρησιμοποιεί το GUI, π.χ. delete(0, "end").
    def get(self):
        """Επιστρέφει το κείμενο της ημερομηνίας."""
        return self.entry.get()

    def delete(self, first, last=None):
        """Σβήνει το περιεχόμενο του πεδίου, όπως ένα κανονικό Entry."""
        self.entry.delete(first, last)

    def insert(self, index, text):
        """Εισάγει κείμενο στο πεδίο, όπως ένα κανονικό Entry."""
        self.entry.insert(index, text)

    def focus_set(self):
        """Δίνει focus στο εσωτερικό Entry."""
        self.entry.focus_set()

    def destroy(self):
        """Κλείνει τυχόν ανοιχτό popup πριν καταστραφεί το widget."""
        self._close_calendar()
        super().destroy()

    def _toggle_calendar(self):
        """Ανοίγει ή κλείνει το popup ημερολόγιο."""

        if self._popup and self._popup.winfo_exists():
            self._close_calendar()
            return

        # Αν υπάρχει άλλο ανοιχτό calendar στο ίδιο αρχείο, το κλείνουμε πρώτα.
        # Έτσι όταν ο χρήστης πάει από "Από" σε "Έως", δεν μένουν δύο popup ανοιχτά.
        if CalendarPopupEntry._active_picker and CalendarPopupEntry._active_picker is not self:
            CalendarPopupEntry._active_picker._close_calendar()

        CalendarPopupEntry._active_picker = self
        self._open_calendar()

    def _open_calendar(self):
        """Δημιουργεί το popup Calendar ακριβώς κάτω από το αντίστοιχο πεδίο."""

        root = self.winfo_toplevel()
        root.update_idletasks()
        self.update_idletasks()
        self.entry.update_idletasks()

        # Δημιουργούμε το popup ως child του κεντρικού παραθύρου.
        # Το κάνουμε πρώτα withdraw(), ώστε να μη φανεί στιγμιαία στο 0,0 της οθόνης
        # πριν προλάβουμε να του δώσουμε τη σωστή θέση.
        self._popup = tk.Toplevel(root)
        # Marker για καθαρισμό σε αλλαγή οθόνης.
        # Έτσι, αν ο χρήστης ανοίξει calendar και μετά αλλάξει section,
        # η εφαρμογή μπορεί να κλείσει σίγουρα το popup και να μη μείνει focus state.
        self._popup._is_calendar_popup = True
        self._popup.withdraw()

        # Κρατάμε το popup σαν μικρό calendar παράθυρο χωρίς να βασιζόμαστε σε FocusOut.
        # Δεν βάζουμε μηχανισμό αυτόματου κλεισίματος στο focus, γιατί αυτό ήταν η αιτία
        # που έκλεινε όταν ο χρήστης πατούσε τα βελάκια μήνα/έτους.
        self._popup.overrideredirect(True)
        self._popup.transient(root)
        self._popup.configure(bg=self.colors.get("card", "#22263a"))

        # Αν το πεδίο έχει ήδη έγκυρη ημερομηνία, ανοίγουμε το calendar σε αυτήν.
        selected_date = None
        current_text = self.variable.get().strip()
        if current_text:
            try:
                selected_date = datetime.strptime(current_text, "%d-%m-%Y").date()
            except ValueError:
                selected_date = None

        calendar_options = {
            "master": self._popup,
            "selectmode": "day",
            "date_pattern": self.date_pattern,
            "locale": self.locale,
            "background": self.colors.get("accent", "#4f8ef7"),
            "foreground": "white",
            "borderwidth": 2,
        }

        if selected_date:
            calendar_options["year"] = selected_date.year
            calendar_options["month"] = selected_date.month
            calendar_options["day"] = selected_date.day

        self._calendar = Calendar(**calendar_options)
        self._calendar.pack(padx=2, pady=2)

        # Όταν ο χρήστης επιλέξει ημέρα, περνάμε την τιμή στο Entry και κλείνουμε.
        # Τα βελάκια αλλαγής μήνα/έτους ΔΕΝ κλείνουν το popup.
        self._calendar.bind("<<CalendarSelected>>", self._on_date_selected)
        self._popup.bind("<Escape>", lambda _event: self._close_calendar())

        # Υπολογισμός θέσης popup.
        # Πρώτα δοκιμάζουμε τις κανονικές screen συντεταγμένες του Entry.
        popup_x = self.entry.winfo_rootx()
        popup_y = self.entry.winfo_rooty() + self.entry.winfo_height()

        # Σε κάποια Windows/Tk περιβάλλοντα το winfo_rootx/rooty μπορεί να γυρίσει 0
        # για nested custom widgets. Τότε κάνουμε ασφαλές fallback:
        # παίρνουμε τη θέση του κεντρικού παραθύρου και αθροίζουμε τις τοπικές θέσεις
        # των γονικών widgets μέχρι να φτάσουμε στο root.
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()

        if popup_x <= 1 and popup_y <= 1:
            local_x = self.entry.winfo_x()
            local_y = self.entry.winfo_y() + self.entry.winfo_height()
            widget = self.entry.master

            while widget is not None and widget is not root:
                local_x += widget.winfo_x()
                local_y += widget.winfo_y()
                widget = widget.master

            popup_x = root_x + local_x
            popup_y = root_y + local_y

        # Αν για οποιονδήποτε λόγο το popup βγήκε έξω από τα όρια του παραθύρου,
        # το επαναφέρουμε κοντά στο πεδίο με βάση το κεντρικό παράθυρο.
        if popup_x < root_x - 20 or popup_y < root_y - 20:
            local_x = self.winfo_x() + self.entry.winfo_x()
            local_y = self.winfo_y() + self.entry.winfo_y() + self.entry.winfo_height()
            parent = self.master

            while parent is not None and parent is not root:
                local_x += parent.winfo_x()
                local_y += parent.winfo_y()
                parent = parent.master

            popup_x = root_x + local_x
            popup_y = root_y + local_y

        self._popup.update_idletasks()
        popup_width = self._popup.winfo_reqwidth()
        popup_height = self._popup.winfo_reqheight()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Αν το popup βγαίνει εκτός δεξιού ή κάτω ορίου οθόνης, το μετακινούμε
        # ώστε να φαίνεται ολόκληρο.
        if popup_x + popup_width > screen_width:
            popup_x = max(0, screen_width - popup_width - 10)

        if popup_y + popup_height > screen_height:
            popup_y = max(0, self.entry.winfo_rooty() - popup_height)

        self._popup.geometry(f"+{int(popup_x)}+{int(popup_y)}")
        self._popup.deiconify()
        self._popup.lift(root)
        self._calendar.focus_set()

    def _on_date_selected(self, _event=None):
        """Μεταφέρει την επιλεγμένη ημερομηνία στο πεδίο και κλείνει το popup."""

        if self._calendar is not None:
            self.variable.set(self._calendar.get_date())

        self._close_calendar()

    def _close_calendar(self):
        """Κλείνει το popup ημερολόγιο αν είναι ανοιχτό."""

        if self._popup and self._popup.winfo_exists():
            try:
                self._popup.destroy()
            except tk.TclError:
                # Αν το popup έχει ήδη κλείσει από την Tkinter, συνεχίζουμε ήρεμα.
                pass

        self._popup = None
        self._calendar = None

        if CalendarPopupEntry._active_picker is self:
            CalendarPopupEntry._active_picker = None

# date: για να βάζουμε αυτόματα τη σημερινή ημερομηνία.
# datetime: για να ελέγχουμε ότι η ημερομηνία γράφεται σωστά ως YYYY-MM-DD.
from datetime import date, datetime

# Το sqlite3 εδώ χρησιμοποιείται μόνο για να πιάσουμε συγκεκριμένα database errors,
# π.χ. όταν πάει να μπει δεύτερη φορά ίδια κατηγορία.
# Δεν το χρησιμοποιούμε για να γράψουμε SQL μέσα στο GUI.
import sqlite3

# Από το database.py φέρνουμε τις functions που χρειάζεται το GUI.
# Με αυτόν τον τρόπο το GUI δεν επικοινωνεί απευθείας με τη SQLite.
# Όλες οι αλλαγές στη βάση περνούν από ένα κοινό database layer.
from Db.database import (
    delete_category,
    delete_recurring_transaction,
    delete_transaction,
    insert_category,
    insert_recurring_transaction,
    insert_transaction,
    select_categories,
    select_recurring_by_id,
    select_recurring_transactions,
    select_transaction_by_id,
    select_transactions,
    update_category,
    update_recurring_transaction,
    update_transaction,
)

# Το re χρησιμοποιείται για regular expressions.
# Εδώ το χρειαζόμαστε για να εντοπίζουμε και να κρύβουμε από το GUI
# το εσωτερικό marker των αυτόματων recurring συναλλαγών, π.χ. [AUTO-REC:3].
import re



# Η οθόνη γραφημάτων και εξαγωγών βρίσκεται σε ξεχωριστό αρχείο.
# Έτσι το app.py παραμένει υπεύθυνο κυρίως για την πλοήγηση και τις βασικές φόρμες.
from Gui.charts_export import ChartsExportScreen

# Η δημιουργία πραγματικών συναλλαγών από recurring εγγραφές
# γίνεται στο Logic/recurring_service.py, όχι απευθείας μέσα στο GUI.
from Logic.recurring_service import generate_monthly_transactions

# Χρησιμοποιούμε helper για τον έλεγχο ονόματος κατηγορίας.
# Οι υπόλοιποι απλοί έλεγχοι της φόρμας γίνονται κοντά στα πεδία που αφορούν.
from Logic.validation import validate_category_name



# ──────────────────────────────────────────────
#  ΧΡΩΜΑΤΑ & ΘΕΜΑ ΕΦΑΡΜΟΓΗΣ
# ──────────────────────────────────────────────
# Κρατάμε όλα τα χρώματα σε ένα dictionary.
# Έτσι η εμφάνιση είναι συγκεντρωμένη σε ένα σημείο και δεν έχουμε διάσπαρτα χρώματα στον κώδικα.
C = {
    "bg":       "#0f1117",  # βασικό φόντο εφαρμογής
    "panel":    "#1a1d27",  # αριστερό μενού
    "card":     "#22263a",  # πλαίσια / κάρτες
    "border":   "#2e3250",  # γραμμές και περιγράμματα
    "accent":   "#4f8ef7",  # βασικό μπλε χρώμα
    "accent2":  "#6c63ff",  # δεύτερο χρώμα για βοηθητικά κουμπιά
    "success":  "#2ecc71",  # πράσινο για έσοδα / επιτυχία
    "danger":   "#e74c3c",  # κόκκινο για έξοδα / διαγραφή
    "warning":  "#f39c12",  # πορτοκαλί για προειδοποιήσεις
    "text":     "#e8eaf6",  # βασικό χρώμα κειμένου
    "text_sub": "#7b82a8",  # δευτερεύον κείμενο
    "hover":    "#2d3149",  # χρώμα όταν περνάει το mouse
    "entry_bg": "#181c2e",  # φόντο πεδίων εισαγωγής
    "select":   "#3d4470",  # επιλογή σε πίνακες / combobox
}

# Βασικές γραμματοσειρές που χρησιμοποιούνται σε όλη την εφαρμογή.
FONT_TITLE = ("Segoe UI", 15, "bold")
FONT_HEAD  = ("Segoe UI", 11, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)





def date_to_greek(date_text):
    """
    Μετατρέπει ημερομηνία από YYYY-MM-DD σε DD-MM-YYYY για εμφάνιση στον χρήστη.

    Η βάση κρατάει την ημερομηνία ως YYYY-MM-DD για σωστή ταξινόμηση και φιλτράρισμα.
    Στο GUI όμως εμφανίζουμε ελληνική μορφή DD-MM-YYYY.
    """

    try:
        return datetime.strptime(date_text, "%Y-%m-%d").strftime("%d-%m-%Y")
    except (TypeError, ValueError):
        return date_text or ""


def date_to_database(date_text):
    """
    Μετατρέπει ημερομηνία από DD-MM-YYYY σε YYYY-MM-DD για αποθήκευση στη βάση.

    Ο χρήστης γράφει ελληνική μορφή ημερομηνίας, αλλά η βάση κρατάει ISO μορφή.
    """

    try:
        return datetime.strptime(date_text, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Μορφή ημερομηνίας: DD-MM-YYYY") from exc




def amount_to_entry(amount):
    """
    Μορφοποιεί ποσό για εμφάνιση μέσα στη φόρμα.

    Αν το ποσό είναι ακέραιο, δείχνουμε 5 αντί για 5.0.
    Αν έχει δεκαδικά, κρατάμε τα δεκαδικά χωρίς περιττά μηδενικά.
    """

    try:
        value = float(amount)

        if value.is_integer():
            return str(int(value))

        return str(value).rstrip("0").rstrip(".")

    except (TypeError, ValueError):
        return str(amount or "")



AUTO_REC_MARKER_PATTERN = re.compile(r"\s*\[AUTO-REC:\d+\]\s*")
AUTO_REC_MARKER_EXTRACT_PATTERN = re.compile(r"\[AUTO-REC:\d+\]")


def description_to_display(description):
    """
    Επιστρέφει καθαρή περιγραφή για εμφάνιση στον χρήστη.

    Οι αυτόματες συναλλαγές από recurring εγγραφές κρατούν εσωτερικό marker
    τύπου [AUTO-REC:3], ώστε η εφαρμογή να αποφεύγει διπλές δημιουργίες.
    Το marker παραμένει στη βάση, αλλά δεν εμφανίζεται στο GUI.
    """

    if not description:
        return ""

    return AUTO_REC_MARKER_PATTERN.sub("", str(description)).strip()


def extract_auto_rec_marker(description):
    """
    Επιστρέφει το εσωτερικό recurring marker από την περιγραφή, αν υπάρχει.

    Το marker π.χ. [AUTO-REC:4] χρειάζεται να μένει στη βάση,
    γιατί χρησιμοποιείται για να μη δημιουργούνται διπλές αυτόματες συναλλαγές.
    Δεν πρέπει όμως να εμφανίζεται στον χρήστη στη φόρμα επεξεργασίας.
    """

    if not description:
        return ""

    match = AUTO_REC_MARKER_EXTRACT_PATTERN.search(str(description))

    if match:
        return match.group(0)

    return ""




# ──────────────────────────────────────────────
#  ΜΙΚΡΕΣ ΒΟΗΘΗΤΙΚΕΣ FUNCTIONS ΓΙΑ ΤΟ UI
# ──────────────────────────────────────────────
def styled_button(parent, text, command, color=None, width=12):
    """Φτιάχνει κουμπί με κοινό στυλ για να μην επαναλαμβάνουμε κώδικα."""

    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color or C["accent"],
        fg="white",
        relief="flat",
        font=FONT_BODY,
        padx=12,
        pady=6,
        cursor="hand2",
        width=width,
        activebackground=C["hover"],
        activeforeground="white",
        bd=0,
    )


def styled_entry(parent, textvariable=None, width=24):
    """Φτιάχνει πεδίο εισαγωγής με κοινό dark theme."""

    return tk.Entry(
        parent,
        textvariable=textvariable,
        width=width,
        bg=C["entry_bg"],
        fg=C["text"],
        insertbackground=C["accent"],
        relief="flat",
        font=FONT_BODY,
        highlightthickness=1,
        highlightbackground=C["border"],
        highlightcolor=C["accent"],
    )


def styled_combo(parent, textvariable, values, width=22):
    """Φτιάχνει Combobox με κοινό dark theme."""

    # Το ttk θέλει Style object για να αλλάξει εμφάνιση.
    style = ttk.Style()

    # Το clam theme δίνει καλύτερο έλεγχο στα χρώματα.
    style.theme_use("clam")

    # Ορίζουμε χρώματα για το combobox.
    style.configure(
        "Dark.TCombobox",
        fieldbackground=C["entry_bg"],
        background=C["card"],
        foreground=C["text"],
        selectbackground=C["select"],
        selectforeground=C["text"],
        arrowcolor=C["accent"],
        bordercolor=C["border"],
    )

    # Κάνουμε πιο ευδιάκριτο το κείμενο στα readonly comboboxes.
    # Σε κάποια Windows themes το readonly combobox εμφανίζεται πολύ γκρι.
    style.map(
        "Dark.TCombobox",
        fieldbackground=[("readonly", C["entry_bg"])],
        foreground=[("readonly", C["text"])],
        selectbackground=[("readonly", C["select"])],
        selectforeground=[("readonly", C["text"])],
    )

    return ttk.Combobox(
        parent,
        textvariable=textvariable,
        values=values,
        width=width,
        state="readonly",
        style="Dark.TCombobox",
        font=FONT_BODY,
    )



def styled_date_entry(parent, textvariable, width=12):
    """
    Φτιάχνει πεδίο ημερομηνίας με popup ημερολόγιο.

    Η μορφή που βλέπει ο χρήστης είναι DD-MM-YYYY,
    ίδια με τις υπόλοιπες ημερομηνίες της εφαρμογής.
    """

    return CalendarPopupEntry(
        parent,
        textvariable=textvariable,
        width=width,
        colors=C,
        font=FONT_BODY,
        date_pattern="dd-mm-yyyy",
        locale="el_GR",
    )


def card_frame(parent, **kw):
    """Φτιάχνει frame που μοιάζει με κάρτα."""

    return tk.Frame(
        parent,
        bg=C["card"],
        highlightthickness=1,
        highlightbackground=C["border"],
        **kw,
    )


def separator(parent):
    """Μικρή οριζόντια γραμμή διαχωρισμού."""

    return tk.Frame(parent, bg=C["border"], height=1)


def setup_treeview_style():
    """Ορίζει την εμφάνιση των πινάκων Treeview."""

    style = ttk.Style()

    # Εμφάνιση γραμμών του πίνακα.
    style.configure(
        "Dark.Treeview",
        background=C["card"],
        foreground=C["text"],
        rowheight=30,
        fieldbackground=C["card"],
        bordercolor=C["border"],
        font=FONT_BODY,
    )

    # Εμφάνιση κεφαλίδων του πίνακα.
    style.configure(
        "Dark.Treeview.Heading",
        background=C["panel"],
        foreground=C["text_sub"],
        font=FONT_SMALL,
        relief="flat",
    )

    # Χρώματα όταν επιλέγεται γραμμή.
    style.map(
        "Dark.Treeview",
        background=[("selected", C["select"])],
        foreground=[("selected", C["text"])],
    )


# ──────────────────────────────────────────────
#  ΚΕΝΤΡΙΚΟ ΠΑΡΑΘΥΡΟ ΕΦΑΡΜΟΓΗΣ
# ──────────────────────────────────────────────
class FinanceApp(tk.Tk):
    """Κεντρική κλάση της εφαρμογής Tkinter."""

    def __init__(self):
        # Καλούμε τον constructor της Tkinter.
        super().__init__()

        # Βασικά στοιχεία παραθύρου.
        # Ο τίτλος φαίνεται στη μπάρα του παραθύρου των Windows.
        self.title("Personal Finance Manager")
        self.geometry("1280x760")
        self.minsize(1100, 680)
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        # Εφαρμόζουμε το στυλ στους πίνακες.
        setup_treeview_style()

        # Φτιάχνουμε sidebar και κεντρικό χώρο.
        self._build_layout()

        # Με την εκκίνηση ανοίγουμε την οθόνη συναλλαγών.
        self._show_screen("transactions")

    def _close_calendar_popups(self):
        """
        Κλείνει τυχόν ανοιχτά calendar popups πριν αλλάξει η οθόνη.

        Το custom ημερολόγιο ανοίγει ως μικρό Toplevel παράθυρο.
        Αν ο χρήστης αλλάξει section ενώ είναι ανοιχτό, το κλείνουμε πρώτα,
        ώστε να μη μείνει focus/popup state που μπορεί να κάνει το GUI να φαίνεται παγωμένο.

        Δεν επηρεάζει βάση, συναλλαγές, κατηγορίες ή recurring logic.
        Είναι μόνο UI cleanup κατά την πλοήγηση.
        """

        # Πρώτα κλείνουμε το ενεργό calendar του app.py, αν υπάρχει.
        try:
            if CalendarPopupEntry._active_picker is not None:
                CalendarPopupEntry._active_picker._close_calendar()
        except Exception:
            pass

        # Έπειτα καθαρίζουμε όποιο Toplevel έχει δηλωθεί ως calendar popup.
        # Αυτό καλύπτει και popups από οθόνες που φορτώνονται/καταστρέφονται δυναμικά.
        for child in list(self.winfo_children()):
            try:
                if isinstance(child, tk.Toplevel) and getattr(child, "_is_calendar_popup", False):
                    child.destroy()
            except tk.TclError:
                pass

        try:
            self.focus_force()
            self.update_idletasks()
        except tk.TclError:
            pass

    def _build_layout(self):
        """Φτιάχνει το βασικό layout: αριστερό menu και κεντρικό panel."""

        # Αριστερό sidebar.
        self.sidebar = tk.Frame(self, bg=C["panel"], width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Τίτλος εφαρμογής στο αριστερό μενού.
        # Χρησιμοποιούμε ελληνικό τίτλο, γιατί η εφαρμογή και η εργασία είναι στα ελληνικά.
        # Το κείμενο χωρίζεται σε γραμμές για να χωράει σωστά στο sidebar.
        tk.Label(
            self.sidebar,
            text="Διαχείριση\nΠροσωπικών\nΟικονομικών",
            font=("Segoe UI", 13, "bold"),
            bg=C["panel"],
            fg=C["accent"],
            justify="center",
        ).pack(pady=(32, 8))

        # Μικρός υπότιτλος για να φαίνεται πιο ολοκληρωμένη η εφαρμογή.
        tk.Label(
            self.sidebar,
            text="Personal Finance Manager",
            font=("Segoe UI", 9),
            bg=C["panel"],
            fg=C["text_sub"],
            justify="center",
        ).pack(pady=(0, 24))

        separator(self.sidebar).pack(fill="x", padx=16)

        # Κρατάμε τα κουμπιά σε dictionary για να αλλάζουμε χρώμα στο ενεργό menu.
        self.nav_buttons = {}

        # Κάθε tuple έχει εσωτερικό κλειδί και κείμενο κουμπιού.
        nav_items = [
            ("transactions",    "Συναλλαγές"),
            ("add_transaction", "Νέα Συναλλαγή"),
            ("categories",      "Κατηγορίες"),
            ("recurring",       "Επαναλαμβανόμενα"),
            ("charts",          "Γραφήματα / Export"),
        ]

        # Δημιουργούμε τα κουμπιά πλοήγησης.
        for key, text in nav_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                command=lambda k=key: self._show_screen(k),
                bg=C["panel"],
                fg=C["text_sub"],
                font=FONT_BODY,
                relief="flat",
                anchor="w",
                padx=20,
                pady=10,
                cursor="hand2",
                activebackground=C["hover"],
                activeforeground=C["text"],
                bd=0,
                width=22,
            )
            btn.pack(fill="x", pady=1)
            self.nav_buttons[key] = btn

        

        # Κεντρικός χώρος όπου φορτώνονται οι οθόνες.
        self.main = tk.Frame(self, bg=C["bg"])
        self.main.pack(side="left", fill="both", expand=True)

    def _show_screen(self, name):
        """Καθαρίζει το main panel και φορτώνει την οθόνη που ζητήθηκε."""

        # Πριν αλλάξουμε οθόνη, κλείνουμε τυχόν ανοιχτό calendar popup.
        # Αυτό αποφεύγει μικρά focus freezes όταν ο χρήστης πάει από φίλτρα σε άλλη ενότητα.
        self._close_calendar_popups()

        # Χρωματίζουμε το ενεργό κουμπί του sidebar.
        for key, btn in self.nav_buttons.items():
            btn.config(
                bg=C["card"] if key == name else C["panel"],
                fg=C["accent"] if key == name else C["text_sub"],
            )

        # Αφαιρούμε ό,τι υπάρχει ήδη στο κεντρικό panel.
        for widget in self.main.winfo_children():
            widget.destroy()

        # Αντιστοίχιση ονόματος οθόνης με κλάση οθόνης.
        screens = {
            "transactions": TransactionsScreen,
            "add_transaction": TransactionFormScreen,
            "categories": CategoriesScreen,
            "recurring": RecurringScreen,
            "charts": lambda parent, app: ChartsExportScreen(
                parent,
                C,
                {
                    "title": FONT_TITLE,
                    "head": FONT_HEAD,
                    "body": FONT_BODY,
                    "small": FONT_SMALL,
                },
            ),
        }

        # Αν υπάρχει η οθόνη, τη δημιουργούμε και τη βάζουμε στο main panel.
        if name in screens:
            screens[name](self.main, app=self).pack(fill="both", expand=True)

    def go_to(self, screen, **kwargs):
        """Μικρή function πλοήγησης όταν θέλουμε να πάμε σε ειδική οθόνη, π.χ. edit."""

        # Κλείνουμε τυχόν ανοιχτό calendar popup πριν την ειδική πλοήγηση.
        self._close_calendar_popups()

        # Καθαρίζουμε το main panel.
        for widget in self.main.winfo_children():
            widget.destroy()

        # Ξε-επιλέγουμε τα κουμπιά του sidebar.
        for btn in self.nav_buttons.values():
            btn.config(bg=C["panel"], fg=C["text_sub"])

        # Η επεξεργασία συναλλαγής χρησιμοποιεί την ίδια φόρμα με τη νέα συναλλαγή.
        if screen == "edit_transaction":
            TransactionFormScreen(self.main, app=self, **kwargs).pack(fill="both", expand=True)
        else:
            self._show_screen(screen)


# ──────────────────────────────────────────────
#  ΟΘΟΝΗ ΣΥΝΑΛΛΑΓΩΝ
# ──────────────────────────────────────────────
class TransactionsScreen(tk.Frame):
    """Εμφανίζει συναλλαγές και δίνει επιλογές φιλτραρίσματος, edit και delete."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])

        # Κρατάμε reference στο κεντρικό app για να μπορούμε να αλλάζουμε οθόνες.
        self.app = app

        # Εδώ κρατάμε το TranID της γραμμής που επέλεξε ο χρήστης.
        self.sel_id = None

        # Μεταβλητές Tkinter που συνδέονται με τα νέα φίλτρα της οθόνης.
        # Τα φίλτρα Από / Έως ξεκινούν κενά, ώστε αρχικά να εμφανίζονται όλες οι συναλλαγές.
        self.var_date_from = tk.StringVar(value="")
        self.var_date_to = tk.StringVar(value="")
        self.var_cat = tk.StringVar(value="Όλες")

        # Διαβάζουμε τις κατηγορίες απευθείας από το database layer.
        self.cats = select_categories()

        # Δημιουργούμε τα widgets της οθόνης.
        # Μετά φορτώνουμε τα δεδομένα από τη βάση.
        self._build()
        self._load()

    def _build(self):
        """Στήνει οπτικά την οθόνη συναλλαγών."""

        # Header οθόνης.
        hdr = tk.Frame(self, bg=C["bg"], pady=16, padx=24)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="Συναλλαγές",
            font=FONT_TITLE,
            bg=C["bg"],
            fg=C["text"],
        ).pack(side="left")

        # Μπάρα φίλτρων.
        fbar = card_frame(self)
        fbar.pack(fill="x", padx=24, pady=(0, 10))

        inner = tk.Frame(fbar, bg=C["card"], pady=10, padx=16)
        inner.pack(fill="x")

        # Φίλτρο ημερομηνίας Από.
        tk.Label(
            inner,
            text="Από:",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text"],
        ).pack(side="left")

        self.date_from_entry = styled_date_entry(inner, self.var_date_from, width=12)
        self.date_from_entry.pack(side="left", padx=(4, 14))

        # Το custom calendar field μπορεί να δεχθεί κενή τιμή.
        # Το καθαρίζουμε ώστε αρχικά να μην εφαρμόζεται φίλτρο.
        self.date_from_entry.delete(0, "end")

        # Φίλτρο ημερομηνίας Έως.
        tk.Label(
            inner,
            text="Έως:",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text"],
        ).pack(side="left")

        self.date_to_entry = styled_date_entry(inner, self.var_date_to, width=12)
        self.date_to_entry.pack(side="left", padx=(4, 14))

        # Αρχικά και το Έως μένει κενό.
        self.date_to_entry.delete(0, "end")

        # Φίλτρο κατηγορίας.
        tk.Label(
            inner,
            text="Κατηγορία:",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text"],
        ).pack(side="left")

        # Η επιλογή "Όλες" σημαίνει ότι δεν εφαρμόζεται φίλτρο κατηγορίας.
        cat_names = ["Όλες"] + [c["Category"] for c in self.cats]
        cat_cb = styled_combo(inner, self.var_cat, cat_names, width=16)
        cat_cb.pack(side="left", padx=(4, 14))

        # Τα φίλτρα εφαρμόζονται μόνο όταν ο χρήστης πατήσει "Εύρεση".
        styled_button(inner, "Εύρεση", self._load, width=10).pack(side="left", padx=4)

        # Με τον καθαρισμό επιστρέφουμε στην αρχική προβολή όλων των συναλλαγών.
        styled_button(
            inner,
            "Καθαρισμός",
            self._clear_filters,
            C["text_sub"],
            width=12,
        ).pack(side="left", padx=4)

        # Κάρτες συνόλων.
        totals_frame = tk.Frame(self, bg=C["bg"], padx=24)
        totals_frame.pack(fill="x", pady=(0, 8))

        self.lbl_income = self._total_card(totals_frame, "Έσοδα", "0.00 €", C["success"])
        self.lbl_expense = self._total_card(totals_frame, "Έξοδα", "0.00 €", C["danger"])
        self.lbl_balance = self._total_card(totals_frame, "Ισοζύγιο", "0.00 €", C["accent"])

        # Πίνακας συναλλαγών.
        tbl = card_frame(self)
        tbl.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        cols = ("id", "Ημερομηνία", "Κατηγορία", "Τύπος", "Ποσό", "Περιγραφή")
        self.tree = ttk.Treeview(
            tbl,
            columns=cols,
            show="headings",
            style="Dark.Treeview",
            selectmode="browse",
        )

        # Πλάτη στηλών.
        widths = {
            "id": 0,
            "Ημερομηνία": 100,
            "Κατηγορία": 140,
            "Τύπος": 80,
            "Ποσό": 90,
            "Περιγραφή": 280,
        }

        # Ρυθμίζουμε τις κεφαλίδες και τις στήλες.
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                width=widths[col],
                anchor="center" if col in ("id", "Τύπος", "Ποσό") else "w",
                stretch=col != "id",
            )

        # Το ID το κρατάμε κρυφό, αλλά υπάρχει για edit/delete.
        self.tree.column("id", stretch=False)

        # Scrollbar για τον πίνακα.
        vsb = ttk.Scrollbar(tbl, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Όταν ο χρήστης επιλέγει γραμμή, κρατάμε το TranID.
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Κουμπιά επεξεργασίας / διαγραφής.
        btn_bar = tk.Frame(self, bg=C["bg"], padx=24, pady=8)
        btn_bar.pack(fill="x")

        styled_button(
            btn_bar,
            "Επεξεργασία",
            self._edit,
            C["accent2"],
            width=16,
        ).pack(side="left", padx=4)

        styled_button(
            btn_bar,
            "Διαγραφή",
            self._delete,
            C["danger"],
            width=14,
        ).pack(side="left", padx=4)

    def _total_card(self, parent, lbl, val, color):
        """Δημιουργεί μικρή κάρτα συνόλου, π.χ. Έσοδα / Έξοδα / Ισοζύγιο."""

        frame = card_frame(parent)
        frame.pack(side="left", padx=(0, 10), pady=4, ipadx=16, ipady=8)

        tk.Label(
            frame,
            text=lbl,
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text_sub"],
        ).pack()

        value_label = tk.Label(
            frame,
            text=val,
            font=("Segoe UI", 14, "bold"),
            bg=C["card"],
            fg=color,
        )
        value_label.pack()

        return value_label

    def _clear_filters(self):
        """Καθαρίζει όλα τα φίλτρα και εμφανίζει ξανά όλες τις συναλλαγές."""

        # Καθαρίζουμε τα πεδία ημερομηνίας Από / Έως.
        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")

        # Επαναφέρουμε την κατηγορία στο "Όλες".
        self.var_cat.set("Όλες")

        # Ξαναφορτώνουμε τη λίστα χωρίς φίλτρα.
        self._load()

    def _get_filter_values(self):
        """
        Διαβάζει και ελέγχει τα φίλτρα της οθόνης.

        Επιστρέφει:
        - date_from σε μορφή YYYY-MM-DD ή None
        - date_to σε μορφή YYYY-MM-DD ή None
        - cat_id ή None

        Το GUI δείχνει ημερομηνίες ως DD-MM-YYYY,
        αλλά η βάση κρατά YYYY-MM-DD για σωστή σύγκριση.
        """

        date_from_text = self.var_date_from.get().strip()
        date_to_text = self.var_date_to.get().strip()
        cat_name = self.var_cat.get().strip()

        date_from = None
        date_to = None
        cat_id = None

        # Αν ο χρήστης έβαλε ημερομηνία Από,
        # τη μετατρέπουμε από DD-MM-YYYY σε YYYY-MM-DD για τη βάση.
        if date_from_text:
            try:
                date_from = date_to_database(date_from_text)
            except ValueError as error:
                messagebox.showwarning("Φίλτρα", str(error))
                return None

        # Αν ο χρήστης έβαλε ημερομηνία Έως,
        # τη μετατρέπουμε και αυτή από DD-MM-YYYY σε YYYY-MM-DD.
        if date_to_text:
            try:
                date_to = date_to_database(date_to_text)
            except ValueError as error:
                messagebox.showwarning("Φίλτρα", str(error))
                return None

        # Αν έχουν συμπληρωθεί και οι δύο ημερομηνίες,
        # ελέγχουμε ότι το Από δεν είναι μετά το Έως.
        if date_from and date_to and date_from > date_to:
            messagebox.showwarning(
                "Φίλτρα",
                "Η ημερομηνία Από δεν μπορεί να είναι μετά την ημερομηνία Έως.",
            )
            return None

        # Αν έχει επιλεγεί κατηγορία, βρίσκουμε το CategoryID της.
        if cat_name and cat_name != "Όλες":
            found = [c for c in self.cats if c["Category"] == cat_name]

            if found:
                cat_id = found[0]["CategoryID"]
            else:
                messagebox.showwarning("Φίλτρα", "Μη έγκυρη κατηγορία.")
                return None

        return date_from, date_to, cat_id

    def _load(self):
        """Φορτώνει συναλλαγές και σύνολα από τη βάση σύμφωνα με τα ενεργά φίλτρα."""

        # Κάθε φορά που ξαναφορτώνουμε, μηδενίζουμε την επιλογή.
        self.sel_id = None

        # Καθαρίζουμε τις παλιές γραμμές του πίνακα.
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)

        # Παίρνουμε τα φίλτρα από ξεχωριστή helper function
        # ώστε η _load να μείνει καθαρή και ευανάγνωστη.
        filter_values = self._get_filter_values()

        # Αν τα φίλτρα έχουν λάθος τιμή, η helper έχει ήδη εμφανίσει μήνυμα.
        if filter_values is None:
            return

        date_from, date_to, cat_id = filter_values

        # Διαβάζουμε συναλλαγές από το database.py με τα νέα φίλτρα ημερομηνιών.
        # Τα month/year δεν τα χρησιμοποιούμε εδώ πλέον.
        transactions = select_transactions(
            category_id=cat_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Τα σύνολα υπολογίζονται από τις συναλλαγές που εμφανίζονται στον πίνακα,
        # ώστε οι κάρτες να συμφωνούν πάντα με τα ενεργά φίλτρα.
        income = 0.0
        expense = 0.0

        for tran in transactions:
            is_income = tran["CategoryType"] == "income"
            amount = float(tran["TranAmount"])

            if is_income:
                income += amount
                amount_text = f"+{amount:.2f} €"
            else:
                expense += amount
                amount_text = f"-{amount:.2f} €"

            self.tree.insert(
                "",
                "end",
                values=(
                    tran["TranID"],
                    date_to_greek(tran["TranRegDate"]),
                    tran["Category"],
                    "Έσοδο" if is_income else "Έξοδο",
                    amount_text,
                    description_to_display(tran["TranDescr"]),
                ),
                tags=("income" if is_income else "expense",),
            )

        # Χρωματίζουμε διαφορετικά έσοδα και έξοδα.
        self.tree.tag_configure("income", foreground=C["success"])
        self.tree.tag_configure("expense", foreground=C["danger"])

        # Υπολογισμός ισοζυγίου με βάση τις εμφανιζόμενες συναλλαγές.
        balance = income - expense

        # Ενημερώνουμε τις κάρτες συνόλων.
        self.lbl_income.config(text=f"+{income:.2f} €")
        self.lbl_expense.config(text=f"{expense:.2f} €")
        self.lbl_balance.config(
            text=f"{balance:+.2f} €",
            fg=C["success"] if balance >= 0 else C["danger"],
        )

    def _on_select(self, _event):
        """Κρατάει το ID της συναλλαγής που επέλεξε ο χρήστης."""

        selected = self.tree.selection()

        if selected:
            values = self.tree.item(selected[0], "values")
            self.sel_id = int(values[0])

    def _edit(self):
        """Ανοίγει τη φόρμα επεξεργασίας για την επιλεγμένη συναλλαγή."""

        if not self.sel_id:
            messagebox.showwarning("Επιλογή", "Επιλέξτε πρώτα μια συναλλαγή.")
            return

        self.app.go_to("edit_transaction", tx_id=self.sel_id)

    def _delete(self):
        """Διαγράφει την επιλεγμένη συναλλαγή μετά από επιβεβαίωση."""

        if not self.sel_id:
            messagebox.showwarning("Επιλογή", "Επιλέξτε πρώτα μια συναλλαγή.")
            return

        if messagebox.askyesno("Διαγραφή", "Να διαγραφεί η συναλλαγή;"):
            delete_transaction(self.sel_id)
            self._load()


# ──────────────────────────────────────────────
#  ΦΟΡΜΑ ΝΕΑΣ / ΕΠΕΞΕΡΓΑΣΙΑΣ ΣΥΝΑΛΛΑΓΗΣ
# ──────────────────────────────────────────────
class TransactionFormScreen(tk.Frame):
    """Φόρμα που χρησιμοποιείται και για νέα συναλλαγή και για επεξεργασία."""

    def __init__(self, parent, app, tx_id=None):
        super().__init__(parent, bg=C["bg"])

        # Reference στο κεντρικό app.
        self.app = app

        # Αν υπάρχει tx_id, τότε είμαστε σε edit mode.
        # Αν δεν υπάρχει, τότε είμαστε σε νέα συναλλαγή.
        self.tx_id = tx_id

        # Φορτώνουμε κατηγορίες από τη βάση.
        self.cats = select_categories()

        # Tkinter variables της φόρμας.
        self.var_amount = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_type = tk.StringVar(value="expense")
        self.var_date = tk.StringVar(value=date.today().strftime("%d-%m-%Y"))
        self.var_desc = tk.StringVar()

        # Κρατάμε κρυφά το recurring marker της συναλλαγής, αν υπάρχει.
        # Έτσι δεν εμφανίζεται στη φόρμα, αλλά δεν χάνεται από τη βάση όταν γίνει αποθήκευση.
        self._hidden_auto_rec_marker = ""


        # Στήνουμε φόρμα.
        self._build()

        # Αν είναι edit, γεμίζουμε τη φόρμα με υπάρχοντα στοιχεία.
        if tx_id:
            self._fill(tx_id)
        else:
            # Αν είναι νέα εγγραφή, βάζουμε default πρώτη διαθέσιμη κατηγορία.
            self._update_cats()

    def _build(self):
        """Στήνει οπτικά τη φόρμα συναλλαγής."""

        title = "Επεξεργασία Συναλλαγής" if self.tx_id else "Νέα Συναλλαγή"

        hdr = tk.Frame(self, bg=C["bg"], pady=16, padx=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, font=FONT_TITLE,
                 bg=C["bg"], fg=C["text"]).pack(side="left")

        form = card_frame(self)
        form.pack(padx=60, pady=10, fill="x")
        inner = tk.Frame(form, bg=C["card"], padx=32, pady=28)
        inner.pack(fill="x")

        def row(lbl_text, widget_factory, row_number):
            """Τοπική helper function για να μη γράφουμε συνέχεια grid κώδικα."""

            tk.Label(
                inner,
                text=lbl_text,
                font=FONT_BODY,
                bg=C["card"],
                fg=C["text_sub"],
                anchor="e",
                width=28,
            ).grid(row=row_number, column=0, pady=10, padx=(0, 14))

            widget = widget_factory()
            widget.grid(row=row_number, column=1, pady=10, sticky="w")
            return widget

        def type_widget():
            """Radio buttons για επιλογή εσόδου ή εξόδου."""

            frame = tk.Frame(inner, bg=C["card"])
            for value, text, color in [
                ("income", "Έσοδο", C["success"]),
                ("expense", "Έξοδο", C["danger"]),
            ]:
                tk.Radiobutton(
                    frame,
                    text=text,
                    variable=self.var_type,
                    value=value,
                    bg=C["card"],
                    fg=color,
                    selectcolor=C["entry_bg"],
                    activebackground=C["card"],
                    font=FONT_BODY,
                    cursor="hand2",
                    command=self._update_cats,
                ).pack(side="left", padx=8)
            return frame

        row("Τύπος κίνησης:", type_widget, 0)

        def cat_widget():
            """Combobox κατηγοριών, με βάση τον τύπο κίνησης."""

            self.cat_cb = styled_combo(inner, self.var_cat, self._cat_names(), width=24)
            return self.cat_cb

        row("Κατηγορία:", cat_widget, 1)
        row("Ποσό (€):", lambda: styled_entry(inner, self.var_amount, width=16), 2)
        row("Ημερομηνία (DD-MM-YYYY):", lambda: styled_entry(inner, self.var_date, width=16), 3)
        row("Περιγραφή:", lambda: styled_entry(inner, self.var_desc, width=36), 4)

        # Κουμπιά φόρμας.
        btn_frame = tk.Frame(inner, bg=C["card"])
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        styled_button(btn_frame, "Αποθήκευση", self._save,
                      C["success"], width=16).pack(side="left", padx=8)
        styled_button(btn_frame, "Άκυρο",
                      lambda: self.app._show_screen("transactions"),
                      C["text_sub"], width=12).pack(side="left", padx=8)

    def _cat_names(self):
        """Επιστρέφει μόνο τις κατηγορίες που ταιριάζουν στον τύπο income/expense."""

        return [
            cat["Category"]
            for cat in self.cats
            if cat["CategoryType"] == self.var_type.get()
        ]

    def _update_cats(self):
        """Ανανεώνει το combobox κατηγοριών όταν αλλάζει ο τύπος συναλλαγής."""

        names = self._cat_names()
        self.cat_cb["values"] = names
        self.var_cat.set(names[0] if names else "")

    def _fill(self, tx_id):
        """Φορτώνει μία υπάρχουσα συναλλαγή στη φόρμα για επεξεργασία."""

        # Διαβάζουμε τη συναλλαγή από το database.py.
        tx = select_transaction_by_id(tx_id)
        if not tx:
            return

        # Πρώτα βάζουμε τύπο, ώστε να φορτώσουν σωστές κατηγορίες.
        self.var_type.set(tx["CategoryType"])
        self._update_cats()

        # Μετά γεμίζουμε τα πεδία.
        self.var_cat.set(tx["Category"])
        self.var_amount.set(amount_to_entry(tx["TranAmount"]))
        self.var_date.set(date_to_greek(tx["TranRegDate"]))
        
        # Αν η συναλλαγή έχει δημιουργηθεί από recurring εγγραφή,
        # η περιγραφή περιέχει marker τύπου [AUTO-REC:4].
        # Το κρύβουμε από τον χρήστη, αλλά το κρατάμε εσωτερικά για να μη χαθεί στο save.
        self._hidden_auto_rec_marker = extract_auto_rec_marker(tx["TranDescr"])
        self.var_desc.set(description_to_display(tx["TranDescr"]))



    def _save(self):
        """Ελέγχει τα στοιχεία και κάνει insert ή update συναλλαγής."""

        # Παίρνουμε τιμές από τη φόρμα.
        cat_name = self.var_cat.get().strip()
        amount_text = self.var_amount.get().strip()
        date_text = self.var_date.get().strip()
        desc = self.var_desc.get().strip()
        
        # Αν επεξεργαζόμαστε αυτόματη συναλλαγή από recurring,
        # ξανακολλάμε το κρυφό marker στην περιγραφή πριν την αποθήκευση.
        # Έτσι ο χρήστης δεν το βλέπει, αλλά η εφαρμογή συνεχίζει να το χρησιμοποιεί
        # για αποφυγή διπλών recurring συναλλαγών.
        if self._hidden_auto_rec_marker and self._hidden_auto_rec_marker not in desc:
            desc = f"{desc} {self._hidden_auto_rec_marker}".strip()

        # Βασικός έλεγχος υποχρεωτικών πεδίων.
        if not cat_name or not amount_text or not date_text:
            messagebox.showerror("Σφάλμα", "Συμπληρώστε όλα τα υποχρεωτικά πεδία.")
            return

        # Έλεγχος ποσού.
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Σφάλμα", "Εισάγετε έγκυρο θετικό ποσό.")
            return

        # Έλεγχος ημερομηνίας.
        # Ο χρήστης γράφει DD-MM-YYYY, αλλά στη βάση αποθηκεύουμε YYYY-MM-DD.
        try:
            db_date = date_to_database(date_text)
        except ValueError as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        # Βρίσκουμε το αντικείμενο κατηγορίας από το όνομα που επέλεξε ο χρήστης.
        cat_obj = next((c for c in self.cats if c["Category"] == cat_name), None)
        if not cat_obj:
            messagebox.showerror("Σφάλμα", "Μη έγκυρη κατηγορία.")
            return

        # Αν υπάρχει tx_id, η φόρμα βρίσκεται σε λειτουργία επεξεργασίας.
        # Αν δεν υπάρχει tx_id, η φόρμα δημιουργεί νέα συναλλαγή.
        if self.tx_id:
            update_transaction(self.tx_id, cat_obj["CategoryID"], amount, db_date, desc)
            messagebox.showinfo("Επιτυχία", "Η συναλλαγή ενημερώθηκε!")
        else:
            insert_transaction(cat_obj["CategoryID"], amount, db_date, desc)
            messagebox.showinfo("Επιτυχία", "Η συναλλαγή καταχωρήθηκε!")

        # Επιστροφή στη λίστα συναλλαγών.
        self.app._show_screen("transactions")


# ──────────────────────────────────────────────
#  ΟΘΟΝΗ ΚΑΤΗΓΟΡΙΩΝ
# ──────────────────────────────────────────────
class CategoriesScreen(tk.Frame):
    """Οθόνη διαχείρισης κατηγοριών εσόδων και εξόδων."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])

        self.app = app

        # Μεταβλητές φόρμας.
        self.var_name = tk.StringVar()
        self.var_descr = tk.StringVar()
        self.var_type = tk.StringVar(value="expense")

        # CategoryID επιλεγμένης κατηγορίας.
        self.sel_id = None

        self._build()
        self._load()

    def _build(self):
        """Στήνει την οθόνη κατηγοριών."""

        hdr = tk.Frame(self, bg=C["bg"], pady=16, padx=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Κατηγορίες", font=FONT_TITLE,
                 bg=C["bg"], fg=C["text"]).pack(side="left")

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill="both", expand=True, padx=24)

        # Αριστερή φόρμα.
        form_frame = card_frame(content)
        form_frame.pack(side="left", fill="y", padx=(0, 12), pady=4, ipadx=8)
        form_inner = tk.Frame(form_frame, bg=C["card"], padx=20, pady=20)
        form_inner.pack(fill="both", expand=True)

        tk.Label(form_inner, text="Στοιχεία Κατηγορίας", font=FONT_HEAD,
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 14))

        tk.Label(form_inner, text="Όνομα:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        styled_entry(form_inner, self.var_name, width=22).pack(anchor="w", pady=(4, 10))

        tk.Label(form_inner, text="Περιγραφή:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        styled_entry(form_inner, self.var_descr, width=22).pack(anchor="w", pady=(4, 10))

        tk.Label(form_inner, text="Τύπος:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        rb_frame = tk.Frame(form_inner, bg=C["card"])
        rb_frame.pack(anchor="w", pady=(4, 18))

        # Radio buttons για income / expense.
        for value, text, color in [
            ("income", "Έσοδο", C["success"]),
            ("expense", "Έξοδο", C["danger"]),
        ]:
            tk.Radiobutton(
                rb_frame,
                text=text,
                variable=self.var_type,
                value=value,
                bg=C["card"],
                fg=color,
                selectcolor=C["entry_bg"],
                activebackground=C["card"],
                font=FONT_BODY,
                cursor="hand2",
            ).pack(side="left", padx=(0, 10))

        # Κουμπιά CRUD.
        styled_button(form_inner, "Προσθήκη", self._add,
                      C["accent"], width=18).pack(fill="x")
        styled_button(form_inner, "Αποθήκευση αλλαγών", self._update,
                      C["success"], width=18).pack(fill="x", pady=(6, 0))
        tk.Frame(form_inner, bg=C["border"], height=1).pack(fill="x", pady=14)
        styled_button(form_inner, "Διαγραφή", self._delete,
                      C["danger"], width=18).pack(fill="x")
        styled_button(form_inner, "Καθαρισμός", self._clear_form,
                      C["text_sub"], width=18).pack(fill="x", pady=(6, 0))

        # Label για μηνύματα επιτυχίας/λάθους.
        self.lbl_status = tk.Label(form_inner, text="", font=FONT_SMALL,
                                   bg=C["card"], fg=C["success"], wraplength=190)
        self.lbl_status.pack(pady=(12, 0))

        # Δεξιά λίστα κατηγοριών.
        list_frame = card_frame(content)
        list_frame.pack(side="left", fill="both", expand=True, pady=4)
        list_inner = tk.Frame(list_frame, bg=C["card"], padx=16, pady=16)
        list_inner.pack(fill="both", expand=True)

        tk.Label(list_inner, text="Υπάρχουσες Κατηγορίες", font=FONT_HEAD,
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))

        cols = ("id", "Κατηγορία", "Περιγραφή", "Τύπος")
        self.tree = ttk.Treeview(list_inner, columns=cols, show="headings",
                                 style="Dark.Treeview", selectmode="browse", height=18)

        # Κρύβουμε το id από τον χρήστη, αλλά το κρατάμε για update/delete.
        self.tree.column("id", width=0, stretch=False)

        for col, width in [("Κατηγορία", 150), ("Περιγραφή", 200), ("Τύπος", 80)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="w" if col != "Τύπος" else "center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _load(self):
        """Φορτώνει όλες τις κατηγορίες από τη βάση στον πίνακα."""

        # Καθαρίζουμε τον πίνακα.
        for row_id in self.tree.get_children():
            self.tree.delete(row_id)

        # Διαβάζουμε απευθείας από το database layer.
        for cat in select_categories():
            tag = cat["CategoryType"]
            self.tree.insert(
                "",
                "end",
                values=(
                    cat["CategoryID"],
                    cat["Category"],
                    cat["CategoryDescr"] or "",
                    "Έσοδο" if tag == "income" else "Έξοδο",
                ),
                tags=(tag,),
            )

        self.tree.tag_configure("income", foreground=C["success"])
        self.tree.tag_configure("expense", foreground=C["danger"])

    def _on_select(self, _event):
        """Όταν επιλέγεται κατηγορία, γεμίζουμε τη φόρμα για πιθανή αλλαγή."""

        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0], "values")
            self.sel_id = int(values[0])
            self.var_name.set(values[1])
            self.var_descr.set(values[2])
            self.var_type.set("income" if values[3] == "Έσοδο" else "expense")

    def _add(self):
        """Προσθέτει νέα κατηγορία στη βάση."""

        try:
            # validate_category_name καθαρίζει/ελέγχει το όνομα.
            name = validate_category_name(self.var_name.get())
            description = self.var_descr.get().strip()
            category_type = self.var_type.get()

            # Κλήση απευθείας στο database.py.
            insert_category(name, description, category_type)

            # Καθαρίζουμε και ανανεώνουμε.
            self._clear_form()
            self._load()
            self._status(f"Η κατηγορία '{name}' προστέθηκε.", C["success"])

        except sqlite3.IntegrityError:
            # Πιθανό duplicate όνομα κατηγορίας.
            self._status("Η κατηγορία υπάρχει ήδη.", C["danger"])
        except Exception as error:
            self._status(str(error), C["danger"])

    def _update(self):
        """Ενημερώνει την επιλεγμένη κατηγορία."""

        if not self.sel_id:
            self._status("Επιλέξτε πρώτα κατηγορία για αλλαγή.", C["warning"])
            return

        try:
            name = validate_category_name(self.var_name.get())
            description = self.var_descr.get().strip()
            category_type = self.var_type.get()

            # Κλήση απευθείας στο database.py.
            update_category(self.sel_id, name, description, category_type)

            self._load()
            self._status("Η κατηγορία ενημερώθηκε.", C["success"])

        except Exception as error:
            self._status(str(error), C["danger"])

    def _clear_form(self):
        """Καθαρίζει τη φόρμα κατηγορίας."""

        self.sel_id = None
        self.var_name.set("")
        self.var_descr.set("")
        self.var_type.set("expense")

    def _delete(self):
        """Διαγράφει την επιλεγμένη κατηγορία μετά από επιβεβαίωση."""

        if not self.sel_id:
            self._status("Επιλέξτε κατηγορία.", C["warning"])
            return

        if messagebox.askyesno("Διαγραφή", "Να διαγραφεί η κατηγορία;"):
            try:
                # Αν η κατηγορία χρησιμοποιείται ήδη από συναλλαγές,
                # η βάση δεν θα επιτρέψει τη διαγραφή λόγω foreign key.
                delete_category(self.sel_id)
                self._clear_form()
                self._load()
                self._status("Η κατηγορία διαγράφηκε.", C["success"])
            except sqlite3.IntegrityError:
                    # Η SQLite δεν επιτρέπει τη διαγραφή γιατί η κατηγορία χρησιμοποιείται ήδη.
                    # Αυτό είναι σωστή λειτουργία λόγω FOREIGN KEY / ON DELETE RESTRICT.
                self._status(
                    "Η κατηγορία δεν μπορεί να διαγραφεί γιατί χρησιμοποιείται ήδη "
                    "σε συναλλαγές ή επαναλαμβανόμενες εγγραφές.",
                    C["warning"],
                )

            except Exception as error:
                # Γενικό fallback για οποιοδήποτε άλλο απρόβλεπτο σφάλμα.
                self._status(f"Σφάλμα: {error}", C["danger"])


    def _status(self, msg, color):
        """Εμφανίζει προσωρινό μήνυμα στην οθόνη κατηγοριών."""

        self.lbl_status.config(text=msg, fg=color)
        self.after(3000, lambda: self.lbl_status.config(text=""))


# ──────────────────────────────────────────────
#  ΟΘΟΝΗ RECURRING / ΜΗΝΙΑΙΩΝ ΕΓΓΡΑΦΩΝ
# ──────────────────────────────────────────────
class RecurringScreen(tk.Frame):
    """Οθόνη για επαναλαμβανόμενες μηνιαίες εγγραφές."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=C["bg"])

        self.app = app

        # Διαβάζουμε κατηγορίες για τα combobox.
        self.cats = select_categories()

        # sel_id: τι έχει επιλεγεί στον πίνακα.
        # _edit_id: αν έχει τιμή, τότε η αποθήκευση κάνει update αντί για insert.
        self.sel_id = None
        self._edit_id = None

        # Μεταβλητές φόρμας.
        self.var_cat = tk.StringVar()
        self.var_type = tk.StringVar(value="expense")
        self.var_amount = tk.StringVar()
        self.var_date = tk.StringVar(value=date.today().strftime("%d-%m-%Y"))
        self.var_desc = tk.StringVar()
        self.var_active = tk.IntVar(value=1)

        # Μεταβλητές για τη δημιουργία συναλλαγών σε διάστημα μηνών.
        # Δεν αλλάζουν τη recurring εγγραφή στη βάση.
        # Χρησιμοποιούνται μόνο όταν πατηθεί το κουμπί δημιουργίας.
        today = date.today()
        self.var_gen_from_month = tk.StringVar(value=str(today.month))
        self.var_gen_from_year = tk.StringVar(value=str(today.year))
        self.var_gen_to_month = tk.StringVar(value=str(today.month))
        self.var_gen_to_year = tk.StringVar(value=str(today.year))

        self._build()
        self._update_cats()
        self._load()

    def _build(self):
        """Στήνει την οθόνη recurring."""

        hdr = tk.Frame(self, bg=C["bg"], pady=16, padx=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Επαναλαμβανόμενες Συναλλαγές", font=FONT_TITLE,
                 bg=C["bg"], fg=C["text"]).pack(side="left")

        content = tk.Frame(self, bg=C["bg"])
        content.pack(fill="both", expand=True, padx=24)

        # Αριστερή φόρμα.
        form_frame = card_frame(content)
        form_frame.pack(side="left", fill="y", padx=(0, 12), pady=4, ipadx=8)
        form_inner = tk.Frame(form_frame, bg=C["card"], padx=20, pady=20)
        form_inner.pack(fill="both", expand=True)

        self.form_title = tk.Label(form_inner, text="Νέα Εγγραφή", font=FONT_HEAD,
                                   bg=C["card"], fg=C["text"])
        self.form_title.pack(anchor="w", pady=(0, 14))

        tk.Label(form_inner, text="Τύπος:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        rb_frame = tk.Frame(form_inner, bg=C["card"])
        rb_frame.pack(anchor="w", pady=(2, 10))

        for value, text, color in [
            ("income", "Έσοδο", C["success"]),
            ("expense", "Έξοδο", C["danger"]),
        ]:
            tk.Radiobutton(
                rb_frame,
                text=text,
                variable=self.var_type,
                value=value,
                bg=C["card"],
                fg=color,
                selectcolor=C["entry_bg"],
                activebackground=C["card"],
                font=FONT_BODY,
                cursor="hand2",
                command=self._update_cats,
            ).pack(side="left", padx=(0, 8))

        tk.Label(form_inner, text="Κατηγορία:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        self.cat_cb = styled_combo(form_inner, self.var_cat, self._cat_names(), width=22)
        self.cat_cb.pack(anchor="w", pady=(2, 10))

        tk.Label(form_inner, text="Ποσό (€):", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        styled_entry(form_inner, self.var_amount, width=14).pack(anchor="w", pady=(2, 10))

        tk.Label(form_inner, text="Ημ/νία Έναρξης (DD-MM-YYYY):", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        styled_entry(form_inner, self.var_date, width=16).pack(anchor="w", pady=(2, 10))

        tk.Label(form_inner, text="Περιγραφή:", font=FONT_SMALL,
                 bg=C["card"], fg=C["text_sub"]).pack(anchor="w")
        styled_entry(form_inner, self.var_desc, width=24).pack(anchor="w", pady=(2, 10))

        # Το RecTranActive αποθηκεύεται στη βάση ως 1/0.
        tk.Checkbutton(
            form_inner,
            text="Ενεργό",
            variable=self.var_active,
            bg=C["card"],
            fg=C["text"],
            selectcolor=C["entry_bg"],
            activebackground=C["card"],
            font=FONT_BODY,
            cursor="hand2",
        ).pack(anchor="w", pady=(0, 14))

        styled_button(form_inner, "Αποθήκευση", self._save,
                      C["success"], width=20).pack(fill="x")
        tk.Frame(form_inner, bg=C["border"], height=1).pack(fill="x", pady=8)
        styled_button(form_inner, "Διαγραφή", self._delete,
                      C["danger"], width=20).pack(fill="x")
        styled_button(form_inner, "Καθαρισμός", self._reset,
                      C["text_sub"], width=20).pack(fill="x", pady=(6, 0))

        # Περιοχή δημιουργίας συναλλαγών από recurring εγγραφές.
        # Δεν αλλάζει η λογική των recurring συναλλαγών.
        # Απλώς δίνουμε στον χρήστη τη δυνατότητα να επιλέξει διάστημα μηνών.
        # Η υπάρχουσα generate_monthly_transactions() καλείται μία φορά για κάθε μήνα.
        tk.Label(
            form_inner,
            text=(
                "Δημιουργεί κανονικές συναλλαγές από τις ενεργές "
                "επαναλαμβανόμενες εγγραφές.\n"
                "Δεν δημιουργεί διπλές εγγραφές για τον ίδιο μήνα."
            ),
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text_sub"],
            wraplength=220,
            justify="left",
        ).pack(anchor="w", pady=(8, 4))

        tk.Label(
            form_inner,
            text="Δημιουργία από (ΜΜ / ΕΕΕΕ):",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text_sub"],
        ).pack(anchor="w")

        gen_from_frame = tk.Frame(form_inner, bg=C["card"])
        gen_from_frame.pack(anchor="w", pady=(2, 6))

        styled_entry(gen_from_frame, self.var_gen_from_month, width=5).pack(side="left")
        tk.Label(
            gen_from_frame,
            text="/",
            font=FONT_BODY,
            bg=C["card"],
            fg=C["text"],
        ).pack(side="left", padx=3)
        styled_entry(gen_from_frame, self.var_gen_from_year, width=7).pack(side="left")

        tk.Label(
            form_inner,
            text="Δημιουργία έως (ΜΜ / ΕΕΕΕ):",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["text_sub"],
        ).pack(anchor="w")

        gen_to_frame = tk.Frame(form_inner, bg=C["card"])
        gen_to_frame.pack(anchor="w", pady=(2, 6))

        styled_entry(gen_to_frame, self.var_gen_to_month, width=5).pack(side="left")
        tk.Label(
            gen_to_frame,
            text="/",
            font=FONT_BODY,
            bg=C["card"],
            fg=C["text"],
        ).pack(side="left", padx=3)
        styled_entry(gen_to_frame, self.var_gen_to_year, width=7).pack(side="left")

        styled_button(
            form_inner,
            "Δημιουργία διαστήματος",
            self._generate_month,
            C["warning"],
            width=20,
        ).pack(fill="x", pady=(6, 0))

        self.lbl_status = tk.Label(form_inner, text="", font=FONT_SMALL,
                                   bg=C["card"], fg=C["success"], wraplength=200)
        self.lbl_status.pack(pady=(10, 0))

        # Δεξιά λίστα recurring εγγραφών.
        list_frame = card_frame(content)
        list_frame.pack(side="left", fill="both", expand=True, pady=4)
        list_inner = tk.Frame(list_frame, bg=C["card"], padx=16, pady=16)
        list_inner.pack(fill="both", expand=True)

        tk.Label(list_inner, text="Επαναλαμβανόμενες Εγγραφές", font=FONT_HEAD,
                 bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))

        cols = ("id", "Κατηγορία", "Τύπος", "Ποσό", "Ημ/νία Έναρξης", "Ενεργό", "Περιγραφή")
        self.tree = ttk.Treeview(list_inner, columns=cols, show="headings",
                                 style="Dark.Treeview", selectmode="browse", height=18)
        self.tree.column("id", width=0, stretch=False)

        for col, width in [
            ("Κατηγορία", 130),
            ("Τύπος", 70),
            ("Ποσό", 80),
            ("Ημ/νία Έναρξης", 110),
            ("Ενεργό", 60),
            ("Περιγραφή", 180),
        ]:
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                width=width,
                anchor="center" if col in ("Τύπος", "Ποσό", "Ενεργό") else "w",
            )

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _cat_names(self):
        """Φέρνει ονόματα κατηγοριών ανάλογα με τον τύπο income/expense."""

        return [
            cat["Category"]
            for cat in self.cats
            if cat["CategoryType"] == self.var_type.get()
        ]

    def _update_cats(self):
        """Ανανεώνει τις κατηγορίες όταν αλλάζει ο τύπος recurring εγγραφής."""

        names = self._cat_names()
        self.cat_cb["values"] = names
        self.var_cat.set(names[0] if names else "")

    def _load(self):
        """Φορτώνει recurring εγγραφές από τη βάση."""

        for row_id in self.tree.get_children():
            self.tree.delete(row_id)

        for rec in select_recurring_transactions():
            is_income = rec["CategoryType"] == "income"
            amount_text = f"{'+' if is_income else '-'}{rec['RecTranAmount']:.2f} €"
            active_text = "Ναι" if rec["RecTranActive"] == 1 else "Όχι"

            self.tree.insert(
                "",
                "end",
                values=(
                    rec["RecTranID"],
                    rec["Category"],
                    "Έσοδο" if is_income else "Έξοδο",
                    amount_text,
                    date_to_greek(rec["RecTranStartDate"]),
                    active_text,
                    rec["RecTranDescr"] or "",
                ),
                tags=("income" if is_income else "expense",),
            )

        self.tree.tag_configure("income", foreground=C["success"])
        self.tree.tag_configure("expense", foreground=C["danger"])

    def _on_select(self, _event):
        """Όταν επιλέγεται recurring εγγραφή, τη φορτώνουμε στη φόρμα."""

        selected = self.tree.selection()
        if not selected:
            return

        values = self.tree.item(selected[0], "values")
        self.sel_id = int(values[0])
        self._edit_id = self.sel_id

        # Διαβάζουμε τη συγκεκριμένη recurring εγγραφή από το database.py.
        rec = select_recurring_by_id(self.sel_id)
        if not rec:
            return

        self.var_type.set(rec["CategoryType"])
        self._update_cats()
        self.var_cat.set(rec["Category"])
        self.var_amount.set(str(rec["RecTranAmount"]))
        self.var_date.set(date_to_greek(rec["RecTranStartDate"]))
        self.var_desc.set(rec["RecTranDescr"] or "")
        self.var_active.set(rec["RecTranActive"])
        self.form_title.config(text="Επεξεργασία")

    def _save(self):
        """Κάνει insert ή update σε recurring εγγραφή."""

        cat_name = self.var_cat.get().strip()
        amount_text = self.var_amount.get().strip()
        date_text = self.var_date.get().strip()
        desc = self.var_desc.get().strip()

        if not cat_name or not amount_text or not date_text:
            self._status("Συμπληρώστε όλα τα πεδία.", C["danger"])
            return

        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError

            # Ο χρήστης γράφει DD-MM-YYYY, αλλά στη βάση αποθηκεύουμε YYYY-MM-DD.
            db_date = date_to_database(date_text)

        except ValueError:
            self._status("Μη έγκυρο ποσό ή ημερομηνία. Χρησιμοποιήστε DD-MM-YYYY.", C["danger"])
            return

        cat_obj = next((c for c in self.cats if c["Category"] == cat_name), None)
        if not cat_obj:
            self._status("Μη έγκυρη κατηγορία.", C["danger"])
            return

        active = self.var_active.get()

        # Αν έχουμε _edit_id, η φόρμα ενημερώνει υπάρχουσα recurring εγγραφή.
        # Διαφορετικά δημιουργεί νέα recurring εγγραφή.
        if self._edit_id:
            update_recurring_transaction(
                self._edit_id,
                cat_obj["CategoryID"],
                amount,
                db_date,
                desc,
                active,
            )
            self._status("Η εγγραφή ενημερώθηκε.", C["success"])
        else:
            insert_recurring_transaction(
                cat_obj["CategoryID"],
                amount,
                db_date,
                desc,
                active,
            )
            self._status("Η εγγραφή προστέθηκε.", C["success"])

        self._reset()
        self._load()

    def _delete(self):
        """Διαγράφει την επιλεγμένη recurring εγγραφή."""

        if not self.sel_id:
            self._status("Επιλέξτε εγγραφή.", C["warning"])
            return

        if messagebox.askyesno("Διαγραφή", "Να διαγραφεί η εγγραφή;"):
            delete_recurring_transaction(self.sel_id)
            self._reset()
            self._load()
            self._status("Η εγγραφή διαγράφηκε.", C["success"])

    def _reset(self):
        """Καθαρίζει τη φόρμα recurring και την επαναφέρει σε νέα εγγραφή."""

        self.sel_id = None
        self._edit_id = None
        self.var_amount.set("")
        self.var_date.set(date.today().strftime("%d-%m-%Y"))
        self.var_desc.set("")
        self.var_type.set("expense")
        self.var_active.set(1)
        self._update_cats()
        self.form_title.config(text="Νέα Εγγραφή")

    def _get_generation_range(self):
        """
        Διαβάζει το διάστημα μηνών για το οποίο θα δημιουργηθούν recurring συναλλαγές.

        Επιστρέφει λίστα με ζευγάρια (month, year), π.χ.
        [(6, 2026), (7, 2026), (8, 2026)].

        Δεν αλλάζει τη βάση και δεν αλλάζει τις recurring εγγραφές.
        Απλώς ελέγχει την είσοδο του χρήστη πριν γίνει η δημιουργία.
        """

        try:
            from_month = int(self.var_gen_from_month.get())
            from_year = int(self.var_gen_from_year.get())
            to_month = int(self.var_gen_to_month.get())
            to_year = int(self.var_gen_to_year.get())
        except ValueError:
            self._status("Ο μήνας και το έτος δημιουργίας πρέπει να είναι αριθμοί.", C["danger"])
            return None

        if from_month < 1 or from_month > 12 or to_month < 1 or to_month > 12:
            self._status("Ο μήνας πρέπει να είναι από 1 έως 12.", C["danger"])
            return None

        if from_year < 2000 or from_year > 2100 or to_year < 2000 or to_year > 2100:
            self._status("Το έτος πρέπει να είναι ανάμεσα στο 2000 και στο 2100.", C["danger"])
            return None

        # Μετατρέπουμε μήνα/έτος σε αριθμό σειράς.
        # Έτσι μπορούμε εύκολα να ελέγξουμε αν το Από είναι μετά το Έως.
        start_index = from_year * 12 + from_month
        end_index = to_year * 12 + to_month

        if start_index > end_index:
            self._status("Το διάστημα Από δεν μπορεί να είναι μετά το Έως.", C["danger"])
            return None

        months = []
        current_year = from_year
        current_month = from_month

        # Δημιουργούμε όλους τους μήνες του διαστήματος.
        # Παράδειγμα: 11/2026 έως 02/2027 -> 11/2026, 12/2026, 01/2027, 02/2027.
        while current_year * 12 + current_month <= end_index:
            months.append((current_month, current_year))

            current_month += 1

            if current_month > 12:
                current_month = 1
                current_year += 1

        return months

    def _generate_month(self):
        """
        Δημιουργεί πραγματικές συναλλαγές από τις ενεργές recurring εγγραφές
        για το διάστημα μηνών που επέλεξε ο χρήστης.

        Δεν αλλάζουμε το Logic/recurring_service.py.
        Καλούμε την υπάρχουσα generate_monthly_transactions(month, year)
        μία φορά για κάθε μήνα του διαστήματος.
        """

        months = self._get_generation_range()

        # Αν ο χρήστης έδωσε λάθος διάστημα, σταματάμε εδώ.
        # Το μήνυμα λάθους έχει ήδη εμφανιστεί από τη helper function.
        if months is None:
            return

        total_created = 0
        total_skipped = 0

        # Για κάθε μήνα του διαστήματος χρησιμοποιούμε την υπάρχουσα λογική.
        # Η generate_monthly_transactions() παίρνει μόνο ενεργές recurring εγγραφές
        # και αποφεύγει διπλές αυτόματες συναλλαγές για τον ίδιο μήνα.
        for month, year in months:
            result = generate_monthly_transactions(month, year)
            total_created += result["created"]
            total_skipped += result["skipped"]

        first_month, first_year = months[0]
        last_month, last_year = months[-1]

        # Ενημερώνουμε τον χρήστη για το διάστημα και το αποτέλεσμα.
        self._status(
            f"{first_month:02d}/{first_year} έως {last_month:02d}/{last_year}: "
            f"Δημιουργήθηκαν {total_created} εγγραφές, "
            f"παραλείφθηκαν {total_skipped}.",
            C["success"],
        )

    def _status(self, msg, color):
        """Εμφανίζει προσωρινό μήνυμα στην οθόνη recurring."""

        self.lbl_status.config(text=msg, fg=color)
        self.after(3000, lambda: self.lbl_status.config(text=""))


# ──────────────────────────────────────────────
#  ΕΚΚΙΝΗΣΗ GUI
# ──────────────────────────────────────────────
def run_app():
    """Εκκινεί το Tkinter GUI."""

    # Δημιουργούμε το κεντρικό παράθυρο.
    app = FinanceApp()

    # Το mainloop κρατάει την εφαρμογή ανοιχτή και ακούει τα events του χρήστη.
    app.mainloop()

