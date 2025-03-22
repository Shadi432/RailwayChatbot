import ftplib
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

MINUTE = 60
DATA_FILE_NAME = "data.gzip"

# Credentials for accessing the FTP server
FTP_HOSTNAME = os.getenv("FTP_HOSTNAME")
FTP_USERNAME = os.getenv("FTP_USERNAME")
FTP_PASSWORD = os.getenv("FTP_PASSWORD")

ftp = ftplib.FTP(FTP_HOSTNAME, FTP_USERNAME, FTP_PASSWORD)
ftp.cwd("pushport")

# Get most recent file in pushport
for filename in ftp.nlst():
    # Stripping out the date time from the filenames
    timeCreated = datetime.datetime.fromisoformat(filename[14:-3])
    currentTime = datetime.datetime.now()
    timeDifference = currentTime - timeCreated
    # 7 Minutes because files are uploaded to Darwin in roughly 5 minute intervals so sometimes 6 minute gaps will exist.
    if timeDifference.seconds < 7*MINUTE:
        print("The one")
        with open(DATA_FILE_NAME, "wb") as file:
            # Writing the contents to a file
            ftp.retrbinary(f"RETR {filename}", file.write)
            # Unzip the gzip and put it somewhere
            # Delete DATA_FILE_NAME


# Storing results in a database by running the right program via command line and passing the data as an argument.
