from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin

app = Flask(__name__)
app.config["SECRET_KEY"] = "f42228c3084eba5c057abdb77e7325d2"
conn = "mysql+mysqlconnector://root:root@localhost:8889/flask_ticket_booking"
app.config["SQLALCHEMY_DATABASE_URI"] = conn

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

class Airline(db.Model):
    name = db.Column(db.String(20), primary_key=True)

class Airport(db.Model):
    name = db.Column(db.String(20), primary_key=True)
    city = db.Column(db.String(20), nullable=False)

class Airplane(db.Model):
    id = db.Column(db.String(5), primary_key=True)
    airline = db.Column(db.String(20), db.ForeignKey("airline.name"), primary_key=True)
    num_seat = db.Column(db.Integer, nullable=False)

class Flight(db.Model):
    flight_num = db.Column(db.String(5), primary_key=True)
    depart_date = db.Column(db.Date, primary_key=True)
    depart_time = db.Column(db.Time, primary_key=True)
    depart_airport = db.Column(db.String(20), db.ForeignKey("airport.name"), nullable=False)
    arrival_date = db.Column(db.Date, nullable=False)
    arrival_time = db.Column(db.Time, nullable=False)
    arrival_airport = db.Column(db.String(20), db.ForeignKey("airport.name"), nullable=False)
    airline = db.Column(db.String(20), db.ForeignKey("airline.name"), primary_key=True)
    base_price = db.Column(db.Integer, nullable=False)
    airplane_id = db.Column(db.String(5), db.ForeignKey("airplane.id"), nullable=False)
    status = db.Column(db.String(10), nullable=False)

class Customer(db.Model, UserMixin):
    email = db.Column(db.String(120), primary_key=True, unique=True)
    passwrod = db.Column(db.String(60), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    building = db.Column(db.String(20), nullable=False)
    street = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(20), nullable=False)
    state = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    passport_number = db.Column(db.String(20), nullable=False)
    passport_expire = db.Column(db.Date, nullable=False)
    passport_country = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)

class Ticket(db.Model):
    id = db.Column(db.String(12), primary_key=True)
    flight_num = db.Column(db.String(5), db.ForeignKey("flight.flight_num"), nullable=False)
    # flight_num = db.Column(db.String(5), primary_key=True)
    depart_date = db.Column(db.Date, db.ForeignKey("flight.depart_date"), nullable=False)
    # depart_date = db.Column(db.Date, primary_key=True)
    depart_time = db.Column(db.Time, db.ForeignKey("flight.depart_time"), nullable=False)
    # depart_time = db.Column(db.Time, primary_key=True)
    airline = db.Column(db.String(20), db.ForeignKey("flight.airline"), nullable=False)
    # airline = db.Column(db.String(20), db.ForeignKey("airline.name"), primary_key=True)
    customer_email = db.Column(db.String(120), db.ForeignKey("customer.email"), nullable=False)
    # email = db.Column(db.String(120), primary_key=True, unique=True)
    price = db.Column(db.Integer, nullable=False)
    card_type = db.Column(db.String(20), nullable=False)
    card_number = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    expire_date = db.Column(db.Date, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    purchase_time = db.Column(db.Time, nullable=False)

class Staff(db.Model, UserMixin):
    username = db.Column(db.String(20), primary_key=True)
    password = db.Column(db.String(60), nullable=False)
    first_name = db.Column(db.String(20), nullable=False)
    last_name = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    airline = db.Column(db.String(20), db.ForeignKey("airline.name"), nullable=False)

class Phone(db.Model):
    username = db.Column(db.String(20), db.ForeignKey("staff.username"), primary_key=True)
    number = db.Column(db.String(20), nullable=False, primary_key=True)

from app import routes