# Taxi Fare Prediction

A Machine Learning application that predicts NYC taxi fares using a Random Forest model, served via FastAPI, with a Streamlit frontend, PostgreSQL for storing predictions, and **Apache Airflow 3** for fully automated data pipelines — all orchestrated with Docker.

---

## Project Structure

```text
taxi-fare-prediction/
├── data/                        # All datasets
│   ├── train.csv                # Main clean training dataset (gitignored)
│   ├── raw/                     # Raw incoming CSV files (error-injected chunks)
│   ├── processed/               # Cleaned/validated data from ingestion DAG
│   └── archived/                # Processed files that have been predicted & stored
│
├── dags/                        # Apache Airflow 3 DAGs
│   ├── ingestion_dag_dsp.py     # Cleans raw data and moves to processed/
│   └── predict_taxi_fares.py    # Batches processed data to API and archives
│
├── logs/                        # Airflow task execution logs
├── plugins/                     # Airflow custom plugins
│
├── db_init/                     # Database initialization scripts
│   └── init.sql                 # Bootstraps the PostgreSQL database
│
├── model/                       # Model training
│   ├── train.py                 # Training script (reads from data/train.csv)
│   └── saved_model/             # Trained model artifacts (gitignored)
│       ├── taxi_model.pkl
│       └── features.pkl
│
├── model_service/               # FastAPI backend (port 8000)
│   ├── main.py
│   ├── database.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── webapp/                      # Streamlit frontend (port 8501)
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── scripts/                     # Data utility scripts
│   ├── split_dataset.py         # Splits train.csv into raw chunk files
│   └── data_error_injection.py  # Injects synthetic errors (historical)
│
├── docker-compose.yml           # Orchestrates Airflow, DB, API, and Web UI
└── requirements.txt             # Root-level dependencies
```

---

## Automated Data Pipeline Architecture

Our project implements a continuous, automated ETL & Inference pipeline via **Airflow 3**:

1. **Ingestion (`ingest_taxi_data` DAG)**: Runs every 5 minutes. Picks up raw data from `data/raw/`, cleans it (e.g., drops negative fares), and saves validated files to `data/processed/`.
2. **Prediction (`predict_taxi_fares` DAG)**: Runs every 5 minutes. Reads clean files from `data/processed/`, sends the batch to the FastAPI endpoint (`/predict`), stores the predictions in PostgreSQL, and moves the finished file to `data/archived/` to prevent duplicate processing.

---

## How to Run

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and **running**
- Python 3.12+ (for model training only)

### Step 1 — Train the model (Once)

> ⚠️ You must run this before starting Docker, as the API depends on the saved model files.

```bash
cd model
python train.py
```

This reads `../data/train.csv` and outputs two files into `model/saved_model/`:
- `taxi_model.pkl` — the trained Random Forest model
- `features.pkl` — the list of feature column names

### Step 2 — Build and launch with Docker

```bash
# Return to the root folder
cd ..
docker compose up -d
```

This starts the entire ecosystem:
| Service | Container | Port | Description |
|---|---|---|---|
| PostgreSQL database | `taxi_db` | `5432` | Stores predictions & Airflow metadata |
| FastAPI backend | `model_service` | `8000` | Machine Learning inference API |
| Streamlit frontend | `webapp` | `8501` | User facing interactive dashboard |
| Airflow API Server | `airflow-api-server`| `8080` | Airflow 3 Control Panel (Dashboard) |
| Airflow Scheduler | `airflow-scheduler` | - | Triggers DAGs on schedule |
| Airflow DAG Processor | `airflow-dag-processor`| - | Parses Python DAG files |

*(Note: The `airflow-init` container will run once to initialize the database and then exit automatically).*

### Step 3 — Open the Applications

| Application | URL | Features |
|---|---|---|
| **Streamlit UI** | [http://localhost:8501](http://localhost:8501) | Main App, Fare Prediction, Past Predictions (Read from DB) |
| **Airflow 3 UI** | [http://localhost:8080](http://localhost:8080) | Monitor the Ingestion and Prediction DAGs (Auto-login as Admin) |
| **FastAPI Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger documentation for the API |

To stop everything:
```bash
docker compose down
```

---

## Technologies Used

| Category | Tools |
|---|---|
| Machine Learning | Python, Scikit-learn, Pandas, NumPy |
| Orchestration | Apache Airflow 3, Docker Compose |
| Backend API | FastAPI, Uvicorn, SQLAlchemy |
| Database | PostgreSQL 15 |
| Frontend | Streamlit |
