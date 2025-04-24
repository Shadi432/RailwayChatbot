import ftplib
import gzip 
import datetime
from dotenv import load_dotenv
import os
import shutil
import xml.etree.ElementTree as et
import concurrent.futures
import time
import pyodbc

load_dotenv()

MINUTE = 60
DARWIN_PULL_INTERVAL = 5*MINUTE
RUNTIME_LENGTH_MINUTES = 180
ZIPPED_OUTPUT_NAME = "data.gzip"
DATA_OUTPUT_NAME = "trainUpdates.dat"
# Index of the end <PPort> and <Ur> tags that aren't necessary
SUFFIX_TAG_INDEX = -14
RID_LENGTH = 15

# Credentials for accessing the FTP server
FTP_HOSTNAME = os.getenv("FTP_HOSTNAME")
FTP_USERNAME = os.getenv("FTP_USERNAME")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")

# [rid] = True
ridCache = {}

iterationCount = 0

# Get most recent file in pushport and writes it to filesystem
def getMostRecentDarwinFile():
    # Verifying if all the credentials are in the env file
    if (FTP_HOSTNAME and FTP_USERNAME and FTP_PASSWORD):
        # If lines below this one aren't running it's because the credentials are incorrect check the NRDP website.
        ftp = ftplib.FTP(FTP_HOSTNAME, FTP_USERNAME, FTP_PASSWORD)
        ftp.cwd("pushport")
        
        # Need a check here for if ftp.nlst doesn't return stuff because that's a bug based on DARWIN's timing
        for filename in ftp.nlst():
            # Stripping out the date time from the filenames - Darwin runs on UTC all year round
            timeCreated = datetime.datetime.fromisoformat(filename[14:-3]).astimezone(datetime.timezone.utc)
            currentTime = datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=1)
            timeDifference = currentTime - timeCreated
            # 7 Minutes because files are uploaded to Darwin in roughly 5 minute intervals so sometimes 6 minute gaps will exist.
            
            if timeDifference.seconds < 7*MINUTE:
                with open(ZIPPED_OUTPUT_NAME, "wb") as file:
                    # Writing the contents to a file
                    ftp.retrbinary(f"RETR {filename}", file.write)
                    break
        ftp.quit()
    else:
        print(f"""The credentials in the .env file are not filled in. Check the readme for details.
            FTP_HOSTNAME: {FTP_HOSTNAME}, FTP_USERNAME: {FTP_USERNAME}, FTP_PASSWORD: {FTP_PASSWORD}""")

# Unzips then deletes a gzip
def ungzipFile(zippedFilename, outputFilename):
    with gzip.open(zippedFilename, "rb") as file_in:
        with open(outputFilename, "wb") as file_out:
            shutil.copyfileobj(file_in,file_out)
    os.remove(zippedFilename)


# Takes a string and separates it into sections obeying a length limit on each entry.
# Accepts data(string), numPartitions(int) maxLength(int)
def partitionString(data, numPartitions, maxLength):
    # Empty string entries represent the possible data fields in the database, right now there are 4.
    sectionedData = ["" for partition in range(numPartitions)]

    if len(data) > maxLength * numPartitions:
        print(f"Length of line of Darwin input exceeds db limits: {data}")

    while len(data) > 0:
        sectionNum = len(data)//maxLength

        # if this is less than 1 then want to take the entirety of this and put it into the section
        # if more than 1 then can just take up to the 4k and cut it.
        if sectionNum < 1:
            sectionedData[sectionNum] = data
            data = ""
            break
        else:
            sectionedData[sectionNum] = data[sectionNum*maxLength-1:(sectionNum+1)*maxLength-1]
            data = data[:sectionNum*maxLength-1]
    return sectionedData

