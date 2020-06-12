from app.models import *
from app import app, db, bcrypt
from flask import render_template

@app.route("/")
def home():
    flights = Flight.query.order_by(Flight.depart_datetime).all()
    return render_template("home.html", flights=flights)