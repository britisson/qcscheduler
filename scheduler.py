######################## QCELLS Battery Scheduler v0.1 ########################
######################## Wednesday 18th September 2024 ########################

import requests
import json
import warnings
#import inspect
import yaml
#import mariadb
from datetime import datetime, timedelta
from methods import qcells

#Write to log to say program started
linenoStart, filenameStart = qcells.get_linenumber()
qcells.writeToLog(filenameStart, linenoStart, "n/a", "Program execution started")

#Turn off Python warnings about invalid certificates etc
warnings.filterwarnings("ignore")


#Get settings from YAML file
with open('settings.yaml', 'r') as yamlFile:
    settings = yaml.safe_load(yamlFile)


#Create an object to store all the outputs and calculations
outputs = {
        "energyPlanDate": "",
        "solcastEstType": "",
        "solcastEstTypeDesc": "",
        "pv1ForecastkWh": 0,
        "pv2ForecastkWh": 0,
        "totalForecastkWh": 0,
        "totalForecastWithVariance": 0,
        "realSoc": 0,
        "userSoc": 0,
        "tomorrowUsagekWh": 0,
        "batteryChargekWh": 0,
        "backupChargekWh": 0,
        "shortfallkWh": 0,
        "energyPolicy": "",
        "chargingPlan": 0,
        "chargingTimeHours": 0,
        "chargingRatekWh": 0,
        "chargingStartTime": "",
        "chargingEndTime": "",
        "energySettings":{},
        "batteryInfo":{
            "batteries": []
            },
        "errorMessage": ""
}

errors = False

#******************** Get JSON from QCells Inverter *****************#
#Create a new  web session
qcellsSession = requests.Session()  

#print(settings["inverter"]["logonPassword"])

#Call the login screen to obtain the session cookie
try:
    response = qcellsSession.post(settings["inverter"]["logonURL"], data={'name':'Login', 'pswd':settings["inverter"]["logonPassword"]}, verify=False ) 
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    errors = True
    lineno, filename = qcells.get_linenumber()
    qcells.writeToLog(filename, lineno, repr(e), "Unable to connect to the inverter")

if not(errors):
    try:
        #Fetch the system status information from the inverter
        response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["pcssystem"], verify=False )
        response.raise_for_status()
        pcsSystem = response.json()
    except requests.exceptions.RequestException as e:    
        errors = True
        lineno, filename = qcells.get_linenumber()
        qcells.writeToLog(filename, lineno, repr(e), "Unable to retrieve the pcssystem endpoint")

if not(errors):
    try:
        #Fetch the configuration settings
        response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["allnvm"], verify=False )
        response.raise_for_status()
        allnvm = response.json()
    except requests.exceptions.RequestException as e:    
        errors = True
        lineno, filename = qcells.get_linenumber()
        qcells.writeToLog(filename, lineno, repr(e), "Unable to retrieve the allnvm endpoint")





    #Fetch the Time Of Use settings
    #response = qcellsSession.get(settings["inverter"]["rootUrl"] + settings["endpoints"]["tou"], verify=False )
    #tou = response.json


#******************* Get JSON from SolCast ********************#
if not(errors) and settings["solcastLocation"] == "web":
    try:
        solcastSession = requests.Session()  #Create session
        response = solcastSession.get(settings["solcast"]["solcastAPIURLSite1"]+"&api_key="+settings["solcast"]["solcastApiKey"])
        response.raise_for_status()
        solcastPvArray1 = response.json()
    except requests.exceptions.RequestException:
        errors = True 
        qcells.sendErrorEmail("Unable to connect to the Solcast API. Inverter settings unchanged, please set manually")


if not(errors) and settings["solcastLocation"] == "web":
    if pcsSystem["nvm"]["installed_PV_count"] == 2:
        try:    
            response = solcastSession.get(settings["solcast"]["solcastAPIURLSite2"]+"&api_key="+settings["solcast"]["solcastApiKey"])
            response.raise_for_status()
            solcastPvArray2 = response.json()
        except requests.exceptions.RequestException:
            errors = True
            qcells.sendErrorEmail("Unable to connect to the Solcast API. Inverter settings unchanged, please set manually")



