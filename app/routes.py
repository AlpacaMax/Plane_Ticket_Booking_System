import hashlib
import datetime
from flask import render_template, request, url_for, flash, redirect
from markupsafe import escape
from app.models import *
from app import app, db, bcrypt
from app.forms import FilterForm, LoginForm, CustomerRegisterForm, StaffRegisterForm, PurchaseForm, CommentForm
from sqlalchemy.orm import aliased
from flask_login import login_user, current_user, logout_user, login_required

def filter_form_processor(form, flights):
    if (form.same_airports()):
        form.source_city_airport.data = "any"
        form.dest_city_airport.data = "any"
        flash(f"Cannot have same source airport and destination airport.")
    
    if (form.gonna_filter_date.data and not form.is_future_depart_date()):
        form.depart_date.data = None
        flash(f"Departure date must at least be today.")

    if (form.submit.data and not form.same_airports()):
        if (form.source_city_airport.data != "any"):
            flights = flights.filter(Flight.depart_airport==form.source_city_airport.data)
        if (form.dest_city_airport.data != "any"):
            flights = flights.filter(Flight.arrival_airport==form.source_city_airport.data)
        if (form.gonna_filter_date.data and form.depart_date.data is not None):
            depart_date = form.depart_date.data
            next_day = depart_date + datetime.timedelta(days=1)
            flights = flights.filter(Flight.depart_datetime >= depart_date)
            flights = flights.filter(Flight.depart_datetime < next_day)
    
    return flights
    

@app.route("/", methods=["GET"])
def home():
    form = FilterForm(request.args)

    airports = Airport.query.order_by(Airport.city).all()
    choices = [("any", "Any")]\
              + [(airport.name, "%s/%s" % (airport.city, airport.name)) 
                 for airport in airports]

    form.source_city_airport.choices = choices
    form.dest_city_airport.choices = choices

    flights = Flight.query.filter(
        Flight.depart_datetime >= datetime.datetime.today()
    ).order_by(Flight.depart_datetime)

    flights = filter_form_processor(form, flights)

    return render_template("home.html", 
                           flights=flights.all(), 
                           form=form,
                           template_for_select="select_for_home.html")