def sendTrainDataToDB(rid, informationType, data, relatedRid):
    sectionedData = partitionString(data, 5, 4000)

    try:
        connection = pyodbc.connect("DSN=TrainDB;")
    except pyodbc.Error as ex:
        print(ex)
    
    cursor = connection.cursor()

    # want rid cache so if rid is duplicate for this file then I don't need to send to rid table.
    if rid not in ridCache:
        try: 
            cursor.execute("INSERT INTO Trains (Rid) VALUES (?)", rid)
        except pyodbc.DatabaseError as err:
            ridCache[rid] = True
    
    try:
        cursor.execute("INSERT INTO JourneyData VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rid, relatedRid, informationType, *sectionedData)
    except pyodbc.DatabaseError as err:
        print(err)
    
    cursor.commit()
    

def processXML():
    with open(DATA_OUTPUT_NAME, "r+") as file:
        for line in file:
            # If a <OW> tag appears then Darwin line breaks which breaks up the XML, so this checks we have a properly formed Darwin line.
            if "<Pport" in line and "</Pport>" in line:
                targetTags = ["TS", "schedule", "deactivated"] 
                
                # Match the target tags to the current line of XML and if there snip the data within
                for tag in targetTags:
                    # The " r" is needed because of the scheduleFormations tag which means schedule will match to that too. This makes the code work for all cases.                    
                    tagPosition = line.find(f"<{tag} r")
                    data = line[tagPosition:SUFFIX_TAG_INDEX]
                    if data != "":
                        relatedRid = ""
                        ridIndex = data.find("rid")
                        # 5 needs to be added since find finds the start of the word rid
                        rid = data[ridIndex+5: ridIndex+RID_LENGTH+5]
                        if tag == "schedule":
                            # In the case of a train taking up the schedule of another the program needs to split the line into both separate schedules
                            schedules = data.split("schedule>", 1)
                            # There will always be two elements in the schedules list due to how .split works.
                            
                            if schedules[1] != "":
                                relatedRidIndex = schedules[1].find("rid")
                                # 5 needs to be added since find finds the start of the word rid
                                relatedRid = schedules[1][relatedRidIndex+5: relatedRidIndex+RID_LENGTH+5]

                        
                        sendTrainDataToDB(rid, tag, data, relatedRid)
                        

def job():
    getMostRecentDarwinFile()
    ungzipFile(ZIPPED_OUTPUT_NAME, DATA_OUTPUT_NAME)

    startTime = datetime.datetime.now()
    processXML()
    endTime = datetime.datetime.now()
    diff = endTime-startTime
    print(f"Time taken to process: {diff}")
    # Cleanup UNCOMMENT FOR FINAL VERSION
    os.remove(DATA_OUTPUT_NAME)

if __name__ == '__main__':
    # Init for testing so that file remains after program execution for inspection
    if os.path.isfile(DATA_OUTPUT_NAME):
        os.remove(DATA_OUTPUT_NAME)
    # Init
    try:
        connection = pyodbc.connect("DSN=TrainDB;")
        with connection:
            cursor = connection.cursor()
            DELETE_ALL_TABLES_QUERY="DROP TABLE JourneyData;DROP TABLE Trains;"
            CREATE_ALL_TABLES_QUERY="""CREATE TABLE Trains (Rid varchar(15) NOT NULL PRIMARY KEY,);
                CREATE TABLE JourneyData (
                    DataId int IDENTITY(1,1) NOT NULL PRIMARY KEY,

                    Rid varchar(15) NOT NULL REFERENCES Trains(Rid),
                    RelatedRid varchar(15),
                    RecordType varchar(20),
                    DataField1 varchar(4000),
                    DataField2 varchar(4000),
                    DataField3 varchar(4000),
                    DataField4 varchar(4000),
                    DataField5 varchar(4000));"""
            cursor.execute(f"{DELETE_ALL_TABLES_QUERY};{CREATE_ALL_TABLES_QUERY};")
            # Need everything cleared out here, all table data removed.
    except pyodbc.Error as ex:
        print(ex)

    

    endTime = datetime.datetime.now() + datetime.timedelta(minutes=RUNTIME_LENGTH_MINUTES)

    while endTime > datetime.datetime.now():
        # Pass off the job to another processor 
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
            future = executor.submit(job)
            
        print("finished")
        time.sleep(DARWIN_PULL_INTERVAL)
        iterationCount += 1
        print(iterationCount)
    print("stopped")

