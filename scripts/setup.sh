#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

AIRFLOW_BASE_IMAGE="apache/airflow:3.3.2-python3.12"
AIRFLOW_CUSTOM_IMAGE="audio-translator-airflow:3.3.2-python3.12"

echo
echo "========================================"
echo " Audio Translator - Local Setup"
echo "========================================"
echo


# ---------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------

echo "→ Checking Docker..."

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed."
    echo "Install Docker Desktop and run this script again."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is installed but the Docker engine is not running."
    echo "Start Docker Desktop and run this script again."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose is not available."
    exit 1
fi

echo "✓ Docker is available"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

get_env_value() {
    local key="$1"

    if [[ -f .env ]]; then
        sed -n "s/^${key}=//p" .env | tail -n 1
    fi
}


set_env_if_missing() {
    local key="$1"
    local value="$2"

    touch .env

    if ! grep -q "^${key}=" .env; then
        printf '%s=%s\n' "$key" "$value" >> .env
    fi
}


generate_random_hex() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
    else
        docker run --rm \
            --entrypoint python \
            "$AIRFLOW_BASE_IMAGE" \
            -c 'import secrets; print(secrets.token_hex(16))'
    fi
}


generate_fernet_key() {
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<'PY'
import base64
import os

print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
    else
        docker run --rm \
            --entrypoint python \
            "$AIRFLOW_BASE_IMAGE" \
            -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'
    fi
}


# ---------------------------------------------------------
# 2. Create local environment configuration
# ---------------------------------------------------------

echo
echo "→ Preparing local environment..."

if [[ "$(uname -s)" == "Linux" ]]; then
    DEFAULT_AIRFLOW_UID="$(id -u)"
else
    DEFAULT_AIRFLOW_UID="50000"
fi

set_env_if_missing \
    "AIRFLOW_UID" \
    "$DEFAULT_AIRFLOW_UID"

set_env_if_missing \
    "AIRFLOW_IMAGE_NAME" \
    "$AIRFLOW_CUSTOM_IMAGE"

if [[ -z "$(get_env_value FERNET_KEY)" ]]; then
    FERNET_KEY="$(generate_fernet_key)"
    set_env_if_missing "FERNET_KEY" "$FERNET_KEY"
fi

if [[ -z "$(get_env_value MSSQL_SA_PASSWORD)" ]]; then
    MSSQL_SA_PASSWORD="MssqlA9_$(generate_random_hex)"
    set_env_if_missing \
        "MSSQL_SA_PASSWORD" \
        "$MSSQL_SA_PASSWORD"
fi

set_env_if_missing \
    "AUDIO_PIPELINE_DB_USER" \
    "audio_pipeline_app"

if [[ -z "$(get_env_value AUDIO_PIPELINE_DB_PASSWORD)" ]]; then
    AUDIO_PIPELINE_DB_PASSWORD="AppA9_$(generate_random_hex)"
    set_env_if_missing \
        "AUDIO_PIPELINE_DB_PASSWORD" \
        "$AUDIO_PIPELINE_DB_PASSWORD"
fi

MSSQL_SA_PASSWORD="$(get_env_value MSSQL_SA_PASSWORD)"
AUDIO_PIPELINE_DB_PASSWORD="$(get_env_value AUDIO_PIPELINE_DB_PASSWORD)"
AUDIO_PIPELINE_DB_USER="$(get_env_value AUDIO_PIPELINE_DB_USER)"

echo "✓ Environment configuration ready"


# ---------------------------------------------------------
# 3. Validate Docker Compose
# ---------------------------------------------------------

echo
echo "→ Validating Docker Compose..."

docker compose config >/dev/null

echo "✓ Docker Compose configuration valid"


# ---------------------------------------------------------
# 4. Build custom Airflow image
# ---------------------------------------------------------

echo
echo "→ Building Airflow image..."

docker compose build

echo "✓ Airflow image built"


# ---------------------------------------------------------
# 5. Start SQL Server
# ---------------------------------------------------------

echo
echo "→ Starting SQL Server..."

docker compose up -d sqlserver

echo "→ Waiting for SQL Server..."

SQL_READY=false

for attempt in {1..30}; do
    if docker compose exec -T sqlserver \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost \
        -U sa \
        -P "$MSSQL_SA_PASSWORD" \
        -C \
        -Q "SELECT 1;" \
        >/dev/null 2>&1
    then
        SQL_READY=true
        break
    fi

    sleep 5
done

