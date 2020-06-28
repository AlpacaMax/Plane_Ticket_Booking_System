import hashlib
import copy
import datetime
from flask import render_template, request, url_for, flash, redirect
from markupsafe import escape
from app.models import *
from app import app, db, bcrypt
from app.forms import FilterForm, LoginForm, CustomerRegisterForm, StaffRegisterForm, PurchaseForm, CommentForm, DateFilterForm, CreateFlightForm, to_datetime, AddAirplaneForm, AddAirportForm, AddPhoneNumberForm, ChangeStatusForm, StaffFlightFilterForm
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
            flights = flights.filter(Flight.arrival_airport==form.dest_city_airport.data)
        if (form.gonna_filter_date.data and form.depart_date.data is not None):
            depart_date = form.depart_date.data
            next_day = depart_date + datetime.timedelta(days=1)
            flights = flights.filter(Flight.depart_datetime >= depart_date)
            flights = flights.filter(Flight.depart_datetime < next_day)
    
    return flights

def date_to_datetime(a_date):
    return datetime.datetime(a_date.year, a_date.month, a_date.day)

@app.route("/", methods=["GET", "POST"])
def home():
    form = FilterForm()

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

@app.route("/returnTrip", methods=["GET", "POST"])
def return_trip_choosing():
    if (current_user.is_authenticated and current_user.get_user_type() == "Staff"):
        flash("You are not allowed to purchase flights")
        return redirect(url_for("home"))

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
    elif (depart_flight.get_num_tickets() == depart_flight.airplane.num_seat):
        flash(f"This flight is full. Please choose a different flight.")
        return redirect(url_for("home"))
    elif (depart_datetime < datetime.datetime.now()):
        flash(f"This flight has departed. Please choose a different flight.")
        return redirect(url_for("home"))
    
    if (current_user.is_authenticated):
        ticket = Ticket.query.filter(Ticket.flight_num==depart_flight_num,
                                    Ticket.depart_datetime==depart_datetime,
                                    Ticket.airline_name==depart_airline_name,
                                    Ticket.customer_email==current_user.email).first()

        if (ticket):
            flash("You've already booked this flight. Choose a different one.")
            return redirect(url_for("home"))

    depart_city = Airport.query.filter(Airport.name == depart_flight.depart_airport).first().city
    arrival_city = Airport.query.filter(Airport.name == depart_flight.arrival_airport).first().city

    return_depart_city = arrival_city
    return_arrival_city = depart_city

    form = FilterForm()

    airports = Airport.query.order_by(Airport.city).all()
    choices = [("any", "Any")]\
              + [(airport.name, "%s/%s" % (airport.city, airport.name))
                 for airport in airports]

    form.source_city_airport.choices = choices
    form.dest_city_airport.choices = choices

    all_airports_A = aliased(Airport)
    all_airports_B = aliased(Airport)

    flights = Flight.query.\
              join(all_airports_A, Flight.depart_airport==all_airports_A.name).\
              join(all_airports_B, Flight.arrival_airport==all_airports_B.name).\
              filter(all_airports_A.city == return_depart_city).\
              filter(all_airports_B.city == return_arrival_city).\
              filter(Flight.depart_datetime > depart_flight.arrival_datetime)

    flights = filter_form_processor(form, flights).order_by(Flight.depart_datetime)

    return render_template("return_trip_select.html",
                           form=form,
                           flights = flights.all(),
                           template_for_select = "select_for_return_trip.html",
                           depart_flight_num = depart_flight_num,
                           depart_datetime = depart_datetime,
                           depart_airline_name = depart_airline_name)

