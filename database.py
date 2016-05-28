#!/usr/bin/env python3

from modules import pg8000
import configparser


# Define some useful variables
ERROR_CODE = 55929

#####################################################
##  Database Connect
#####################################################

def database_connect():
    # Read the config file
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Create a connection to the database
    connection = None
    try: 
        connection = pg8000.connect(database=config['DATABASE']['user'],
            user=config['DATABASE']['user'],
            password=config['DATABASE']['password'],
            host=config['DATABASE']['host'])
    except pg8000.OperationalError as e:
        print("""Error, you haven't updated your config.ini or you have a bad
        connection, please try again. (Update your files first, then check
        internet connection) 
        """)
        print(e)
    #return the connection to use
    return connection

#####################################################
##  Login
#####################################################

def check_login(email, password):
    # checks if user details are correct
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    try:
        # try getting information returned from query
        check = """SELECT nickname, nameTitle, nameGiven, nameFamily, Member.address, CarBay.name,
                    since, subscribed, stat_nrofbookings
                   FROM CarSharing.Member JOIN CarSharing.CarBay ON (homeBay=bayID)
                   WHERE email=%s AND password=%s;""" 
        cur.execute(check, (email, password))
        val = cur.fetchone()
        cur.close()             # close the cursor
        conn.close()            # close the connection to db
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error. Please check your login details.")
    cur.close()                 # close the cursor
    cur.close()                 # close the connection to db
    return None


#####################################################
##  Homebay
#####################################################
def update_homebay(email, bayname):
    # updates the user's homebay
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    try:
        # try getting information returned from query
        # call stored procedure for updating homebay ID in Member table
        cur.execute('SELECT CarSharing.BayIDfromBayName(%s)', (bayname,))
        bayID = cur.fetchone()[0] # get bayID value

        # update member's homebay in database
        update = """UPDATE Member M
                    SET homeBay = %s  
                    WHERE M.email = %s    
                        AND (SELECT CarSharing.CheckBayExists(%s));"""             
        print('before')
        cur.execute(update, (bayID, email, bayname))
        print('after')
        # update member's homebay in user details
        newHB = """SELECT CarBay.name
                   FROM CarBay JOIN Member ON (bayID=homeBay)
                   WHERE Member.email=%s;"""
        cur.execute(newHB, (email,))
        val = cur.fetchone()
        conn.commit()       # COMMIT the transaction
        return val # return new homeBay to be updated in user_details
    except:
        # if any error, print error message and return False
        print("Error with the Database.")
        conn.rollback() 
    cur.close()             # close the cursor
    conn.close()            # close the connection to db
    return False
    

#####################################################
##  Booking (make, get all, get details)
#####################################################

def make_booking(email, car_rego, date, hour, duration):   
    # Insert a new booking, checking for conflict with other bookings
    # return False if booking was unsuccessful
    conn = database_connect();
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    duration_hrs = duration + ' hours'

    try:
        cur.execute("""SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;""")   # Set transaction level to serializable

        # check if member has conflicting booking
        hasBooked = """SELECT CarSharing.hasBooking(%s, %s, %s, %s);"""
        cur.execute(hasBooked, (email, date, hour, duration_hrs))
        booked = cur.fetchone()[0]

        # check if another member is using car at that time
        hasOverlap = """SELECT CarSharing.overlapped_Book(%s, %s, %s, %s);"""
        cur.execute(hasOverlap, (car_rego, date, hour, duration_hrs))
        overlapped = cur.fetchone()[0]
        
        # check if user is booking at a valid date
        timeCheck = """SELECT CarSharing.validTimes(%s);"""
        cur.execute(timeCheck, (date,)) 
        timesvalid = cur.fetchone()[0]

        if booked or overlapped or (not timesvalid): # checks failed
            return False

        # Make new booking in database
        # Get member number
        cur.execute('SELECT CarSharing.emailToMembershipNo(%s)',(email,))
        mem_number = cur.fetchone()[0]
        print(mem_number)

        # Get start time
        starting_time = """SELECT CarSharing.getStartTime(%s, %s);"""
        cur.execute(starting_time, (date, hour))
        start_time = cur.fetchone()[0]
        # Get end time
        cur.execute('SELECT CarSharing.getEndTime(%s, %s, %s)', (date, hour, duration_hrs))
        end_time = cur.fetchone()[0]

        # Insert into Booking table
        new_booking = """INSERT INTO Booking(car, madeBy, starttime, endtime)
                         VALUES(%s, %s, %s, %s);"""
        cur.execute(new_booking,(car_rego, mem_number, start_time, end_time))

        # Update booking statistic
        increment_booking = """UPDATE CarSharing.Member
                               SET stat_nrOfBookings = stat_nrOfBookings + 1
                               WHERE email=%s AND  memberNo=%s;"""
        cur.execute(increment_booking, (email, mem_number))

        conn.commit()        # COMMIT the transaction
        return True

    except:
        # if any error, print error message and return False
        print("Error with the Database.")
        conn.rollback()
    cur.close()             # close the cursor
    conn.close()            # close the connection to db
    return False


def get_all_bookings(email):
    # Get all the bookings made by this member's email
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None
    try:
        # try getting information returned from query
        bookings = """SELECT car as CarRegistration, name as CarName,                                        
                        DATE(starttime) as Date, starttime::time as Time
                      FROM CarSharing.Booking JOIN CarSharing.Member ON (memberNo = madeBy)
                        JOIN CarSharing.Car ON (car = regno)
                      WHERE email=%s
                      ORDER BY whenBooked DESC;"""
        cur.execute(bookings, (email,))
        val = cur.fetchall()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()             # close the cursor
    conn.close()            # close the connection to db
    return None


