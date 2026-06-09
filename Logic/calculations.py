"""
Βοηθητικές συναρτήσεις υπολογισμών.

Οι βασικές οικονομικές πράξεις είναι απλές, αλλά τις κρατάμε εδώ για να φαίνεται
καθαρά ότι η εφαρμογή χωρίζει τη λογική από το GUI.
"""


def calculate_balance(total_income, total_expense):
    """Υπολογίζει το υπόλοιπο αφαιρώντας έξοδα από έσοδα."""

    return float(total_income) - float(total_expense)


def calculate_percentage(part, total):
    """Υπολογίζει ποσοστό συμμετοχής μιας τιμής στο σύνολο."""

    if total == 0:
        return 0

    return (float(part) / float(total)) * 100