@app.route("/summary_of_trip", methods=["GET", "POST"])
def view_selected_flights():
    if (current_user.is_authenticated and current_user.get_user_type() == "Staff"):
        flash("You are not allowed to purchase flights")
        return redirect(url_for("home"))
        
    depart_airline_name = escape(request.args.get("depart_airline_name"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    depart_flight_num = escape(request.args.get("depart_flight_num"))

    depart_flight = Flight.query.filter(Flight.airline_name==depart_airline_name,
                                        Flight.depart_datetime==depart_datetime,
                                        Flight.flight_num==depart_flight_num).first()

    if (depart_flight is None):
        flash("Departure flight doesn't exist. Please choose an existing flight.")
        return redirect(url_for("home"))
    elif (depart_flight.get_num_tickets() == depart_flight.airplane.num_seat):
        flash(f"This flight is full. Please choose a different flight.")
        return redirect(url_for("home"))
    elif (depart_datetime < datetime.datetime.now()):
        flash(f"This flight has departed. Please choose a different flight.")
        return redirect(url_for("home"))

    if (current_user.is_authenticated):
        ticket = Ticket.query.filter(Ticket.flight_num==depart_flight_num,
                                    Ticket.depart_datetime==depart_datetime,
                                    Ticket.airline_name==depart_airline_name,
                                    Ticket.customer_email==current_user.email).first()

        if (ticket):
            flash("You've already booked this flight. Choose a different one.")
            return redirect(url_for("home"))
    
    form = PurchaseForm()

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
            flash("Return flight doesn't exist! Please choose an existing flight.")
            return redirect(url_for(
                "return_trip_choosing",
                depart_airline_name = depart_airline_name,
                depart_datetime = depart_datetime,
                depart_flight_num = depart_flight_num
            ))
        elif (return_flight.get_num_tickets() == return_flight.airplane.num_seat):
            flash(f"This flight is full. Please choose a different flight.")
            return redirect(url_for(
                "return_trip_choosing",
                depart_airline_name = depart_airline_name,
                depart_datetime = depart_datetime,
                depart_flight_num = depart_flight_num
            ))
        
        if (current_user.is_authenticated):
            ticket = Ticket.query.filter(Ticket.flight_num==return_flight_num,
                                        Ticket.depart_datetime==return_datetime,
                                        Ticket.airline_name==return_airline_name,
                                        Ticket.customer_email==current_user.email).first()

            if (ticket):
                flash("You've already booked this flight. Choose a different one.")
                return redirect(url_for(
                    "return_trip_choosing",
                    depart_airline_name = depart_airline_name,
                    depart_datetime = depart_datetime,
                    depart_flight_num = depart_flight_num
                ))
    
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
    ).order_by(Ticket.depart_datetime).all()
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

@app.route("/spending", methods=["GET", "POST"])
@login_required
def spending_track():
    if (current_user.get_user_type() == "Staff"):
        flash("Please login as a customer to track your spendings")
        return redirect(url_for("home"))
    
    form = DateFilterForm()

    has_range = False
    if (form.validate_on_submit()):
        has_range = True
        start_datetime = date_to_datetime(form.start_date.data)
        end_datetime = date_to_datetime(form.end_date.data)
    
    if (has_range):
        tickets_year = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
                                           Ticket.purchase_datetime>=start_datetime,
                                           Ticket.purchase_datetime<=end_datetime).all()
    else:
        tickets_year = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
        Ticket.purchase_datetime>=datetime.datetime(datetime.datetime.now().year,1,1)).all()

    past_year_spending = sum([ticket.price for ticket in tickets_year])

    if (has_range):
        first_month = (start_datetime.year, start_datetime.month)
        end_month = (end_datetime.year, end_datetime.month)
        month = first_month
        months = [month]
        while (month != end_month):
            next_month = month[1] + 1
            year = month[0]
            if (next_month > 12):
                next_month = 1
                year += 1
            month = (year, next_month)
            months.append(month)
    else:
        today = datetime.datetime.today()
        month = (today.year, today.month)
        months = [month]
        for i in range(5):
            last_month = month[1] - 1
            year = month[0]
            if (last_month < 1):
                last_month += 12
                year -= 1
            
            month = (year, last_month)
            months.append(month)

        months.reverse()

    month_labels = [month[1] for month in months]

    if (has_range):
        first_month_end = datetime.datetime(start_datetime.year, start_datetime.month, 1)
        first_month_end += datetime.timedelta(days=31)
        first_month_end -= datetime.timedelta(days=first_month_end.day - 1)
        tickets_first_month = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
                                                  Ticket.purchase_datetime<first_month_end,
                                                  Ticket.purchase_datetime>=start_datetime).all()
        first_month_spending = sum([ticket.price for ticket in tickets_first_month])

        month_spendings = [first_month_spending]
        for i in range(1, len(months) - 1):
            month_start = datetime.datetime(months[i][0], months[i][1], 1)
            month_end = month_start + datetime.timedelta(days=31)
            month_end -= datetime.timedelta(days=month_end.day - 1)
            tickets_month = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
                Ticket.purchase_datetime<month_end,
                Ticket.purchase_datetime>=month_start).all()
            month_spending = sum([ticket.price for ticket in tickets_month])
            month_spendings.append(month_spending)

        last_month_start = datetime.datetime(end_datetime.year, end_datetime.month, 1)
        tickets_last_month = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
                                                 Ticket.purchase_datetime<=end_datetime,
                                                 Ticket.purchase_datetime>=last_month_start).all()
        last_month_spending = sum([ticket.price for ticket in tickets_last_month])
        month_spendings.append(last_month_spending)
    else:
        month_spendings = []
        for a_month in months:
            month_start = datetime.datetime(a_month[0], a_month[1], 1)
            month_end = month_start + datetime.timedelta(days=31)
            month_end -= datetime.timedelta(days=month_end.day - 1)
            tickets_month = Ticket.query.filter(Ticket.customer_email==current_user.get_id(),
                Ticket.purchase_datetime<month_end,
                Ticket.purchase_datetime>=month_start).all()
            month_spending = sum([ticket.price for ticket in tickets_month])
            month_spendings.append(month_spending)

    return render_template("customer_spend_track.html",
                           has_range=has_range,
                           form=form,
                           past_year_spending=past_year_spending,
                           month_labels=month_labels,
                           month_spendings=month_spendings)

