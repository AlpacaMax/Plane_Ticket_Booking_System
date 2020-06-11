from app import app, db, bcrypt

@app.route("/")
def home():
    return "Hello world!"