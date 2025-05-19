# imports:
import os
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from datetime import datetime

# set up absolute path to dataFile.txt:
data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dataFile.txt"))

# load dataset:
df = pd.read_csv(data_path, header=None, names=["origin", "destination", "scheduled", "actual", "date"])

# remove any missing data:
df.dropna(inplace=True)

# remove rows with blank station codes:
df = df[(df["origin"].str.strip() != "") & (df["destination"].str.strip() != "")]

# convert to datetime:
df["sched_dt"] = pd.to_datetime(df["date"] + " " + df["scheduled"], errors="coerce")
df["actual_dt"] = pd.to_datetime(df["date"] + " " + df["actual"], errors="coerce")

# remove rows with failed datetime parsing:
df.dropna(subset=["sched_dt", "actual_dt"], inplace=True)

# calculate delay in minutes:
df["delay_minutes"] = (df["actual_dt"] - df["sched_dt"]).dt.total_seconds() / 60.0

# build station id map from origin and destination columns:
all_stations = pd.concat([df["origin"], df["destination"]]).unique()
station_ids = {station: i for i, station in enumerate(all_stations)}
df["origin_id"] = df["origin"].map(station_ids)
df["dest_id"] = df["destination"].map(station_ids)
df["station_deviation"] = abs(df["origin_id"] - df["dest_id"])

# extract hour and day of week:
df["hour"] = df["sched_dt"].dt.hour
df["day_of_week"] = df["sched_dt"].dt.weekday

# rush hour feature:
df["on_peak"] = df["hour"].apply(lambda x: 1 if 7 <= x <= 9 or 17 <= x <= 19 else 0)

# define features and label:
features = ["station_deviation", "day_of_week", "hour", "on_peak"]
X = df[features]
y = df["delay_minutes"]

# split into training and testing sets:
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# train the model:
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# evaluate model performance:
y_pred = model.predict(X_test)
print("mae:", mean_absolute_error(y_test, y_pred))

# save the model:
model_dir = os.path.join(os.path.dirname(__file__), "ml_model")
os.makedirs(model_dir, exist_ok=True)

model_path = os.path.join(model_dir, "model.pkl")
with open(model_path, "wb") as file:
    pickle.dump(model, file)

print("model saved to", model_path)
