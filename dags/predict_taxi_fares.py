import logging
import os

import pandas as pd
import pendulum
import requests
from datetime import timedelta
from airflow.sdk import dag, task
from airflow.exceptions import AirflowSkipException
from airflow.models import Variable

API_URL = "http://model_service:8000/predict"
GOOD_DIR = "/opt/airflow/data/good_data"

@dag(
    dag_id="predict_taxi_fares",
    description="Send validated taxi data to the FastAPI model for batch predictions",
    tags=["dsp", "prediction", "epita"],
    schedule=timedelta(minutes=2),
    start_date=pendulum.today("UTC"),
    max_active_runs=1,
    catchup=False,
)
def predict_taxi_fares():

    @task
    def check_for_new_data() -> list[str]:
        """Check for new ingested files in good_data, skipping if none."""
        if not os.path.exists(GOOD_DIR):
            raise AirflowSkipException("No good_data directory found. Skipping DAG.")

        all_files = sorted([f for f in os.listdir(GOOD_DIR) if f.endswith(".csv")])
        if not all_files:
            raise AirflowSkipException("No files in good_data. Skipping DAG.")

        # Get the last processed file from Airflow Variables
        last_processed = Variable.get("last_processed_file", default_var="")
        
        new_files = [f for f in all_files if f > last_processed]
        if not new_files:
            raise AirflowSkipException(f"No new files after {last_processed}. Skipping DAG.")

        # Process the oldest new file to avoid memory overload
        chosen_file = new_files[0]
        logging.info(f"Found new file to process: {chosen_file}")
        
        # Save it as the new last processed file so we don't process it again
        Variable.set("last_processed_file", chosen_file)

        return [os.path.join(GOOD_DIR, chosen_file)]

    @task
    def make_predictions(file_paths: list[str]) -> dict:
        """Read clean CSV and POST each row to /predict."""
        # Due to Airflow 3 Task Flow, if previous task skips, this won't run.
        if not file_paths:
            return {"predicted": 0, "file": None}

        file_path = file_paths[0]
        filename = os.path.basename(file_path)

        df = pd.read_csv(file_path)
        logging.info(f"Loaded {len(df)} rows from {filename}")

        # Ensure correct formatting for API
        required_cols = [
            "pickup_datetime",
            "pickup_longitude",
            "pickup_latitude",
            "dropoff_longitude",
            "dropoff_latitude",
            "passenger_count",
        ]

        # Ignore columns not expected
        df = df[[c for c in df.columns if c in required_cols]]
        df = df.dropna()
        if "pickup_datetime" in df.columns:
            df["pickup_datetime"] = df["pickup_datetime"].astype(str)
        if "passenger_count" in df.columns:
            df["passenger_count"] = df["passenger_count"].astype(int)

        rides = df.to_dict(orient="records")
        if not rides:
            logging.info("No valid rides found. Skipping API call.")
            return {"predicted": 0, "file": filename}

        payload = {
            "rides": rides,
            "source": "scheduled",
        }

        logging.info(f"POSTing {len(rides)} rides to {API_URL} ...")
        try:
            response = requests.post(API_URL, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            logging.info(f"API response: {result.get('message', 'OK')}")
        except requests.exceptions.RequestException as exc:
            logging.error(f"Failed to reach the prediction API: {exc}")
            raise Exception("Prediction API call failed") from exc

        # Do NOT delete or move file from good_data. 
        # "Files are moved to archived_data only by the training DAG after a successful model promotion."
        logging.info("Predictions saved! File kept in good_data per requirements.")
        return {"predicted": len(rides), "file": filename}


    # Wire the tasks together
    new_files = check_for_new_data()
    make_predictions(new_files)

predict_taxi_fares()
