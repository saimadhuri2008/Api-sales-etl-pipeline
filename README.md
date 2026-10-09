# API Sales ETL Pipeline

A production-style **API-to-PostgreSQL incremental ETL pipeline** built with Python, Pandas, SQLAlchemy, and PostgreSQL.

The project extracts product data from a paginated REST API, validates and transforms the source records, identifies new or updated records using a source timestamp watermark, loads data through a staging layer, performs idempotent UPSERT operations into PostgreSQL, executes automated data-quality checks, protects watermark advancement when processing fails, and records operational metrics and logs for pipeline monitoring.

---

## Project Overview

This project demonstrates a practical ETL workflow for ingesting data from an external REST API into a relational database.

The pipeline was designed around several common ETL engineering requirements:

- REST API extraction
- Offset-based pagination
- HTTP retry handling
- Request timeout protection
- Source completeness validation
- Data cleaning and transformation
- Business-rule validation
- Rejected-record handling
- PostgreSQL staging
- Incremental loading
- Watermark management
- Idempotent target UPSERTs
- Automated data-quality checks
- Failure-aware watermark protection
- Operational logging
- Pipeline run metrics
- Exit-code-based execution status
- Controlled integration testing

The source dataset contains **194 products** retrieved from the DummyJSON Products API.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | ETL orchestration and processing |
| Pandas | Data transformation and validation |
| Requests | REST API communication |
| SQLAlchemy | PostgreSQL connectivity and SQL execution |
| psycopg2 | PostgreSQL database driver |
| PostgreSQL | Staging, target, and watermark storage |
| python-dotenv | Environment-based database configuration |
| PowerShell | Pipeline execution |
| Git / GitHub | Version control and portfolio publication |

---

## ETL Architecture

The pipeline follows this processing flow:

```text
                  REST API
                     |
                     v
          +----------------------+
          | Paginated Extraction |
          | Retry + Timeout       |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Source Completeness  |
          | Validation           |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Watermark Filter     |
          | New / Updated Rows   |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Transformation       |
          | Business Validation  |
          +----------+-----------+
                     |
             +-------+-------+
             |               |
             v               v
       Valid Records    Rejected Records
             |
             v
          +----------------------+
          | PostgreSQL Staging   |
          | stg_products         |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Target UPSERT        |
          | products             |
          +----------+-----------+
                     |
                     v
          +----------------------+
          | Data Quality Checks  |
          +----------+-----------+
                     |
                PASS | FAIL
             +-------+-------+
             |               |
             v               v
      Advance Watermark   Keep Existing
                         Watermark
             |
             v
          +----------------------+
          | Logging & Run Metrics|
          +----------------------+
```

The central reliability rule is:

> **The watermark advances only after the incremental batch has been transformed, loaded, and successfully passed post-load data-quality validation.**

This prevents failed or invalid batches from being incorrectly marked as successfully processed.

---

# Pipeline Components

## 1. API Extraction

The pipeline extracts product data from the DummyJSON Products API.

The source fields used by the pipeline include:

- `id`
- `title`
- `category`
- `price`
- `discountPercentage`
- `rating`
- `stock`
- `brand`
- `sku`
- `meta.updatedAt`

The source `meta.updatedAt` value is converted into:

```text
source_updated_at
```

and used for incremental change detection.

---

## 2. Pagination

The API returns data in pages.

The extraction process uses offset-based pagination with:

```text
limit = 30
skip = 0, 30, 60, 90, ...
```

The pipeline continues requesting pages until the complete source dataset has been retrieved.

A successful full extraction currently retrieves:

```text
194 product(s)
```

Example:

```text
Fetched 30 product(s) with skip=0.
Fetched 30 product(s) with skip=30.
Fetched 30 product(s) with skip=60.
Fetched 30 product(s) with skip=90.
Fetched 30 product(s) with skip=120.
Fetched 30 product(s) with skip=150.
Fetched 14 product(s) with skip=180.

Pagination finished: 194 product(s) retrieved.
Extraction validated: 194/194 product(s) retrieved.
```

---

## 3. HTTP Reliability

API requests use a reusable `requests.Session` configured with retry handling.

Retries are configured for transient HTTP errors including:

```text
429
500
502
503
504
```

The extraction layer also uses request timeouts so that the pipeline does not wait indefinitely for an unresponsive API.

The retry mechanism was tested against a controlled HTTP `503` response to confirm retry exhaustion and failure behavior.

---

## 4. Source Completeness Validation

The extraction layer validates the number of records returned by the API against the source-reported total.

The pipeline fails extraction if:

