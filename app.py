from flask import Flask, request, render_template, redirect, url_for, flash, session
import hashlib
import boto3
import uuid
import os
from botocore.exceptions import ClientError

app = Flask(__name__)

# Use a secure secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key')

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'your-region')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'your-sns-aws-key')

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)

# Define DynamoDB table names
users_table = dynamodb.Table('MovieMagic_Users')
booking_table = dynamodb.Table('MovieMagic_Bookings')


# Send email via SNS
def send_booking_email(email, movie, date, time, seat, booking_id):
    message = f"""
    🎟 MovieMagic Booking Confirmed 🎟

    Movie: {movie}
    Date: {date}
    Time: {time}
    Seat: {seat}
    Booking ID: {booking_id}

    Thank you for using MovieMagic!
    """
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="Your Movie Ticket Booking Confirmation"
        )
    except ClientError as e:
        print(f"Failed to send SNS email: {e.response['Error']['Message']}")


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash("Message sent successfully!", "success")
    return render_template('contact.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        # Store in DynamoDB
        try:
            users_table.put_item(Item={'Email': email, 'Password': password})
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except ClientError as e:
            flash("Registration failed. Try again.", "danger")
            print(e.response['Error']['Message'])

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        try:
            response = users_table.get_item(Key={'Email': email})
            user = response.get('Item')

            if user and user.get('Password') == password:
                session['user'] = email
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid email or password.", "danger")
        except ClientError as e:
            flash("Login failed. Please try again.", "danger")
            print(e.response['Error']['Message'])

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))


@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', user=session['user'])


@app.route('/booking', methods=['GET'])
def booking_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    movie = request.args.get('movie')
    return render_template('booking_form.html', movie=movie)


@app.route('/book', methods=['POST'])
def book_ticket():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = {
        'Email': session['user'],
        'Movie': request.form['movie'],
        'Date': request.form['date'],
        'Time': request.form['time'],
        'Seat': request.form['seat'],
        'BookingID': str(uuid.uuid4())
    }

    try:
        booking_table.put_item(Item=data)
        send_booking_email(data['Email'], data['Movie'], data['Date'], data['Time'], data['Seat'], data['BookingID'])
        return render_template('tickets.html', booking=data)
    except ClientError as e:
        flash("Booking failed. Try again.", "danger")
        print(e.response['Error']['Message'])
        return redirect(url_for('booking_page'))


# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=True)