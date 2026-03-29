import logging
from datetime import datetime, timedelta
import os
import glob
import random
import shutil
import json
import requests

import pandas as pd
import pendulum
from airflow.sdk import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from sqlalchemy import create_engine

# -- Directories --
RAW_DIR = "/opt/airflow/data/raw"
GOOD_DIR = "/opt/airflow/data/good_data"
BAD_DIR = "/opt/airflow/data/bad_data"

TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "https://hookb.in/dummy")

@dag(
    dag_id='ingest_taxi_data',
    description='Ingest and validate NYC Taxi data with Great Expectations',
    tags=['dsp', 'data_ingestion', 'epita'],
    schedule=timedelta(minutes=1),
    start_date=pendulum.today("UTC"), 
    max_active_runs=1, 
    catchup=False
)
def ingest_taxi_data():
    
    @task
    def read_data() -> dict:
        if not os.path.exists(RAW_DIR):
            os.makedirs(RAW_DIR, exist_ok=True)
            
        all_files = glob.glob(os.path.join(RAW_DIR, "*.csv"))
        if not all_files:
            logging.info("No files available in raw_data")
            return {"filepath": None}
            
        chosen_file = sorted(all_files)[0]
        logging.info(f"Picked file: {chosen_file}")
        
        # Read the file to pass to the next task
        input_data_df = pd.read_csv(chosen_file)
        
        # Remove the file to avoid reprocessing (Data split task will place it to proper dir later)
        # Actually, let's keep the file and either delete it or move it at the end 
        os.remove(chosen_file)
        
        return {
            "filepath": chosen_file, 
            "content": input_data_df.to_dict(orient="records")
        }

    @task(multiple_outputs=True)
    def validate_data(data_info: dict) -> dict:
        if not data_info.get("filepath"):
            return {"skip": True}
            
        filepath = data_info["filepath"]
        content = data_info["content"]
        df = pd.DataFrame(content)
        total_rows = len(df)
        
        # Avoid GX error if no rows
        if total_rows == 0:
            return {
                "skip": False,
                "filename": os.path.basename(filepath),
                "total": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "missing_values": 0,
                "negative_fares": 0,
                "wrong_passengers": 0,
                "wrong_coordinates": 0,
                "string_in_number": 0,
                "future_dates": 0,
                "zero_coordinates": 0,
                "criticality": "None",
                "docs_url": "No Docs",
                "valid_rows": [],
                "invalid_rows": []
            }

        import great_expectations as gx
        context = gx.get_context(mode="ephemeral")
        
        # Using GX Core 1.x API
        data_source = context.data_sources.add_pandas("pandas_source")
        data_asset = data_source.add_dataframe_asset(name="taxi_data")
        batch_definition = data_asset.add_batch_definition_whole_dataframe("taxi_batch")
        
        suite = gx.ExpectationSuite(name="taxi_suite")
        
        # Expectations
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="passenger_count"))
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column="fare_amount"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="passenger_count"))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="fare_amount", min_value=0.0))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="passenger_count", min_value=1, max_value=6))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="pickup_latitude", min_value=40.0, max_value=42.0))
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column="pickup_longitude", min_value=-75.0, max_value=-72.0))
        # Ensure 'fare_amount' can be converted to numeric
        suite.add_expectation(gx.expectations.ExpectColumnValuesToBeOfType(column="fare_amount", type_="float"))

        # Time expectations
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotMatchRegex(column="pickup_datetime", regex="^2099"))
        # Ocean coordinate (0,0)
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeInSet(column="dropoff_latitude", value_set=[0.0]))
        
        suite = context.suites.add(suite)
        
        validation_def = context.validation_definitions.add(
            gx.ValidationDefinition(name="taxi_val", data=batch_definition, suite=suite)
        )
        
        action_list = [gx.checkpoint.actions.UpdateDataDocsAction(name="update_data_docs")]
        
        checkpoint = context.checkpoints.add(
            gx.Checkpoint(name="taxi_cp", validation_definitions=[validation_def], actions=action_list)
        )
        
        batch_parameters = {"dataframe": df}
        result = checkpoint.run(batch_parameters=batch_parameters)
        val_result = list(result.run_results.values())[0]
        eval_results = [r.to_json_dict() for r in val_result.results]
        
        # Tally metrics (rough approximation based on GX outputs)
        missing_values_count = 0
        negative_fare_count = 0
        wrong_pass_count = 0
        wrong_coord_count = 0
        string_number_count = 0
        future_count = 0
        ocean_count = 0
        
        missing_col = False
        invalid_row_set = set() # indices of invalid
        
        for res in eval_results:
            exp_type = res["expectation_config"]["type"]
            success = res["success"]
            col = res.get("expectation_config", {}).get("kwargs", {}).get("column")
            
            if not success:
                if exp_type == "expect_column_to_exist":
                    missing_col = True
                else:
                    unexpecteds_indices = res.get("result", {}).get("unexpected_index_list", [])
                    invalid_row_set.update(unexpecteds_indices)
                    
                    # Approximated
                    count = res.get("result", {}).get("unexpected_count", 0)
                    if exp_type == "expect_column_values_to_not_be_null":
                        missing_values_count = count
                    elif exp_type == "expect_column_values_to_be_between":
                        if col == "fare_amount":
                            negative_fare_count = count
                        elif col == "passenger_count":
                            wrong_pass_count = count
                        elif "latitude" in col or "longitude" in col:
                            wrong_coord_count = max(wrong_coord_count, count)
                    elif exp_type == "expect_column_values_to_be_of_type":
                        string_number_count = count
                    elif exp_type == "expect_column_values_to_not_match_regex":
                        future_count = count
                    elif exp_type == "expect_column_values_to_not_be_in_set":
                        ocean_count = count

        invalid_count = len(invalid_row_set) if not missing_col else total_rows
        valid_count = total_rows - invalid_count
            
        invalid_pct = invalid_count / total_rows if total_rows > 0 else 0
        
        criticality = "Low"
        if missing_col or invalid_pct > 0.5:
            criticality = "High"
        elif 0.1 <= invalid_pct <= 0.5:
            criticality = "Medium"
        elif invalid_count == 0:
            criticality = "None"
            
        # We manually split via simple rule since getting indices out of GX sometimes requires configuring result_format="COMPLETE" 
        # which can be complex in v1. We do a fallback split implementation in pandas:
        valid_mask = pd.Series(True, index=df.index)
        if not missing_col:
            valid_mask &= df['passenger_count'].notna()
            valid_mask &= pd.to_numeric(df['fare_amount'], errors='coerce').between(0.01, 1000.0)
            valid_mask &= pd.to_numeric(df['passenger_count'], errors='coerce').between(1, 6)
            valid_mask &= pd.to_numeric(df['pickup_latitude'], errors='coerce').between(40.0, 42.0)
            valid_mask &= pd.to_numeric(df['pickup_longitude'], errors='coerce').between(-75.0, -72.0)
            valid_mask &= (df['dropoff_latitude'] != 0.0)
        else:
            valid_mask = pd.Series(False, index=df.index)
            
        valid_rows = df[valid_mask].to_dict(orient="records")
        invalid_rows = df[~valid_mask].to_dict(orient="records")

        # Get docs URL
        site_urls = context.build_data_docs()
        docs_url = list(site_urls.values())[0] if site_urls else "No Docs URL"
        
        return {
            "skip": False,
            "filename": os.path.basename(filepath),
            "total": total_rows,
            "valid_count": len(valid_rows),
            "invalid_count": len(invalid_rows),
            "missing_values": missing_values_count,
            "negative_fares": negative_fare_count,
            "wrong_passengers": wrong_pass_count,
            "wrong_coordinates": wrong_coord_count,
            "string_in_number": string_number_count,
            "future_dates": future_count,
            "zero_coordinates": ocean_count,
            "criticality": criticality,
            "docs_url": docs_url,
            "valid_rows": valid_rows,
            "invalid_rows": invalid_rows
        }

    @task
    def save_statistics(val_result: dict):
        if val_result.get("skip", True):
            return
            
        hook = PostgresHook(postgres_conn_id="taxi_db")
        
        insert_sql = """
            INSERT INTO ingestion_stats 
            (filename, ingested_at, total_rows, valid_rows, invalid_rows, 
             missing_values_count, negative_fare_count, wrong_passengers_count, 
             wrong_coordinates_count, string_in_number_count, future_date_count, 
             zero_coordinates_count, status)
            VALUES 
            (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        
        hook.run(insert_sql, parameters=(
            val_result["filename"],
            val_result["total"],
            val_result["valid_count"],
            val_result["invalid_count"],
            val_result["missing_values"],
            val_result["negative_fares"],
            val_result["wrong_passengers"],
            val_result["wrong_coordinates"],
            val_result["string_in_number"],
            val_result["future_dates"],
            val_result["zero_coordinates"],
            val_result["criticality"]
        ))
        logging.info("Saved ingestion stats to database successfully.")

    @task
    def send_alerts(val_result: dict):
        if val_result.get("skip", True):
            return
            
        if val_result["criticality"] not in ["High", "Medium"]:
            logging.info("Criticality is Low or None. No alert sent.")
            return
            
        msg = f"Data Quality Alert! Criticality: {val_result['criticality']}\n"
        msg += f"File: {val_result['filename']}\n"
        msg += f"Invalid Rows: {val_result['invalid_count']} out of {val_result['total']}\n"
        msg += f"Report Available At: {val_result['docs_url']}"
        
        logging.info("Sending Teams Alert: " + msg)
        try:
            requests.post(
                TEAMS_WEBHOOK_URL, 
                json={"text": msg},
                timeout=10
            )
        except Exception as e:
            logging.error(f"Failed to post to webhook: {e}")

    @task
    def split_and_save_data(val_result: dict):
        if val_result.get("skip", True):
            return
            
        os.makedirs(GOOD_DIR, exist_ok=True)
        os.makedirs(BAD_DIR, exist_ok=True)
        
        filename = val_result["filename"]
        valid_rows = val_result["valid_rows"]
        invalid_rows = val_result["invalid_rows"]
        
        if valid_rows:
            good_file = os.path.join(GOOD_DIR, filename)
            pd.DataFrame(valid_rows).to_csv(good_file, index=False)
            logging.info(f"Saved {len(valid_rows)} good rows to {good_file}")
            
        if invalid_rows:
            # Append _bad to filename
            name, ext = os.path.splitext(filename)
            bad_file = os.path.join(BAD_DIR, f"{name}_bad{ext}")
            pd.DataFrame(invalid_rows).to_csv(bad_file, index=False)
            logging.info(f"Saved {len(invalid_rows)} bad rows to {bad_file}")

    # Wire tasks
    raw_info = read_data()
    validation = validate_data(raw_info)
    
    # These three run in parallel after validation
    save_statistics(validation)
    send_alerts(validation)
    split_and_save_data(validation)

ingest_taxi_data()