- the API does not provide a usable total record count, or
- the number of retrieved records does not equal the reported source total.

Conceptually:

```text
retrieved records == source-reported total
```

A successful run reports:

```text
Extraction validated: 194/194 product(s) retrieved.
```

This prevents silently processing an incomplete API snapshot.

---

# Transformation and Validation

The transformation layer standardizes incoming data before database loading.

## String Processing

String fields are normalized and stripped of surrounding whitespace.

Fields include:

```text
title
category
brand
sku
```

Missing brand values are standardized as:

```text
Unknown
```

The current API snapshot contains **92 products with missing brand values**, which are normalized during transformation.

---

## Numeric Conversion

Numeric fields are converted using controlled numeric conversion.

These include:

```text
id
price
discountPercentage
rating
stock
```

Invalid numeric values are converted to null-like values and subsequently handled by validation rules.

---

## Required Fields

Critical fields are validated before loading.

These include fields such as:

```text
id
title
category
price
stock
sku
source_updated_at
```

Records violating required-field rules are rejected.

---

## Business Rules

The transformation layer validates the following rules:

```text
id > 0
price > 0
0 <= discountPercentage <= 100
0 <= rating <= 5
stock >= 0
```

Duplicate product IDs and duplicate SKUs are also detected.

---

## Rejected Records

Invalid source records are separated from valid records rather than silently loaded into the warehouse.

Each rejected record contains a:

```text
rejection_reason
```

A record may contain multiple rejection reasons.

A controlled transformation test injects invalid data and verifies detection of:

```text
Invalid rating    2
Invalid price     1
Missing title     1
Invalid stock     1
Duplicate SKU     1
```

The controlled test produces:

```text
189 valid products
5 rejected products
```

from the 194-record source snapshot.

---

# PostgreSQL Loading

The pipeline uses two primary product tables:

```text
stg_products
products
```

and a separate watermark-control table:

```text
etl_watermark
```

---

## Staging Table

Validated incremental records are first loaded into:

```text
stg_products
```

The staging table provides an intermediate layer between transformation and the final target table.

Before loading a new incremental batch, the staging table is cleared.

This ensures that staging represents the current batch being processed.

---

## Target Table

The final product data is stored in:

```text
products
```

The target table includes fields such as:

```text
product_id
title
category
price
discount_percentage
rating
stock
brand
sku
created_at
updated_at
```

`product_id` is the primary key.

---

# Idempotent UPSERT Strategy

The staging-to-target process uses PostgreSQL UPSERT logic.

Conceptually:

```sql
INSERT INTO products (...)
SELECT ...
FROM stg_products

ON CONFLICT (product_id)
DO UPDATE ...
```

Existing rows are updated only when relevant values have actually changed.

This makes repeated executions idempotent.

For example, rerunning the pipeline against unchanged source data does not create duplicate products.

During validation, an unchanged target load produced:

```text
Target load completed: 0 row(s) affected.
```

A controlled change to an existing product resulted in exactly one affected target row.

---

# Incremental Loading

The pipeline implements timestamp-based incremental processing.

The source provides:

```text
meta.updatedAt
```

which is stored in the extracted dataset as:

```text
source_updated_at
```

The pipeline maintains the most recently processed timestamp in:

```text
etl_watermark
```

under the pipeline name:

```text
products_api_etl
```

---

## Incremental Filter

For an existing watermark, the pipeline selects records where:

```text
source_updated_at > last_watermark
```

Conceptually:

```python
incremental_data = source_data[
    source_data["source_updated_at"] > watermark
]
```

If no watermark exists, the run behaves as an initial load and processes the complete source snapshot.

---

## No-Change Runs

When no source record has a timestamp later than the stored watermark, the pipeline exits successfully without transforming or loading unnecessary data.

Example:

```text
Extracted records: 194

Incremental records identified: 0
Records selected for processing: 0

No new or updated records found.
Nothing to process.
```

A no-change run is considered a successful ETL execution.

---

# Watermark Management

The watermark table stores pipeline state such as:

```text
pipeline_name
last_watermark
last_run_at
status
```

The pipeline reads the existing watermark before incremental filtering.

A candidate new watermark is calculated from:

```text
MAX(source_updated_at)
```

for the selected incremental batch.

However, the candidate watermark is **not immediately committed**.

It advances only after successful downstream processing.

---

## Watermark Safety

The pipeline follows this sequence:

```text
Read current watermark
        |
        v
Extract source
        |
        v
Identify incremental records
        |
        v
Transform
        |
        v
Load staging
        |
        v
UPSERT target
        |
        v
Run data-quality checks
        |
        +--------------------+
        |                    |
      PASS                  FAIL
        |                    |
        v                    v
Advance watermark      Do NOT advance
```

