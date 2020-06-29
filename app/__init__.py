from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

app = Flask(__name__)
app.config["SECRET_KEY"] = "f42228c3084eba5c057abdb77e7325d2"
# mysqlConn = "mysql+mysqlconnector://root:root@localhost:8889/flask_ticket_booking"
sqliteConn = 'sqlite:///site.db'
app.config["SQLALCHEMY_DATABASE_URI"] = sqliteConn

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

from app import routes