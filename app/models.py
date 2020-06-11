from app import db, login_manager
from flask_login import UserMixin

class Airline(db.Model):
    name = db.Column(db.String(20), primary_key=True)

