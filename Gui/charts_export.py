"""
Οθόνη γραφημάτων και εξαγωγών της εφαρμογής.

Το αρχείο αυτό είναι κομμάτι του GUI.
Δεν γράφει SQL απευθείας και δεν χρησιμοποιεί aliases.
Όλα τα δεδομένα έρχονται από functions του Db/database.py.

Η εκφώνηση ζητά τουλάχιστον 3 γραφικές αναπαραστάσεις.
Εδώ δίνουμε 4 επιλογές:
1. Έξοδα ανά κατηγορία.
2. Έσοδα ανά κατηγορία.
3. Έσοδα / έξοδα ανά μήνα.
4. Υπόλοιπο ανά μήνα.

Στην ίδια οθόνη υπάρχουν και exports:
- Excel αρχείο για συγκεκριμένο μήνα.
- PDF αρχείο για συγκεκριμένο μήνα.

Νέα βελτίωση:
Τα γραφήματα φιλτράρονται πλέον με ημερομηνίες Από / Έως μέσω popup Calendar.
Τα exports παραμένουν μηνιαία, ώστε να μη χαλάσουν οι υπάρχουσες export functions.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import date, datetime

# Το Calendar εμφανίζει popup ημερολόγιο.
# Χρησιμοποιούμε δικό μας μικρό wrapper αντί για DateEntry, ώστε να μη κλείνει
# όταν ο χρήστης πατάει τα βελάκια αλλαγής μήνα/έτους.
from tkcalendar import Calendar

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Εδώ κάνουμε απευθείας import τις πραγματικές functions του database layer.
# Δεν χρησιμοποιούμε ονόματα τύπου get_categories/add_category κτλ.
# Έτσι μπορούμε να εξηγήσουμε καθαρά ότι το GUI ζητά δεδομένα από το Db/database.py.
from Db.database import (
    select_expenses_by_category,
    select_income_by_category,
    select_monthly_summary,
)

# Τα exports είναι σε ξεχωριστό φάκελο, ώστε να μη γεμίζει το GUI με λογική αρχείων.
from Exports_Pdf_Excel.excel_export import export_month_to_excel
from Exports_Pdf_Excel.pdf_export import export_month_to_pdf

# Το validation κρατιέται επίσης ξεχωριστά.
# Έτσι ο έλεγχος μήνα/έτους των exports δεν είναι σκορπισμένος μέσα στο GUI.
from Logic.validation import validate_month, validate_year


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

    @classmethod
    def close_active_popup(cls):
        """
        Κλείνει με ασφάλεια οποιοδήποτε ενεργό popup calendar.

        Χρησιμοποιείται όταν ο χρήστης πάει να γράψει σε άλλο πεδίο της ίδιας οθόνης,
        π.χ. στο Μήνας / Έτος του export, ώστε να μη μείνει παλιό popup ή focus state
        που κάνει τα Entry πεδία να φαίνονται σαν παγωμένα.
        """

        picker = cls._active_picker

        if picker is not None:
            try:
                picker._close_calendar()
            except Exception:
                cls._active_picker = None

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
        """
        Κλείνει το popup ημερολόγιο με ασφαλές cleanup.

        Σημαντικό:
        Όλο το CalendarPopupEntry καλεί τη function _close_calendar().
        Το popup αποθηκεύεται στη μεταβλητή self._popup και όχι self.popup.

        Αν μείνει ανοιχτό popup/focus/grab state, τα υπόλοιπα πεδία της ίδιας οθόνης,
        π.χ. ο Μήνας ή το Έτος του export, μπορεί να φαίνονται σαν να έχουν παγώσει.
        """

        # Αν αυτό το calendar είναι το ενεργό popup, καθαρίζουμε το class reference.
        if CalendarPopupEntry._active_picker is self:
            CalendarPopupEntry._active_picker = None

        popup = self._popup

        if popup is not None:
            # Απελευθερώνουμε τυχόν grab που μπορεί να κρατάει το popup ή το Calendar.
            # Αυτό είναι το πιο σημαντικό για να μην "παγώνουν" τα επόμενα Entry πεδία.
            for widget in (self._calendar, popup):
                try:
                    widget.grab_release()
                except Exception:
                    pass

            try:
                popup.destroy()
            except Exception:
                pass

        # Καθαρίζουμε references για να μη μείνει παλιό calendar/focus state.
        self._popup = None
        self._calendar = None

        # Επιστρέφουμε το focus στο βασικό παράθυρο.
        # Δεν το κλειδώνουμε στο date field, ώστε ο χρήστης να μπορεί αμέσως
        # να πατήσει και να γράψει σε Μήνας / Έτος του export.
        try:
            self.winfo_toplevel().focus_force()
        except Exception:
            pass


class ChartsExportScreen(tk.Frame):
    """
    Οθόνη Tkinter για γραφήματα και exports.

    Η κλάση αυτή εμφανίζεται μέσα στο κεντρικό παράθυρο της εφαρμογής.
    Παίρνει χρώματα και γραμματοσειρές από το app.py για να κρατάει ίδιο στυλ.
    """

    def __init__(self, parent, colors, fonts):
        # Καλούμε τον constructor του tk.Frame.
        # Το bg μπαίνει από το κοινό theme της εφαρμογής.
        super().__init__(parent, bg=colors["bg"])

        # Κρατάμε το λεξικό χρωμάτων σε μεταβλητή της κλάσης.
        # Έτσι δεν ξαναγράφουμε σταθερά χρώματα μέσα σε κάθε widget.
        self.C = colors

        # Κρατάμε και τα fonts που μας στέλνει το app.py.
        self.F = fonts

        # Φίλτρα γραφημάτων.
        # Τα αφήνουμε κενά στην αρχή ώστε τα γραφήματα να δείχνουν όλα τα διαθέσιμα δεδομένα.
        self.var_date_from = tk.StringVar(value="")
        self.var_date_to = tk.StringVar(value="")

        # Φίλτρα exports.
        # Τα exports παραμένουν μηνιαία, επειδή οι υπάρχουσες functions
        # export_month_to_excel() και export_month_to_pdf() δέχονται μήνα και έτος.
        today = date.today()
        self.var_export_month = tk.StringVar(value=str(today.month))
        self.var_export_year = tk.StringVar(value=str(today.year))

        # Εδώ θα κρατήσουμε το ενεργό matplotlib canvas.
        # Όταν αλλάζει γράφημα, το καθαρίζουμε και φτιάχνουμε νέο.
        self.canvas = None

        # Χτίζουμε την οθόνη.
        self._build()

    # ──────────────────────────────────────────────
    #  ΒΑΣΙΚΟ ΣΤΗΣΙΜΟ ΟΘΟΝΗΣ
    # ──────────────────────────────────────────────
    def _build(self):
        """
        Δημιουργεί:
        - τίτλο οθόνης
        - φίλτρα Από / Έως για τα γραφήματα
        - κουμπιά γραφημάτων
        - ξεχωριστή περιοχή export με μήνα/έτος
        - περιοχή εμφάνισης γραφήματος
        """

        # Header της οθόνης.
        header = tk.Frame(self, bg=self.C["bg"], pady=16, padx=24)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Γραφήματα / Export",
            font=self.F["title"],
            bg=self.C["bg"],
            fg=self.C["text"],
        ).pack(side="left")

        self._build_chart_filters()
        self._build_chart_buttons()
        self._build_export_section()
        self._build_chart_area()

    def _build_chart_filters(self):
        """Δημιουργεί την κάρτα φίλτρων Από / Έως για τα γραφήματα."""

        filter_card = self._card()
        filter_card.pack(fill="x", padx=24, pady=(0, 10))

        filter_inner = tk.Frame(filter_card, bg=self.C["card"], padx=16, pady=12)
        filter_inner.pack(fill="x")

        tk.Label(
            filter_inner,
            text="Φίλτρα γραφημάτων:",
            font=self.F["head"],
            bg=self.C["card"],
            fg=self.C["text"],
        ).pack(side="left", padx=(0, 18))

        tk.Label(
            filter_inner,
            text="Από:",
            font=self.F["small"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(side="left")

        self.date_from_entry = self._date_entry(filter_inner, self.var_date_from, width=12)
        self.date_from_entry.pack(side="left", padx=(5, 16))
        self.date_from_entry.delete(0, "end")

        tk.Label(
            filter_inner,
            text="Έως:",
            font=self.F["small"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(side="left")

        self.date_to_entry = self._date_entry(filter_inner, self.var_date_to, width=12)
        self.date_to_entry.pack(side="left", padx=(5, 16))
        self.date_to_entry.delete(0, "end")

        self._button(
            filter_inner,
            "Καθαρισμός",
            self._clear_chart_filters,
            self.C["text_sub"],
        ).pack(side="left", padx=4)

        tk.Label(
            filter_inner,
            text="Αν τα πεδία μείνουν κενά, εμφανίζονται όλα τα διαθέσιμα δεδομένα.",
            font=self.F["small"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(side="left", padx=(16, 0))

    def _build_chart_buttons(self):
        """Δημιουργεί την κάρτα κουμπιών των γραφημάτων."""

        buttons_card = self._card()
        buttons_card.pack(fill="x", padx=24, pady=(0, 10))

        buttons = tk.Frame(buttons_card, bg=self.C["card"], padx=16, pady=12)
        buttons.pack(fill="x")

        tk.Label(
            buttons,
            text="Γραφήματα:",
            font=self.F["head"],
            bg=self.C["card"],
            fg=self.C["text"],
        ).pack(side="left", padx=(0, 12))

        self._button(
            buttons,
            "Έξοδα ανά κατηγορία",
            self.show_expenses_by_category,
        ).pack(side="left", padx=4)

        self._button(
            buttons,
            "Έσοδα ανά κατηγορία",
            self.show_income_by_category,
        ).pack(side="left", padx=4)

        self._button(
            buttons,
            "Μηνιαία σύνοψη",
            self.show_monthly_income_expense,
        ).pack(side="left", padx=4)

        self._button(
            buttons,
            "Υπόλοιπο ανά μήνα",
            self.show_monthly_balance,
        ).pack(side="left", padx=4)

    def _build_export_section(self):
        """
        Δημιουργεί την περιοχή των exports.

        Τα exports μένουν ξεχωριστά από τα φίλτρα γραφημάτων,
        γιατί οι υπάρχουσες export functions είναι μηνιαίες αναφορές.
        """

        export_card = self._card()
        export_card.pack(fill="x", padx=24, pady=(0, 10))

        export_inner = tk.Frame(export_card, bg=self.C["card"], padx=16, pady=12)
        export_inner.pack(fill="x")

        tk.Label(
            export_inner,
            text="Export μηνιαίας αναφοράς:",
            font=self.F["head"],
            bg=self.C["card"],
            fg=self.C["text"],
        ).pack(side="left", padx=(0, 18))

        tk.Label(
            export_inner,
            text="Μήνας:",
            font=self.F["small"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(side="left")

        self._entry(export_inner, self.var_export_month, 6).pack(side="left", padx=(5, 16))

        tk.Label(
            export_inner,
            text="Έτος:",
            font=self.F["small"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(side="left")

        self._entry(export_inner, self.var_export_year, 8).pack(side="left", padx=(5, 16))

        self._button(
            export_inner,
            "Export Excel",
            self.export_excel,
            self.C["success"],
        ).pack(side="left", padx=4)

        self._button(
            export_inner,
            "Export PDF",
            self.export_pdf,
            self.C["danger"],
        ).pack(side="left", padx=4)

    def _build_chart_area(self):
        """Δημιουργεί την περιοχή όπου εμφανίζεται το ενεργό γράφημα."""

        self.chart_area = self._card()
        self.chart_area.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        tk.Label(
            self.chart_area,
            text="Επιλέξτε γράφημα από τα παραπάνω κουμπιά.",
            font=self.F["body"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(expand=True)

    # ──────────────────────────────────────────────
    #  ΜΙΚΡΑ ΒΟΗΘΗΤΙΚΑ ΓΙΑ ΤΟ UI
    # ──────────────────────────────────────────────
    def _card(self):
        """Φτιάχνει κάρτα με ίδιο στυλ με το υπόλοιπο GUI."""

        return tk.Frame(
            self,
            bg=self.C["card"],
            highlightthickness=1,
            highlightbackground=self.C["border"],
        )

    def _entry(self, parent, variable, width):
        """
        Φτιάχνει ένα απλό entry με dark εμφάνιση.

        Πριν δοθεί focus στο πεδίο, κλείνουμε τυχόν ανοιχτό popup calendar.
        Αυτό αποτρέπει focus/grab state από το calendar που μπορεί να κάνει
        τα πεδία Μήνας / Έτος του export να φαίνονται σαν παγωμένα.
        """

        entry = tk.Entry(
            parent,
            textvariable=variable,
            width=width,
            bg=self.C["entry_bg"],
            fg=self.C["text"],
            insertbackground=self.C["accent"],
            relief="flat",
            font=self.F["body"],
            highlightthickness=1,
            highlightbackground=self.C["border"],
            highlightcolor=self.C["accent"],
        )

        def focus_entry(_event=None):
            """Κλείνει ενεργό calendar popup και δίνει focus στο συγκεκριμένο Entry."""
            CalendarPopupEntry.close_active_popup()
            entry.after_idle(entry.focus_set)

        entry.bind("<Button-1>", focus_entry, add="+")
        entry.bind("<FocusIn>", lambda _event: CalendarPopupEntry.close_active_popup(), add="+")

        return entry

    def _date_entry(self, parent, variable, width=12):
        """
        Φτιάχνει πεδίο ημερομηνίας με popup ημερολόγιο.

        date_pattern="dd-mm-yyyy" κρατά την εμφάνιση σε ελληνική μορφή.
        locale="el_GR" προσπαθεί να εμφανίσει το ημερολόγιο στα ελληνικά.
        Αν σε κάποιο PC δεν υποστηρίζεται, μπορεί να αφαιρεθεί μόνο αυτή η γραμμή.
        """

        return CalendarPopupEntry(
            parent,
            textvariable=variable,
            width=width,
            colors=self.C,
            font=self.F["body"],
            date_pattern="dd-mm-yyyy",
            locale="el_GR",
        )

    def _button(self, parent, text, command, color=None):
        """Φτιάχνει κουμπί με ίδιο ύφος με το υπόλοιπο GUI."""

        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color or self.C["accent"],
            fg="white",
            relief="flat",
            font=self.F["body"],
            padx=10,
            pady=6,
            cursor="hand2",
            activebackground=self.C["hover"],
            activeforeground="white",
            bd=0,
        )

    # ──────────────────────────────────────────────
    #  ΒΟΗΘΗΤΙΚΑ ΓΙΑ ΔΕΔΟΜΕΝΑ / ΓΡΑΦΗΜΑΤΑ
    # ──────────────────────────────────────────────
    def _date_to_database(self, date_text):
        """
        Μετατρέπει ημερομηνία από DD-MM-YYYY σε YYYY-MM-DD για τα queries.

        Η βάση κρατάει τις ημερομηνίες ως YYYY-MM-DD,
        γιατί αυτή η μορφή βοηθάει στη σωστή ταξινόμηση και σύγκριση.
        """

        try:
            return datetime.strptime(date_text, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Μορφή ημερομηνίας: DD-MM-YYYY") from exc

    def _get_date_range(self):
        """
        Διαβάζει τα φίλτρα Από / Έως και τα επιστρέφει σε μορφή βάσης.

        Αν κάποιο πεδίο είναι κενό, επιστρέφει None για αυτό το φίλτρο.
        """

        date_from_text = self.var_date_from.get().strip()
        date_to_text = self.var_date_to.get().strip()

        date_from = None
        date_to = None

        if date_from_text:
            date_from = self._date_to_database(date_from_text)

        if date_to_text:
            date_to = self._date_to_database(date_to_text)

        if date_from and date_to and date_from > date_to:
            raise ValueError("Η ημερομηνία Από δεν μπορεί να είναι μετά την ημερομηνία Έως.")

        return date_from, date_to

    def _date_range_title(self, date_from, date_to):
        """Φτιάχνει μικρό κείμενο τίτλου για το ενεργό διάστημα φίλτρων."""

        if date_from and date_to:
            return f"{self.var_date_from.get()} έως {self.var_date_to.get()}"

        if date_from:
            return f"από {self.var_date_from.get()}"

        if date_to:
            return f"έως {self.var_date_to.get()}"

        return "όλα τα δεδομένα"

    def _get_export_month_year(self):
        """
        Διαβάζει μήνα και έτος για τα exports.

        Δεν χρησιμοποιείται για τα γραφήματα.
        Τα γραφήματα χρησιμοποιούν τα φίλτρα Από / Έως.
        """

        month = validate_month(self.var_export_month.get())
        year = validate_year(self.var_export_year.get())
        return month, year

    def _clear_chart_filters(self):
        """Καθαρίζει τα φίλτρα γραφημάτων Από / Έως."""

        self.date_from_entry.delete(0, "end")
        self.date_to_entry.delete(0, "end")

    def _clear_chart(self):
        """Καθαρίζει την περιοχή γραφήματος πριν εμφανιστεί νέο γράφημα."""

        for child in self.chart_area.winfo_children():
            child.destroy()

        self.canvas = None

    def _draw_figure(self, figure):
        """Εμφανίζει ένα matplotlib Figure μέσα στο Tkinter."""

        self._clear_chart()

        self.canvas = FigureCanvasTkAgg(figure, master=self.chart_area)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _show_no_data(self):
        """Δείχνει φιλικό μήνυμα όταν το query δεν επιστρέφει δεδομένα."""

        self._clear_chart()

        tk.Label(
            self.chart_area,
            text="Δεν υπάρχουν δεδομένα για προβολή στο επιλεγμένο διάστημα.",
            font=self.F["body"],
            bg=self.C["card"],
            fg=self.C["text_sub"],
        ).pack(expand=True)

    def _month_to_display(self, month_text):
        """
        Μετατρέπει μήνα από YYYY-MM σε MM-YYYY για εμφάνιση στο GUI.

        Η βάση και τα queries κρατούν το YYYY-MM γιατί βοηθάει στη σωστή
        ταξινόμηση και στο φιλτράρισμα.
        """

        try:
            year, month = str(month_text).split("-")
            return f"{month}-{year}"
        except (TypeError, ValueError):
            return month_text or ""

    # ──────────────────────────────────────────────
    #  ΓΡΑΦΗΜΑ 1
    # ──────────────────────────────────────────────
    def show_expenses_by_category(self):
        """Γράφημα εξόδων ανά κατηγορία για το επιλεγμένο διάστημα Από / Έως."""

        try:
            date_from, date_to = self._get_date_range()
            rows = select_expenses_by_category(date_from=date_from, date_to=date_to)
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        if not rows:
            self._show_no_data()
            return

        labels = [row["Category"] for row in rows]
        values = [float(row["TotalExpense"]) for row in rows]

        # Ταξινομούμε τις κατηγορίες με βάση το ποσό.
        # Αυτό κάνει το γράφημα πιο καθαρό για παρουσίαση.
        chart_data = sorted(zip(labels, values), key=lambda item: item[1])

        labels = [item[0] for item in chart_data]
        values = [item[1] for item in chart_data]

        fig = Figure(figsize=(7.5, 4.8), dpi=100)
        ax = fig.add_subplot(111)

        # Χρησιμοποιούμε οριζόντιο bar chart αντί για pie chart.
        # Έτσι δεν μπερδεύονται labels και ποσοστά όταν υπάρχουν πολλές κατηγορίες.
        ax.barh(labels, values)

        ax.set_title(f"Έξοδα ανά κατηγορία - {self._date_range_title(date_from, date_to)}")
        ax.set_xlabel("Ποσό (€)")

        # Εμφανίζουμε το ποσό δίπλα σε κάθε μπάρα.
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
        self._draw_figure(fig)

       

    # ──────────────────────────────────────────────
    #  ΓΡΑΦΗΜΑ 2
    # ──────────────────────────────────────────────
    def show_income_by_category(self):
        """Γράφημα εσόδων ανά κατηγορία για το επιλεγμένο διάστημα Από / Έως."""

        try:
            date_from, date_to = self._get_date_range()
            rows = select_income_by_category(date_from=date_from, date_to=date_to)
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        if not rows:
            self._show_no_data()
            return

        labels = [row["Category"] for row in rows]
        values = [row["TotalIncome"] for row in rows]

        fig = Figure(figsize=(7.5, 4.8), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar(labels, values)
        ax.set_title(f"Έσοδα ανά κατηγορία - {self._date_range_title(date_from, date_to)}")
        ax.set_ylabel("Ποσό")
        ax.tick_params(axis="x", rotation=25)

        fig.tight_layout()
        self._draw_figure(fig)

    # ──────────────────────────────────────────────
    #  ΓΡΑΦΗΜΑ 3
    # ──────────────────────────────────────────────
    def show_monthly_income_expense(self):
        """Γράφημα σύγκρισης εσόδων και εξόδων ανά μήνα για το επιλεγμένο διάστημα."""

        try:
            date_from, date_to = self._get_date_range()
            rows = select_monthly_summary(date_from=date_from, date_to=date_to)
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        if not rows:
            self._show_no_data()
            return

        months = [self._month_to_display(row["Month"]) for row in rows]
        incomes = [row["TotalIncome"] for row in rows]
        expenses = [row["TotalExpense"] for row in rows]

        positions = list(range(len(months)))
        width = 0.35

        fig = Figure(figsize=(7.5, 4.8), dpi=100)
        ax = fig.add_subplot(111)

        ax.bar([x - width / 2 for x in positions], incomes, width, label="Έσοδα")
        ax.bar([x + width / 2 for x in positions], expenses, width, label="Έξοδα")

        ax.set_xticks(positions)
        ax.set_xticklabels(months, rotation=25)
        ax.set_title(f"Μηνιαία σύνοψη εσόδων / εξόδων - {self._date_range_title(date_from, date_to)}")
        ax.set_ylabel("Ποσό")
        ax.legend()

        fig.tight_layout()
        self._draw_figure(fig)

    # ──────────────────────────────────────────────
    #  ΓΡΑΦΗΜΑ 4
    # ──────────────────────────────────────────────
    def show_monthly_balance(self):
        """Γράφημα εξέλιξης υπολοίπου ανά μήνα για το επιλεγμένο διάστημα."""

        try:
            date_from, date_to = self._get_date_range()
            rows = select_monthly_summary(date_from=date_from, date_to=date_to)
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        if not rows:
            self._show_no_data()
            return

        months = [self._month_to_display(row["Month"]) for row in rows]
        balances = [row["Balance"] for row in rows]

        fig = Figure(figsize=(7.5, 4.8), dpi=100)
        ax = fig.add_subplot(111)

        ax.plot(months, balances, marker="o")
        ax.set_title(f"Υπόλοιπο ανά μήνα - {self._date_range_title(date_from, date_to)}")
        ax.set_ylabel("Υπόλοιπο")
        ax.tick_params(axis="x", rotation=25)
        ax.grid(True)

        fig.tight_layout()
        self._draw_figure(fig)

    # ──────────────────────────────────────────────
    #  EXPORT EXCEL
    # ──────────────────────────────────────────────
    def export_excel(self):
        """
        Εξάγει τις συναλλαγές του επιλεγμένου μήνα σε αρχείο Excel.

        Το export παραμένει μηνιαίο για να μη χαλάσουν οι υπάρχουσες functions.
        """

        try:
            month, year = self._get_export_month_year()
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        default_name = f"finance_report_{year}_{month:02d}.xlsx"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel files", "*.xlsx")],
        )

        if not file_path:
            return

        try:
            export_month_to_excel(month, year, file_path)
            messagebox.showinfo(
                "Export Excel",
                f"Το αρχείο δημιουργήθηκε επιτυχώς:\n{file_path}",
            )
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))

    # ──────────────────────────────────────────────
    #  EXPORT PDF
    # ──────────────────────────────────────────────
    def export_pdf(self):
        """
        Εξάγει τις συναλλαγές του επιλεγμένου μήνα σε αρχείο PDF.

        Το PDF export παραμένει μηνιαίο για να μη χαλάσει η υπάρχουσα αναφορά.
        """

        try:
            month, year = self._get_export_month_year()
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
            return

        default_name = f"finance_report_{year}_{month:02d}.pdf"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF files", "*.pdf")],
        )

        if not file_path:
            return

        try:
            export_month_to_pdf(month, year, file_path)
            messagebox.showinfo(
                "Export PDF",
                f"Το αρχείο PDF δημιουργήθηκε επιτυχώς:\n{file_path}",
            )
        except Exception as error:
            messagebox.showerror("Σφάλμα", str(error))