@app.route("/staffFlights", methods=["GET", "POST"])
@login_required
def staff_flights():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot see these flights!")
        return redirect(url_for("home"))

    form = StaffFlightFilterForm()
    form.create_choices()

    if (form.validate_on_submit()):
        flights = Flight.query.filter(Flight.airline_name==current_user.airline_name)
        
        if (form.source_city_airport.data != "any"):
            flights = flights.filter(Flight.depart_airport==form.source_city_airport.data)
        if (form.dest_city_airport.data != "any"):
            flights = flights.filter(Flight.arrival_airport==form.dest_city_airport.data)
        
        if (form.gonna_filter_date.data and form.start_date.data and form.end_date.data):
            flights = flights.filter(Flight.depart_datetime>=to_datetime(form.start_date.data),
                                     Flight.depart_datetime<=to_datetime(form.end_date.data))
        
    else:
        flights = Flight.query.filter(Flight.airline_name==current_user.airline_name,
                                      Flight.depart_datetime>=datetime.datetime.today(),
                                      Flight.depart_datetime<=datetime.datetime.today() + datetime.timedelta(days=30))

    return render_template("staff_flights.html", form=form, flights=flights.all())

@app.route("/createFlight", methods=["GET", "POST"])
@login_required
def create_flight():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot create flights!")
        return redirect(url_for("home"))
    
    form = CreateFlightForm()
    form.airline_name.data = current_user.airline_name
    form.create_airplane_choices(current_user.airline_name)

    if (form.validate_on_submit()):
        new_flight = Flight(
            flight_num = form.flight_num.data,
            depart_datetime = to_datetime(str(form.depart_date.data), form.depart_time.data),
            airline_name = current_user.airline_name,
            depart_airport = form.depart_airport.data,
            arrival_datetime = to_datetime(str(form.arrival_date.data), form.arrival_time.data),
            arrival_airport = form.arrival_airport.data,
            base_price = form.base_price.data,
            airplane_id = form.airplane_id.data,
            status = "On-time"
        )
        db.session.add(new_flight)
        db.session.commit()
        flash("Flight added!")

    return render_template("create_flight.html", form=form)

