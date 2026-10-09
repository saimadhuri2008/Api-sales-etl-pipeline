# ============================================================
# API Sales ETL Pipeline Runner
# ============================================================

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------
# Resolve project paths
# ------------------------------------------------------------

$ProjectRoot = $PSScriptRoot

$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$PythonExecutable = Join-Path $VirtualEnvironment "Scripts\python.exe"
$PipelineScript = Join-Path $ProjectRoot "src\incremental_pipeline.py"


Write-Host ""
Write-Host "=========================================="
Write-Host " API Sales Incremental ETL Pipeline"
Write-Host "=========================================="
Write-Host ""


# ------------------------------------------------------------
# 1. Validate Python virtual environment
# ------------------------------------------------------------

if (-not (Test-Path $PythonExecutable)) {

    Write-Host "ERROR: Virtual environment was not found."
    Write-Host ""
    Write-Host "Expected Python executable:"
    Write-Host $PythonExecutable
    Write-Host ""
    Write-Host "Create the environment with:"
    Write-Host "python -m venv .venv"

    exit 1
}


# ------------------------------------------------------------
# 2. Validate pipeline entry point
# ------------------------------------------------------------

if (-not (Test-Path $PipelineScript)) {

    Write-Host "ERROR: Pipeline script was not found."
    Write-Host ""
    Write-Host "Expected pipeline script:"
    Write-Host $PipelineScript

    exit 1
}


# ------------------------------------------------------------
# 3. Validate environment configuration
# ------------------------------------------------------------

$EnvironmentFile = Join-Path $ProjectRoot ".env"

if (-not (Test-Path $EnvironmentFile)) {

    Write-Host "ERROR: .env configuration file was not found."
    Write-Host ""
    Write-Host "Create .env from .env.example and provide"
    Write-Host "your PostgreSQL connection settings."

    exit 1
}


# ------------------------------------------------------------
# 4. Run incremental ETL pipeline
# ------------------------------------------------------------

Write-Host "Project root:"
Write-Host $ProjectRoot
Write-Host ""

Write-Host "Starting ETL pipeline..."
Write-Host ""

& $PythonExecutable $PipelineScript

$PipelineExitCode = $LASTEXITCODE


# ------------------------------------------------------------
# 5. Report pipeline result
# ------------------------------------------------------------

Write-Host ""

if ($PipelineExitCode -eq 0) {

    Write-Host "=========================================="
    Write-Host " Pipeline completed successfully"
    Write-Host "=========================================="

}
else {

    Write-Host "=========================================="
    Write-Host " Pipeline FAILED"
    Write-Host " Exit code: $PipelineExitCode"
    Write-Host "=========================================="
}


# ------------------------------------------------------------
# 6. Return pipeline exit code
# ------------------------------------------------------------

exit $PipelineExitCode