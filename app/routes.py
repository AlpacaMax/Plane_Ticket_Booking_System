import hashlib
import copy
import datetime
from flask import render_template, request, url_for, flash, redirect
from markupsafe import escape
from app.models import *
from app import app, db, bcrypt
from app.forms import FilterForm, LoginForm, CustomerRegisterForm, StaffRegisterForm, PurchaseForm, CommentForm, DateFilterForm, CreateFlightForm, to_datetime, AddAirplaneForm, AddAirportForm, AddPhoneNumberForm
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

def date_to_datetime(a_date):
    return datetime.datetime(a_date.year, a_date.month, a_date.day)

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
        month_spendings = []
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

@app.route("/staffFlights", methods=["GET"])
@login_required
def staff_flights():
    return render_template("staff_flights.html")

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