@app.route("/createAirplane", methods=["GET", "POST"])
@login_required
def create_airplane():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot add airplanes!")
        return redirect(url_for("home"))
    
    form = AddAirplaneForm()
    form.airline_name.data = current_user.airline_name

    if (form.validate_on_submit()):
        airplane = Airplane(
            id = form.id.data,
            airline_name = current_user.airline_name,
            num_seat = form.num_seat.data
        )
        db.session.add(airplane)
        db.session.commit()
        flash("Airplane added!")

    return render_template("create_airplane.html", form=form)

@app.route("/addAirport", methods=["GET", "POST"])
@login_required
def add_airport():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot add airport!")
        return redirect(url_for("home"))
    
    form = AddAirportForm()

    if (form.validate_on_submit()):
        airport = Airport(
            name = form.name.data,
            city = form.city.data
        )
        db.session.add(airport)
        db.session.commit()
        flash("Airport added!")

    return render_template("add_airport.html", form=form)

@app.route("/addPhoneNumber", methods=["GET", "POST"])
@login_required
def add_phone_number():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot add phone number")
        return redirect(url_for("home"))
    
    form = AddPhoneNumberForm()
    form.username.data = current_user.username

    if (form.validate_on_submit()):
        phone = Phone(
            username = current_user.username,
            number = form.number.data
        )
        db.session.add(phone)
        db.session.commit()
        flash("Phone number added!")

    return render_template("add_phone_number.html", form=form)

@app.route("/quarterlyRevenue", methods=["GET"])
@login_required
def quarterly_revenue_earned():
    if (current_user.get_user_type() == "Customer"):
        flash("You are not allowed to see quarterly revenue earned")
        return redirect(url_for("home"))
    
    last_year = datetime.datetime.today().year - 1

    first_day = datetime.datetime(last_year, 1, 1)
    first_quarter = datetime.datetime(last_year, 4, 1)
    second_quarter = datetime.datetime(last_year, 7, 1)
    third_quarter = datetime.datetime(last_year, 10, 1)
    fourth_quarter = datetime.datetime(last_year+1, 1, 1)
    
    first_quarter_tickets = Ticket.query.filter(
        Ticket.airline_name == current_user.airline_name,
        Ticket.purchase_datetime >= first_day,
        Ticket.purchase_datetime < first_quarter
    ).all()
    second_quarter_tickets = Ticket.query.filter(
        Ticket.airline_name == current_user.airline_name,
        Ticket.purchase_datetime >= first_quarter,
        Ticket.purchase_datetime < second_quarter
    ).all()
    third_quarter_tickets = Ticket.query.filter(
        Ticket.airline_name == current_user.airline_name,
        Ticket.purchase_datetime >= second_quarter,
        Ticket.purchase_datetime < third_quarter
    ).all()
    fourth_quarter_tickets = Ticket.query.filter(
        Ticket.airline_name == current_user.airline_name,
        Ticket.purchase_datetime >= third_quarter,
        Ticket.purchase_datetime < fourth_quarter
    ).all()

    first_quarter_revenue = sum([ticket.price for ticket in first_quarter_tickets])
    second_quarter_revenue = sum([ticket.price for ticket in second_quarter_tickets])
    third_quarter_revenue = sum([ticket.price for ticket in third_quarter_tickets])
    fourth_quarter_revenue = sum([ticket.price for ticket in fourth_quarter_tickets])

    return render_template("quarterly_revenue_earned.html",
                           year=last_year,
                           data=[first_quarter_revenue,
                                 second_quarter_revenue,
                                 third_quarter_revenue,
                                 fourth_quarter_revenue])

