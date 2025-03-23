import ftplib
import gzip 
import datetime
from dotenv import load_dotenv
import os
import shutil
import xml.etree.ElementTree as et

load_dotenv()

MINUTE = 60
ZIPPED_OUTPUT_NAME = "data.gzip"
DATA_OUTPUT_NAME = "trainUpdates.dat"

# Credentials for accessing the FTP server
FTP_HOSTNAME = os.getenv("FTP_HOSTNAME")
FTP_USERNAME = os.getenv("FTP_USERNAME")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")

ftp = ftplib.FTP(FTP_HOSTNAME, FTP_USERNAME, FTP_PASSWORD)
ftp.cwd("pushport")

# Unzips then deletes a gzip
def ungzipFile(zippedFilename, outputFilename):
    with gzip.open(zippedFilename, "rb") as file_in:
        with open(outputFilename, "wb") as file_out:
            shutil.copyfileobj(file_in,file_out)
    os.remove(zippedFilename)

# Get most recent file in pushport
for filename in ftp.nlst():
    # Stripping out the date time from the filenames
    timeCreated = datetime.datetime.fromisoformat(filename[14:-3])
    currentTime = datetime.datetime.now()
    timeDifference = currentTime - timeCreated
    # 7 Minutes because files are uploaded to Darwin in roughly 5 minute intervals so sometimes 6 minute gaps will exist.
    if timeDifference.seconds < 7*MINUTE:
        with open(ZIPPED_OUTPUT_NAME, "wb") as file:
            # Writing the contents to a file
            ftp.retrbinary(f"RETR {filename}", file.write)
            break

ftp.quit()

ungzipFile(ZIPPED_OUTPUT_NAME, DATA_OUTPUT_NAME)

# Loop through this file and for each line I need to turn it into xml, extract specific fields then send them to the db.
with open(DATA_OUTPUT_NAME, "r+") as file:
    for line in file:
        root = et.fromstring(line)
        
        for child in root:
            print(child.tag, child.attrib) 
# Storing results in a database by running the right program via command line and passing the data as an argument.