if [[ "$SQL_READY" != "true" ]]; then
    echo "ERROR: SQL Server did not become ready."
    echo "Check:"
    echo "  docker compose logs sqlserver"
    exit 1
fi

echo "✓ SQL Server ready"


# ---------------------------------------------------------
# 6. Create application database
# ---------------------------------------------------------

echo
echo "→ Creating audio_pipeline database..."

docker compose exec -T sqlserver \
    /opt/mssql-tools18/bin/sqlcmd \
    -S localhost \
    -U sa \
    -P "$MSSQL_SA_PASSWORD" \
    -C \
    -Q "
IF DB_ID(N'audio_pipeline') IS NULL
BEGIN
    CREATE DATABASE audio_pipeline;
END;
"

echo "✓ Database ready"


# ---------------------------------------------------------
# 7. Create application login/user
# ---------------------------------------------------------

echo
echo "→ Configuring application database user..."

docker compose exec -T sqlserver \
    /opt/mssql-tools18/bin/sqlcmd \
    -S localhost \
    -U sa \
    -P "$MSSQL_SA_PASSWORD" \
    -C \
    -v APP_DB_PASSWORD="$AUDIO_PIPELINE_DB_PASSWORD" \
    < sql/bootstrap/001_create_app_login.sql

echo "✓ Application database user ready"


# ---------------------------------------------------------
# 8. Apply database migrations
# ---------------------------------------------------------

echo
echo "→ Applying database migrations..."

for migration in sql/migrations/*.sql; do

    [[ -f "$migration" ]] || continue

    echo "  Applying: $migration"

    docker compose exec -T sqlserver \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost \
        -U sa \
        -P "$MSSQL_SA_PASSWORD" \
        -C \
        < "$migration"

done

echo "✓ Database migrations applied"


# ---------------------------------------------------------
# 9. Initialize Airflow
# ---------------------------------------------------------

echo
echo "→ Initializing Airflow..."

docker compose up airflow-init

echo "✓ Airflow initialized"


# ---------------------------------------------------------
# 10. Start complete stack
# ---------------------------------------------------------

echo
echo "→ Starting application stack..."

docker compose up -d

echo "→ Waiting for Airflow API server..."

AIRFLOW_READY=false

for attempt in {1..30}; do

    if docker compose exec -T airflow-apiserver \
        airflow version \
        >/dev/null 2>&1
    then
        AIRFLOW_READY=true
        break
    fi

    sleep 5
done

if [[ "$AIRFLOW_READY" != "true" ]]; then
    echo "ERROR: Airflow API server did not become ready."
    echo "Check:"
    echo "  docker compose logs airflow-apiserver"
    exit 1
fi

echo "✓ Airflow ready"


# ---------------------------------------------------------
# 11. Configure Airflow → SQL Server connection
# ---------------------------------------------------------

echo
echo "→ Configuring Airflow SQL Server connection..."

docker compose exec -T airflow-apiserver \
    airflow connections delete sqlserver_pipeline \
    >/dev/null 2>&1 || true

docker compose exec -T airflow-apiserver \
    airflow connections add sqlserver_pipeline \
    --conn-type odbc \
    --conn-host sqlserver \
    --conn-login "$AUDIO_PIPELINE_DB_USER" \
    --conn-password "$AUDIO_PIPELINE_DB_PASSWORD" \
    --conn-port 1433 \
    --conn-schema audio_pipeline \
    --conn-extra \
    '{"driver":"ODBC Driver 18 for SQL Server","Encrypt":"Yes","TrustServerCertificate":"Yes"}'

echo "✓ Airflow connection created"


# ---------------------------------------------------------
# 12. Test database connection
# ---------------------------------------------------------

echo
echo "→ Testing Airflow → SQL Server connection..."

docker compose exec -T airflow-apiserver \
    airflow connections test sqlserver_pipeline

echo "✓ Airflow can connect to SQL Server"


# ---------------------------------------------------------
# 13. Check DAG parsing
# ---------------------------------------------------------

echo
echo "→ Checking Airflow DAGs..."

docker compose exec -T airflow-apiserver \
    airflow dags list-import-errors

echo
echo "========================================"
echo " Setup complete ✓"
echo "========================================"
echo
echo "Airflow:"
echo "  http://localhost:8080"
echo
echo "Username:"
echo "  airflow"
echo
echo "Password:"
echo "  airflow"
echo
echo "Next:"
echo "  Trigger stage1_smoke_test in Airflow."
echo
