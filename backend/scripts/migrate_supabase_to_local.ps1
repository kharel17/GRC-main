$ErrorActionPreference = "Stop"

Write-Host "===================================================================="
Write-Host "  Starting Supabase to Local PostgreSQL Migration Pipeline"
Write-Host "===================================================================="

# ── 1. Ensure Local PostgreSQL Container is Running ──────────────────────────
Write-Host "`n[1/6] Ensuring local database container is running..."
docker compose up -d db

Write-Host "Waiting for database to be ready..."
$maxAttempts = 30
$attempt = 0
$dbReady = $false

while (-not $dbReady -and $attempt -lt $maxAttempts) {
    $attempt++
    try {
        $check = docker exec -i grc-main-db-1 psql -U grc_admin -d postgres -c "SELECT 1;" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dbReady = $true
            Write-Host "Database container is healthy and responding!"
        } else {
            Start-Sleep -Seconds 2
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $dbReady) {
    Write-Error "CRITICAL: Local database container failed to become ready in time."
    exit 1
}

# ── 2. Ensure Clean grc_db Database Exists ───────────────────────────────────
Write-Host "`n[2/6] Ensuring grc_db database exists..."
$dbExists = docker exec -i grc-main-db-1 psql -U grc_admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'grc_db';"
if ($dbExists.Trim() -ne "1") {
    Write-Host "Creating grc_db database..."
    docker exec -i grc-main-db-1 psql -U grc_admin -d postgres -c "CREATE DATABASE grc_db;"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "CRITICAL: Failed to create grc_db database."
        exit 1
    }
} else {
    Write-Host "Database grc_db exists."
}

# ── 3. Supabase Session Pooler Configuration & Pre-checks ────────────────────
Write-Host "`n[3/6] Connecting to Supabase Session Pooler..."
$SUPABASE_HOST = "aws-1-ap-southeast-2.pooler.supabase.com"
$SUPABASE_PORT = "5432"
$SUPABASE_USER = "postgres.htgojajcceunavgchrgc"
$SUPABASE_DB   = "postgres"
$SUPABASE_PASS = "VVGHSBUjYyvYWuhF"

Write-Host "Testing network reachability to $SUPABASE_HOST..."
try {
    [System.Net.Dns]::GetHostAddresses($SUPABASE_HOST) | Out-Null
    Write-Host "DNS resolution successful."
} catch {
    Write-Error "DNS Resolution failed for $SUPABASE_HOST. Halting script."
    exit 1
}

$dumpFilePath = "$PSScriptRoot\local_dump.sql"
$dumpDir = (Resolve-Path $PSScriptRoot).Path

# ── 4. Execute Clean Native Dump Without Supabase ACLs (NO REGEX) ────────────
Write-Host "`n[4/6] Executing clean native pg_dump from Supabase Session Pooler..."
docker run --rm `
    -v "${dumpDir}:/dump" `
    -e PGPASSWORD=$SUPABASE_PASS `
    postgres:17-alpine `
    pg_dump --clean --if-exists --no-owner --no-privileges --no-acl --schema=public `
    -h $SUPABASE_HOST -p $SUPABASE_PORT -U $SUPABASE_USER -d $SUPABASE_DB -F p -f /dump/local_dump.sql

# Exit code and file integrity check
if ($LASTEXITCODE -ne 0) {
    Write-Error "CRITICAL: pg_dump failed with exit code $LASTEXITCODE. Halting migration pipeline."
    exit 1
}

if (-not (Test-Path $dumpFilePath) -or (Get-Item $dumpFilePath).Length -lt 100) {
    $fileLen = if (Test-Path $dumpFilePath) { (Get-Item $dumpFilePath).Length } else { 0 }
    Write-Error "CRITICAL: pg_dump produced an empty or truncated file ($fileLen bytes). Halting."
    exit 1
}

$dumpSize = (Get-Item $dumpFilePath).Length
$dumpSizeKB = [math]::Round($dumpSize / 1KB, 2)
Write-Host "SUCCESS: Native pg_dump completed cleanly. File: $dumpFilePath ($dumpSize bytes / $dumpSizeKB KB)"

# ── 5. Restore into Local Database & Apply Permissions ───────────────────────
Write-Host "`n[5/6] Restoring dump into local database (grc_db)..."