#Testing from files
if not(errors) and settings["solcastLocation"] == "local":
    jsonFile1 = open("forecasts/forecasts1.json")
    solcastPvArray1 = json.load(jsonFile1)
    jsonFile2 = open("forecasts/forecasts2.json")
    solcastPvArray2 = json.load(jsonFile2)


if not(errors):
    #**************** Get Solcast Forecast for tomorrow  ******************# 
    tomorrow = datetime.today() + timedelta(days=1)
    tomorrowStr = tomorrow.strftime("%Y-%m-%d")

    solcastPv1kWh = 0
    solcastPv2kWh = 0
    solcastTotalkWh = 0

    estimateType = ""

    if settings["solcast"]["solcastEstimate"] == 1:
        estimateType = "pv_estimate"
        estimateTypeDesc = "Standard Estimate"
    elif settings["solcast"]["solcastEstimate"] == 2:
        estimateType = "pv_estimate10"
        estimateTypeDesc = "Conservative Estimate (10th percentile)"
    elif settings["solcast"]["solcastEstimate"] == 3:
        estimateType = "pv_estimate90"
        estimateTypeDesc = "Optimistic Estimate (90th percentile)"

    #print("Forecast made using " + estimateTypeDesc)
    outputs["energyPlanDate"] = tomorrowStr
    outputs["solcastEstType"] = estimateType
    outputs["solcastEstTypeDesc"] = estimateTypeDesc


    #Loop through the estimates which match tomorrows date and add them up
    for item in solcastPvArray1["forecasts"]:
        #print(item[estimateType],item["period_end"], item["period_end"][:10])
        periodEndDate = item["period_end"][:10]
        if tomorrowStr == periodEndDate:
            solcastPv1kWh = solcastPv1kWh + (item[estimateType]/2)  #Div by 2 because it's a 30 min estimate
            #print(item[estimateType],item["period_end"])
    #print("PV1 Forecast kWh: " + str(solcastPv1kWh))  
    outputs["pv1ForecastkWh"] = round(solcastPv1kWh,3)


    if pcsSystem["nvm"]["installed_PV_count"] == 2:
        for item in solcastPvArray2["forecasts"]:
            #print(item[estimateType],item["period_end"], item["period_end"][:10])
            periodEndDate = item["period_end"][:10]
            if tomorrowStr == periodEndDate:
                solcastPv2kWh = solcastPv2kWh + (item[estimateType]/2)
                #print(item[estimateType],item["period_end"])
        #print("PV2 Forecast kWh: " + str(solcastPv2kWh))
        outputs["pv2ForecastkWh"] = round(solcastPv2kWh,3)

    solcastTotalkWh = (solcastPv1kWh + solcastPv2kWh)
    outputs["totalForecastkWh"] = round(solcastTotalkWh,3)

    #Adjust according to variance in settings
    solcastTotalkWh = (100 + settings["solcast"]["solcastVariance"])*solcastTotalkWh/100
    #print("Total Forecast kWh for " + tomorrowStr + ": " + str(solcastTotalkWh))
    outputs["totalForecastWithVariance"] = round(solcastTotalkWh,2)


    



    #******************** Get current battery status ***************************#

    #Get battery health and temperature
    batteriesInstalled = pcsSystem["nvm"]["installed_rack_count"]
    i = 0
    while i <= batteriesInstalled - 1:
        batteryDictionary = {
            "batteryNumber": (i+1),
            "stateOfHealth": pcsSystem["ess_all"]["bat_info"]["bat_rack_info"][i]["soh"],
            "batteryTemperature": pcsSystem["ess_all"]["bat_info"]["bat_rack_info"][i]["avg_cell_temperature"]
        }
        outputs["batteryInfo"]["batteries"].append(batteryDictionary)
        i += 1
    batteryInfoStr = json.dumps(outputs["batteryInfo"], indent=4)
    #print(batteryInfoStr)
    #print(len(outputs["batteryInfo"]))
    #print(outputs["batteryInfo"]["batteries"][0]["batteryNumber"])



    #Get current charge level
    realSoc = pcsSystem["current_avg_soc"]
    userSoc = (realSoc - pcsSystem["nvm"]["battery_user_soc_min"]) *100 / (pcsSystem["nvm"]["battery_user_soc_max"] - pcsSystem["nvm"]["battery_user_soc_min"])
    #print("Current Battery SOC %(Real) :" + str(realSoc))
    #print("Current Battery SOC % (Usable) :" + str(userSoc))
    outputs["realSoc"] = round(realSoc,2)
    outputs["userSoc"] = round(userSoc,2)


    #Get tomorrows estimated usage
    dailyUsage = settings["user"]["dailyUsage"]
    tomorrowUsage = dailyUsage[tomorrow.weekday()]
    #print("Tomorrow's Eastimated Usage: " + str(tomorrowUsage)) 
    outputs["tomorrowUsagekWh"] = tomorrowUsage


    #Get current charge in battery in kWh
    batteryChargekWh = userSoc * (settings["inverter"]["usableBatteryCapacity"]) /100
    #print("Current total usable charge in battery: " + str(batteryChargekWh) + " kWh")
    outputs["batteryChargekWh"] = round(batteryChargekWh,3)


    #Get reserved battery charge (backup battery amount from QCells settings screen)
    backupSoc = allnvm["battery_backup_soc"]
    backupChargekWh = settings["inverter"]["usableBatteryCapacity"] * backupSoc / 100
    outputs["backupChargekWh"] = round(backupChargekWh,2)

    #Show charge remaining in battery, taking out the backup
    #print("Current charge left minus backup: " + str(batteryChargekWh - backupChargekWh) + " kWh")

    #Workout the shortfall
    shortfall = batteryChargekWh - tomorrowUsage - backupChargekWh + solcastTotalkWh
    if shortfall >= 0:
        shortfall = 0

    #print("Overnight charge needed from Grid: " + str(shortfall))
    outputs["shortfallkWh"] = round(shortfall,2)



    if shortfall < 0:
        outputs["energyPolicy"] = "Time Based"
        #*********** Work out the charging window in hours and what the charge rate needs to be **********
        if settings["user"]["chargingPlan"] == 1:
            startTimeObj = datetime.strptime(settings["user"]["chargeWindowStart"], '%H:%M')
            endTimeObj = datetime.strptime(settings["user"]["chargeWindowEnd"], '%H:%M')
            timeWindow = endTimeObj-startTimeObj
            timeWindowHours = timeWindow.seconds/(60*60)

            #print("Charging Time Window: " + str(timeWindowHours))

            chargeRate = round(shortfall*1000/timeWindowHours)
            if chargeRate < settings["user"]["maxChargeRate"]*-1000:
                chargeRate = settings["user"]["maxChargeRate"]*-1000

            #print("Required Charge Rate (kWh): " + str(chargeRate/1000))

            outputs["chargingPlan"] = settings["user"]["chargingPlan"]
            outputs["chargingTimeHours"] = round(timeWindowHours,2)
            outputs["chargingRatekWh"] = round(chargeRate/1000, 3)
            outputs["chargingStartTime"] = settings["user"]["chargeWindowStart"]
            outputs["chargingEndTime"] = settings["user"]["chargeWindowEnd"]


            #print("Charging Plan: " + str(outputs["chargingPlan"]))
            #print("Charging Time Window: " + str(outputs["chargingTimeHours"]))
            #print("Required Charge Rate (kWh): " + str(outputs["chargingRatekWh"]))
            #print("Charging Start Time: " + outputs["chargingStartTime"])
            #print("Charging End Time: " + outputs["chargingEndTime"])





        else:
            startTimeObj = datetime.strptime(settings["user"]["chargeWindowStart"], '%H:%M')
            endTimeObj = datetime.strptime(settings["user"]["chargeWindowEnd"], '%H:%M')
            maxTimeWindow = endTimeObj-startTimeObj
            maxTimeWindowHours = maxTimeWindow.seconds/(60*60)
            maxChargeRate = settings["user"]["maxChargeRate"]*-1

            

            timeWindow = (shortfall/maxChargeRate)
            if timeWindow > maxTimeWindowHours:
                timeWindow = maxTimeWindowHours

            chargeRate = maxChargeRate * 1000

            #print("Charging Time Window: " + str(timeWindow))

            chargeEndTime = startTimeObj + timedelta(hours=timeWindow)
            chargeEndTimeStr = chargeEndTime.strftime("%H:%M")

            #print("Charging End Time: " + str(chargeEndTimeStr))

            #print("Required Charge Rate (kWh): " + str(maxChargeRate))

            outputs["chargingPlan"] = settings["user"]["chargingPlan"]
            outputs["chargingTimeHours"] = round(timeWindow,2)
            outputs["chargingRatekWh"] = round(maxChargeRate,3)
            outputs["chargingStartTime"] = settings["user"]["chargeWindowStart"]
            outputs["chargingEndTime"] = chargeEndTimeStr


            #print("Charging Plan: " + str(outputs["chargingPlan"]))
            #print("Charging Time Window: " + str(outputs["chargingTimeHours"]))
            #print("Required Charge Rate (kWh): " + str(outputs["chargingRatekWh"]))
            #print("Charging Start Time: " + outputs["chargingStartTime"])
            #print("Charging End Time: " + outputs["chargingEndTime"])

    else:
        outputs["energyPolicy"] = "Self Consumption"
        #print("No charge needed overnight")


    if shortfall >= 0:
        outputs["energySettings"] = {
            "energy_policy": "1",
            "pv_connection_type": "2"
        }
    else:
        tou_start_date = datetime.today() + timedelta(days=-1)
        tou_end_date = datetime.today() + timedelta(days=2)
        tomorrowStr = tomorrow.strftime("%Y-%m-%d")
        outputs["energySettings"]  = {
            "advanced_tou_flag": 0,
            "energy_policy": "3",
            "pv_connection_type": "2",
            "tou_action": [
                "2",
                "1"
            ],
            "tou_action_weekend": [
                "2",
                "1"
            ],
            "tou_info_end_date": tou_end_date.strftime("%Y%m%d"),
            "tou_info_start_date": tou_start_date.strftime("%Y%m%d"),
            "tou_inverter_ref": [
                str(round(outputs["chargingRatekWh"]*1000)),
                "0"
            ],
            "tou_inverter_ref_weekend": [
                str(round(outputs["chargingRatekWh"]*1000)),
                "0"
            ],
            "tou_time": [
                outputs["chargingStartTime"],
                outputs["chargingEndTime"]
            ],
            "tou_time_weekend": [
                outputs["chargingStartTime"],
                outputs["chargingEndTime"]
            ]
        }

    dataStr = json.dumps(outputs["energySettings"], indent=4)
    #print(dataStr)



    

    try:
        qcells.updateInverterSettings(outputs, qcellsSession, settings)
    except  Exception as e:
        errors = True
        lineno, filename = qcells.get_linenumber()
        qcells.writeToLog(filename, lineno, repr(e), "Unable to update inverter settings")


    try:    
        qcells.updateDatabase(outputs, qcellsSession, settings)
    except  Exception as e:
        errors = True
        lineno, filename = qcells.get_linenumber()
        qcells.writeToLog(filename, lineno, repr(e), "Unable to write to database")
        
    try:    
        qcells.generateEmail(outputs, settings)
    except  Exception as e:
        errors = True
        lineno, filename = qcells.get_linenumber()
        qcells.writeToLog(filename, lineno, repr(e), "Unable to send settings email")



#Write to log to say program finished
linenoEnd, filenameEnd = qcells.get_linenumber()
qcells.writeToLog(filenameEnd, linenoEnd, "n/a", "Program execution finished")
    
        



    # https://192.168.0.12:7000/system/status/pv-meter-connect

    # https://192.168.0.12:7000/system/status/pcsconntectstatus

    # https://192.168.0.12:7000/system/status/cloudconnectstatus

    # https://192.168.0.12:7000/json/error_code_list.json

    # https://192.168.0.12:7000/system/information/ems-version

    # https://192.168.0.12:7000/system/information/serial-number

    # https://192.168.0.12:7000/system/information/product-model-name?EMS_serial_number=121141246012232237

    # https://192.168.0.12:7000/system/information/ess-version

    # https://192.168.0.12:7000/install/datetime 

    # https://192.168.0.12:7000/install/network-info

    # https://192.168.0.12:7000/system/information/installState

    # https://192.168.0.12:7000/system/latest-version

    # https://192.168.0.12:7000/install/internet-connection  POST
    
    # https://192.168.0.12:7000/resource/grid-code/default/826

    # https://192.168.0.12:7000/install/ntp-status








