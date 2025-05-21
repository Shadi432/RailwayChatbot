import requests


x = requests.get("http://localhost:3000/", params={"originStation": "NRW", "destinationStation": "LST"})
print(x.json()["Flexi Season"])