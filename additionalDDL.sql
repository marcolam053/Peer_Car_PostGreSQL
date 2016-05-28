------------------------------------------------------------
------------------ STORED PROCEDURES -----------------------
------------------------------------------------------------
-- Procedure for retrieving bayID from bayname
CREATE OR REPLACE FUNCTION CarSharing.BayIDfromBayName(bayname VARCHAR) RETURNS INTEGER AS
$$
BEGIN
  RETURN (SELECT CB.bayID
  	       FROM CarBay CB
  	       WHERE CB.name=bayname);
END;
$$ LANGUAGE plpgsql;

-- Procedure for checking if bay exists
CREATE OR REPLACE FUNCTION CarSharing.CheckBayExists(bayname VARCHAR) RETURNS BOOLEAN AS
$$
BEGIN
	RETURN EXISTS (SELECT 1
				   FROM CarBay CB
				   WHERE CB.name=bayname);
END
$$ LANGUAGE plpgsql;

-- Check if the user already has a booking at that time (if so, returns true)
CREATE OR REPLACE FUNCTION CarSharing.hasBooking(emailaddress VARCHAR, date date, hour INT, duration_hrs VARCHAR) RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS( SELECT 1
                FROM CarSharing.Member JOIN CarSharing.Booking ON (memberNo = madeBy)   
                WHERE Member.email=emailaddress
                  AND Booking.startTime::date=date
                  AND ( (Booking.startTime::time > (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                    AND Booking.startTime::time < (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                  OR
                  (Booking.endTime::time > (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                      AND Booking.endTime::time < (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                  )
                 OR 
                 (Booking.startTime::time <= (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                  AND Booking.endTime::time >= (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                 )  ) 
             ));
END;
$$ LANGUAGE plpgsql;

-- Check if the user is booking at a valid date
CREATE OR REPLACE FUNCTION CarSharing.validTimes(d date) RETURNS BOOLEAN AS
$$
BEGIN
  RETURN (d >= CURRENT_DATE);
END;
$$ LANGUAGE plpgsql;

-- Check if there is an overlapped booking FIX THIS ONE
CREATE OR REPLACE FUNCTION CarSharing.overlapped_Book(carr CHAR, date date, hour INT, duration_hrs VARCHAR) RETURNS BOOLEAN AS
$$
BEGIN
  RETURN EXISTS( SELECT 1
                FROM CarSharing.Member JOIN CarSharing.Booking ON (memberNo = madeBy)
                WHERE Booking.car = carr
                AND Booking.startTime::date = date
                AND ( (Booking.startTime::time > (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                    AND Booking.startTime::time < (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                  OR
                  (Booking.endTime::time > (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                      AND Booking.endTime::time < (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                  )
                 OR 
                 (Booking.startTime::time <= (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time)
                  AND Booking.endTime::time >= (to_timestamp(CAST(hour as VARCHAR), 'HH24:MM:SS')::time + CAST(duration_hrs AS interval))
                 )  )
              ));
END;
$$ LANGUAGE plpgsql;

-- Convert email to member_No.
CREATE OR REPLACE FUNCTION CarSharing.emailToMembershipNo(emailaddress VARCHAR) RETURNS INTEGER AS
$$
BEGIN
  RETURN (Select memberNo
          FROM Member
          Where Member.email = emailaddress);
END;
$$ LANGUAGE plpgsql;

-- calculate end time
CREATE OR REPLACE FUNCTION CarSharing.getEndTime(mydate VARCHAR, hour VARCHAR, duration_hrs VARCHAR) RETURNS TIMESTAMP AS
$$
BEGIN
  RETURN CAST(mydate AS date) + (to_timestamp(hour, 'HH24:MM:SS'))::time + CAST(duration_hrs as interval);
END;
$$ LANGUAGE plpgsql;

-- calculate start time
CREATE OR REPLACE FUNCTION CarSharing.getStartTime(mydate VARCHAR, hour VARCHAR) RETURNS TIMESTAMP AS
$$
BEGIN
  RETURN (CAST(mydate AS date) + (to_timestamp(hour, 'HH24:MM:SS'))::time);  
END;
$$ LANGUAGE plpgsql;



------------------------------------------------------------
-- Physical Optimization and Materialized View
------------------------------------------------------------
-- Reservation table, query to populate existing bookings, and triggers to make corresponding updates

--DROP TABLE Reservation;
--DROP INDEX Reservation_Index;

CREATE INDEX Reservation_Index ON Booking(car, starttime, endtime);

--DROP TABLE Reservation;

CREATE TABLE Reservation AS 
(SELECT car, starttime, endtime
FROM Booking
 
GROUP BY car, starttime, endtime
ORDER BY car, starttime);

--DROP TRIGGER ReserveNewBooking
--ON Booking;

--DROP FUNCTION ReserveBooking() CASCADE;

CREATE FUNCTION ReserveBooking() RETURNS trigger AS $$
BEGIN
  INSERT INTO Reservation(car, starttime, endtime)
      VALUES (new.car, new.starttime, new.endtime);
                              
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER ReserveNewBooking
   AFTER INSERT ON Booking
   FOR EACH ROW
   EXECUTE PROCEDURE ReserveBooking();
   
--DROP TRIGGER RemovedBooking
--ON Booking;

--DROP FUNCTION RemoveBooking() CASCADE;

CREATE FUNCTION RemoveBooking() RETURNS trigger AS $$
BEGIN
    DELETE FROM Reservation WHERE (car = OLD.car AND starttime = OLD.starttime AND endtime = OLD.endtime);                  
  RETURN OLD;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER RemovedBooking
   AFTER DELETE ON Booking
   FOR EACH ROW
   EXECUTE PROCEDURE RemoveBooking();

 
-- ADDITIONAL INDEXES:
--DROP INDEX bay_name_search;
CREATE INDEX bay_name_search ON CarBay(name DESC); 

--DROP INDEX member_no_search_ASC;
CREATE INDEX member_no_search_ASC ON Member(memberNo ASC);

--DROP INDEX member_email_password;
CREATE INDEX member_email_password ON member(email, password);


