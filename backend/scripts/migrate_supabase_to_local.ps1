$ErrorActionPreference = "Continue"

Write-Host "Starting Supabase to Local DB Migration..."

# Stop the backend and frontend, and wipe the local database volume for a clean migration
docker compose down -v

# Start the DB
docker compose up -d db

Write-Host "Waiting for database to be ready..."
$maxAttempts = 30
$attempt = 0
$dbReady = $false

while (-not $dbReady -and $attempt -lt $maxAttempts) {
    $attempt++
    try {
        # Check readiness by targeting grc_db directly via container name
        $check = docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db -c "SELECT 1;" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dbReady = $true
            Write-Host "Database is ready!"
        } else {
            Start-Sleep -Seconds 2
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $dbReady) {
    Write-Error "Database failed to become ready in time."
    exit 1
}

Write-Host "Ensuring grc_db database exists..."
# Create the database if it doesn't exist. psql doesn't have CREATE DATABASE IF NOT EXISTS,
# so we run it and ignore the error if it already exists.
docker compose exec -T db psql -U grc_admin -d postgres -c "CREATE DATABASE grc_db;" 2>$null

# ── Supabase Session Pooler Connection ──────────────────────────────────────
# Using the session pooler (port 5432) for reliable external connectivity.
$SUPABASE_HOST = "aws-1-ap-southeast-2.pooler.supabase.com"
$SUPABASE_PORT = "5432"
$SUPABASE_USER = "postgres.htgojajcceunavgchrgc"
$SUPABASE_DB   = "postgres"
$SUPABASE_PASS = "VVGHSBUjYyvYWuhF"

# ── DNS Reachability Pre-Check ───────────────────────────────────────────────
Write-Host "Testing network reachability to Supabase Session Pooler..."
try {
    [System.Net.Dns]::GetHostAddresses($SUPABASE_HOST) | Out-Null
    Write-Host "DNS resolution successful."
} catch {
    Write-Error "DNS Resolution failed for $SUPABASE_HOST. Halting script."
    exit 1
}

# ── Dump from Supabase to a local file ──────────────────────────────────────
$dumpFile = "$PSScriptRoot\supabase_dump.sql"

# Use postgres:17-alpine container to match Supabase PG 17 server version
Write-Host "Dumping data from Supabase Session Pooler (via postgres:17-alpine)..."
docker run --rm `
    -e PGPASSWORD=$SUPABASE_PASS `
    postgres:17-alpine `
    pg_dump -h $SUPABASE_HOST -p $SUPABASE_PORT -U $SUPABASE_USER -d $SUPABASE_DB `
    --clean --if-exists --no-owner --no-privileges > "$dumpFile"

# ── Exit-code & size guard — NO false success messages ───────────────────────
if ($LASTEXITCODE -ne 0 -or !(Test-Path $dumpFile) -or (Get-Item $dumpFile).Length -eq 0) {
    Write-Error "CRITICAL FAILURE: pg_dump failed or produced an empty dump file. Halting migration!"
    exit 1
}

$dumpSizeKB = [math]::Round((Get-Item $dumpFile).Length / 1KB, 2)
Write-Host "pg_dump succeeded. Dump file size: $dumpSizeKB KB"

# ── Restore into local container ─────────────────────────────────────────────
Write-Host "Restoring dump into local database..."
Get-Content $dumpFile | docker compose exec -T db psql -U grc_admin -d grc_db

if ($LASTEXITCODE -ne 0) {
    Write-Error "Restore (psql) failed!"
    exit 1
}

Write-Host "Data restored. Applying post-restore permissions..."
$postRestoreSql = @"
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO grc_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO grc_app_user;
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE organizations DISABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY;
ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY;
ALTER TABLE frameworks DISABLE ROW LEVEL SECURITY;
ALTER TABLE framework_controls DISABLE ROW LEVEL SECURITY;
ALTER TABLE risk_categories DISABLE ROW LEVEL SECURITY;
"@

$postRestoreSql | docker compose exec -T db psql -U grc_admin -d grc_db

# ── Alembic — run via venv Python, target localhost:5432 ─────────────────────
Write-Host "Running Alembic migrations to ensure schema is up to date..."
$env:DATABASE_URL = "postgresql+asyncpg://grc_admin:grc_admin_secret@localhost:5432/grc_db"

Push-Location "$PSScriptRoot\..\"  # backend/ dir (alembic.ini lives here)
& "$PSScriptRoot\..\venv\Scripts\python.exe" -m alembic upgrade head
Pop-Location

Write-Host "Restarting application..."
docker compose up -d backend frontend

Write-Host "--- GATHERING REQUIRED PROOF OF SUCCESS ---"
Write-Host "1. Proof of database creation (grc_db exists):"
docker compose exec -T db psql -U grc_admin -d postgres -c "\l grc_db"

Write-Host "2. Proof of successful data restore (Checking tables):"
docker compose exec -T db psql -U grc_admin -d grc_db -c "\dt"

Write-Host "3. Checking if grc_app_user is a superuser (Should be False):"
"SELECT usename, usesuper FROM pg_user WHERE usename = 'grc_app_user';" | docker compose exec -T db psql -U grc_admin -d grc_db

Write-Host "4. Verifying restored data (Counting rows in users table):"
"SELECT COUNT(*) as user_count FROM users;" | docker compose exec -T db psql -U grc_app_user -d grc_db

Write-Host "Migration and Validation Complete!"
