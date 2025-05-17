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
RUNTIME_LENGTH_MINUTES = 1
ZIPPED_OUTPUT_NAME = "data.gzip"
DATA_OUTPUT_NAME = "trainUpdates.dat"
# Index of the end <PPort> and <Ur> tags that aren't necessary
SUFFIX_TAG_INDEX = -14
RID_LENGTH = 15

SCHEDULE_ENTRIES = ("OR", "IP", "PP", "DT")
TAGS_LIST = {
    "<ns5:pass": "wtp",
    "<ns5:arr": "wta",
    "<ns5:dep": "wtd",
}
TPL_FIELD = 'tpl="'
AT_FIELD = 'at="'
SSD_FIELD = 'ssd="'

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


# Get the rid of the schedule
# Use that rid to get all related records to this schedule
def GetRecordsFromRid(rid):
    GET_BY_RID_QUERY = f"SELECT * FROM [JourneyDump].[dbo].[JourneyData] WHERE Rid='{rid}'"
    recordList = []
    try:
        connection = pyodbc.connect("DSN=TrainDB;")
    except pyodbc.Error as ex:
        print(ex)
    
    cursor = connection.cursor()

    try:
        cursor.execute(GET_BY_RID_QUERY)
        recordsRetrieved = cursor.fetchall()
        # Want to be ready to index all of these fetched values to begin my processing.
        for record in recordsRetrieved:
            if record[3] == "TS":
                recordData = record[4] + record[5] + record[6] + record[7] + record[8]
                recordList.append(recordData)

    except pyodbc.DatabaseError as err:
        print(err)

    return recordList


def GetStartLocationFromSchedule(schedule):
    originalStationTagIndex = schedule.find("ns2:OR")
    originalStationTagStart = schedule[originalStationTagIndex:]
    tplFieldStartIndex = originalStationTagStart.find('tpl="')+len(TPL_FIELD)    
    tplFieldValue = originalStationTagStart[tplFieldStartIndex:]
    tplFieldEndQuote = tplFieldValue.find('"')
    return tplFieldValue[:tplFieldEndQuote]

def GetExpectedTimeFromSchedule(schedule, destination, tag):
    tplFieldInDestinationIndex = schedule.find(destination)
    splitDestinationField = schedule[:tplFieldInDestinationIndex]
    expectedTimeFieldIndex = splitDestinationField.rfind(TAGS_LIST[tag])
    expectedTimeFieldStart = splitDestinationField[expectedTimeFieldIndex:]
    expectedTimeValueIndex = expectedTimeFieldStart.find('"')+1
    expectedTimeValue = expectedTimeFieldStart[expectedTimeValueIndex:]
    expectedTimeEndQuote = expectedTimeValue.find('"')

    return expectedTimeValue[:expectedTimeEndQuote]


# Returns a list of lists of this format (StartLocation, DestinationStop, expectedTime, actualTime, date) and can loop through this list and submit it to the model. 
def GetDelayedStationData(schedule):
    ridIndex = schedule.find("rid")
    # 5 needs to be added since find finds the start of the word rid
    rid = schedule[ridIndex+5: ridIndex+RID_LENGTH+5]
    recordList = GetRecordsFromRid(rid)

    returnList = []

    # For each record I need to look for every occurrence of an at THEN 
    # For the given tag that's found then get destination etc.
    for record in recordList:
        atOccurrences = record.split(AT_FIELD)

        for num in range(len(atOccurrences)):
            # If at field exists
            if num != 0:
                resultsDictionary = {
                    "StartLocation": "",
                    "Destination": "",
                    "ExpectedTime": "",
                    "ActualTime": "",
                    "Date": "",
                }
                        
                actualTimeEndQuote = atOccurrences[num].find('"')
                actualTimeValue = atOccurrences[num][:actualTimeEndQuote]
                resultsDictionary["ActualTime"] = actualTimeValue
                # Need a -1 to go and find the previous characters to get the tag.
                previousChunk = atOccurrences[num-1]

                # Find target tag
                targetTagIndex = previousChunk.rfind("<ns5:")
                tag = previousChunk[targetTagIndex:].strip()

                # Destination - tpl field
                destinationFieldFound = previousChunk.rfind(TPL_FIELD)
                if destinationFieldFound == -1:
                    '''
                    If a departure tag at is found, it'll have an arrival tag above it
                    if that arrival tag also has an at (almost 100%) then there's an extra chunk inbetween the location chunk.
                    '''
                    previousChunk = atOccurrences[num-2]
                    destinationFieldFound = previousChunk.rfind(TPL_FIELD)

                destinationValueStart = previousChunk[destinationFieldFound+len(TPL_FIELD):]
                destinationEndQuoteIndex = destinationValueStart.find('"')
                destinationValue = destinationValueStart[:destinationEndQuoteIndex]
                
                resultsDictionary["Destination"] = destinationValue

                

                # Date
                dateFieldFound = record.find(SSD_FIELD)
                if dateFieldFound != -1:
                    dateFieldSlice = record[dateFieldFound+len(SSD_FIELD):]
                    dateFieldEndQuote = dateFieldSlice.find('"')
                    resultsDictionary["Date"] = dateFieldSlice[:dateFieldEndQuote] 
                
                resultsDictionary["StartLocation"] = GetStartLocationFromSchedule(schedule)
                resultsDictionary["ExpectedTime"] = GetExpectedTimeFromSchedule(schedule, resultsDictionary["Destination"], tag)
                
                returnList.append((resultsDictionary["StartLocation"], resultsDictionary["Destination"], resultsDictionary["ExpectedTime"], resultsDictionary["ActualTime"], resultsDictionary["Date"]))



    return returnList