@app.route("/returnTrip", methods=["GET"])
def return_trip_choosing():
    depart_flight_num = escape(request.args.get("depart_flight_num"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    depart_airline_name = escape(request.args.get("depart_airline_name"))

    depart_flight = Flight.query.filter(
                        Flight.flight_num == depart_flight_num,
                        Flight.depart_datetime == depart_datetime,
                        Flight.airline_name == depart_airline_name
                    ).first()

    if (depart_flight is None):
        flash(f"Departure flight doesn't exist. Please choose an existing flight.")
        return redirect(url_for("home"))

    depart_city = Airport.query.filter(Airport.name == depart_flight.depart_airport).first().city
    arrival_city = Airport.query.filter(Airport.name == depart_flight.arrival_airport).first().city

    return_depart_city = arrival_city
    return_arrival_city = depart_city

    all_airports_A = aliased(Airport)
    all_airports_B = aliased(Airport)

    flights = Flight.query.\
              join(all_airports_A, Flight.depart_airport==all_airports_A.name).\
              join(all_airports_B, Flight.arrival_airport==all_airports_B.name).\
              filter(all_airports_A.city == return_depart_city).\
              filter(all_airports_B.city == return_arrival_city).\
              filter(Flight.depart_datetime > depart_flight.arrival_datetime).all()

    return render_template("return_trip_select.html", 
                           flights = flights, 
                           template_for_select = "select_for_return_trip.html",
                           depart_flight_num = depart_flight_num,
                           depart_datetime = depart_datetime,
                           depart_airline_name = depart_airline_name)

@app.route("/summary_of_trip", methods=["GET", "POST"])
def view_selected_flights():
    depart_airline_name = escape(request.args.get("depart_airline_name"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    depart_flight_num = escape(request.args.get("depart_flight_num"))

    depart_flight = Flight.query.filter(Flight.airline_name==depart_airline_name,
                                        Flight.depart_datetime==depart_datetime,
                                        Flight.flight_num==depart_flight_num).first()
    
    form = PurchaseForm()
    # form.depart_flight_num.data = depart_flight_num
    # form.depart_datetime.data = depart_datetime
    # form.depart_airline_name.data = depart_airline_name

    return_flight = None
    if ("return_airline_name" in request.args
        and "return_datetime" in request.args
        and "return_flight_num" in request.args):

        return_airline_name = escape(request.args.get("return_airline_name"))
        return_datetime = datetime.datetime.fromisoformat(request.args.get("return_datetime"))
        return_flight_num = escape(request.args.get("return_flight_num"))

        return_flight = Flight.query.filter(Flight.airline_name==return_airline_name,
                                            Flight.depart_datetime==return_datetime,
                                            Flight.flight_num==return_flight_num).first()

        if (return_flight is None):
            flash("Return flight doesn't exist! Please choose a different one")
            return redirect(url_for(
                "return_trip_choosing",
                depart_airline_name = depart_airline_name,
                depart_datetime = depart_datetime,
                depart_flight_num = depart_flight_num
            ))
    
    # form.return_flight_num.data = return_flight_num
    # form.return_datetime.data = return_datetime
    # form.return_airline_name.data = return_airline_name
    if (form.validate_on_submit()):
        if (not current_user.is_authenticated):
            flash("Please login first!")
            return redirect(url_for("login"))
        elif (current_user.get_user_type() == "Staff"):
            flash("Only customers are allowed to book tickets")
            return redirect(url_for("home"))
        
        depart_ticket_id = hashlib.md5(
            (depart_airline_name+str(depart_datetime)+depart_flight_num+current_user.get_id()).encode()
        ).hexdigest()

        depart_ticket = Ticket(
            id=depart_ticket_id,
            flight_num=depart_flight_num,
            depart_datetime=depart_datetime,
            airline_name=depart_airline_name,
            customer_email=current_user.get_id(),
            price=depart_flight.get_current_price(),
            card_type=form.card_type.data,
            card_number=form.card_number.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            expire_date=form.expire_date.data,
            purchase_datetime=datetime.datetime.now(),
            rating=None,
            comment=None
        )
        db.session.add(depart_ticket)
        
        if (return_flight):
            return_ticket_id = hashlib.md5(
                (return_airline_name+str(return_datetime)+return_flight_num+current_user.get_id()).encode()
            ).hexdigest()
            return_ticket = Ticket(
                id=return_ticket_id,
                flight_num=return_flight_num,
                depart_datetime=return_datetime,
                airline_name=return_airline_name,
                customer_email=current_user.get_id(),
                price=return_flight.get_current_price(),
                card_type=form.card_type.data,
                card_number=form.card_number.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                expire_date=form.expire_date.data,
                purchase_datetime=datetime.datetime.now(),
                rating=None,
                comment=None
            )
            db.session.add(return_ticket)
        
        db.session.commit()
        flash("Successfully purchased!")
        return redirect(url_for("customer_future_flights"))

    return render_template("customer_purchase.html",
                           depart_flight=depart_flight,
                           return_flight=return_flight,
                           form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    if (current_user.is_authenticated):
        return redirect(url_for("home"))
    form = LoginForm()

    if (form.validate_on_submit()):
        user = None
        
        if (escape(form.identity.data) == "staff"):
            user = Staff.query.filter_by(username=form.username.data).first()
        else:
            user = Customer.query.filter_by(email=form.username.data).first()
        
        if (user
            and hashlib.md5(form.password.data.encode()).hexdigest() == user.password):
            login_user(user, remember = form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash("Login Unsuccessful. Please check username and password")

    return render_template("login.html", form=form)

@app.route("/logout", methods=["GET"])
def logout():
    flash("You are logged out")
    logout_user()
    return redirect(url_for('home'))

@app.route("/customerRegister", methods=["GET", "POST"])
def customer_register():
    if (current_user.is_authenticated):
        return redirect(url_for("home"))

    form = CustomerRegisterForm()
    if (form.validate_on_submit()):
        hashed_password = hashlib.md5(form.password.data.encode()).hexdigest()
        customer = Customer(
            email = form.email.data,
            password = hashed_password,
            name = form.name.data,
            building = form.building.data,
            street = form.street.data,
            city = form.city.data,
            state = form.state.data,
            phone = form.phone.data,
            passport_number = form.passport_number.data,
            passport_expire = form.passport_expire.data,
            passport_country = form.passport_country.data,
            date_of_birth = form.date_of_birth.data
        )
        db.session.add(customer)
        db.session.commit()
        flash("Your account has been created! You are now able to log in")
        return redirect(url_for("login"))

    return render_template("customer_register.html", form=form)

@app.route("/staffRegister", methods=["GET", "POST"])
def staff_register():
    if (current_user.is_authenticated):
        return redirect(url_for("home"))
    
    form = StaffRegisterForm()
    if (form.validate_on_submit()):
        hashed_password = hashlib.md5(form.password.data.encode()).hexdigest()
        staff = Staff(
            username = form.username.data,
            password = hashed_password,
            first_name = form.first_name.data,
            last_name = form.last_name.data,
            date_of_birth = form.date_of_birth.data,
            airline_name = form.airline_name.data
        )
        phone = Phone(
            username = form.username.data,
            number = form.phone.data
        )
        db.session.add(staff)
        db.session.add(phone)
        db.session.commit()
        flash("Your account has been created! You are now able to log in")
        return redirect(url_for("login"))

    return render_template("staff_register.html", form=form)

@app.route("/customerFutureFlights", methods=["GET"])
@login_required
def customer_future_flights():
    if (current_user.get_user_type() == "Staff"):
        return redirect(url_for("staff_future_flights"))

    all_tickets = Ticket.query.filter(
        Ticket.customer_email==current_user.email,
        Ticket.depart_datetime > datetime.datetime.now()
    ).all()
    flights = [ticket.flight for ticket in all_tickets]

    return render_template("customer_future_flights.html", flights=flights)

@app.route("/customerPastFlights", methods=["GET"])
@login_required
def customer_past_flights():
    if (current_user.get_user_type() == "Staff"):
        return redirect(url_for("staff_past_flights"))

    all_tickets = Ticket.query.filter(
        Ticket.customer_email==current_user.email,
        Ticket.depart_datetime <= datetime.datetime.now()
    ).all()
    flights = [ticket.flight for ticket in all_tickets]

    return render_template("customer_past_flights.html", flights=flights)

@app.route("/staffFutureFlights", methods=["GET"])
@login_required
def staff_future_flights():
    if (current_user.get_user_type() == "Customer"):
        return redirect(url_for("customer_future_flights"))
        
    return "Staff Home"

@app.route("/staffPastFlights", methods=["GET"])
@login_required
def staff_past_flights():
    return "Staff Past Flights"

@app.route("/flightComment", methods=["GET", "POST"])
@login_required
def flight_comment():
    if (current_user.get_user_type() == "Staff"):
        flash("Please login as a customer to comment previous flights")
        return redirect(url_for("staff_future_flights"))

    form = CommentForm()
    airline_name = escape(request.args.get("airline_name"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    flight_num = escape(request.args.get("flight_num"))

    form.airline_name.data = airline_name
    form.depart_datetime.data = depart_datetime
    form.flight_num.data = flight_num

    ticket = Ticket.query.filter(
        Ticket.airline_name==airline_name,
        Ticket.depart_datetime==depart_datetime,
        Ticket.flight_num==flight_num,
        Ticket.customer_email==current_user.get_id()
    ).first()

    if (ticket is None):
        flash("You didn't took this flight before. Please comment a different one")
        return redirect(url_for("customer_past_flights"))

    if (form.validate_on_submit()):
        ticket.rating = int(form.rating.data)
        ticket.comment = form.comment.data
        db.session.add(ticket)
        db.session.commit()
        flash("Thank you for your rating and comment!")
        return redirect(url_for("customer_past_flights"))
    
    form.rating.data = ticket.rating
    form.comment.data = ticket.comment

    return render_template("customer_flight_comment.html", form=form, flight=ticket.flight)