from flask import Flask, request, render_template, redirect, flash, session
import hashlib
import boto3
import uuid

app=Flask(__name__)
app.secret_key="your_aws_key"

dynamodb=boto3.resource('dynamodb',region_name='your-region')
users_table=dynamodb.Table('MovieMagic_Users')
booking_table=dynamodb.Table('MovieMagic_Bookings')
sns=boto3.client('sns',region_name='your-region')
sns_topic_arn="your-sns-aws-key"


def send_booking_email(email,movie,date,time,seat,booking_id):
    message=f"""
    Booking Confirmed:
    Movie={movie}
    Date={date}
    Time={time}
    Seat={seat}
    Booking ID={booking_id}
    """
    sns.publish(
        TopicArn=sns_topic_arn,
        Message=message,
        Subject="Your Movie Ticket Booking Confirmation"
    )

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle form (you can log or email it)
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash("Message sent successfully!")
    return render_template('contact.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        email=request.form['email']
        password=hashlib.sha256(request.form['password'].encode()).hexdigest()

        users_table.put_item(Item={'Email':email,'Password':password})
        flash("Registration successful! please login.")
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        response = users_table.get_item(Key={'Email': email})
        user = response.get('Item')

        if user and user.get('Password') == password:
            session['user'] = email 
            flash('Login successful!')
            return redirect('/home')  
        else:
            flash('Invalid email or password. Please try again.')

    return render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template('home.html',user=session['user'])

@app.route('/booking',methods=['GET'])
def booking_page():
    if 'user' not in session:
        return redirect('/login')
    movie=request.args.get('movie')
    return render_template('booking_form.html',movie=movie)

@app.route('/book',methods=['POST'])
def book_ticket():
    if 'user' not in session:
        return redirect('/login')
    data={
        'Email':session['user'],
        'Movie':request.form['movie'],
        'Date':request.form['date'],
        'Time':request.form['time'],
        'Seat':request.form['seat'],
        'BookingID':str(uuid.uuid4())
    }
    booking_table.put_item(Item=data)
    send_booking_email(data['Email'],data['Movie'],data['Date'],data['Time'],data['Seat'],data['BookingID'])
    return render_template('tickets.html',booking=data)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        users_table.put_item(Item={'Email': email, 'Password': password})
        flash("Registration successful! Please log in.")
        return redirect('/login')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("logged out successfully.")
    return redirect('/login')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