This prevents a failed batch from being skipped during future executions.

---

# Automated Data-Quality Checks

The pipeline performs **8 post-load data-quality checks**.

## 1. Staging Reconciliation

Confirms that the number of staging records equals the number of expected valid records.

```text
expected staging count == actual staging count
```

---

## 2. Staging NULL Critical Fields

Checks staging for NULL values in critical fields such as:

```text
id
title
category
price
stock
sku
source_updated_at
```

---

## 3. Staging Business-Rule Validation

Checks staging for invalid values including:

```text
price <= 0
discount_percentage < 0
discount_percentage > 100
rating < 0
rating > 5
stock < 0
```

---

## 4. Duplicate Target Product IDs

Checks the target for duplicate product IDs.

---

## 5. Duplicate Target SKUs

Checks the target for duplicate SKU values.

---

## 6. Target NULL Critical Fields

Checks the final target table for NULL values in required fields.

---

## 7. Target Business-Rule Validation

Checks the final target table for invalid price, discount, rating, and stock values.

---

## 8. Target Row Count

Confirms that the target contains records.

A successful validation reports:

```text
Data quality: 8/8 checks passed.
```

---

# Failure Protection Test

The project includes a controlled integration test that proves a data-quality failure prevents watermark advancement.

The test:

1. Reads the existing watermark.
2. Extracts a clean API snapshot.
3. Simulates one source record with a timestamp five minutes newer than the watermark.
4. Confirms exactly one incremental record is detected.
5. Transforms and stages the record.
6. Runs the normal target load.
7. Deliberately changes the staging price to `-10`.
8. Runs the real data-quality checks.
9. Confirms the invalid staging value is detected.
10. Skips watermark advancement.
11. Confirms the watermark remains unchanged.
12. Restores staging from the clean source snapshot.

Example result:

```text
[FAIL] Staging invalid business values - invalid_records=1

Data quality: 7/8 checks passed.

Expected DQ failure detected.
Watermark update intentionally skipped.

TEST PASSED
1. Newer source record was detected.
2. Controlled staging corruption was detected by DQ.
3. Watermark advancement was skipped.
4. Watermark remained unchanged.
```

After the test, the staging table is restored to its clean state.

---

# Operational Logging

The project maintains two forms of pipeline observability.

## Human-Readable Log

Operational events are written to:

```text
logs/pipeline.log
```

Example:

```text
INFO | Incremental products ETL started.
INFO | Current watermark: ...
INFO | Extraction completed: 194 record(s).
INFO | Incremental filtering completed: 0 record(s) selected.
INFO | No incremental records found. Pipeline completed with no data changes.
INFO | Pipeline run finished: status=SUCCESS, extracted=194, selected=0, ...
```

Exceptions are logged with stack-trace information to support troubleshooting.

---

## Structured Run Metrics

Each execution also writes a structured record to:

```text
logs/pipeline_runs.csv
```

Metrics include:

```text
run_timestamp
status
rows_extracted
rows_selected
rows_valid
rows_rejected
rows_staged
target_affected
watermark_before
watermark_after
duration_seconds
error_message
```

This provides a lightweight audit trail of ETL execution history.

Generated logs are excluded from Git through `.gitignore`.

---

# Exit Codes

The production pipeline uses process exit codes so that external schedulers or automation tools can determine whether execution succeeded.

```text
0 = successful execution
1 = failed execution
```

For example:

```powershell
.\run_pipeline.ps1
$LASTEXITCODE
```

A successful run returns:

```text
0
```

---

# Project Structure

```text
api_sales_etl/
│
├── data/
│
├── logs/
│   ├── pipeline.log
│   └── pipeline_runs.csv
│
├── sql/
│   ├── create_tables.sql
│   └── upsert_products.sql
│
├── src/
│   ├── data_quality.py
│   ├── db_config.py
│   ├── extract_api.py
│   ├── extract_paginated.py
│   ├── incremental.py
│   ├── incremental_pipeline.py
│   ├── inspect_data.py
│   ├── inspect_watermark.py
│   ├── load_staging.py
│   ├── load_target.py
│   ├── logger.py
│   ├── transform.py
│   └── watermark.py
│
├── tests/
│   ├── incremental_test.py
│   ├── pipeline_dq_failure_test.py
│   └── transform_test.py
│
├── .env
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── run_pipeline.ps1
```

> `.env`, `.venv`, generated logs, Python cache files, and local generated data are excluded from version control.

