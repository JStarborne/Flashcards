'''
    application.py
    Main application for Flask framework for final project
    Several snippets taken from Week 9 problem set
    Jessie Starborne
'''


# Requirements
import os
import json
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from tempfile import mkdtemp


# Custom functions
from functions import login_required, deck_required, swap_deck


# Set Flask application
app = Flask(__name__)


# Development use only - Comment out before final submission
app.config['TEMPLATES_AUTO_RELOAD'] = True


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set database
db = SQL('sqlite:///flashcards.db')


# Context processor for global variables
@app.context_processor
def context_processor():
    return dict(username=session.get("username"), deckname=session.get("deckname"))


'''' Routes '''

# Route: Root
@app.route('/')
def index():
    if session.get("user_id") is None:
        return render_template('welcome.html')
    else:
        return redirect('/decks')


# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    errors = []

    # Handle post request for registration
    if request.method == 'POST':
        name = request.form.get('username')
        pass1 = request.form.get('password1')
        pass2 = request.form.get('password2')

        # Error checking
        if not name or len(name) < 1:
            errors.append("You must provide a name!")

        if not pass1 or len(pass1) < 1:
            errors.append("You must provide a password!")

        if pass1 != pass2:
            errors.append("Your passwords must match!")

        # Check for duplicate username
        if db.execute("SELECT id FROM users WHERE username LIKE ?", name):
            return apology("That username is already in use!")

        # If no error, inject into the database and redirect to login
        if len(errors) < 1:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", name, generate_password_hash(pass1))
            return redirect("/login")

    # No post? Display the registration form
    return render_template("register.html", errors=errors)


# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    errors = []

    # Handle post request for login
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get('username'):
            errors.append("You must enter your username!")

        # Ensure password was submitted
        elif not request.form.get('password'):
            errors.append("You must enter your password!")

        # Query database for username
        result = db.execute("SELECT * FROM users WHERE username = ?", request.form.get('username'))

        # Ensure username exists and password is correct
        if len(result) != 1 or not check_password_hash(result[0]["hash"], request.form.get('password')):
            errors.append("Username or password is incorrect!")
            return render_template("login.html")

        # Set the session and global variables
        session['user_id'] = result[0]['id']
        session['username'] = result[0]['username']
        if result[0]['current_deck']:
            swap_deck(db, result[0]['current_deck'])

        # Redirect user to home page on successful login
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# Route: Manage Decks
@app.route('/decks')
@login_required
def managedecks():
    current_deck = session.get("current_deck")
    show_practice = False
    decks = []

    result = db.execute("SELECT * FROM decks WHERE user_id=?", session.get("user_id"))
    for row in result:
        countrow = db.execute("SELECT COUNT(*) AS 'count' FROM cards WHERE deck_id = ?", row['id'])
        if countrow:
            row['count'] = countrow[0]['count']
        else:
            row['count'] = 0
        decks.append(row)

    if len(decks) and not current_deck:
        current_deck = swap_deck(db, decks[0]['id'])
    elif request.args.get('swap', type=int):
        current_deck = swap_deck(db, request.args.get('swap', type=int))

    if current_deck:
        for deck in decks:
            if deck['id'] == current_deck and deck['count'] > 0:
                show_practice = True

    return render_template('decks.html', current_deck=current_deck, decks=decks, show_practice=show_practice)


# Route: Create Deck
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    errors = []

    # Handle post request for login
    if request.method == "POST":

        title = request.form.get('title')
        description = request.form.get('description')

        # Ensure title was submitted
        if not title or not description:
            errors.append("You must enter a title and description!")

        # Check for circumvention of maxlength
        # (This is not technically a problem because we're using TEXT in the dB, but y'know...)
        if len(title) > 50:
            errors.append("Title must not exceed 50 characters!")
        if len(description) > 320:
            errors.append("Description must not exceed 320 characters!")

        # If no error, inject into the database and redirect to login
        if len(errors) < 1:
            db.execute("INSERT INTO decks (user_id, title, description) VALUES (?, ?, ?)", session.get("user_id"), title, description)
            return redirect("/decks")

    # No post? Display the creation form
    return render_template('create.html', errors=errors)

# Route: Cards
@app.route('/cards')
@login_required
@deck_required
def cards():
    cards = []

    # Find all cards within this deck
    result = db.execute("SELECT * FROM cards WHERE deck_id = ?", session.get("current_deck"))
    if result:
        for row in result:
            cards.append(row)

    return render_template('cards.html', cards=cards)

# Route: Add Card
@app.route('/add', methods=['GET', 'POST'])
@login_required
@deck_required
def add():
    success = None
    errors = []
    count = 0

    # Handle post
    if request.method == "POST":
        question = request.form.get('question')
        answer   = request.form.get('answer')

        # Ensure title was submitted
        if not question or not answer:
            errors.append("Your card must have text on both sides!")

        # Check for circumvention of maxlength
        if len(question) > 320 or len(answer) > 320:
            errors.append("The card text cannot exceed 320 characters!")

        # If no error, inject into the database
        if len(errors) < 1:
            result = db.execute("INSERT INTO cards (deck_id, question, answer) VALUES (?, ?, ?)", session.get("current_deck"), question, answer)
            if result:
                success = "Successfully saved card to deck!"
            else:
                errors.append("There was a problem inserting the card into the deck. Please try again.")

    # Grab card count
    result = db.execute("SELECT COUNT(*) as 'count' FROM cards WHERE deck_id = ?", session.get("current_deck"))
    if result:
        count = result[0]['count']

    return render_template('add.html', success=success, count=count, errors=errors)

