"""
Κεντρικό αρχείο εκκίνησης της εφαρμογής.

Το main.py μένει σκόπιμα μικρό:
1. Ελέγχει/δημιουργεί τη βάση.
2. Προσθέτει αρχικές κατηγορίες για να είναι εύκολο το demo.
3. Ανοίγει το GUI.

"""

from Db.database import initialize_database, seed_default_categories
from Gui.app import run_app


def main():
    """Εκτελεί τα απαραίτητα βήματα εκκίνησης."""

    # Δημιουργούμε τους πίνακες αν δεν υπάρχουν ήδη.
    initialize_database()

    # Βάζουμε αρχικές κατηγορίες μόνο αν δεν υπάρχουν.
    seed_default_categories()
    

    # Ξεκινάμε το γραφικό περιβάλλον.
    run_app()


if __name__ == "__main__":
    main()
