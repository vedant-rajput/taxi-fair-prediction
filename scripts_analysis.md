# Project Files — Code Block Analysis

---

## File 1: [data_error_injection.py](file:///Users/vedantrajput/Desktop/dsp-taxifareprediction-project/scripts/data_error_injection.py)

---

### Lines 1–22: Header Comments

```python
# ============================================================
# data_error_injection.py
# ============================================================
#
# SIMPLE EXPLANATION:
# Imagine you have a perfect Excel sheet with taxi data.
# This script deliberately makes some cells wrong.
# Like a teacher adding mistakes to a student's paper
# to see if they can find them!
#
# We add 7 types of mistakes:
# 1. Empty cells (missing values)
# 2. Negative fare (impossible!)
# 3. Too many passengers (impossible!)
# 4. Wrong city coordinates (not New York!)
# 5. Text in a number column (wrong data type!)
# 6. Date in the future (impossible!)
# 7. Dropoff in the ocean (wrong GPS!)
#
# HOW TO RUN:
# python data_error_injection.py
# ============================================================
```

**Explanation:** This is purely documentation — no code runs. It gives an overview of the script's purpose: to deliberately inject 7 types of errors into clean taxi data, simulating real-world dirty data that downstream cleaning pipelines need to handle.

---

### Lines 25–28: Imports

```python
import pandas as pd
import numpy as np
import os
```

**Explanation:** Loads three libraries:
- `pandas` — to read/write CSV files as DataFrames (like tables)
- `numpy` — to pick random rows (`np.random.choice`) and represent missing values (`np.nan`)
- `os` — to create directories on disk

---

### Lines 31–44: Configuration

```python
INPUT_FILE = "../data/train.csv"
OUTPUT_FILE = "../data/raw/train_with_errors.csv"
NUM_ROWS = 1000
NUM_ERROR_ROWS = 50
```

**Explanation:** Four constants that control the script's behavior:
- `INPUT_FILE` — path to the clean source data
- `OUTPUT_FILE` — where the corrupted data will be saved
- `NUM_ROWS = 1000` — only read the first 1000 rows from the source
- `NUM_ERROR_ROWS = 50` — each of the 7 error types will affect 50 rows

---

### Lines 47–51: Load the Clean Data

```python
print("Loading clean data...")
df = pd.read_csv(INPUT_FILE, nrows=NUM_ROWS)
print(f"Loaded {len(df)} rows!")
print(f"Columns: {list(df.columns)}")
```

**Explanation:** Reads the first 1000 rows of `train.csv` into a DataFrame called `df`. Then prints how many rows were loaded and what columns the data has (e.g., `fare_amount`, `pickup_latitude`, `passenger_count`, etc.).

---

### Lines 54–63: Make a Working Copy

```python
df_bad = df.copy()
df_bad["fare_amount"] = df_bad["fare_amount"].astype(object)
print("\nStarting to add errors...")
```

**Explanation:** Creates an independent copy called `df_bad` so the original `df` is never modified. Then converts the `fare_amount` column from numeric to `object` type — this is necessary because Error 5 will insert the string `"unknown"` into this column, and a numeric column can't hold strings.

---

### Lines 66–76: Error 1 — Missing Values

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "passenger_count"] = np.nan
print(f"Error 1 added: {NUM_ERROR_ROWS} rows have missing passenger_count")
```

**Explanation:** Randomly picks 50 unique row indices (`replace=False` prevents duplicates), then sets `passenger_count` to `NaN` (missing/empty) in those rows. Simulates data where someone forgot to fill in a field.

---

### Lines 79–86: Error 2 — Negative Fare

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "fare_amount"] = -10.50
print(f"Error 2 added: {NUM_ERROR_ROWS} rows have negative fare (-10.50)")
```

**Explanation:** Picks a new random set of 50 rows and sets their `fare_amount` to `-10.50`. A taxi fare can never be negative — this tests whether the cleaning pipeline validates fare ranges.