# Route: Edit Card
@app.route('/edit', methods=['GET', 'POST'])
@login_required
@deck_required
def edit_card():
    errors = []

    # Handle post
    if request.method == "POST":
        question = request.form.get('question')
        answer   = request.form.get('answer')
        card_id  = request.form.get('id')

        # Ensure there is a card id
        if not card_id:
            return redirect('/cards')

        # Ensure title was submitted
        if not question or not answer:
            errors.append("Your card must have text on both sides!")

        # Check for circumvention of maxlength
        if len(question) > 320 or len(answer) > 320:
            errors.append("The card text cannot exceed 320 characters!")

        # Make sure card exists and belongs to this user
        result = db.execute("SELECT * FROM cards JOIN decks ON decks.id = cards.deck_id WHERE cards.id = ? AND user_id = ?", card_id, session.get("user_id"))
        if not result:
            return redirect('/cards')

        # If no error, update the card
        if len(errors) < 1:
            result = db.execute("UPDATE cards SET question = ?, answer = ? WHERE id = ?", question, answer, card_id)
            if result:
                return redirect('/cards')
            else:
                errors.append("There was a problem inserting the card into the deck. Please try again.")
                return render_template('cardedit.html', card=card, errors=errors)

    # Error checking
    card_id = request.args.get('id')
    if not card_id:
        return redirect('/edit')

    # Make sure card exists and belongs to this user
    result = db.execute("SELECT cards.id, cards.question, cards.answer FROM cards JOIN decks ON decks.id = cards.deck_id WHERE cards.id = ? AND user_id = ?", card_id, session.get("user_id"))
    if not result:
        return redirect('/cards')
    else:
        card = result[0]
        print("Card: ", card)
        return render_template('cardedit.html', card=card, errors=errors)

# Route: Delete Card
@app.route('/delete_card')
@login_required
@deck_required
def delete_card():
    card_id = request.args.get('id', type=int)

    # Ensure there is a card id
    if not card_id:
        return redirect('/cards')

    # Make sure card exists and belongs to this user's active deck
    result = db.execute("SELECT cards.id FROM cards JOIN decks ON decks.id = cards.deck_id WHERE cards.id = ? AND decks.user_id = ?", card_id, session.get("user_id"))
    if not result:
        return redirect('/cards')

    # Mercilessly yeet the card from existance
    db.execute("DELETE FROM cards WHERE id = ?", card_id)
    return redirect('/cards')

# Route: Delete Deck
@app.route('/delete_deck')
@login_required
@deck_required
def delete_deck():
    deck_id = request.args.get('id', type=int)

    # Ensure there is a deck id
    if not deck_id:
        return redirect('/decks')

    # Make sure deck exists and belongs to this user
    result = db.execute("SELECT * FROM decks WHERE id = ? AND user_id = ?", deck_id, session.get("user_id"))
    if not result:
        return redirect('/decks')

    # If this is the active deck, set to None so it reassigns.
    if deck_id == session.get("current_deck"):
        session['current_deck'] = None
        session['deckname'] = None

    # Mercilessly yeet the deck from existance
    db.execute("DELETE FROM decks WHERE id = ?", deck_id)

    # Also mercilessly yeet all the cards associated with this deck
    db.execute("DELETE FROM cards WHERE deck_id = ?", deck_id)

    return redirect('/decks')

# Route: Edit Deck
@app.route('/deckedit', methods=['GET', 'POST'])
@login_required
@deck_required
def edit_deck():
    deck_id = request.args.get('id')
    errors = []
    deck = {}

    # Handle POST:
    if request.method == "POST":
        description = request.form.get('description')
        title = request.form.get('title')
        deck_id = request.form.get('id')

        # Ensure title was submitted
        if not title or not description:
            errors.append("You must enter a title and description!")

        # Check for circumvention of maxlength
        # (This is not technically a problem because we're using TEXT in the dB, but y'know...)
        if len(title) > 50:
            errors.append("Title must not exceed 50 characters!")
        if len(description) > 320:
            errors.append("Description must not exceed 320 characters!")

        # Make sure card exists and belongs to this user
        result = db.execute("SELECT id FROM decks WHERE id = ? AND user_id = ?", deck_id, session.get("user_id"))
        if not result:
            return redirect('/decks')

        # If no error, update
        if len(errors) < 1:
            db.execute("UPDATE decks SET title = ?, description = ? WHERE id = ?", title, description, deck_id)
            return redirect("/decks")

    # Ensure there is a deck id
    if not deck_id:
        return redirect('/decks')

    # Make sure card exists and belongs to this user
    result = db.execute("SELECT * FROM decks WHERE id = ? AND user_id = ?", deck_id, session.get("user_id"))
    if result:
        deck = result[0]
    else:
        return redirect('/decks')

    return render_template('deckedit.html', deck=deck, errors=errors)

# Route: Practice
@app.route('/practice')
@login_required
@deck_required
def practice():
    cards = []

    # Find all cards within this deck
    result = db.execute("SELECT * FROM cards WHERE deck_id = ?", session.get("current_deck"))
    if result:
        for row in result:
            cards.append(row)

    count = len(cards)

    return render_template('practice.html', count=count, cards=cards)