---

# Main Source Modules

## `extract_api.py`

Initial API extraction implementation used to validate connectivity and inspect the source response.

## `extract_paginated.py`

Production API extraction module responsible for:

- pagination
- retry handling
- request timeout
- extraction completeness validation
- source-field selection
- source timestamp conversion

## `transform.py`

Responsible for:

- data-type conversion
- string normalization
- missing-brand handling
- required-field validation
- business-rule validation
- duplicate detection
- valid/rejected record separation
- rejection reasons

## `incremental.py`

Filters the source snapshot against the stored watermark to identify new or updated records.

## `load_staging.py`

Loads validated incremental records into PostgreSQL staging.

## `load_target.py`

Executes staging-to-target UPSERT logic.

## `watermark.py`

Reads and updates ETL watermark state.

## `data_quality.py`

Executes the eight post-load data-quality checks.

## `logger.py`

Configures human-readable operational logging.

## `incremental_pipeline.py`

Main production orchestration layer.

Coordinates:

```text
Watermark
→ Extraction
→ Incremental filtering
→ Transformation
→ Staging
→ Target UPSERT
→ Data-quality validation
→ Watermark advancement
→ Logging
```

---

# SQL Files

## `create_tables.sql`

Contains SQL definitions for the PostgreSQL tables used by the ETL workflow.

## `upsert_products.sql`

Contains the staging-to-target UPSERT logic used to insert new products and update changed products.

---

# Installation

## Prerequisites

Install:

- Python 3
- PostgreSQL
- Git

A PostgreSQL administration tool such as pgAdmin can also be used to inspect the database and execute SQL scripts.

---

## 1. Clone the Repository

```powershell
git clone https://github.com/PitchGates/api-sales-etl-pipeline.git
```

Move into the project:

```powershell
cd api_sales_etl
```

---

## 2. Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

The project directly depends on:

```text
pandas
requests
SQLAlchemy
psycopg2-binary
python-dotenv
```

---

# Environment Configuration

Copy:

```text
.env.example
```

to:

```text
.env
```

Example configuration:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=api_sales_dw
DB_USER=postgres
DB_PASSWORD=your_password_here
```

Replace the placeholder values with the appropriate local PostgreSQL settings.

The real `.env` file is excluded from Git.

---

# Database Setup

Create the PostgreSQL database:

```text
api_sales_dw
```

Then execute:

```text
sql/create_tables.sql
```

against that database.

This creates the database objects required by the pipeline.

The project uses:

```text
stg_products
products
etl_watermark
```

for staging, final product storage, and incremental state management.

---

# Running the Pipeline

The recommended entry point is the PowerShell runner:

```powershell
.\run_pipeline.ps1
```

The runner:

1. Resolves the project directory.
2. Verifies the project virtual environment exists.
3. Verifies the pipeline entry point exists.
4. Verifies `.env` exists.
5. Executes the pipeline using `.venv\Scripts\python.exe`.
6. Captures the pipeline exit code.
7. Reports success or failure to the terminal.
8. Returns the pipeline exit code to the calling process.

The pipeline can also be executed directly:

```powershell
python src\incremental_pipeline.py
```

---

# Example Successful No-Change Run

```text
Starting incremental products ETL...

Current watermark: ...
Starting paginated API extraction...

Pagination finished: 194 product(s) retrieved.
Extraction validated: 194/194 product(s) retrieved.

Extracted records: 194

Incremental records identified: 0
Records selected for processing: 0

No new or updated records found.
Nothing to process.

Pipeline run logged to pipeline_runs.csv
Pipeline duration: 7.449 second(s)

Pipeline completed successfully
```

Exit code:

```text
0
```

---

# Testing

The project includes controlled tests for transformation, incremental processing, and pipeline failure protection.

---

## Transformation Validation Test

Run:

```powershell
python tests\transform_test.py
```

The test deliberately injects:

- negative price
- invalid rating
- missing title
- negative stock
- duplicate SKU

Expected result:

```text
Valid products: 189
Rejected products: 5

Invalid rating    2
Invalid price     1
Missing title     1
Invalid stock     1
Duplicate SKU     1

TEST PASSED
```

---

## Incremental Change Detection Test

Run:

```powershell
python tests\incremental_test.py
```

The test simulates one product with:

```text
source_updated_at = watermark + 5 minutes
```

Expected result:

```text
Incremental records identified: 1
Records selected: 1

TEST PASSED:
Only the simulated changed record was selected.
```

---

## Data-Quality Failure / Watermark Protection Test

Run:

```powershell
python tests\pipeline_dq_failure_test.py
```

This is a controlled integration test that temporarily corrupts staging data.

Expected behavior:

```text
Staging invalid business values - FAIL

