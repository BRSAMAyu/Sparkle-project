# Integration Test Runner Script for Windows
# Runs all integration tests for the Sparkle system

param(
    [Parameter(Position=0)]
    [ValidateSet("all", "websocket", "grpc", "notification", "cache", "auth", "plan_review", "e2e")]
    [string]$TestType = "all",

    [switch]$Verbose = $false,

    [string]$PythonBackendDir = "backend",
    [string]$GoGatewayDir = "backend\gateway",
    [string]$FlutterDir = "mobile"
)

# Configuration
$ErrorActionPreference = "Continue"

# Functions
function Log-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Log-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Log-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-Services {
    Log-Info "Checking if required services are running..."

    # Check PostgreSQL
    try {
        $null = pg_isready -h localhost -p 5432 -E ADPCM -q
        if ($LASTEXITCODE -eq 0) {
            Log-Info "PostgreSQL is running"
        } else {
            Log-Warn "PostgreSQL may not be running"
        }
    } catch {
        Log-Warn "Could not check PostgreSQL status"
    }

    # Check Redis
    try {
        $result = redis-cli ping 2>&1
        if ($result -eq "PONG") {
            Log-Info "Redis is running"
        } else {
            Log-Warn "Redis may not be running"
        }
    } catch {
        Log-Warn "Could not check Redis status"
    }

    # Check Go Gateway
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Log-Info "Go Gateway is running"
        } else {
            Log-Warn "Go Gateway may not be running"
        }
    } catch {
        Log-Warn "Could not check Go Gateway status"
    }

    # Check Python gRPC server
    try {
        $result = grpcurl -plaintext localhost:50051 list 2>&1
        if ($LASTEXITCODE -eq 0) {
            Log-Info "Python gRPC server is running"
        } else {
            Log-Warn "Python gRPC server may not be running"
        }
    } catch {
        Log-Warn "Could not check Python gRPC server status"
    }
}

function Invoke-PythonTests {
    Log-Info "Running Python integration tests..."

    Push-Location $PythonBackendDir

    # Activate virtual environment if exists
    if (Test-Path ".venv") {
        & .venv\Scripts\Activate.ps1
    }

    # Run tests based on TestType
    switch ($TestType) {
        "websocket" {
            pytest tests/integration/test_websocket_full_stack.py -v -s
        }
        "grpc" {
            pytest tests/integration/test_grpc_streaming_integration.py -v -s
        }
        "notification" {
            pytest tests/integration/test_notification_system_integration.py -v -s
        }
        "cache" {
            pytest tests/integration/test_cache_consistency_integration.py -v -s
        }
        "auth" {
            pytest tests/integration/test_auth_flow_integration.py -v -s
        }
        "all" {
            pytest tests/integration/ -v --cov=app --cov-report=html --cov-report=term
        }
        default {
            pytest tests/integration/ -v
        }
    }

    Pop-Location
}

function Invoke-GoTests {
    Log-Info "Running Go integration tests..."

    Push-Location $GoGatewayDir

    switch ($TestType) {
        "plan_review" {
            go test -v -run=TestPlanReviewE2E ./internal/handler
        }
        "websocket" {
            go test -v -run=TestWebSocket ./internal/handler
        }
        "all" {
            go test ./... -v -tags=integration
        }
        default {
            go test ./... -v
        }
    }

    Pop-Location
}

function Invoke-FlutterTests {
    Log-Info "Running Flutter integration tests..."

    Push-Location $FlutterDir

    switch ($TestType) {
        "all" {
            flutter test test/integration/ -v
        }
        "e2e" {
            flutter test test/integration/full_stack_e2e_test.dart -v
        }
        default {
            flutter test test/integration/ -v
        }
    }

    Pop-Location
}

function Invoke-AllTests {
    Log-Info "Running all integration tests..."

    $failed = 0

    # Python tests
    try {
        Invoke-PythonTests
    } catch {
        Log-Error "Python integration tests failed"
        $failed++
    }

    # Go tests
    try {
        Invoke-GoTests
    } catch {
        Log-Error "Go integration tests failed"
        $failed++
    }

    # Flutter tests
    try {
        Invoke-FlutterTests
    } catch {
        Log-Error "Flutter integration tests failed"
        $failed++
    }

    # Summary
    Write-Host ""
    Log-Info "===================="
    Log-Info "Test Summary"
    Log-Info "===================="

    if ($failed -eq 0) {
        Log-Info "All integration tests passed!"
    } else {
        Log-Error "$failed test suite(s) failed"
        exit 1
    }
}

function Show-Usage {
    Write-Host @"
Integration Test Runner

Usage: .\run-integration-tests.ps1 [TestType] [-Verbose] [-PythonBackendDir path] [-GoGatewayDir path] [-FlutterDir path]

Test Types:
  all              Run all integration tests (default)
  websocket        Run WebSocket integration tests
  grpc             Run gRPC integration tests
  notification     Run notification system tests
  cache            Run cache consistency tests
  auth             Run authentication flow tests
  plan_review      Run plan review E2E tests
  e2e              Run Flutter E2E tests

Examples:
  # Run all tests
  .\run-integration-tests.ps1 all

  # Run only WebSocket tests
  .\run-integration-tests.ps1 websocket

  # Run with verbose output
  .\run-integration-tests.ps1 all -Verbose

  # Run tests for specific backend
  .\run-integration-tests.ps1 all -PythonBackendDir custom_backend

"@
}

# Main execution
function Main {
    # Print banner
    Write-Host ""
    Log-Info "=========================================="
    Log-Info "   Sparkle Integration Test Runner      "
    Log-Info "=========================================="
    Write-Host ""

    # Check services
    Test-Services

    Write-Host ""
    Log-Info "Starting test execution..."
    Write-Host ""

    # Run tests based on type
    if ($TestType -eq "all") {
        Invoke-AllTests
    } elseif ($TestType -in @("websocket", "grpc", "notification", "cache", "auth")) {
        Invoke-PythonTests
    } elseif ($TestType -eq "plan_review") {
        Invoke-GoTests
    } elseif ($TestType -eq "e2e") {
        Invoke-FlutterTests
    } else {
        Log-Error "Unknown test type: $TestType"
        Show-Usage
        exit 1
    }

    Write-Host ""
    Log-Info "Test execution completed!"
}

# Run main
Main
