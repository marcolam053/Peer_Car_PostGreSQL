# Importing the frameworks

from modules import *
from flask import *
import database
import configparser

ERROR_CODE = database.ERROR_CODE    # Error code
user_details = {}                   # User details kept for us
session = {}
page = {}

# Initialise the application
app = Flask(__name__)
app.secret_key = 'aab12124d346928d14710610f'


#####################################################
##  INDEX
#####################################################

@app.route('/')
def index():
    # Check if the user is logged in
    if('logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))
    page['title'] = 'PeerCar'
    return render_template('index.html',
        session=session,
        page=page,
        user=user_details)

#####################################################
##  LOGIN
#####################################################

@app.route('/login', methods=['POST', 'GET'])
def login():
    # Check if they are submitting details, or they are just logging in
    if(request.method == 'POST'):
        # submitting details
        val = database.check_login(request.form['email'] , request.form['password'])

        # Check if the database gave an error
        if(val == ERROR_CODE):
            page['bar'] = False
            flash("""There was an error with the database.""")
            return redirect(url_for('login'))

        # If it's null, saying they have incorrect details
        if(val is None or len(val) < 1):
            page['bar'] = False
            flash("Incorrect email/password, please try again")
            return redirect(url_for('login'))

        # If there was no error, log them in
        page['bar'] = True
        flash('You have been logged in successfully')
        session['logged_in'] = True

        # Store the user details for us to use throughout
        user_details['email'] = request.form['email']
        user_details['nickname'] = val[0]
        user_details['title'] = val[1]
        user_details['first'] = val[2]
        user_details['family'] = val[3]
        user_details['address'] = val[4]
        user_details['homebay'] = val[5]
        user_details['membersince'] = val[6]    
        user_details['plan'] = val[7]
        user_details['num_bookings'] = val[8] 
        return redirect(url_for('index'))

    elif(request.method == 'GET'):
        return(render_template('login.html', page=page))

#####################################################
##  LOGOUT
#####################################################

@app.route('/logout')
def logout():
    session['logged_in'] = False
    page['bar'] = True
    flash('You have been logged out')
    return redirect(url_for('index'))

#####################################################
##  LIST CARS
#####################################################

@app.route('/cars')
def list_cars():
    if( 'logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    car = request.args.get('car', '')
    val = None
    if(car == ''):
        # Try to get all the bays, handling empty
        flash("Error, you did not select a car.")
        page['bar'] = False
        return redirect(url_for('index'))

    # If we have a specific car to get
    # Go to the database and get the details
    val = database.get_car_details(car)
    if(val is None):
        val = []
        flash("Error, car \'{}\' does not exist".format(car))
        page['bar'] = False

    return render_template('car_detail.html', car=val, session=session)

#####################################################
##  LIST BAYS
##  TODO
##      - In the POST, check for null
#####################################################

@app.route('/list-bays', methods=['POST', 'GET'])
def list_bays():
    if( 'logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))
    # The user is just viewing the page
    if (request.method == 'GET'):
        # First check if specific bay
        bay = request.args.get('bay', '')
        val = None
        if(bay == ''):
            # No bay specified, try to get all the bays in a list
            val = database.get_all_bays()
            if(val is None):
                val = []
                flash("Error, no bays in our system.")
                page['bar'] = False
            return render_template('bay_list.html', bays=val, session=session)

        # Try to get from the database
        val = database.get_bay(bay)
        cars = database.get_cars_in_bay(bay)
        if(val is None):
            val = []
            flash("Error, car bay \'{}\' does not exist".format(bay))
            page['bar'] = False

        if(cars is None):
            cars = []
        return render_template('bay_detail.html', bay=val, cars=cars, session=session, user=user_details, page=page)

    elif(request.method == 'POST'):
        # The user is searching for a bay
        val = database.search_bays(request.form['search'])
        # TODO
        # Check for nulls / handle what happens if empty?
        return render_template('bay_list.html', bays=val, session=session)

#####################################################
## HOMEBAY
#####################################################
@app.route('/homebay')
def homebay():
    action = request.args.get('action', '')
    bay = request.args.get('bay', '')

    # Handle if the user didn't give a bay or an action
    # Action is either update or remove
    if(action == '' or bay == ''):
        page['bar'] = False
        flash("Error, no bay or action submitted.")
        return(redirect(url_for('index')))

    if(action == 'update'):
        # Update the homebay
        outcome = database.update_homebay(user_details['email'], bay)

        # Is it successful?
        if(outcome):
            page['bar'] = True
            user_details['homebay'] = outcome[0] # update user_details with new homebay
            flash("Success, homebay updated!")
        else:
            page['bar'] = False
            flash("There was an error adding your homebay.")
        return(redirect('{}?bay={}'.format(url_for('list_bays'), bay)))
    else:
        page['bar'] = False
        flash("Error, invalid action")
        return(redirect(url_for('index')))

#####################################################
##  MAKE BOOKING
#####################################################

@app.route('/new-booking' , methods=['GET', 'POST'])
def new_booking():
    if( 'logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # If we're just looking at the 'new booking' page
    if(request.method == 'GET'):
        # If somemone booked from the car
        from_car = request.args.get('car', '')
        cars = database.get_all_cars()
        if(cars is None):
            flash("Error, there is no car to book in the system")
            page['bar'] = False
            return(redirect(url_for('index')))
        times = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        return render_template('new_booking.html', cars=cars, times=times, session=session, page=page, from_car=from_car)
    # If we're making the booking
    success = database.make_booking(user_details['email'],
                                request.form['car_regno'],                                                            
                                request.form['book_date'],
                                request.form['book_hour'],
                                request.form['duration'])
    if(success == True):
        page['bar'] = True
        flash("Booking Successful!")
        user_details['num_bookings'] += 1   # increment num_bookings if booking is made successfully
        return(redirect(url_for('index')))
    else:
        page['bar'] = False
        flash("There was an error making your booking.")
        return(redirect(url_for('new_booking')))



#####################################################
##  SHOW MY BOOKINGS
#####################################################

@app.route('/my-bookings')
def my_bookings():
    if( 'logged_in' not in session or not session['logged_in']):
        return redirect(url_for('login'))

    # Check if viewing a booking detail
    b_date = request.args.get('b_date', '')
    b_hour = request.args.get('b_hour', '')
    b_car = request.args.get('regno', '')

    if(b_date != '' and b_hour != '' and b_car != ''):
        # Booking details
        val = database.get_booking(b_date, b_hour.split(':')[0], b_car)
        return render_template('booking_detail.html', booking=val, session=session, page=page)

    # If no booking, then get all the bookings made by the user
    val = database.get_all_bookings(user_details['email'])
    return render_template('bookings_list.html', bookings=val, session=session, page=page)


#####################################################
##  SHOW MY INVOICES
#####################################################