def get_booking(b_date, b_hour, car):
    # Get the information about a certain booking that has specified date, hour, and car
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None
    try:
        # try getting information returned from query
        booking = """SELECT Member.nickname as MemberName, Car.regno as CarRegistration,
                        Car.name as CarName, DATE(starttime) as Date, starttime::time as Time,       
                        date_part('hour', (endtime - starttime)) as Duration,
                        DATE(whenBooked) as WhenBooked, CarBay.name as CarBay,
                        (daily_rate+hourly_rate*date_part('hour', (endtime - starttime)))/100 as Cost 
                     FROM CarSharing.Booking JOIN CarSharing.Member ON (memberNo = madeBy)
                        JOIN CarSharing.Car ON (car = regno)
                        JOIN CarSharing.CarBay ON (parkedAt = bayID)
                        JOIN CarSharing.MembershipPlan ON (Member.subscribed = MembershipPlan.title)
                     WHERE DATE(starttime)=%s AND date_part('hour', starttime)=%s AND Car.regno=%s
                     ORDER BY whenBooked DESC;"""
        cur.execute(booking, (b_date, b_hour, car))
        val = cur.fetchone()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")  
    cur.close()             # close the cursor
    conn.close()            # close the connection to db
    return None


#####################################################
##  Car (Details and List)
#####################################################

def get_car_details(regno):
    # val = ['66XY99', 'Ice the Cube','Nissan', 'Cube', '2007', 'auto', 'Luxury', '5', 'SIT', '8', 'http://example.com']
    # Get details of the car with this registration number
    # Return the data (NOTE: look at the information, requires more than a simple select. NOTE ALSO: ordering of columns)
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None
    try:
        cardetails = """SELECT regno, Car.name, Car.make, Car.model, year, transmission,
                        category, capacity, CarBay.name, walkscore, mapURL
                        FROM CarSharing.Car
                            JOIN CarSharing.CarModel ON (Car.model=CarModel.model AND Car.make=CarModel.make)
                            JOIN CarSharing.CarBay ON (Car.parkedAt=CarBay.bayID)
                        WHERE Car.regno = %s;"""
        cur.execute(cardetails, (regno,))
        val = cur.fetchone()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()
    conn.close()
    return None

def get_all_cars():
    #val = [ ['66XY99', 'Ice the Cube', 'Nissan', 'Cube', '2007', 'auto'], ['WR3KD', 'Bob the SmartCar', 'Smart', 'Fortwo', '2015', 'auto']]
    # Get all cars that PeerCar has
    # Return the results
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None
    try:
        cars = """SELECT regno, name, make, model, year, transmission
                  FROM CarSharing.Car"""
        cur.execute(cars)
        val = cur.fetchall()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()
    conn.close()
    return None


#####################################################
##  Bay (detail, list, finding cars inside bay)
#####################################################

def get_all_bays():
    # Get all the bays that PeerCar has :)
    # And the number of cars
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor() 
    val = None
    try:
        bays = """SELECT B.name, B.address, 
                   (SELECT COUNT(*)
                    FROM CarBay JOIN Car C ON (bayID=parkedAt)
                    WHERE B.bayID=C.parkedAt) as NumberOfCars
                  FROM CarBay B
                  ORDER BY B.name"""
        cur.execute(bays)
        val = cur.fetchall()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()
    conn.close()
    return None


def get_bay(name):
    # Get the information about the bay with this unique name
    # Make sure you're checking ordering ;)
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None

    try:
        bay = """SELECT name, description, address, gps_lat, gps_long
                 FROM CarSharing.CarBay
                 WHERE name = %s
                 """
        cur.execute(bay, (name,))
        val = cur.fetchone()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()
    conn.close()
    return None

def search_bays(search_term):
    # Select the bays that match (or are similar) to the search term
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE 
    cur = conn.cursor()
    val = None
    try:
        # try getting information returned from query
        bays = """SELECT B.name, B.address,
                    (SELECT COUNT(*)
                     FROM CarBay JOIN Car C ON (bayID=parkedAt)
                     WHERE B.bayID=C.parkedAt) as NumberOfCars
                  FROM CarBay B
                  WHERE LOWER(B.address) LIKE %s OR LOWER(B.name) LIKE %s;""" # compare search term with address or name
        search_term = '%' + search_term + '%'
        cur.execute(bays, (search_term, search_term))
        val = cur.fetchall()
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()             # close the cursor
    conn.close()            # close the connection to db
    if(val is None):
        val = []
    return val 

def get_cars_in_bay(bay_name):
    # Get the cars inside the bay with specified bay name and return regno and name
    conn = database_connect()   # connect database and configurate cursor
    if(conn is None):
        return ERROR_CODE
    cur = conn.cursor()
    val = None
    try:
        carsInBay = """SELECT c.regno, c.name
                       FROM CarSharing.Car c JOIN CarSharing.CarBay ON (parkedAt = bayID)
                       WHERE CarBay.name = %s
                       ORDER BY c.name"""
        cur.execute(carsInBay, (bay_name,))
        val = cur.fetchall()
        return val
    except:
        # if any error, print error message and return a NULL row
        print("Error with the Database.")
    cur.close()
    conn.close()
    return None
