'''
    functions.py
    Helper functions for final project
    Jessie Starborne
'''

# Requirements
from flask import redirect, session
from functools import wraps


# Flask decorator to redirect to login page
# Stolen mercilessly from CS50's Week 9 project
# (And I believe they stole it directly from the Flask documentation.)
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Decorator to check for the existance of an active deck, redirect otherwise
def deck_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("current_deck") is None:
            return redirect('/decks')
        return f(*args, **kwargs)
    return decorated_function


# Swap currently selected deck
def swap_deck(db, deck):

    # Capture current deck
    current_deck = session.get("current_deck")

    # If the requested deck and the current deck is the same, just return.
    if deck == current_deck:
        return current_deck

    # Make sure the deck exists in the db
    result = db.execute("SELECT * FROM decks WHERE id = ? AND user_id = ? LIMIT 1", deck, session.get("user_id"))
    if result:
        # Update session variables
        session['current_deck'] = result[0]['id']
        session['deckname'] = result[0]['title']

        # Update db
        db.execute("UPDATE users SET current_deck = ? WHERE id = ?", result[0]['id'], session.get("user_id"))

        return result[0]['id']

    return current_deck