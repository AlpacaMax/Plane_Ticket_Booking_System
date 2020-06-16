import datetime
from flask import render_template, request, url_for, flash, redirect
from markupsafe import escape
from app.models import *
from app import app, db, bcrypt
from app.forms import FilterForm
from sqlalchemy.orm import aliased

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

    # form.validate()

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

    # form = FilterForm(request.args)

    depart_city = Airport.query.filter(Airport.name == depart_flight.depart_airport).first().city
    arrival_city = Airport.query.filter(Airport.name == depart_flight.arrival_airport).first().city

    return_depart_city = arrival_city
    return_arrival_city = depart_city

    # depart_airports = Airport.query.filter_by(city=return_depart_city).all()
    # arrival_airports = Airport.query.filter_by(city=return_arrival_city).all()

    # depart_airport_choices = [("any", "Any")] + [
    #     (airport.name, "%s/%s" % (airport.city, airport.name)) for airport in depart_airports
    # ]
    # arrival_airport_choices = [("any", "Any")] + [
    #     (airport.name, "%s/%s" % (airport.city, airport.name)) for airport in arrival_airports
    # ]

    # form.source_city_airport.choices = depart_airport_choices
    # form.dest_city_airport.choices = arrival_airport_choices

    all_airports_A = aliased(Airport)
    all_airports_B = aliased(Airport)

    flights = Flight.query.\
              join(all_airports_A, Flight.depart_airport==all_airports_A.name).\
              join(all_airports_B, Flight.arrival_airport==all_airports_B.name).\
              filter(all_airports_A.city == return_depart_city).\
              filter(all_airports_B.city == return_arrival_city).\
              filter(Flight.depart_datetime > depart_flight.arrival_datetime).all()

    # flights = filter_form_processor(form, flights)

    return render_template("return_trip_select.html", 
                           flights = flights, 
                           template_for_select = "select_for_return_trip.html",
                           depart_flight_num = depart_flight_num,
                           depart_datetime = depart_datetime,
                           depart_airline_name = depart_airline_name)

@app.route("/summary_of_trip", methods=["GET"])
def view_selected_flights():
    return request.args