@app.route("/topDests", methods=["GET"])
@login_required
def top_destinations():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view top destinations")
        return redirect(url_for("home"))
    
    cities = {airport.city : 0 for airport in Airport.query.all()}
    three_months_tickets = Ticket.query.filter(Ticket.purchase_datetime>datetime.datetime.today()-datetime.timedelta(days=90)).all()
    for ticket in three_months_tickets:
        arrival_city = Airport.query.get(ticket.flight.arrival_airport).city
        cities[arrival_city] += 1
    
    three_months_top_dest = sorted(cities, key=cities.__getitem__, reverse=True)[:3]

    cities = {airport.city : 0 for airport in Airport.query.all()}
    last_year = datetime.datetime.today().year - 1
    last_year_tickets = Ticket.query.filter(
        Ticket.purchase_datetime >= datetime.datetime(last_year,1,1),
        Ticket.purchase_datetime <= datetime.datetime(last_year,12,31)
    ).all()

    for ticket in last_year_tickets:
        arrival_city = Airport.query.get(ticket.flight.arrival_airport).city
        cities[arrival_city] += 1
    
    last_year_top_dest = sorted(cities, key=cities.__getitem__, reverse=True)[:3]

    return render_template("top_dests.html",
                           three_months_top_dest=three_months_top_dest,
                           last_year_top_dest=last_year_top_dest)

@app.route("/allCustomers", methods=["GET"])
@login_required
def all_customers():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view all customers")
        return redirect(url_for("home"))

    last_year = datetime.datetime.today().year - 1
    last_year_start = datetime.datetime(last_year, 1, 1)
    this_year_start = datetime.datetime(last_year+1, 1, 1)

    query = '''select customer.email
               from customer
               order by (select count(ticket.id)
                         from ticket
                         where ticket.airline_name="{}"
                         and ticket.purchase_datetime >= "{}"
                         and ticket.purchase_datetime < "{}"
                         and ticket.customer_email=customer.email
                         group by ticket.customer_email) desc'''.format(current_user.airline_name,
                                                                        str(last_year_start),
                                                                        str(this_year_start))

    result = db.session.execute(query)

    return render_template("all_customers.html", result=result)

@app.route("/viewCustomer", methods=["GET"])
@login_required
def view_customer():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view this customer")
        return redirect(url_for("home"))

    email = request.args.get("email")
    tickets = Ticket.query.filter(Ticket.customer_email==email,
                                  Ticket.airline_name==current_user.airline_name,
                                  Ticket.depart_datetime<datetime.datetime.now())
    flights = [ticket.flight for ticket in tickets]
    
    return render_template("view_customer.html", email=email, flights=flights)

