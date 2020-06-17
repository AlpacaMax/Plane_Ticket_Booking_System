import datetime
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, BooleanField, StringField, PasswordField
from wtforms.validators import DataRequired, ValidationError, Length, EqualTo, Email
from app.models import Customer, Staff

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

class CustomerRegisterForm(RegisterForm):
    email = StringField("Email",
                        validators=[DataRequired(), Email()])
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
    
    def email_exist(self):
        customer = Customer.query.filter_by(email=self.email.data).first()
        if (customer):
            return True
        return False

class StaffRegisterForm(RegisterForm):
    username = StringField("Username",
                           validators=[DataRequired(), Length(min=2, max=20)])

    def validate_username(self):
        staff = Staff.query.filter_by(username=self.username.data).first()
        if (staff):
            return False
        return True