---

### Lines 89–96: Error 3 — Too Many Passengers

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "passenger_count"] = 100
print(f"Error 3 added: {NUM_ERROR_ROWS} rows have 100 passengers (impossible!)")
```

**Explanation:** Sets `passenger_count` to `100` in 50 random rows. A normal taxi holds at most 6 passengers, so 100 is an obvious outlier. Note: some of these rows may overlap with Error 1's rows, overwriting the `NaN` with `100`.

---

### Lines 99–108: Error 4 — Wrong City Coordinates

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "pickup_latitude"] = 51.5
df_bad.loc[rows_to_affect, "pickup_longitude"] = -0.1
print(f"Error 4 added: {NUM_ERROR_ROWS} rows have London coordinates (wrong city!)")
```

**Explanation:** Replaces pickup GPS coordinates with London, UK (51.5, -0.1) in 50 rows. NYC coordinates are around (40.7, -74.0), so London values are completely out of range. Tests geographic boundary validation.

---

### Lines 111–119: Error 5 — Text in a Number Column

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "fare_amount"] = "unknown"
print(f"Error 5 added: {NUM_ERROR_ROWS} rows have 'unknown' in fare_amount")
```

**Explanation:** Inserts the string `"unknown"` into `fare_amount` for 50 rows. This column should only contain numbers. This is why line 61 converted the column to `object` type first — otherwise pandas would reject a string in a numeric column.

---

### Lines 122–129: Error 6 — Future Dates

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "pickup_datetime"] = "2099-01-01 00:00:00 UTC"
print(f"Error 6 added: {NUM_ERROR_ROWS} rows have future date (year 2099!)")
```

**Explanation:** Sets pickup date to year 2099 in 50 rows. The dataset contains historical trips from 2009–2015, so a future date is impossible. Tests temporal/date validation.

---

### Lines 132–140: Error 7 — Dropoff in the Ocean

```python
rows_to_affect = np.random.choice(df_bad.index, size=NUM_ERROR_ROWS, replace=False)
df_bad.loc[rows_to_affect, "dropoff_latitude"] = 0.0
df_bad.loc[rows_to_affect, "dropoff_longitude"] = 0.0
print(f"Error 7 added: {NUM_ERROR_ROWS} rows have dropoff in the ocean (0.0, 0.0)!")
```

**Explanation:** Sets dropoff coordinates to `(0.0, 0.0)` — a point in the Gulf of Guinea off West Africa (called "Null Island"). This is a common default/placeholder value. No NYC taxi should drop off passengers in the ocean.

---

### Lines 143–150: Save the Corrupted Data

```python
os.makedirs("../data/raw", exist_ok=True)
df_bad.to_csv(OUTPUT_FILE, index=False)
```

**Explanation:** Creates the output folder `data/raw/` if it doesn't exist (`exist_ok=True` avoids errors if it's already there). Then saves the corrupted DataFrame as a CSV file. `index=False` prevents pandas from writing the row index (0, 1, 2…) as an extra column.

---

### Lines 153–172: Print Summary Report

```python
print("\n" + "="*50)
print("SUMMARY OF ERRORS ADDED")
print("="*50)

total_rows = len(df_bad)

print(f"Total rows in file: {total_rows}")
print(f"")
print(f"Error 1 - Missing passenger_count:  {df_bad['passenger_count'].isna().sum()} rows")
print(f"Error 2 - Negative fare:            {(df_bad['fare_amount'] == -10.50).sum()} rows")
print(f"Error 3 - 100 passengers:           {(df_bad['passenger_count'] == 100).sum()} rows")
print(f"Error 4 - London coordinates:       {(df_bad['pickup_latitude'] == 51.5).sum()} rows")
print(f"Error 5 - 'unknown' in fare:        {(df_bad['fare_amount'] == 'unknown').sum()} rows")
print(f"Error 6 - Future date (2099):       {(df_bad['pickup_datetime'] == '2099-01-01 00:00:00 UTC').sum()} rows")
print(f"Error 7 - Ocean dropoff (0,0):      {(df_bad['dropoff_latitude'] == 0.0).sum()} rows")
print(f"")
print(f"File saved to: {OUTPUT_FILE}")
print("="*50)
print("DONE! Your error injection script worked!")
```

