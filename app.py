import os
import requests

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, flash, jsonify
from flask_session import Session
from tempfile import mkdtemp

from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
# Configure application
app = Flask(__name__)

# Reload templates when they are changed
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def after_request(response):
    """Disable caching"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///weather.db")

@app.route("/", methods=["GET"])
@login_required
def get_index():
    user =  db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
    name = user[0]['name']
    if (user[0]['location']):
        data = get_temp(user[0]['location'])
    else: 
        data = get_temp()
        db.execute("UPDATE users SET location = :location WHERE id = :user_id", location=get_loc(), user_id=session["user_id"])
    
    clothing, analysis, alternates = processWeather(data)
    if not (alternates == ""):
        alternates = f"If you are going out for a while, it also wouldn't be the worst idea to have {alternates} or similar wear on hand because the weather today is prone to high variability."
    return render_template("index.html", name = name, temp = data['current']['temp_f'], location = data['location']['name'], description = data['current']['condition']['text'].lower(), clothing = clothing, alt = alternates, analysis = analysis)
    
@app.route("/homepage", methods=["GET"])
def get_home():
    return render_template("homepage.html")
    
@app.route("/about", methods=["GET"])
def get_about():
    return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) == 0: 
            return apology("Invalid. Please Check Your Username", 403)
            
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid. Please Check Your Password", 403)    

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Hash password / Store password hash_password =
        hashed_password = generate_password_hash(request.form.get("password"))

        # Add user to database
        result = db.execute("INSERT INTO users (username, hash, name, location) VALUES(:username, :hash, :name, :location)",
                username = request.form.get("username"),
                hash = hashed_password, name = request.form.get("name"), location = request.form.get("location"))

        if not result:
            return apology("This username is already taken. Please create another one.")

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                  username = request.form.get("username"))


        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to set up account
        return redirect("/setup")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    rows = db.execute("SELECT * FROM users WHERE username = :username", username = request.args.get("username"))
    if rows or (len(request.args.get("username")) < 1) :
        status = "false"
    else:
        status = "true"
    return status


@app.route("/settings", methods=["GET", "POST"])
@login_required
def get_settings():
    if request.method == "POST":
        # Query database for username
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        if len(user) != 1 or not check_password_hash(user[0]["hash"], request.form.get("currPw")):
            return apology("invalid current password", 403)
        db.execute("UPDATE users SET hash = :newpassword WHERE id = :user_id", newpassword = generate_password_hash(request.form.get("newpassword")), user_id=session["user_id"])
        flash("Successfully changed password")
        # Redirect user to home page
        return redirect("/")
    else:
        user =  db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        username = user[0]['username']
        name = user[0]['name'] 
        return render_template("settings.html", username = username, name = name)
        

@app.route("/setup", methods=["GET", "POST"])
@login_required
def get_setup():
    if request.method == "POST":
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
        username = user[0]['username']
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Hot Days', :clothing, 85, 140, :username)",
                    clothing = request.form.get('extremeheat'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Warm Days', :clothing, 70, 84.9, :username)",
                    clothing = request.form.get('warmdays'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Clear Days', :clothing, 60, 69.9, :username)",
                    clothing = request.form.get('clear'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Cool Days', :clothing, 48, 59.9, :username)",
                    clothing = request.form.get('cooldays'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Cold Days', :clothing, 32, 47.9, :username)",
                    clothing = request.form.get('chillydays'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Freezing Cold Days', :clothing, -70, 31.9, :username)",
                    clothing = request.form.get('snow'), username = username)
        db.execute("INSERT INTO preferences (condition, clothing, lower, upper, user) VALUES('Rainy Days', :clothing, 0, 0, :username)",
                    clothing = request.form.get('rain'), username = username)
        return redirect("/")
    else:
        return render_template("setup.html")

@app.route("/customize", methods=["GET", "POST"])
@login_required
def get_customize():
    user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
    username = user[0]['username']
    if request.method == "POST":
        if request.form.get("name"):
            db.execute("UPDATE users SET name = :name WHERE username = :username", name = request.form.get("name"), username = username) 
        if request.form.get("location"):
            db.execute("UPDATE users SET location = :location WHERE username = :username", location = request.form.get("location"), username = username) 

        info = db.execute("SELECT condition FROM preferences WHERE user = :username", username=username)
        for condition in info:
            conditiontext =(condition['condition']).replace(" ", "_")
            if request.form.get(f"{conditiontext}_min"):
                db.execute("UPDATE preferences SET lower = :lower WHERE user = :username AND condition = :condition", lower = request.form.get(f"{conditiontext}_min"), username = username, condition = condition['condition'])
            if request.form.get(f"{conditiontext}_max"):
                db.execute("UPDATE preferences SET upper = :upper WHERE user = :username AND condition = :condition", upper = request.form.get(f"{conditiontext}_upper"), username = username, condition = condition['condition'])
            if request.form.get(f"{conditiontext}_clothing"):
                db.execute("UPDATE preferences SET clothing = :clothing WHERE user = :username AND condition = :condition", clothing = request.form.get(f"{conditiontext}_clothing"), username = username, condition = condition['condition'])
        
        return redirect("/customize")
    else:
        info = db.execute("SELECT * FROM preferences WHERE user = :username", username=username)
        return render_template("customize.html", name=user[0]['name'], location=user[0]['location'], info = info)
  
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

def processWeather(data):
    # select user
    user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])
    username = user[0]['username']
    
    #obtain specific data of interest
    temperature = float(data['current']['feelslike_f'])
    maxtempf = float(data['forecast']['forecastday'][0]["day"]['maxtemp_f'])
    mintempf = float(data['forecast']['forecastday'][0]["day"]['mintemp_f'])
    condition= data['current']['condition']['text'].lower()
    clothing=""
    analysis=""
    # account for variation due to snow/rain, which can make it feel colder than really is
    # add WIND AND A MESSAGE!s
    if "rain" in condition or "drizzle" in condition:
        analysis = f"It feels like {temperature} F, but due to the moisture in the air, you will be more comfortable dressing like it is {int(temperature - 5)} F outside"
        temperature-=5
        rain = db.execute("SELECT * FROM preferences WHERE user = :username AND condition = 'Rainy Days'", username = username)
        clothing+=rain[0]['clothing']
    if "sleet" in condition or "snow" in condition or "ice" in condition:
        snow = db.execute("SELECT * FROM preferences WHERE user = :username AND condition = 'Freezing Cold Days'", username = username)
        analysis = "Note: Since the forecast detects ice outside, it is imperative that you prepare for the worst and dress for snow."
        clothing+=snow[0]['clothing']
        if "ice" in condition:
            analysis+= f"Note: It feels like {temperature} F, but due to the ice, you will be a lot more comfortable if you dress as if it were {int(temperature - 3)} F."
            temperature-=3
    if "cloud" in condition or "mist" in condition or "fog" in condition:
        analysis = f"Note: It feels like {temperature} F, but with the clouds in the air, you'd be better off dressing for {int(temperature - 3)} F"
        temperature-=3

    #account for days where the temperature is very variable
    alternates=""
    if (maxtempf - mintempf) >= 10:
        variance = "true"
    else:
        variance = "false"
    ranges = db.execute("SELECT lower, upper, clothing FROM preferences WHERE user = :username", username = username)
    if not ranges:
        return("nothing!")
    else:
        for row in ranges:
            mintemp = row["lower"]
            maxtemp = row['upper']
            if temperature >= mintemp and temperature <= maxtemp:
                clothing+=row['clothing']
            if variance:
                if (maxtempf >= mintemp and maxtempf <= maxtemp) or (mintempf >= mintemp and mintempf <= maxtemp):
                    if not(alternates == ""):
                        alternates+=", "
                    alternates+=row['clothing']
    
    return (clothing, analysis, alternates)


def get_loc():
    loc = requests.get('https://api.ipgeolocation.io/ipgeo?apiKey=4a5610be3a46448691115315cb838b76&fields=city')
    loc = loc.json()
    return str(loc['city'])

def get_temp(loc=get_loc()):
    try:
        response = requests.get("http://api.apixu.com/v1/forecast.json?key=73100557ee0f441fa9f155027193006&q=" + loc + "&days=1")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    data = response.json()
    return data

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
