from owletpy.OwletPy import OwletPy
import sys
import time
from datetime import datetime
import os.path
from os import path
import sqlite3


from pprint import pprint

import requests
from requests.exceptions import RequestException

if len(sys.argv) != 3:
    print('usage:  python3 test.py username password \n')
else:
    dbfile = '../data/owlet_data.db'
    dbexisted = path.exists(dbfile)
    conn = None

    try:
        conn = sqlite3.connect(dbfile)
        if not dbexisted:
            #We will duplicate a lot of the fields across the tables for simplicity of implementing GUI
            #  and because this dataset will be small enough it doesnt matter
            c = conn.cursor()
            c.execute('CREATE TABLE Oxygen ("id" integer primary key autoincrement, local_date text, utc_date text, value double precision not null, movement integer not null, sock_off integer not null, base_station integer not null);')
            conn.commit()

            c = conn.cursor()
            c.execute('CREATE TABLE HeartRate ("id" integer primary key autoincrement, local_date text, utc_date text, value double precision not null, movement integer not null, sock_off integer not null, base_station integer not null);')
            conn.commit()

            #For next table, utc_date date will be this system utc_date, and not from the Owlet.
            c = conn.cursor()
            c.execute('CREATE TABLE Status ("id" integer primary key autoincrement, local_date text, utc_date text, movement integer not null, sock_off integer not null, base_station integer not null, sock_connection integer not null, battery integer not null);')
            conn.commit()
        else:
            conn = sqlite3.connect(dbfile)
            print( 'Appending to ../data/owlet_data.db' )
    except Exception:
        print( 'Failed to open or create sqlite3 tables' )
        sys.exit(0)
    

    print('using username: ' + sys.argv[1] + '\n')
    print('using password: ' + sys.argv[2] + '\n')

    print('\n\n\n')

    pyowletClient = OwletPy(sys.argv[1], sys.argv[2])

    print('Our client is instantiated and should have populated attributes')

    print('DSN: ' + pyowletClient.dsn)
    print('\n\n')
    print('BASE_STATION_ON: ' + str(pyowletClient.base_station_on))
    print('\n\n')
    print('movement: ' + str(pyowletClient.movement))
    print('\n\n')
    print('prop_expire_time: ' + str(pyowletClient.prop_expire_time))
    print('\n\n\n')
    
    print('These properties will fetch new information automatically if the information is older than 15 seconds.\n')
    print('You can also bypass the ratelimiting and refresh the properties manually\n')

    pyowletClient.update_properties()
        
    properties = [
        'SOCK_OFF',
        'BASE_STATION_ON',
        'OXYGEN_LEVEL',
        'HEART_RATE',
        'MOVEMENT',
        'BATT_LEVEL',
        'CHARGE_STATUS',
        'SOCK_CONNECTION'
    ]

    # CSV header
    header = "Local-Time,UTC-Time,DSN,MovementUpdatedTime,Movement,OxygenUpdatedTime,Oxygen,HBPMUpdateTime,HBPM,ChargeUpdateTime,"
    header = header + "Charge,SockConnectUpdateTime,SockConnection,SockOffUpdateTime,SockOff,BaseStationUpdateTime,BaseStationOn,BatteryLevelUpdateTime,BatteryLevel"
    #for attribute in properties:
    #    header = header + attribute + "_updated_at;" + attribute + ";"
    print(header)

    last_update = {'SOCK_OFF': None, 'BASE_STATION_ON': None, 'OXYGEN_LEVEL': None, 'HEART_RATE': None, 
                    'MOVEMENT': None, 'BATT_LEVEL': None, 'CHARGE_STATUS': None, 'SOCK_CONNECTION': None 
        }    
    last_update_value = {'SOCK_OFF': None, 'BASE_STATION_ON': None, 'OXYGEN_LEVEL': None, 'HEART_RATE': None, 
                    'MOVEMENT': None, 'BATT_LEVEL': None, 'CHARGE_STATUS': None, 'SOCK_CONNECTION': None 
        }  

    # Stream forever
    while True:
        start = time.time()

        try:
            pyowletClient.update_properties()
        except:
            print( 'Got exception update_properties\n' )
            continue
        
        utctimestamp = datetime.utcnow()
        local_datetime = time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime() )
        
        wait_time = 15 - (time.time() - start)

        num_updates = 0
        num_status_updates = 0
        charging_started = False

        # base station is on and the sock is presumably on the baby's foot, so we can trust heart and oxygen levels
        line = str(local_datetime) + "," + str(utctimestamp) + "," + str(pyowletClient.dsn) + ","
        if last_update['MOVEMENT'] != pyowletClient.movement_updated_at:
            last_update['MOVEMENT'] = pyowletClient.movement_updated_at
            line = line + str(pyowletClient.movement_updated_at) + "," + str(pyowletClient.movement) + ","
            num_updates = num_updates + 1
            num_status_updates = num_status_updates + 1
            last_update_value['MOVEMENT'] = pyowletClient.movement
        else:
            line = line + ",,"
        
        if last_update['OXYGEN_LEVEL'] != pyowletClient.oxygen_level_updated_at:
            last_update['OXYGEN_LEVEL'] = pyowletClient.oxygen_level_updated_at
            line = line + str(pyowletClient.oxygen_level_updated_at) + "," + str(pyowletClient.oxygen_level) + ","
            num_updates = num_updates + 1
            print( "Oxygen: " + str(pyowletClient.oxygen_level) + " at " + str(local_datetime) + ", Movement: " + str(pyowletClient.movement) )
            if pyowletClient.charge_status == 0 and pyowletClient.base_station_on >= 1:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO Oxygen (local_date, utc_date, value, movement, sock_off, base_station) VALUES (?,?,?,?,?,?)", (str(local_datetime),str(pyowletClient.oxygen_level_updated_at),pyowletClient.oxygen_level,pyowletClient.movement,pyowletClient.sock_off,pyowletClient.base_station_on) )
                    conn.commit()
                    #print( 'Wrote Oxygen to DB' )
                except Exception as e:
                    print( 'Caught exception inserting exygen levels:' + str(e) )
        else:
            line = line + ",,"

        if last_update['HEART_RATE'] != pyowletClient.heart_rate_updated_at:
            last_update['HEART_RATE'] = pyowletClient.heart_rate_updated_at
            line = line + str(pyowletClient.heart_rate_updated_at) + "," + str(pyowletClient.heart_rate) + ","
            num_updates = num_updates + 1
            print( "HeartRate: " + str(pyowletClient.heart_rate) + " at " + str(local_datetime) + ", Movement: " + str(pyowletClient.movement) )
            if pyowletClient.charge_status == 0 and pyowletClient.base_station_on == 1:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO HeartRate(local_date, utc_date, value, movement, sock_off, base_station) VALUES (?,?,?,?,?,?)", (str(local_datetime),str(pyowletClient.heart_rate_updated_at),pyowletClient.heart_rate,pyowletClient.movement,pyowletClient.sock_off,pyowletClient.base_station_on) )
                    conn.commit()
                    #print( 'Wrote Heartrate to DB' )
                except Exception as e:
                    print( 'Caught exception inserting heartrate levels: ' + str(e) )
        else:
            line = line + ",,"

        if last_update['CHARGE_STATUS'] != pyowletClient.charge_status_updated_at:
            last_update['CHARGE_STATUS'] = pyowletClient.charge_status_updated_at
            line = line + str(pyowletClient.charge_status_updated_at) + "," + str(pyowletClient.charge_status) + ","
            if last_update_value['CHARGE_STATUS'] != pyowletClient.charge_status:
                charging_started = pyowletClient.charge_status >= 1
                num_updates = num_updates + 1
                num_status_updates = num_status_updates + 1
                last_update_value['CHARGE_STATUS'] = pyowletClient.charge_status
                print( "charge_status=" + str(pyowletClient.charge_status) )
        else:
            line = line + ",,"

        if (last_update['SOCK_CONNECTION'] != pyowletClient.sock_connection_updated_at) and (last_update_value['SOCK_CONNECTION'] != pyowletClient.sock_connection):
            last_update['SOCK_CONNECTION'] = pyowletClient.sock_connection_updated_at
            line = line + str(pyowletClient.sock_connection_updated_at) + "," + str(pyowletClient.sock_connection) + ","
            num_updates = num_updates + 1
            num_status_updates = num_status_updates + 1
            last_update_value['SOCK_CONNECTION'] = pyowletClient.sock_connection
            print( "sock_connection=" + str(pyowletClient.sock_connection) )
        else:
            line = line + ",,"
            
        if last_update['SOCK_OFF'] != pyowletClient.sock_off_updated_at:
            last_update['SOCK_OFF'] = pyowletClient.sock_off_updated_at
            line = line + str(pyowletClient.sock_off_updated_at) + "," + str(pyowletClient.sock_off) + ","
            if last_update_value['SOCK_OFF'] != pyowletClient.sock_off:
                num_updates = num_updates + 1
                num_status_updates = num_status_updates + 1
                last_update_value['SOCK_OFF'] = pyowletClient.sock_off
                print( "sock_off=" + str(pyowletClient.sock_off) )
        else:
            line = line + ",,"

        if last_update['BASE_STATION_ON'] != pyowletClient.base_station_on_updated_at:
            last_update['BASE_STATION_ON'] = pyowletClient.base_station_on_updated_at
            line = line + str(pyowletClient.base_station_on_updated_at) + "," + str(pyowletClient.base_station_on) + ","
            if last_update_value['BASE_STATION_ON'] != pyowletClient.base_station_on:
                num_updates = num_updates + 1
                num_status_updates = num_status_updates + 1
                last_update_value['BASE_STATION_ON'] = pyowletClient.base_station_on
                #print( "base_station_on=" + str(pyowletClient.base_station_on) )
        else:
            line = line + ",,"

        if last_update['BATT_LEVEL'] != pyowletClient.batt_level_updated_at:
            last_update['BATT_LEVEL'] = pyowletClient.batt_level_updated_at
            line = line + str(pyowletClient.batt_level_updated_at) + "," + str(pyowletClient.batt_level) + ","
            if last_update_value['BATT_LEVEL'] != pyowletClient.batt_level:
                num_updates = num_updates + 1
                num_status_updates = num_status_updates + 1
                last_update_value['BATT_LEVEL'] = pyowletClient.batt_level
                #print( "batt_level=" + str(pyowletClient.batt_level) )
        else:
            line = line + ",,"

        if num_status_updates > 0:
            try:
                c = conn.cursor()
                c.execute("INSERT INTO Status(local_date, utc_date, movement, sock_off, base_station, sock_connection, battery) VALUES (?,?,?,?,?,?,?)", (str(local_datetime),str(utctimestamp),pyowletClient.movement,pyowletClient.sock_off,pyowletClient.base_station_on,pyowletClient.sock_connection,pyowletClient.batt_level) )
                conn.commit()
                #print( 'Wrote Status update into DB' )
            except Exception as e:
                print( 'Caught exception inserting Status: ' + str(e) )


        if num_updates > 0 and pyowletClient.charge_status == 0 and pyowletClient.base_station_on == 1:
            #print( line )
            print( "" )

            filename = time.strftime( "%Y%m%d", time.localtime() )
            filename = "../data/" + filename
            filename = filename + "_owlet_data.csv"
            fileexisted = path.exists( filename)
            file_object = open(filename, 'a')
            if not fileexisted:
                file_object.write( header  + "\n" )
            file_object.write( line  + "\n" )
            file_object.close()

        try:
            if charging_started:
                #If we are here, we just started charging the sock - lets shutdown for 50 minutes
                #  so that 
                print( 'Will sleep for about thirtee minutes so the Owlet app can sync its time history (this doesnt seem to happen if we keep polling in this script)' )
                time.sleep(30*60)
                continue
            elif pyowletClient.base_station_on == 0:
                # sock was unplugged, but user did not turn on the base station.
                # heart and oxygen levels appear to be reported, but we can't
                # yet assume the sock was placed on the baby's foot.
                print( "Not charging, but not on" )
            else:
                time.sleep(max(0, wait_time))
        except (KeyboardInterrupt, SystemExit):
            conn.close()
            sys.exit(0)