**Explanation:** Prints a verification report counting how many rows were actually affected by each error. Uses `.isna().sum()` to count missing values, and `(column == value).sum()` to count rows matching a specific bad value. This confirms the injection worked as expected.

---
---

## File 2: `split_dataset.py`

---

### Lines 1–9: Header Comments

```python
# ============================================================
# split_dataset.py
# ============================================================
# WHAT THIS FILE DOES IN SIMPLE WORDS:
# Imagine you have one BIG notebook with 10000 pages
# This script tears it into 50 SMALL notebooks
# Each small notebook has 200 pages
# These small notebooks go into a folder called "raw-data"
# ============================================================
```

**Explanation:** Documentation only — no code runs. Describes the script's purpose: splitting one large CSV file into many smaller ones to simulate how raw data arrives in batches.

---

### Lines 12–20: Imports

```python
import pandas as pd
import os
import numpy as np
```

**Explanation:** Same three libraries:
- `pandas` — for reading/writing CSV data
- `os` — for creating directories and building file paths
- `numpy` — for splitting the data into equal chunks (`np.array_split`)

---

### Lines 23–31: Configuration

```python
DATASET_PATH = "../data/train.csv"
RAW_DATA_FOLDER = "../data/raw"
NUM_FILES = 100
```

**Explanation:** Three constants:
- `DATASET_PATH` — where the big source CSV lives
- `RAW_DATA_FOLDER` — output folder for the small files
- `NUM_FILES = 100` — split into 100 files

---

### Lines 34–40: Create Output Folder

```python
os.makedirs(RAW_DATA_FOLDER, exist_ok=True)
print("Step 1 done: raw-data folder created!")
```

**Explanation:** Creates `data/raw/` on disk. `exist_ok=True` means it won't crash if the folder already exists. Prints a confirmation message.

---

### Lines 43–50: Load the Dataset

```python
print("Step 2: Loading the dataset... please wait...")
df = pd.read_csv(DATASET_PATH, nrows=10000)
print(f"Step 2 done: Loaded {len(df)} rows from train.csv!")
```

**Explanation:** Reads the first 10,000 rows from `train.csv` into a DataFrame. The `nrows=10000` limit prevents loading the entire (potentially huge) file, keeping the script fast and memory-friendly.

---

### Lines 53–62: Split into Equal Chunks

```python
print(f"Step 3: Splitting data into {NUM_FILES} files...")
file_chunks = np.array_split(df, NUM_FILES)
```

**Explanation:** `np.array_split(df, 100)` divides the 10,000-row DataFrame into a list of 100 smaller DataFrames, each with ~100 rows. `array_split` (not `split`) is used because it handles cases where 10,000 doesn't divide evenly — some chunks may get 1 extra row.

---

### Lines 65–87: Save Each Chunk as a CSV File

```python
for i, chunk in enumerate(file_chunks):
    filename = f"raw_data_{str(i+1).zfill(3)}.csv"
    filepath = os.path.join(RAW_DATA_FOLDER, filename)
    chunk.to_csv(filepath, index=False)
    print(f"Saved file {i+1} of {NUM_FILES}: {filename} ({len(chunk)} rows)")
```

**Explanation:** Loops through all 100 chunks:
- `enumerate()` gives both the index `i` (0–99) and the chunk data
- `str(i+1).zfill(3)` pads the number with zeros: `1 → "001"`, `10 → "010"`, `100 → "100"` — this ensures files sort correctly alphabetically
- `os.path.join()` builds the full path like `../data/raw/raw_data_001.csv`
- `chunk.to_csv(filepath, index=False)` saves the chunk without adding a row index column
- Prints progress for each file saved

