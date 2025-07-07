from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mail import Mail, Message
import random
import uuid
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"

# === Flask-Mail Config ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'hitmancrown008@gmail.com'
app.config['MAIL_PASSWORD'] = 'jhojkjwlfjuwsrrj'

mail = Mail(app)

# === In-Memory Data ===
users = {}  # username: {email, password}
registered_users = []
tickets = []

# === Realistic Bus Routes and Dynamic Trips ===
base_routes = [
    {"from": "Islamabad", "to": "Karachi", "distance": 1416, "duration": 21, "price": 5000, "bus_type": "Executive"},
    {"from": "Lahore", "to": "Naran", "distance": 600, "duration": 10, "price": 3000, "bus_type": "Luxury"},
    {"from": "Peshawar", "to": "Rawalpindi", "distance": 160, "duration": 2, "price": 900, "bus_type": "Economy"},
    {"from": "Quetta", "to": "Multan", "distance": 650, "duration": 11, "price": 3500, "bus_type": "Executive"}
]

routes = []
route_id_counter = 1
start_time = datetime.strptime("06:00 AM", "%I:%M %p")

for base in base_routes:
    for trip_num in range(3):  # 3 trips per route
        dep_time = start_time + timedelta(hours=trip_num * base["duration"] + trip_num * 2)
        arr_time = dep_time + timedelta(hours=base["duration"])
        route = {
            "id": route_id_counter,
            "route": f"{base['from']} to {base['to']}",
            "from": base['from'],
            "to": base['to'],
            "time": dep_time.strftime("%I:%M %p"),
            "arrival": arr_time.strftime("%I:%M %p"),
            "seats": 25,
            "seat_map": [False] * 25,
            "distance": base['distance'],
            "duration": f"{base['duration']} Hrs",
            "price": base['price'],
            "discounted": int(base['price'] * 0.95),
            "bus_type": base['bus_type']
        }
        routes.append(route)
        route_id_counter += 1

# === Load and Save Tickets ===
TICKET_FILE = 'tickets.json'

def save_tickets():
    with open(TICKET_FILE, 'w') as f:
        json.dump(tickets, f)

def load_tickets():
    global tickets
    if os.path.exists(TICKET_FILE):
        with open(TICKET_FILE, 'r') as f:
            tickets = json.load(f)

load_tickets()

# === ROUTES ===

@app.route('/')
def home():
    return render_template('home.html', routes=routes, user=session.get('user'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        otp = str(random.randint(100000, 999999))

        session['temp_user'] = {'email': email, 'username': username, 'password': password, 'otp': otp}

        msg = Message("PyDaewoo Email Verification", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Hello {username},\n\nYour OTP is: {otp}\n\nPyDaewoo Bus Service"
        mail.send(msg)

        return redirect(url_for('verify_otp'))
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if session.get('temp_user') and session['temp_user']['otp'] == user_otp:
            temp = session['temp_user']
            users[temp['username']] = {'email': temp['email'], 'password': temp['password']}
            registered_users.append({'username': temp['username'], 'email': temp['email'], 'password': temp['password']})
            session['user'] = temp['username']
            session.pop('temp_user', None)
            return redirect(url_for('home'))
        else:
            return render_template('verify_otp.html', error='Invalid OTP')
    return render_template('verify_otp.html')

@app.route('/resend_otp')
def resend_otp():
    if 'temp_user' not in session:
        return redirect(url_for('register'))

    otp = str(random.randint(100000, 999999))
    session['temp_user']['otp'] = otp

    msg = Message("Your New OTP - PyDaewoo", sender=app.config['MAIL_USERNAME'], recipients=[session['temp_user']['email']])
    msg.body = f"Hello {session['temp_user']['username']},\n\nYour new OTP is: {otp}\n\nPyDaewoo Bus Service"
    mail.send(msg)

    flash("OTP has been resent to your email.")
    return redirect(url_for('verify_otp'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        username = next((u for u in users if users[u]['email'] == email and users[u]['password'] == password), None)
        if username:
            session['user'] = username
            return redirect(url_for('home'))
        return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/book', methods=['GET', 'POST'])
def book():
    if 'user' not in session:
        return redirect(url_for('login'))

    route_id = request.args.get('route_id', type=int)
    if not route_id:
        return "Invalid route. Please go back and select from home.", 400

    selected_route = next((r for r in routes if r['id'] == route_id), None)
    if not selected_route:
        return "Route not found.", 404

    if request.method == 'POST':
        name = request.form['name']
        cnic = request.form['cnic']
        selected = request.form.get('selected_seats', '')

        if not selected:
            return render_template('error.html', message="No seat selected.")

        selected_seats = list(map(int, selected.split(',')))
        booked_tickets = []
        order_no = str(uuid.uuid4())[:8]  # Unique 8-character order number

        for seat in selected_seats:
            index = seat - 1
            if 0 <= index < len(selected_route['seat_map']) and not selected_route['seat_map'][index]:
                selected_route['seat_map'][index] = True
                selected_route['seats'] -= 1
                ticket = {
                    'order_no': order_no,
                    'name': name,
                    'cnic': cnic,
                    'seat': seat,
                    'route': selected_route['route'],
                    'time': selected_route['time']
                }
                tickets.append(ticket)
                booked_tickets.append(ticket)

        if booked_tickets:
            save_tickets()
            return redirect(url_for(
                'ticket_success',
                order_no=order_no,
                name=name,
                cnic=cnic,
                seat=','.join(str(t['seat']) for t in booked_tickets),
                route=selected_route['route'],
                time=selected_route['time']
            ))
        else:
            return render_template('error.html', message="All selected seats are already booked.")

    return render_template("book.html", selected_route=selected_route)

@app.route('/ticket_success')
def ticket_success():
    ticket = {
        'order_no': request.args.get('order_no'),
        'name': request.args.get('name'),
        'cnic': request.args.get('cnic'),
        'seat': request.args.get('seat'),
        'route': request.args.get('route'),
        'time': request.args.get('time')
    }
    return render_template('ticket_success.html', ticket=ticket)

@app.route('/check', methods=['GET', 'POST'])
def check():
    if request.method == 'POST':
        cnic = request.form['cnic']
        user_tickets = [t for t in tickets if t['cnic'] == cnic]
        return render_template('check_result.html', tickets=user_tickets, cnic=cnic)
    return render_template('check.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == "Afnanshah" and password == "Allahisone":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_tickets'))
        return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin'))

@app.route('/admin/tickets')
def admin_tickets():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    return render_template('admin_tickets.html', tickets=tickets)

@app.route('/admin/users')
def admin_users():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    return render_template('admin_users.html', users=users)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        for username, info in users.items():
            if info['email'] == email:
                otp = str(random.randint(100000, 999999))
                session['reset_user'] = {'username': username, 'email': email, 'otp': otp}
                msg = Message("Password Reset OTP", sender=app.config['MAIL_USERNAME'], recipients=[email])
                msg.body = f"Hi {username},\nYour OTP to reset password is: {otp}"
                mail.send(msg)
                return redirect(url_for('verify_reset_otp'))
        return render_template('forgot_password.html', error="Email not found.")
    return render_template('forgot_password.html')

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if session.get('reset_user') and session['reset_user']['otp'] == user_otp:
            return redirect(url_for('reset_password'))
        return render_template('verify_reset_otp.html', error="Invalid OTP.")
    return render_template('verify_reset_otp.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_pass = request.form['password']
        user = session.get('reset_user')
        if user:
            users[user['username']]['password'] = new_pass
            session.pop('reset_user', None)
            return redirect(url_for('login'))
    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)
