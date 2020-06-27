import datetime
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, BooleanField, StringField, PasswordField, HiddenField, TextAreaField, IntegerField, DateTimeField
from wtforms.validators import DataRequired, ValidationError, Length, EqualTo, Email, NumberRange, Regexp
from app.models import Customer, Staff, Airline, Airport, Airplane, Flight, Phone

def diff_data(another_field):
    def _diff_data(form, field):
        if (field.data and field.data==another_field.data):
            message = "Cannot have the same source airport and destination airport."
            raise ValidationError(message)
    
    return _diff_data

def GreaterEqualToToday(value, message, enabled=True):
    def _GreaterEqualToToday(form, field):
        if (enabled and field.data is not None and field.data < value):
            raise ValidationError(message)
    
    return _GreaterEqualToToday

def to_datetime(date, time):
    return datetime.datetime.fromisoformat(date + ' ' + time)

class FilterForm(FlaskForm):
    source_city_airport = SelectField("Source city/Airport",
                                      validators=[DataRequired()])
    dest_city_airport = SelectField("Destination city/Airport",
                                    validators=[DataRequired()])
    gonna_filter_date = BooleanField("Select a date")
    depart_date = DateField("Departure Date")
    submit = SubmitField("Filter")

    def same_airports(self):
        if (self.source_city_airport.data == self.dest_city_airport.data
            and self.source_city_airport.data != "any"
            and self.source_city_airport.data is not None):
            return True
        else:
            return False
    
    def is_future_depart_date(self):
        if (self.depart_date is not None
            and self.depart_date.data < datetime.datetime.today().date()):
            return False
        else:
            return True

class LoginForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    identity = SelectField("Sign in as ",
                           choices=[
                               ("customer", "Customer"),
                               ("staff", "Staff")
                           ])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")

class RegisterForm(FlaskForm):
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
                                     validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Sign Up")

class CustomerRegisterForm(FlaskForm):
    email = StringField("Email",
                        validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
                                     validators=[DataRequired(), EqualTo("password")])
    name = StringField("Name",
                       validators=[DataRequired()])
    building = StringField("Building",
                           validators=[DataRequired()])
    street = StringField("Street",
                         validators=[DataRequired()])
    city = StringField("City",
                       validators=[DataRequired()])
    state = StringField("State",
                        validators=[DataRequired()])
    phone = StringField("Phone",
                        validators=[DataRequired()])
    passport_number = StringField("Number",
                                  validators=[DataRequired()])
    passport_expire = DateField("Expire Date",
                                  validators=[DataRequired()])
    passport_country = StringField("Country",
                                  validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth",
                                  validators=[DataRequired()])
    submit = SubmitField("Sign Up")
    
    def validate_email(self, email):
        customer = Customer.query.filter_by(email=email.data).first()
        if (customer):
            raise ValidationError("That email is taken. Please choose a different one.")

class StaffRegisterForm(FlaskForm):
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm Password",
                                     validators=[DataRequired(), EqualTo("password")])
    first_name = StringField("First name",
                             validators=[DataRequired()])
    last_name = StringField("Last name",
                             validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth",
                              validators=[DataRequired()])
    airline_name = SelectField("Airline name", choices=[
        (airline.name, airline.name) for airline in Airline.query.all()
    ])
    phone = StringField("Phone",
                        validators=[DataRequired(),
                                    Regexp('[0-9]',
                                           message="Only digits are allowed")])
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        staff = Staff.query.filter_by(username=self.username.data).first()
        if (staff):
            raise ValidationError("That username is taken. Please choose another one")

class PurchaseForm(FlaskForm):
    # depart_flight_num = HiddenField()
    # depart_datetime = HiddenField()
    # depart_airline_name = HiddenField()
    # return_flight_num = HiddenField()
    # return_datetime = HiddenField()
    # return_airline_name = HiddenField()
    card_type = SelectField("Card Type", 
                            choices=[("Credit", "Credit Card"), ("Debit", "Debit Card")])
    card_number = StringField("Card Number",
                              validators=[DataRequired(), 
                                          Length(16,16,"Please enter a valid card number"),
                                          Regexp('[0-9]',
                                                message="Please enter a valid card number")])
    cvv = StringField("CVV",
                      validators=[DataRequired(),
                                  Length(3,3,"Please enter a valid cvv code"),
                                  Regexp('[0-9]',
                                         message="Please enter a valid cvv code")])
    first_name = StringField("First Name",
                             validators=[DataRequired()])
    last_name = StringField("Last Name",
                            validators=[DataRequired()])
    expire_date = DateField("Expire Date",
                            validators=[DataRequired()])
    submit = SubmitField("Buy")

