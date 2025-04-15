import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# Load dataset (replace with actual train data)
df = pd.read_csv("train_data.csv")

# Feature Engineering
df["day_of_week"] = pd.to_datetime(df["departure_time"]).dt.weekday
df["hour"] = pd.to_datetime(df["departure_time"]).dt.hour
df["on_peak"] = df["hour"].apply(lambda x: 1 if 7 <= x <= 9 or 17 <= x <= 19 else 0)

# Define features and target variable
features = ["station_deviation", "day_of_week", "hour", "on_peak"]
X = df[features]
y = df["delay_minutes"]

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, y_pred))

# Save trained model
with open("ml_model/model.pkl", "wb") as file:
    pickle.dump(model, file)