# Reset public schema so no stale/conflicting tables remain before restoring
Write-Host "Resetting public schema in grc_db for pristine restore..."
docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public; GRANT ALL ON SCHEMA public TO grc_admin;"

# Copy dump into db container and execute via psql to bypass shell pipe encoding distortions
docker cp $dumpFilePath grc-main-db-1:/tmp/local_dump.sql
docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db -f /tmp/local_dump.sql

if ($LASTEXITCODE -ne 0) {
    Write-Error "CRITICAL: psql restore failed with exit code $LASTEXITCODE. Halting migration pipeline."
    exit 1
}

Write-Host "SUCCESS: psql restore completed cleanly with exit code 0."

# Apply standard PostgreSQL compliant privileges and enable app access
Write-Host "Applying compliant role privileges and schema settings..."
$postRestoreSql = @'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'grc_app_user') THEN
        CREATE USER grc_app_user WITH PASSWORD 'grc_app_secret';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE grc_db TO grc_app_user;
GRANT USAGE ON SCHEMA public TO grc_app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO grc_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO grc_app_user;

-- Enable Row Level Security (RLS) across all public tables
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' ENABLE ROW LEVEL SECURITY;';
    END LOOP;
END
$$;

-- Ensure current_org_id() accepts both app.org_id and app.current_org_id
CREATE OR REPLACE FUNCTION current_org_id() RETURNS uuid AS $$
BEGIN
    RETURN COALESCE(
        NULLIF(current_setting('app.org_id', true), '')::uuid,
        NULLIF(current_setting('app.current_org_id', true), '')::uuid
    );
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

ALTER POLICY org_isolation ON organizations USING (id = current_org_id());
ALTER POLICY org_isolation ON users USING (organization_id = current_org_id());
'@

$postRestoreSql | docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db

if ($LASTEXITCODE -ne 0) {
    Write-Error "CRITICAL: Applying post-restore permissions failed with exit code $LASTEXITCODE. Halting."
    exit 1
}

Write-Host "Post-restore permissions and schema settings applied successfully."

# ── 6. Verify Alembic State & SQLAlchemy Application Engine ──────────────────
Write-Host "`n[6/6] Verifying Alembic state and SQLAlchemy application engine..."

Write-Host "--- Checking alembic_version table in grc_db (post-restore) ---"
docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db -c "SELECT version_num FROM alembic_version;"

$repoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$pythonExe = "$repoRoot\backend\venv\Scripts\python.exe"

Push-Location $repoRoot
try {
    Write-Host "`n--- Running Alembic current ---"
    & $pythonExe -m alembic current
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Alembic current failed with exit code $LASTEXITCODE."
        exit 1
    }

    Write-Host "`n--- Running Alembic upgrade head ---"
    & $pythonExe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Alembic upgrade head failed with exit code $LASTEXITCODE."
        exit 1
    }

    # Ensure permissions and RLS enforcement for any tables created by Alembic upgrade head
    $postUpgradeSql = @'
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO grc_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO grc_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO grc_app_user;
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' ENABLE ROW LEVEL SECURITY;';
    END LOOP;
END
$$;
'@
    $postUpgradeSql | docker exec -i grc-main-db-1 psql -U grc_admin -d grc_db

    Write-Host "`n--- Running Cross-Tenant RLS & Application Engine Verification ---"
    & $pythonExe "$PSScriptRoot\verify_cross_tenant_rls.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Cross-tenant RLS verification failed with exit code $LASTEXITCODE."
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "`n===================================================================="
Write-Host "  Database Migration & Verification Pipeline Completed Successfully"
Write-Host "===================================================================="
