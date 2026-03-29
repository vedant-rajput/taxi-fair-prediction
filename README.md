# NYC Taxi Fare Prediction

A Machine Learning application that predicts NYC taxi fares using a Random Forest model, served via FastAPI, with a Streamlit frontend, PostgreSQL for storing predictions, and **Apache Airflow 3** for fully automated data pipelines — all orchestrated with Docker.

---

## Project Structure

```text
taxi-fare-prediction/
├── data/                        # All datasets
│   ├── train.csv                # Main clean training dataset (gitignored)
│   ├── raw/                     # Raw incoming CSV files (error-injected chunks)
│   ├── good_data/               # Validated clean data that passed all tests
│   └── bad_data/                # Invalid data that failed Great Expectations
│
├── .github/workflows/           # Automated CI/CD pipeline (Flake8 & Pytest)
│   └── ci.yml
│
├── dags/                        # Apache Airflow 3 DAGs
│   ├── ingestion_dag_dsp.py     # Validates via Great Expectations & splits data
│   └── predict_taxi_fares.py    # Generates predictions & records state-tracking
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

1. **Ingestion (`ingest_taxi_data` DAG)**: Runs dynamically on a schedule. It selects fresh files from `data/raw/` and rigorously evaluates them utilizing **Great Expectations v1**. Valid rows are outputted into `data/good_data/`, and broken rows are isolated in `data/bad_data/`. It additionally writes analytics to PostgreSQL and actively fires MS Teams alerts upon detecting critical issues!
2. **Prediction (`predict_taxi_fares` DAG)**: Auto-detects whenever new clean files arrive in `data/good_data/`. It dispatches the clean properties to the FastAPI endpoints to generate model inferences, commits the results into PostgreSQL natively, and securely memorizes its processed history using purely invisible **Airflow Variables**—ensuring core files are perfectly preserved without ever being moved!

### CI/CD Pipeline
- **GitHub Actions (`.github/workflows/ci.yml`)**: Instantly triggers upon commits to `main` branch. Validates complete system code integrity via `Flake8` linting and prepares behavioral tests efficiently via `Pytest`!

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
| Data Ops / Orchestration | Apache Airflow 3, Docker Compose |
| Data Quality / Testing | Great Expectations v1, Pytest, Flake8, GitHub Actions |
| Backend API | FastAPI, Uvicorn, SQLAlchemy |
| Database | PostgreSQL 15 |
| Frontend | Streamlit |
