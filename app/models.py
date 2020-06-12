import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    result = Staff.query.get(user_id)
    if (result is None):
        return Customer.query.get(user_id)
    else:
        return result

class Airline(db.Model):
    name = db.Column(db.String(20), primary_key=True)
    airplanes = db.relationship("Airplane", backref="airline", lazy=True)
    staffs = db.relationship("Staff", backref="airline", lazy=True)

class Airport(db.Model):
    name = db.Column(db.String(20),
                     primary_key=True)

    city = db.Column(db.String(20),
                     nullable=False)

    departing_flights = db.relationship("Flight",
                                        lazy=True,
                                        primaryjoin="Airport.name==Flight.depart_airport")

    arriving_flights = db.relationship("Flight",
                                       lazy=True,
                                       primaryjoin="Airport.name==Flight.arrival_airport")

class Airplane(db.Model):
    id = db.Column(db.String(5),
                   primary_key=True)

    airline_name = db.Column(db.String(20), 
                             db.ForeignKey("airline.name"), 
                             primary_key=True)

    num_seat = db.Column(db.Integer, 
                         nullable=False)

    flights = db.relationship("Flight", 
                              backref="airplane", 
                              lazy=True, 
                              primaryjoin='''and_(Airplane.id==Flight.airplane_id, 
                                            Airplane.airline_name==Flight.airline_name)''')

class Flight(db.Model):
    flight_num = db.Column(db.String(5), 
                           primary_key=True)

    depart_datetime = db.Column(db.DateTime, 
                                primary_key=True)

    airline_name = db.Column(db.String(20), 
                             db.ForeignKey("airplane.airline_name"), 
                             primary_key=True)

    depart_airport = db.Column(db.String(20), 
                               db.ForeignKey("airport.name"), 
                               nullable=False)

    arrival_datetime = db.Column(db.DateTime, 
                                 nullable=False)

    arrival_airport = db.Column(db.String(20), 
                                db.ForeignKey("airport.name"), 
                                nullable=False)

    base_price = db.Column(db.Integer, 
                           nullable=False)

    airplane_id = db.Column(db.String(5), 
                            db.ForeignKey("airplane.id"), 
                            nullable=False)

    status = db.Column(db.String(10), 
                       nullable=False)

    tickets = db.relationship("Ticket", 
                              backref="flight", 
                              lazy=True,
                              primaryjoin='''and_(Flight.flight_num==Ticket.flight_num,
                                            Flight.depart_datetime==Ticket.depart_datetime,
                                            Flight.airline_name==Ticket.airline_name)''')

class Customer(db.Model, UserMixin):
    email = db.Column(db.String(120), 
                      primary_key=True)

    password = db.Column(db.String(60), 
                         nullable=False)

    name = db.Column(db.String(100), 
                     nullable=False)

    building = db.Column(db.String(20), 
                         nullable=False)

    street = db.Column(db.String(20), 
                       nullable=False)

    city = db.Column(db.String(20), 
                     nullable=False)

    state = db.Column(db.String(20), 
                      nullable=False)

    phone = db.Column(db.String(20), 
                      nullable=False)

    passport_number = db.Column(db.String(20),
                                nullable=False)

    passport_expire = db.Column(db.Date, 
                                nullable=False)

    passport_country = db.Column(db.String(20), 
                                 nullable=False)

    date_of_birth = db.Column(db.Date, 
                              nullable=False)

    tickets = db.relationship("Ticket", 
                              backref="customer", 
                              lazy=True)

class Ticket(db.Model):
    id = db.Column(db.String(12),
                   primary_key=True)

    flight_num = db.Column(db.String(5), 
                           db.ForeignKey("flight.flight_num"), 
                           nullable=False)

    depart_datetime = db.Column(db.DateTime, 
                                db.ForeignKey("flight.depart_datetime"), 
                                nullable=False)

    airline_name = db.Column(db.String(20), 
                             db.ForeignKey("flight.airline_name"), 
                             nullable=False)

    customer_email = db.Column(db.String(120), 
                               db.ForeignKey("customer.email"), 
                               nullable=False)

    price = db.Column(db.Integer, 
                      nullable=False)

    card_type = db.Column(db.String(20),
                          nullable=False)

    card_number = db.Column(db.String(20), 
                            nullable=False)

    first_name = db.Column(db.String(20), 
                           nullable=False)

    last_name = db.Column(db.String(20), 
                          nullable=False)

    expire_date = db.Column(db.Date, 
                            nullable=False)

    purchase_datetime = db.Column(db.DateTime, 
                                  nullable=False)

class Staff(db.Model, UserMixin):
    username = db.Column(db.String(20), 
                         primary_key=True)

    password = db.Column(db.String(60), 
                         nullable=False)

    first_name = db.Column(db.String(20), 
                           nullable=False)

    last_name = db.Column(db.String(20), 
                          nullable=False)

    date_of_birth = db.Column(db.Date, 
                              nullable=False)

    airline_name = db.Column(db.String(20), 
                             db.ForeignKey("airline.name"), 
                             nullable=False)

    phones = db.relationship("Phone", 
                             backref="staff", 
                             lazy=True)

class Phone(db.Model):
    username = db.Column(db.String(20), 
                         db.ForeignKey("staff.username"), 
                         primary_key=True)

    number = db.Column(db.String(20), 
                       primary_key=True)

