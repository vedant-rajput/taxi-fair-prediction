# main.py — The FastAPI Backend (The Brain of our app)
# This file creates 2 API endpoints:
#   POST /predict           → Takes trip details, returns predicted fare
#   GET  /past-predictions  → Returns all past predictions from database

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pickle
import numpy as np
import os
from sqlalchemy.orm import Session

from database import get_db, create_tables, Prediction, IngestionStats

# ── Load the ML Model when API starts ──
MODEL_PATH = os.getenv("MODEL_PATH", "saved_model/taxi_model.pkl")
FEATURES_PATH = os.getenv("FEATURES_PATH", "saved_model/features.pkl")

print("Loading ML model...")
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

with open(FEATURES_PATH, "rb") as f:
    FEATURES = pickle.load(f)

print("Model loaded successfully!")

# ── Create the FastAPI app ──
app = FastAPI(
    title="NYC Taxi Fare Prediction API",
    description="Predicts NYC taxi fares using Machine Learning",
    version="1.0.0"
)

# Allow Streamlit to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables when app starts
@app.on_event("startup")
def startup():
    create_tables()

# ── Define what data we expect ──
# This is like a form — it defines what fields are required

class TaxiRide(BaseModel):
    pickup_datetime: str = "2015-01-01 00:00:00 UTC"
    pickup_longitude: float
    pickup_latitude: float
    dropoff_longitude: float
    dropoff_latitude: float
    passenger_count: int = 1

class PredictRequest(BaseModel):
    rides: List[TaxiRide]
    source: str = "webapp"

# ── Helper: Calculate distance between 2 GPS points ──
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# ── Helper: Prepare features for the model ──
def prepare_features(ride: TaxiRide):
    try:
        dt = datetime.strptime(ride.pickup_datetime, "%Y-%m-%d %H:%M:%S %Z")
    except:
        dt = datetime.now()

    distance_km = haversine_distance(
        ride.pickup_latitude, ride.pickup_longitude,
        ride.dropoff_latitude, ride.dropoff_longitude
    )

    return [
        ride.pickup_longitude,
        ride.pickup_latitude,
        ride.dropoff_longitude,
        ride.dropoff_latitude,
        ride.passenger_count,
        dt.hour,
        dt.weekday(),
        dt.month,
        distance_km
    ]

# ── Endpoint 1: Health Check ──
@app.get("/")
def root():
    return {"status": "running", "message": "Taxi Fare API is up!"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "API is running fine!"
    }

# ── Endpoint 2: Make Predictions ──
@app.post("/predict")
def predict(request: PredictRequest, db: Session = Depends(get_db)):
    if not request.rides:
        raise HTTPException(status_code=400, detail="No rides provided")

    # Prepare features for all rides
    features_list = [prepare_features(ride) for ride in request.rides]
    features_array = np.array(features_list)

    # Make predictions
    predictions = model.predict(features_array).tolist()

    # Save each prediction to the database
    for ride, pred in zip(request.rides, predictions):
        try:
            dt = datetime.strptime(ride.pickup_datetime, "%Y-%m-%d %H:%M:%S %Z")
        except:
            dt = datetime.now()

        distance_km = haversine_distance(
            ride.pickup_latitude, ride.pickup_longitude,
            ride.dropoff_latitude, ride.dropoff_longitude
        )

        db_prediction = Prediction(
            pickup_longitude=ride.pickup_longitude,
            pickup_latitude=ride.pickup_latitude,
            dropoff_longitude=ride.dropoff_longitude,
            dropoff_latitude=ride.dropoff_latitude,
            passenger_count=ride.passenger_count,
            hour=dt.hour,
            day_of_week=dt.weekday(),
            month=dt.month,
            distance_km=distance_km,
            pickup_datetime=ride.pickup_datetime,
            predicted_fare=round(pred, 2),
            prediction_source=request.source
        )
        db.add(db_prediction)

    db.commit()

    return {
        "predictions": [round(p, 2) for p in predictions],
        "message": f"Successfully predicted {len(predictions)} fare(s)"
    }

# ── Endpoint 3: Get Past Predictions ──
@app.get("/past-predictions")
def get_past_predictions(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    source: str = Query("all"),
    db: Session = Depends(get_db)
):
    query = db.query(Prediction)

    if start_date:
        query = query.filter(Prediction.created_at >= start_date)
    if end_date:
        query = query.filter(Prediction.created_at <= end_date + " 23:59:59")
    if source != "all":
        query = query.filter(Prediction.prediction_source == source)

    results = query.order_by(Prediction.created_at.desc()).limit(500).all()

    return [
        {
            "id": r.id,
            "pickup_datetime": r.pickup_datetime,
            "pickup_longitude": r.pickup_longitude,
            "pickup_latitude": r.pickup_latitude,
            "dropoff_longitude": r.dropoff_longitude,
            "dropoff_latitude": r.dropoff_latitude,
            "passenger_count": r.passenger_count,
            "distance_km": round(r.distance_km, 2) if r.distance_km else None,
            "predicted_fare": r.predicted_fare,
            "prediction_source": r.prediction_source,
            "created_at": str(r.created_at)
        }
        for r in results
    ]