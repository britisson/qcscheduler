import smtplib, ssl
import requests
import json
import sqlite3
import mariadb
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from email.message import EmailMessage
from inspect import currentframe, getframeinfo


class qcells:

    def sendMail(plainMessage, htmlMessage, subject, settings):
        sender_email = settings["email"]["username"]
        receiver_email = settings["email"]["toAddress"]
        password = settings["email"]["password"]

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = formataddr((settings["email"]["fromName"], settings["email"]["username"]))
        message["To"] = receiver_email


        # Turn these into plain/html MIMEText objects
        part1 = MIMEText(plainMessage, "plain")

        if htmlMessage == "":
            htmlMessage = "<html><body><p>" + plainMessage.replace("\n","<br/>") + "</p></body></html>"
        part2 = MIMEText(htmlMessage, "html")

        # Add HTML/plain-text parts to MIMEMultipart message
        # The email client will try to render the last part first
        message.attach(part1)
        message.attach(part2)

        # Create secure connection with server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings["email"]["smtpServer"], settings["email"]["smtpPort"], context=context) as server:
            server.login(sender_email, password)
            server.sendmail(
                sender_email, receiver_email, message.as_string()
            )

    
    def sendErrorEmail(message):
        pass

    def updateInverterSettings(outputs, qcellsSession, settings):
        responseDevice = qcellsSession.post(settings["inverter"]["rootUrl"] + settings["endpoints"]["device"], json=outputs["energySettings"], verify=False )  
        responseDeviceJson = responseDevice.json()
        #print("Just run POST command")
        #print(responseDeviceJson["error_code"])

        responseBatSync = qcellsSession.post(settings["inverter"]["rootUrl"] + settings["endpoints"]["battery-sync"], verify=False )  
        responseBatSyncJson = responseBatSync.json()
        #print("Just run second POST command")
        #print(responseBatSyncJson)


    def updateDatabase(outputs, qcellsSession, settings):
        # Connect to an SQLite database (or create it if it doesn't exist)
        # Connect to an SQLite database (or create it if it doesn't exist)
        conn = mariadb.connect(host=settings["database"]["host"],
            port=settings["database"]["port"],
            user=settings["database"]["user"],
            password=settings["database"]["password"],
            database=settings["database"]["databaseName"],
            autocommit=True)

        #Create a cursor object using the cursor() method
        cursor = conn.cursor()

        timestamp = str(datetime.today())


        sqlStr = f"""INSERT INTO energy_setting (ts, energyPlanDate,solcastEstType,solcastEstTypeDesc,pv1ForecastkWh,
                                                pv2ForecastkWh,totalForecastkWh,
                                                totalForecastWithVariance,realSoc,userSoc,
                                                tomorrowUsagekWh,batteryChargekWh,backupChargekWh,
                                                shortfallkWh,energyPolicy,chargingPlan,chargingTimeHours,chargingRatekWh,
                                                chargingStartTime,chargingEndTime,errorMessage)
        
        VALUES ('{timestamp}','{outputs["energyPlanDate"]}','{outputs["solcastEstType"]}','{outputs["solcastEstTypeDesc"]}',{outputs["pv1ForecastkWh"]},
                                             {outputs["pv2ForecastkWh"]},{outputs["totalForecastkWh"]}, 
                                             {outputs["totalForecastWithVariance"]},{outputs["realSoc"]},{outputs["userSoc"]}, 
                                             {outputs["tomorrowUsagekWh"]},{outputs["batteryChargekWh"]},{outputs["backupChargekWh"]}, 
                                             {outputs["shortfallkWh"]},'{outputs["energyPolicy"]}',{outputs["chargingPlan"]},{outputs["chargingTimeHours"]},{outputs["chargingRatekWh"]},
                                             '{outputs["chargingStartTime"]}','{outputs["chargingEndTime"]}','{outputs["errorMessage"]}');"""
        #print(sqlStr)

        # Insert a row of data
        #print(sqlStr)

        # Insert a row of data
        cursor.execute(sqlStr)
        conn.commit()
        conn.close()

    
    def generateEmail(outputs, settings):
        plainMessage = ""
        htmlMessage = ""

        energyPlanDate = outputs["energyPlanDate"]


        batteryInfoPlainText = ""
        batteryInfoHtmlText = ""
        j = 0
        while j <= len(outputs["batteryInfo"]["batteries"]) - 1:
            batteryInfoPlainText = batteryInfoPlainText + "Battery " + str(j+1) + " Health (%): " + str(outputs["batteryInfo"]["batteries"][0]["stateOfHealth"]) + "\n"
            batteryInfoPlainText = batteryInfoPlainText + "Battery " + str(j+1) + " Temperature (°C): " + str(outputs["batteryInfo"]["batteries"][0]["batteryTemperature"]) + "\n"
            batteryInfoHtmlText = batteryInfoHtmlText + "<b>Battery " + str(j+1) + " Health (%): </b>" + str(outputs["batteryInfo"]["batteries"][0]["stateOfHealth"]) + "<br/>"
            batteryInfoHtmlText = batteryInfoHtmlText + "<b>Battery " + str(j+1) + " Temperature (°C): </b>" + str(outputs["batteryInfo"]["batteries"][0]["batteryTemperature"]) + "<br/>"
            j += 1


        plainMessage = f"""\
Inverter Setting Report for {energyPlanDate}

System State:
    Current Battery SOC (%) (Real): {str(outputs["realSoc"])}
    Current Battery SOC (%) (Usable): {str(outputs["userSoc"])}
    Current Battery SOC (kWh) (Usable): {str(outputs["batteryChargekWh"])}
    {batteryInfoPlainText}


Forecast:
    Solcast Forecast Type: {outputs["solcastEstTypeDesc"]}
    PV1 Forecast (kWh): {str(outputs["pv1ForecastkWh"])}
    PV2 Forecast (kWh): {str(outputs["pv2ForecastkWh"])}
    Total Forecast (kWh): {str(outputs["totalForecastkWh"])}
    Tommorow's Usage (kWh): {str(outputs["tomorrowUsagekWh"])}
    Shortfall (kWh): {str(outputs["shortfallkWh"])}


Inverter Setting:
    Charging Plan: {str(outputs["chargingPlan"])}
    Energy Policy: {outputs["energyPolicy"]}
    Charging Time (hours): {str(outputs["chargingTimeHours"])}
    Charging Rate (kWh): {str(outputs["chargingRatekWh"])}
    Charging Start Time: {outputs["chargingStartTime"]}
    Charging End Time: {outputs["chargingEndTime"]}


Errors:
{outputs["errorMessage"]}

Report End

"""
        

        htmlMessage = f"""\
<h2>Inverter Setting Report for {energyPlanDate}</h2>

<h3>System State:</h3>
<p>
    <b>Current Battery SOC (%) (Real):</b> {str(outputs["realSoc"])}<br/>
    <b>Current Battery SOC (%) (Usable):</b> {str(outputs["userSoc"])}<br/>
    <b>Current Battery SOC (kWh) (Usable):</b> {str(outputs["batteryChargekWh"])}<br/>
    {batteryInfoHtmlText}
</p>

<h3>Forecast:</h3>
<p>
    <b>Solcast Forecast Type:</b> {outputs["solcastEstTypeDesc"]}<br/>
    <b>PV1 Forecast (kWh):</b> {str(outputs["pv1ForecastkWh"])}<br/>
    <b>PV2 Forecast (kWh):</b> {str(outputs["pv2ForecastkWh"])}<br/>
    <b>Total Forecast (kWh):</b> {str(outputs["totalForecastkWh"])}<br/>
    <b>Tommorow's Usage (kWh):</b> {str(outputs["tomorrowUsagekWh"])}<br/>
    <b>Shortfall (kWh):</b> {str(outputs["shortfallkWh"])}<br/>
</p>


<h3>Inverter Setting:</h3>
<p>
    <b>Charging Plan:</b> {str(outputs["chargingPlan"])}<br/>
    <b>Energy Policy:</b> {outputs["energyPolicy"]}<br/>
    <b>Charging Time (hours):</b> {str(outputs["chargingTimeHours"])}<br/>
    <b>Charging Rate (kWh):</b> {str(outputs["chargingRatekWh"])}<br/>
    <b>Charging Start Time:</b> {outputs["chargingStartTime"]}<br/>
    <b>Charging End Time:</b> {outputs["chargingEndTime"]}<br/>
</p>


<h3>Errors:</h3>
<p>
    {outputs["errorMessage"]}<br/>
</p>

<h3>Report End</h3>

"""
        subject = "Invert Settings Report for " + outputs["energyPlanDate"]


        qcells.sendMail(plainMessage, htmlMessage, subject, settings)

    def get_linenumber():
        cf = currentframe()
        filename = getframeinfo(cf.f_back).filename
        return cf.f_back.f_lineno, filename
        

    def writeToLog(scriptName, lineno, exceptionError, comment=""):
            with open(scriptName+".log", "a") as filename:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                content = timestamp + "\t" + scriptName + "\t" + str(lineno) + "\t" + exceptionError +  "\t" + comment + "\n"
                filename.write(content)
    