---

### Lines 90–96: Final Summary

```python
print("")
print("====================================")
print("ALL DONE!")
print(f"Created {NUM_FILES} files in '{RAW_DATA_FOLDER}' folder")
print(f"Each file has about {len(df) // NUM_FILES} rows")
print("====================================")
```

**Explanation:** Prints a completion message. `len(df) // NUM_FILES` does integer division (10000 ÷ 100 = 100) to show the approximate number of rows per output file.

---
---

## File 3: `ci.yml` (GitHub Actions CI/CD Pipeline)

---

### Lines 1–2: Workflow Name

```yaml
name: CI/CD Pipeline
```

**Explanation:** Gives the workflow a human-readable name. This name appears in the **Actions** tab on GitHub when the workflow runs.

---

### Lines 3–9: Trigger Events

```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
```

**Explanation:** Defines **when** this workflow runs:
- `push → main` — runs every time code is pushed directly to the `main` branch
- `pull_request → main` — runs every time a Pull Request targeting `main` is opened or updated

This means the CI pipeline checks your code **before** it gets merged into `main`.

---

### Lines 11–13: Job Definition

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
```

**Explanation:**
- `jobs:` — a workflow can have multiple jobs; this one has one called `test`
- `test:` — the job name (appears in the GitHub Actions UI)
- `runs-on: ubuntu-latest` — the job runs on a fresh Ubuntu Linux virtual machine provided by GitHub (free for public repos)

---

### Lines 15–17: Step 1 — Checkout Code

```yaml
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3
```

**Explanation:** The first step in every CI pipeline. `actions/checkout@v3` is a pre-built GitHub Action that clones your repository into the virtual machine so subsequent steps can access your code.

---

### Lines 19–22: Step 2 — Set Up Python

```yaml
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
```

**Explanation:** Installs Python 3.12 on the virtual machine. `actions/setup-python@v4` is a pre-built action that handles downloading and configuring the specified Python version.

---

### Lines 24–28: Step 3 — Install Dependencies

```yaml
    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        pip install flake8 pytest
```

**Explanation:** Runs three shell commands:
- `python -m pip install --upgrade pip` — upgrades `pip` to the latest version
- `if [ -f requirements.txt ]; then pip install -r requirements.txt; fi` — if a `requirements.txt` file exists, install all project dependencies listed in it
- `pip install flake8 pytest` — installs two testing tools: `flake8` (code linter) and `pytest` (test runner)

The `|` after `run:` means "multi-line shell script".

---

### Lines 30–35: Step 4 — Run Linter (Flake8)

```yaml
    - name: Run Linter (Flake8)
      run: |
        # stop the build if there are Python syntax errors or undefined names
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        # exit-zero treats all errors as warnings.
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

**Explanation:** Runs Flake8 (a Python code quality checker) in two passes:

1. **First pass (strict):** `--select=E9,F63,F7,F82` — only checks for **critical errors**:
   - `E9` — syntax errors (code won't run at all)
   - `F63` — invalid `assert` tests
   - `F7` — bad syntax in statements
   - `F82` — undefined variable names
   - If any of these are found, the **build fails** immediately

2. **Second pass (advisory):** `--exit-zero` — checks for **style issues** (line length > 127 chars, code complexity > 10) but treats them as **warnings only** — the build won't fail for these.

---

### Lines 37–41: Step 5 — Run Tests

```yaml
    - name: Run Tests
      run: |
        # Placeholder for pytest
        # pytest tests/
        echo "Tests passed!"
```

**Explanation:** This is a **placeholder** step. The actual test command (`pytest tests/`) is commented out. Instead, it just prints "Tests passed!". Once you have actual tests written in a `tests/` folder, you would uncomment `pytest tests/` and remove the `echo` line.