def GetStoredSchedulesList():
    GET_ALL_SCHEDULES_QUERY = "SELECT * FROM [JourneyDump].[dbo].[JourneyData] WHERE RecordType='schedule'"

    storedSchedulesList = []

    try:
        connection = pyodbc.connect("DSN=TrainDB;")
    except pyodbc.Error as ex:
        print(ex)
    
    cursor = connection.cursor()

    try:
        cursor.execute(GET_ALL_SCHEDULES_QUERY)
        recordsRetrieved = cursor.fetchall()
        # Want to be ready to index all of these fetched values to begin my processing.
        for record in recordsRetrieved:
            if record[3] == "schedule":
                scheduleData = record[4] + record[5] + record[6] + record[7] + record[8]
                storedSchedulesList.append(scheduleData)

    except pyodbc.DatabaseError as err:
        print(err)

    return storedSchedulesList

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

# Takes a schedule in string format - Checks if its a passenger service by checking if it has ns2:OR ns2:PP ns2:IP and ns2:DT
def isSchedulePassengerService(schedule):
    for SCHEDULE_ENTRY in SCHEDULE_ENTRIES:
        scheduleEntryCheck = schedule.find(SCHEDULE_ENTRY)
        if scheduleEntryCheck == -1:
            return False
    return True

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
                targetTags = ["TS", "schedule"] 
                
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
                        if tag == "TS":
                            sendTrainDataToDB(rid, tag, data, relatedRid)
                        elif tag == "schedule":
                            # In the case of a train taking up the schedule of another the program needs to split the line into both separate schedules
                            schedules = data.split("schedule>", 1)
                            
                            # Because of split I need to replace the match or I'm stuck with an incomplete xml statement.
                            schedules[0] = schedules[0] + "schedule>"

                            for schedule in schedules: 
                                if schedule != "" and isSchedulePassengerService(schedule):
                                    scheduleRidIndex = data.find("rid")
                                    # 5 needs to be added since find finds the start of the word rid
                                    scheduleRid = data[scheduleRidIndex+5: scheduleRidIndex+RID_LENGTH+5]
                                    sendTrainDataToDB(scheduleRid, tag, schedule, "")
                        

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

# if __name__ == '__main__':
#     # Init for testing so that file remains after program execution for inspection
#     if os.path.isfile(DATA_OUTPUT_NAME):
#         os.remove(DATA_OUTPUT_NAME)
#     # Init
#     try:
#         connection = pyodbc.connect("DSN=TrainDB;")
#         with connection:
#             cursor = connection.cursor()
#             DELETE_ALL_TABLES_QUERY="DROP TABLE JourneyData;DROP TABLE Trains;"
#             CREATE_ALL_TABLES_QUERY="""CREATE TABLE Trains (Rid varchar(15) NOT NULL PRIMARY KEY,);
#                 CREATE TABLE JourneyData (
#                     DataId int IDENTITY(1,1) NOT NULL PRIMARY KEY,

#                     Rid varchar(15) NOT NULL REFERENCES Trains(Rid),
#                     RelatedRid varchar(15),
#                     RecordType varchar(20),
#                     DataField1 varchar(4000),
#                     DataField2 varchar(4000),
#                     DataField3 varchar(4000),
#                     DataField4 varchar(4000),
#                     DataField5 varchar(4000));"""
#             cursor.execute(f"{DELETE_ALL_TABLES_QUERY};{CREATE_ALL_TABLES_QUERY};")
#             # Need everything cleared out here, all table data removed.
#     except pyodbc.Error as ex:
#         print(ex)

    

#     endTime = datetime.datetime.now() + datetime.timedelta(minutes=RUNTIME_LENGTH_MINUTES)

#     while endTime > datetime.datetime.now():
#         # Pass off the job to another processor 
#         with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
#             future = executor.submit(job)
            
#         print("Pull completed beginning wait for next Darwin update...")
#         time.sleep(DARWIN_PULL_INTERVAL)
#         iterationCount += 1
#         print(f"Iteration Count: {iterationCount}")
#     print("Pull from Darwin phase completed... Beginning processing the stored data")

schedulesList = GetStoredSchedulesList()

with open("dataFile.txt", "a") as file:
    for schedule in schedulesList:
        delayedStationData = GetDelayedStationData(schedule)
        if delayedStationData != []:
            for stopData in delayedStationData:
                file.write(f"{",".join(stopData)}\n")

print("Processing the stored data completed. Stored in dataFile.txt")