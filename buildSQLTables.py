import mariadb
import yaml


#Get settings from YAML file
with open('settings.yaml', 'r') as yamlFile:
    settings = yaml.safe_load(yamlFile)

# Connect to an SQLite database (or create it if it doesn't exist)
conn = mariadb.connect(host=settings["database"]["host"],
            port=settings["database"]["port"],
            user=settings["database"]["user"],
            password=settings["database"]["password"],
            database=settings["database"]["databaseName"],
            autocommit=True)

# Create a cursor object using the cursor() method
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE energy_setting (
	id INT(11) NOT NULL AUTO_INCREMENT,
	ts TIMESTAMP NULL DEFAULT NULL,
	energyPlanDate DATE NULL DEFAULT NULL,
	solcastEstType VARCHAR(20) NULL DEFAULT NULL,
	solcastEstTypeDesc VARCHAR(50) NULL DEFAULT NULL,
	pv1ForecastkWh DOUBLE NULL DEFAULT NULL,
	pv2ForecastkWh DOUBLE NULL DEFAULT NULL,
	totalForecastkWh DOUBLE NULL DEFAULT NULL,
	totalForecastWithVariance DOUBLE NULL DEFAULT NULL,
	realSoc DOUBLE NULL DEFAULT NULL,
	userSoc DOUBLE NULL DEFAULT NULL,
	tomorrowUsagekWh DOUBLE NULL DEFAULT NULL,
	batteryChargekWh DOUBLE NULL DEFAULT NULL,
	backupChargekWh DOUBLE NULL DEFAULT NULL,
	shortfallkWh DOUBLE NULL DEFAULT NULL,
	energyPolicy VARCHAR(20) NULL DEFAULT NULL,
	chargingPlan INT(11) NULL DEFAULT NULL,
	chargingTimeHours DOUBLE NULL DEFAULT NULL,
	chargingRatekWh DOUBLE NULL DEFAULT NULL,
	chargingStartTime VARCHAR(10) NULL DEFAULT NULL,
	chargingEndTime VARCHAR(10) NULL DEFAULT NULL,
	errorMessage VARCHAR(500) NULL DEFAULT NULL,
	PRIMARY KEY (id) USING BTREE
)''')


cursor.execute('''CREATE TABLE battery_status (
	id INT(11) NOT NULL AUTO_INCREMENT,
	ts TIMESTAMP NULL DEFAULT NULL,
	batteryNumber INT(11) NULL DEFAULT NULL,
	soh DOUBLE NULL DEFAULT NULL,
	temperature DOUBLE NULL DEFAULT NULL,
	errorMessage VARCHAR(500) NULL DEFAULT NULL,
	PRIMARY KEY (id) USING BTREE
)''')



cursor.execute('''CREATE TABLE readings (
	id INT(11) NOT NULL AUTO_INCREMENT,
	ts TIMESTAMP NULL DEFAULT NULL,
	batteryPower DOUBLE NULL DEFAULT NULL,
	batteryVoltage DOUBLE NULL DEFAULT NULL,
	batteryCurrent DOUBLE NULL DEFAULT NULL,
	batteryRealSoc DOUBLE NULL DEFAULT NULL,
	batteryUserSoc DOUBLE NULL DEFAULT NULL,
	inverterPower DOUBLE NULL DEFAULT NULL,
	inverterVoltage DOUBLE NULL DEFAULT NULL,
	inverterCurrent DOUBLE NULL DEFAULT NULL,
	gridPower DOUBLE NULL DEFAULT NULL,
	gridVoltage DOUBLE NULL DEFAULT NULL,
	gridCurrent DOUBLE NULL DEFAULT NULL,
	pv1Power DOUBLE NULL DEFAULT NULL,
	pv2Power DOUBLE NULL DEFAULT NULL,
	pvTotalPower DOUBLE NULL DEFAULT NULL,
	pv1Voltage DOUBLE NULL DEFAULT NULL,
	pv2Voltage DOUBLE NULL DEFAULT NULL,
	pv1Current DOUBLE NULL DEFAULT NULL,
	pv2Current DOUBLE NULL DEFAULT NULL,
	currentLoad DOUBLE NULL DEFAULT NULL,
	errorMessage VARCHAR(500) NULL DEFAULT NULL,
	PRIMARY KEY (id) USING BTREE,
	INDEX ts (ts) USING BTREE
)''')






# Insert a row of data
#cursor.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")

# Save (commit) the changes
conn.commit()

# Close the connection
conn.close()