class CommentForm(FlaskForm):
    flight_num = HiddenField()
    depart_datetime = HiddenField()
    airline_name = HiddenField()
    rating = SelectField("Rating",
                         choices=[
                             ('5','5'),
                             ('4','4'),
                             ('3','3'),
                             ('2','2'),
                             ('1','1')
                         ],
                         validators=[DataRequired()])
    comment = TextAreaField("Comment")
    submit = SubmitField("Submit")

class DateFilterForm(FlaskForm):
    start_date = DateField("From", validators=[DataRequired()])
    end_date = DateField("To", validators=[DataRequired()])
    submit = SubmitField("Filter")

    def validate_end_date(self, end_date):
        if (end_date.data < self.start_date.data):
            raise ValidationError("Please choose a date later than start date")

class CreateFlightForm(FlaskForm):
    airline_name = HiddenField()
    flight_num = StringField("Flignt Number",
                             validators=[DataRequired(), Length(3,5)])
    depart_date = DateField("Depart Date", validators=[DataRequired()])
    depart_time = StringField("Depart Time", validators=[DataRequired()])
    depart_airport = SelectField("Depart Airport",
                choices=[(airport.name, airport.name) for airport in Airport.query.all()])
    arrival_date = DateField("Arrival Date", validators=[DataRequired()])
    arrival_time = StringField("Arrival Time", validators=[DataRequired()])
    arrival_airport = SelectField("Arrival Airport",
                choices=[(airport.name, airport.name) for airport in Airport.query.all()])
    base_price = IntegerField("Base Price", validators=[DataRequired()])
    airplane_id = SelectField("Airplane")
    submit = SubmitField("Create")

    def create_airplane_choices(self, airline_name):
        self.airplane_id.choices = [
            (airplane.id, airplane.id) for airplane in Airplane.query.filter_by(airline_name=airline_name).all()
        ]

    def validate_flight_num(self, flight_num):
        depart_datetime = to_datetime(str(self.depart_date.data), self.depart_time.data)
        print(depart_datetime)
        flight = Flight.query.filter(Flight.flight_num==flight_num.data,
                                     Flight.depart_datetime==depart_datetime,
                                     Flight.airline_name==self.airline_name.data).first()
        if (flight):
            raise ValidationError("Flight exists! Please create a different one")
    
    def validate_depart_date(self, depart_date):
        if (depart_date.data <= datetime.date.today()):
            raise ValidationError("Please choose a future depart datetime")
    
    def validate_arrival_date(self, arrival_date):
        depart_datetime = to_datetime(str(self.depart_date.data), self.depart_time.data)
        arrival_datetime = to_datetime(str(self.arrival_date.data), self.arrival_time.data)
        if (arrival_datetime <= depart_datetime):
            raise ValidationError("Please choose an arrival datetime that is later than depart datetime")
    
    def validate_arrival_airport(self, arrival_airport):
        if (arrival_airport.data == self.depart_airport.data):
            raise ValidationError("Arrival and depart airport cannot be the same")

class AddAirplaneForm(FlaskForm):
    airline_name = HiddenField()
    id = StringField("Airplane ID", validators=[DataRequired(), Length(3,5)])
    num_seat = IntegerField("Number Of Seat", 
                            validators=[DataRequired(), 
                                        NumberRange(min=0,
                                                    message="Please enter a non-negative number")])
    submit = SubmitField("Add")

    def validate_id(self, id):
        airplane = Airplane.query.filter(Airplane.airline_name==self.airline_name.data,
                                         Airplane.id==id.data).first()
        if (airplane):
            raise ValidationError("Airplane ID exists! Please write a different one")

class AddAirportForm(FlaskForm):
    name = StringField("Airport name", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    submit = SubmitField("Add")

    def validate_name(self, name):
        airport = Airport.query.filter(Airport.name==name.data).first()
        if (airport):
            raise ValidationError("Airport name exists! Please write a different one")

class AddPhoneNumberForm(FlaskForm):
    username = HiddenField()
    number = StringField("Phone Number", validators=[DataRequired()])
    submit = SubmitField("Add")

    def validate_number(self, number):
        phone = Phone.query.filter(Phone.username==self.username.data,
                                   Phone.number==number.data).first()
        if (phone):
            raise ValidationError("You already have this number! Add a different one")