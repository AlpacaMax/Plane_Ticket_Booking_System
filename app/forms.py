import datetime
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, BooleanField, StringField, PasswordField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length, EqualTo, Email, NumberRange, Regexp
from app.models import Customer, Staff, Airline

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