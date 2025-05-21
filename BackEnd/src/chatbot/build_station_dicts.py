import csv

STATION_CODES = {}
STATION_NAME_TO_CODE = {}

with open('stations_codes.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        code = row['crsCode'].strip().upper()
        name = row['stationName'].strip().lower()
        if code and name:
            STATION_CODES[code] = row['stationName'].strip()
            STATION_NAME_TO_CODE[name] = code

# Optionally, print a few entries to check
print("Sample STATION_CODES:", list(STATION_CODES.items())[:5])
print("Sample STATION_NAME_TO_CODE:", list(STATION_NAME_TO_CODE.items())[:5])

# Save to a Python file for import
with open('station_dicts.py', 'w', encoding='utf-8') as f:
    f.write(f"STATION_CODES = {repr(STATION_CODES)}\n")
    f.write(f"STATION_NAME_TO_CODE = {repr(STATION_NAME_TO_CODE)}\n")