@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view report")
        return redirect(url_for("home"))

    form = DateFilterForm()

    if (form.validate_on_submit()):
        start_datetime = date_to_datetime(form.start_date.data)
        end_datetime = date_to_datetime(form.end_date.data)
    elif (request.args.get("last_month")):
        this_year = datetime.datetime.today().year
        this_month = datetime.datetime.today().month
        start_year = this_year
        start_month = this_month - 1
        if (start_month < 1):
            start_year -= 1
            start_month = 12
        
        start_datetime = datetime.datetime(start_year, start_month, 1)
        end_datetime = datetime.datetime(this_year, this_month, 1) - datetime.timedelta(seconds=1)
    else:
        last_year = datetime.datetime.today().year - 1
        start_datetime = datetime.datetime(last_year, 1, 1)
        end_datetime = datetime.datetime(last_year + 1, 1, 1) - datetime.timedelta(seconds=1)

    tickets_year = Ticket.query.filter(Ticket.airline_name==current_user.airline_name,
                                       Ticket.purchase_datetime>=start_datetime,
                                       Ticket.purchase_datetime<end_datetime).all()

    total_sold = len(tickets_year)

    first_month = (start_datetime.year, start_datetime.month)
    end_month = (end_datetime.year, end_datetime.month)
    month = first_month
    months = [month]
    while (month != end_month):
        next_month = month[1] + 1
        year = month[0]
        if (next_month > 12):
            next_month = 1
            year += 1
        month = (year, next_month)
        months.append(month)
    
    month_labels = months

    first_month_end = datetime.datetime(start_datetime.year, start_datetime.month, 1)
    first_month_end += datetime.timedelta(days=31)
    first_month_end -= datetime.timedelta(days=first_month_end.day - 1)
    tickets_first_month = Ticket.query.filter(Ticket.airline_name==current_user.airline_name,
                                              Ticket.purchase_datetime<first_month_end,
                                              Ticket.purchase_datetime>=start_datetime).all()
    first_month_spending = len(tickets_first_month)

    month_spendings = [first_month_spending]
    for i in range(1, len(months) - 1):
        month_start = datetime.datetime(months[i][0], months[i][1], 1)
        month_end = month_start + datetime.timedelta(days=31)
        month_end -= datetime.timedelta(days=month_end.day - 1)
        tickets_month = Ticket.query.filter(Ticket.airline_name==current_user.airline_name,
                                            Ticket.purchase_datetime<month_end,
                                            Ticket.purchase_datetime>=month_start).all()
        month_spending = len(tickets_month)
        month_spendings.append(month_spending)

    last_month_start = datetime.datetime(end_datetime.year, end_datetime.month, 1)
    tickets_last_month = Ticket.query.filter(Ticket.airline_name==current_user.airline_name,
                                             Ticket.purchase_datetime<=end_datetime,
                                             Ticket.purchase_datetime>=last_month_start).all()
    last_month_spending = len(tickets_last_month)
    month_spendings.append(last_month_spending)

    return render_template("report.html",
                           form=form,
                           total_sold=total_sold,
                           month_labels=month_labels,
                           month_spendings=month_spendings)

@app.route("/changeStatus", methods=["GET", "POST"])
@login_required
def change_status():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view report")
        return redirect(url_for("home"))

    form = ChangeStatusForm()

    flight_num = escape(request.args.get("flight_num"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    airline_name = current_user.airline_name

    flight = Flight.query.filter(
        Flight.flight_num==flight_num,
        Flight.depart_datetime==depart_datetime,
        Flight.airline_name==airline_name
    ).first()

    if (flight is None):
            flash("Flight doesn't exist. Please choose a different one!")
            return redirect(url_for("staff_flights"))

    if (form.validate_on_submit()):
        flight.status = form.status.data
        db.session.add(flight)
        db.session.commit()

        flash("Successfully changed the status")
        return redirect(url_for("staff_flights"))
    
    form.status.data = flight.status
    
    return render_template("change_status.html", form=form)

@app.route("/viewComments", methods=["GET", "POST"])
@login_required
def view_comments():
    if (current_user.get_user_type() == "Customer"):
        flash("You cannot view all comments")
        return redirect(url_for("home"))

    flight_num = escape(request.args.get("flight_num"))
    depart_datetime = datetime.datetime.fromisoformat(request.args.get("depart_datetime"))
    airline_name = current_user.airline_name

    flight = Flight.query.filter(Flight.flight_num == flight_num,
                                 Flight.depart_datetime == depart_datetime,
                                 Flight.airline_name == airline_name).first()

    if (flight is None):
        flash("Flight doesn't exist. Please choose a different flight")
        return redirect(url_for("staff_flights"))

    all_ratings = [ticket.rating for ticket in flight.tickets if ticket.rating != None]
    avg_rating = sum(all_ratings)/len(all_ratings) if len(all_ratings) > 0 else 5.0

    return render_template("view_comment.html", flight=flight, avg_rating=avg_rating)