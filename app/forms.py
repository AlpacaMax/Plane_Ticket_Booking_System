import datetime
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, DateField, BooleanField
from wtforms.validators import DataRequired, ValidationError

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
    source_city_airport = SelectField("Source city/Airport: ",
                                      validators=[DataRequired()])
    dest_city_airport = SelectField("Destination city/Airport: ",
                                    validators=[DataRequired()])
    gonna_filter_date = BooleanField("Select a date: ")
    depart_date = DateField("Departure Date: ")
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