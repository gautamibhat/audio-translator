# Audio Translator

This is a learning-focused data engineering project I’m building to understand how an end-to-end audio processing pipeline works in practice.

The long-term goal is to take audio files through ingestion, preprocessing, transcription, storage, translation and downstream processing, while keeping the pipeline reliable, retry-safe and easy to run locally.

I’m building the project in stages so that the infrastructure and data flow are clear before adding the actual transcription and translation logic.

---

## Current Stage

### Stage 1 — Local Data Pipeline Foundation

Stage 1 sets up the local development foundation for the project.

The current stack includes:

- Apache Airflow for orchestration
- PostgreSQL for Airflow metadata
- Redis for Airflow workers
- SQL Server as the application database
- Python application code
- Microsoft ODBC Driver 18
- Docker and Docker Compose
- database bootstrap and migration scripts
- Airflow → SQL Server connectivity
- pipeline run tracking
- retry-safe / idempotent pipeline execution

The current flow is roughly:

```text
Airflow DAG
    ↓
Python application code
    ↓
SQL Server
    ↓
dbo.pipeline_run
```

Each Airflow run is tracked using its `dag_id` and `run_id`.

A new DAG run creates a new database record. If the same DAG run is retried, the existing record is updated instead of creating a duplicate.

---

# Prerequisites

Before setting up the project on a new machine, install the following.

## Git

Check that Git is available:

```bash
git --version
```

## Docker Desktop

Docker Desktop needs to be installed and running.

Check Docker:

```bash
docker --version
```

Check Docker Compose:

```bash
docker compose version
```

Confirm the Docker engine is running:

```bash
docker info
```

If `docker info` fails, start Docker Desktop before continuing.

### Apple Silicon Macs

SQL Server does not currently have a native ARM64 Linux image.

On Apple Silicon Macs, this project runs the SQL Server `linux/amd64` image through Docker emulation. This is fine for local development and learning, although it can be slower than running on an x86 machine.

---

# Setup on a New Machine

Once the prerequisites are installed, clone the repository:

```bash
git clone git@github.com:gautamibhat/audio-translator.git
cd audio-translator
```

Then run:

```bash
./scripts/setup.sh
```

The setup script is intended to take care of the local environment automatically, including:

- checking Docker and Docker Compose
- creating the local `.env` file when required
- generating local secrets
- building the custom Airflow image
- starting SQL Server
- creating the `audio_pipeline` database
- creating the application database user
- applying database migrations
- initializing Airflow
- starting the complete Docker stack
- creating the Airflow → SQL Server connection
- testing the database connection
- checking for DAG import errors

The setup script should be safe to run again. It should not intentionally delete existing database volumes or replace secrets that are already present.

---

# Starting the Project

After the initial setup, start the project with:

```bash
docker compose up -d
```

Check the running services with:

```bash
docker compose ps
```

---

# Airflow

Airflow is available locally at:

```text
http://localhost:8080
```

Local development credentials:

```text
Username: airflow
Password: airflow
```

The current Stage 1 DAG is:

```text
stage1_smoke_test
```

The DAG currently runs:

```text
start_pipeline_run
        ↓
verify_application_code
        ↓
verify_sqlserver_connection
        ↓
complete_pipeline_run
```

A successful run should finish with all four tasks in the `success` state.

---

# Stopping the Project

To stop the containers while keeping local database data:

```bash
docker compose down
```

Avoid using this during normal development:

```bash
docker compose down -v
```

The `-v` option also deletes Docker volumes, including the local PostgreSQL and SQL Server data.

Use it only when deliberately testing a completely clean rebuild.

---

# Adding or Updating DAGs

The local `dags/` directory is mounted into the Airflow containers, so adding or changing a DAG normally does not require restarting Docker.

Airflow should detect the change automatically.

Check for DAG import errors with:

```bash
docker compose exec airflow-apiserver \
  airflow dags list-import-errors
```

If the DAG processor genuinely needs to be restarted:

```bash
docker compose restart airflow-dag-processor
```

---

# Rebuilding After Dependency Changes

Changes to normal Python application code or DAG code do not usually require rebuilding the Docker image.

If `Dockerfile` or `requirements-airflow.txt` changes, rebuild with:

```bash
docker compose build
docker compose up -d --force-recreate
```

---

# Environment Variables

Local environment values and secrets are stored in:

```text
.env
```

This file must not be committed to Git.

The repository should contain:

```text
.env.example
```

which documents the variables the project expects without containing real passwords or API keys.

---

# Database

The application database is:

```text
audio_pipeline
```

The Airflow pipeline connects using:

```text
audio_pipeline_app
```

Airflow does not use the SQL Server `sa` account for application work.

Database scripts are organised as:

```text
sql/
├── bootstrap/
└── migrations/
```

`bootstrap/` contains administrative setup such as creating the application login.

`migrations/` contains application schema changes.

The Stage 1 migration creates:

```text
dbo.pipeline_run
```

which tracks each Airflow pipeline execution.

---

# Project Structure

```text
audio-translator/
├── dags/
│   └── stage1_smoke_test.py
├── src/
│   └── audio_translator/
│       ├── common/
│       ├── database/
│       ├── ingestion/
│       ├── transcription/
│       └── translation/
├── sql/
│   ├── bootstrap/
│   └── migrations/
├── scripts/
│   └── setup.sh
├── tests/
├── config/
├── plugins/
├── logs/
├── Dockerfile
├── docker-compose.yaml
├── requirements-airflow.txt
├── environment.yml
├── .env.example
└── README.md
```

I’m keeping orchestration and application logic separate where possible.

Airflow DAG files belong under `dags/`, while reusable Python logic belongs under `src/audio_translator/`.

---

# Stage 1 Status

Stage 1 covers:

```text
✅ Docker-based local environment
✅ Apache Airflow
✅ PostgreSQL + Redis
✅ Python application structure
✅ SQL Server
✅ dedicated application database user
✅ database bootstrap scripts
✅ database migrations
✅ Airflow → SQL Server connectivity
✅ pipeline run tracking
✅ RUNNING → SUCCESS status handling
✅ separate DAG runs create separate records
✅ retries of the same DAG run do not create duplicates
✅ automated local setup
✅ reproducible setup from the repository
```

---

# Next Stage

Stage 2 will start introducing the actual audio-processing workflow.

Before adding transcription itself, the next step is to design how an audio file moves through the system and how that journey should be represented in the database.

This will include areas such as:

- audio ingestion
- audio metadata
- processing status
- transcription jobs
- transcripts
- translation jobs
- translated output
- retry and failure information
- audit information