Expected DQ failure detected.
Watermark update intentionally skipped.

Watermark after DQ failure:
<same watermark as before>

TEST PASSED
```

The test restores clean staging data after execution.

---

# Security and Repository Hygiene

Sensitive and generated files are excluded through `.gitignore`.

Examples include:

```text
.env
.venv/
__pycache__/
*.pyc
logs/*.log
logs/*.csv
data/*.csv
data/*.json
.vscode/
.idea/
.pytest_cache/
```

This prevents:

- database credentials from being committed
- local virtual environments from being uploaded
- generated execution logs from polluting source control
- Python cache files from entering the repository

A safe configuration template is provided through:

```text
.env.example
```

---

# Reliability Features

The project implements several safeguards commonly required in ETL workflows:

| Risk | Pipeline Control |
|---|---|
| API temporarily unavailable | HTTP retry strategy |
| API hangs | Request timeout |
| Incomplete pagination | Source-count reconciliation |
| Invalid source data | Transformation validation |
| Multiple validation failures | Field-specific rejection reasons |
| Duplicate records | ID and SKU duplicate checks |
| Repeated pipeline execution | Idempotent UPSERT |
| Unnecessary full reloads | Timestamp watermark |
| Invalid staging data | Post-load DQ checks |
| Failed batch skipped permanently | Watermark advances only after DQ success |
| Operational troubleshooting | Human-readable log |
| Run auditing | Structured CSV metrics |
| Scheduler integration | Process exit codes |
| Credentials exposed in repository | `.env` excluded from Git |

---

# Engineering Decisions

## Why Use a Staging Table?

The staging layer separates source ingestion from final target persistence.

This provides a controlled point for:

- batch reconciliation
- validation
- target loading
- troubleshooting

before data is treated as part of the final target dataset.

---

## Why Use a Watermark?

Without incremental processing, the pipeline would repeatedly process the complete API snapshot.

The watermark allows the pipeline to identify only records newer than the last successfully processed source timestamp.

This reduces unnecessary downstream processing.

---

## Why Advance the Watermark Last?

Advancing the watermark too early creates a reliability risk.

For example:

```text
extract
→ update watermark
→ load fails
```

would cause the failed records to appear already processed during the next run.

This project instead uses:

```text
extract
→ transform
→ stage
→ target load
→ DQ
→ update watermark
```

Therefore a failed batch does not advance the pipeline's incremental state.

---

## Why Keep Both Logs and Run Metrics?

`pipeline.log` is intended primarily for human troubleshooting.

`pipeline_runs.csv` provides structured execution metrics that can be analyzed programmatically.

Together they provide lightweight pipeline observability without requiring an external monitoring platform.

---

# Skills Demonstrated

This project demonstrates hands-on experience with:

- Python ETL development
- REST API integration
- API pagination
- HTTP retry strategies
- Data extraction validation
- Pandas transformation
- Data cleaning
- Business-rule validation
- Rejected-record handling
- SQL
- PostgreSQL
- SQLAlchemy
- Staging-table design
- UPSERT patterns
- Incremental loading
- Timestamp watermarks
- Idempotent data loading
- Data-quality engineering
- Failure handling
- Pipeline logging
- Run metrics
- Exit-code handling
- Integration testing
- Environment-based configuration
- Git repository hygiene

---

# Portfolio Summary

This project demonstrates the development of an end-to-end incremental ETL pipeline that ingests paginated REST API data into PostgreSQL while incorporating production-oriented reliability controls.

Key capabilities include:

- extraction of a 194-record paginated API dataset
- retry and timeout handling
- source completeness validation
- transformation and business-rule enforcement
- rejected-record handling
- staging-to-target PostgreSQL loading
- idempotent UPSERT processing
- source-timestamp watermarking
- eight automated post-load data-quality checks
- failure-aware watermark protection
- structured pipeline metrics
- human-readable operational logging
- controlled integration testing

The result is a reproducible ETL workflow designed to demonstrate practical ETL and data-engineering patterns beyond a basic extract-transform-load script.

---

## Future Enhancements

Potential next steps include:

- scheduling the pipeline with an orchestration platform
- persisting rejected records for historical auditing
- migrating run metrics from CSV into a database audit table
- implementing automated unit tests with `pytest`
- containerizing the pipeline with Docker
- adding CI/CD validation
- integrating cloud-based orchestration
- adding analytical or dimensional downstream models
- implementing alerting for failed pipeline executions