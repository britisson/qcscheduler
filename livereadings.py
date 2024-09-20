import requests
import json
import warnings

import yaml
#import sqlite3
import mariadb
from datetime import datetime
from methods import qcells
import time, traceback


def every(delay, task):
  next_time = time.time() + delay
  while True:
    time.sleep(max(0, next_time - time.time()))
    try:
      task()
    except Exception:
      traceback.print_exc()
      # in production code you might want to have this instead of course:
      # logger.exception("Problem while executing repetitive task.")
    # skip tasks if we are behind schedule:
    next_time += (time.time() - next_time) // delay * delay + delay


def getData():
  otherError = False
  httpError = False
  
  try:
    response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["pcssystem"], verify=False )
    response.raise_for_status()
  except requests.exceptions.HTTPError as e:
    httpError = True
    lineno, filename = qcells.get_linenumber()
    qcells.writeToLog(filename, lineno, repr(e), "Unable to retrieve pcssystem - no valid session")
  except requests.exceptions.RequestException as e:
    otherError = True
    lineno, filename = qcells.get_linenumber()
    qcells.writeToLog(filename, lineno, repr(e), "Unable to connect to the inverter")
  
  
  if not(otherError) and httpError:
    print("No valid session, requesting new session")
        
    #Call the login screen to obtain the session cookie
    try:
      response = qcellsSession.post(settings["inverter"]["logonURL"], data={'name':'Login', 'pswd':settings["inverter"]["logonPassword"]}, verify=False )
      response.raise_for_status()  
      response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["pcssystem"], verify=False )
      response.raise_for_status()
    except requests.exceptions.RequestException as e:
      otherError = True
      lineno, filename = qcells.get_linenumber()
      qcells.writeToLog(filename, lineno, repr(e), "Unable to connect to the inverter")


  
  if not(otherError):
    getReadings(response.json())


        



def getReadings(dataObject):
  #Fetch the system status information from the inverter
  #response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["pcssystem"], verify=False )
  

  timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  batteryPower = dataObject["ess_all"]["inverter_info"]["bdc"]["power"]
  batteryVoltage = dataObject["ess_all"]["inverter_info"]["bdc"]["voltage"]
  batteryCurrent = dataObject["ess_all"]["inverter_info"]["bdc"]["current_ref"]
  batteryRealSoc = dataObject["current_avg_soc"]
  batteryUserSoc = (batteryRealSoc - dataObject["nvm"]["battery_user_soc_min"]) *100 / (dataObject["nvm"]["battery_user_soc_max"] - dataObject["nvm"]["battery_user_soc_min"])

  inverterPower = dataObject["ess_all"]["inverter_info"]["inv"]["active_power"]
  inverterVoltage = dataObject["ess_all"]["inverter_info"]["inv"]["voltage"]
  inverterCurrent = dataObject["ess_all"]["inverter_info"]["inv"]["current"]

  gridPower = dataObject["meter_info"]["grid_active_power"]
  gridVoltage = dataObject["meter_info"]["grid_voltage"]
  gridCurrent = dataObject["meter_info"]["grid_current"]

  pv1Power = dataObject["ess_all"]["pv_info"]["power"][0]
  pv2Power = dataObject["ess_all"]["pv_info"]["power"][1]
  pvTotalPower = pv1Power + pv2Power
  pv1Voltage = dataObject["ess_all"]["pv_info"]["voltage"][0]
  pv2Voltage = dataObject["ess_all"]["pv_info"]["voltage"][1]
  pv1Current = dataObject["ess_all"]["pv_info"]["current"][0]
  pv2Current = dataObject["ess_all"]["pv_info"]["current"][1]

  currentLoad = batteryPower + gridPower + pv1Power + pv2Power

  print("Timestamp: " + timestamp)
  print("Battery Power: " + str(batteryPower))
  print("Inverter Power: " + str(inverterPower))
  print("Grid Power: " + str(gridPower))
  print("PV1 Power: " + str(pv1Power))
  print("PV2 Power: " + str(pv2Power))
  print("PV Total Power: " + str(pvTotalPower))
  print("Current Load: " + str(currentLoad))




  sqlStr = f"""INSERT INTO readings 
                (ts,batteryPower,batteryVoltage,batteryCurrent,batteryRealSoc,batteryUserSoc,inverterPower,inverterVoltage,inverterCurrent,
                gridPower,gridVoltage,gridCurrent,pv1Power,pv2Power,pvTotalPower,pv1Voltage,pv2Voltage,pv1Current,pv2Current,currentLoad,errorMessage)
                VALUES ('{timestamp}',{batteryPower},{batteryVoltage},{batteryCurrent},{batteryRealSoc},{batteryUserSoc}, 
                                            {inverterPower},{inverterVoltage},{inverterCurrent}, 
                                            {gridPower},{gridVoltage},{gridCurrent}, 
                                            {pv1Power},{pv2Power},{pvTotalPower},{pv1Voltage},{pv2Voltage},{pv1Current},{pv2Current}, 
                                            {currentLoad}, '');"""
  #print(sqlStr)

  # Insert a row of data
  cursor.execute(sqlStr)
  conn.commit



#Write to log to say program started
linenoStart, filenameStart = qcells.get_linenumber()
qcells.writeToLog(filenameStart, linenoStart, "n/a", "Program execution started")

#Turn off Python warnings about invalid certificates etc
warnings.filterwarnings("ignore")

#Get settings from YAML file
with open('settings.yaml', 'r') as yamlFile:
    settings = yaml.safe_load(yamlFile)

#Create a new  web session
qcellsSession = requests.Session()  

# Connect to an SQLite database (or create it if it doesn't exist)
conn = mariadb.connect(host=settings["database"]["host"],
        port=settings["database"]["port"],
        user=settings["database"]["user"],
        password=settings["database"]["password"],
        database=settings["database"]["databaseName"],
        autocommit=True)

#Create a cursor object using the cursor() method
cursor = conn.cursor()

every(5, getData)



