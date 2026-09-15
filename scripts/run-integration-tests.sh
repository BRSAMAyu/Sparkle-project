#!/bin/bash

# Integration Test Runner Script
# Runs all integration tests for the Sparkle system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PYTHON_BACKEND_DIR="${PYTHON_BACKEND_DIR:-backend}"
GO_GATEWAY_DIR="${GO_GATEWAY_DIR:-backend/gateway}"
FLUTTER_DIR="${FLUTTER_DIR:-mobile}"

# Parse command line arguments
TEST_TYPE="${1:-all}"
VERBOSE="${VERBOSE:-false}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_services() {
    log_info "Checking if required services are running..."

    # Check PostgreSQL
    if pg_isready -h localhost -p 5432 &>/dev/null; then
        log_info "✓ PostgreSQL is running"
    else
        log_error "✗ PostgreSQL is not running"
        log_info "Start it with: make dev-all"
        exit 1
    fi

    # Check Redis
    if redis-cli ping &>/dev/null; then
        log_info "✓ Redis is running"
    else
        log_error "✗ Redis is not running"
        log_info "Start it with: make dev-all"
        exit 1
    fi

    # Check Go Gateway
    if curl -s http://localhost:8080/health &>/dev/null; then
        log_info "✓ Go Gateway is running"
    else
        log_warn "✗ Go Gateway is not running"
        log_info "Start it with: make gateway-dev"
    fi

    # Check Python gRPC server
    if grpcurl -plaintext localhost:50051 list &>/dev/null; then
        log_info "✓ Python gRPC server is running"
    else
        log_warn "✗ Python gRPC server is not running"
        log_info "Start it with: make grpc-server"
    fi
}

run_python_tests() {
    log_info "Running Python integration tests..."

    cd "$PYTHON_BACKEND_DIR"

    # Activate virtual environment if exists
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # Run specific test based on TEST_TYPE
    case $TEST_TYPE in
        websocket)
            pytest tests/integration/test_websocket_full_stack.py -v -s
            ;;
        grpc)
            pytest tests/integration/test_grpc_streaming_integration.py -v -s
            ;;
        notification)
            pytest tests/integration/test_notification_system_integration.py -v -s
            ;;
        cache)
            pytest tests/integration/test_cache_consistency_integration.py -v -s
            ;;
        auth)
            pytest tests/integration/test_auth_flow_integration.py -v -s
            ;;
        all)
            pytest tests/integration/ -v --cov=app --cov-report=html --cov-report=term
            ;;
        *)
            pytest tests/integration/ -v
            ;;
    esac
}

run_go_tests() {
    log_info "Running Go integration tests..."

    cd "$GO_GATEWAY_DIR"

    # Run tests
    case $TEST_TYPE in
        plan_review)
            go test -v -run=TestPlanReviewE2E ./internal/handler
            ;;
        websocket)
            go test -v -run=TestWebSocket ./internal/handler
            ;;
        all)
            go test ./... -v -tags=integration
            ;;
        *)
            go test ./... -v
            ;;
    esac
}

run_flutter_tests() {
    log_info "Running Flutter integration tests..."

    cd "$FLUTTER_DIR"

    # Run tests
    case $TEST_TYPE in
        all)
            flutter test test/integration/ -v
            ;;
        e2e)
            flutter test test/integration/full_stack_e2e_test.dart -v
            ;;
        *)
            flutter test test/integration/ -v
            ;;
    esac
}

run_all_tests() {
    log_info "Running all integration tests..."

    # Track failures
    FAILED=0

    # Python tests
    if ! run_python_tests; then
        log_error "Python integration tests failed"
        FAILED=$((FAILED + 1))
    fi

    # Go tests
    if ! run_go_tests; then
        log_error "Go integration tests failed"
        FAILED=$((FAILED + 1))
    fi

    # Flutter tests
    if ! run_flutter_tests; then
        log_error "Flutter integration tests failed"
        FAILED=$((FAILED + 1))
    fi

    # Summary
    echo ""
    log_info "===================="
    log_info "Test Summary"
    log_info "===================="

    if [ $FAILED -eq 0 ]; then
        log_info "✓ All integration tests passed!"
    else
        log_error "✗ $FAILED test suite(s) failed"
        exit 1
    fi
}

print_usage() {
    cat << EOF
Integration Test Runner

Usage: $0 [test_type] [options]

Test Types:
  all              Run all integration tests (default)
  websocket        Run WebSocket integration tests
  grpc             Run gRPC integration tests
  notification     Run notification system tests
  cache            Run cache consistency tests
  auth             Run authentication flow tests
  plan_review      Run plan review E2E tests
  e2e              Run Flutter E2E tests

Options:
  VERBOSE=true     Enable verbose output

Environment Variables:
  PYTHON_BACKEND_DIR    Path to Python backend (default: backend)
  GO_GATEWAY_DIR        Path to Go gateway (default: backend/gateway)
  FLUTTER_DIR          Path to Flutter app (default: mobile)

Examples:
  # Run all tests
  $0 all

  # Run only WebSocket tests
  $0 websocket

  # Run with verbose output
  VERBOSE=true $0 all

  # Run tests for specific backend
  PYTHON_BACKEND_DIR=custom_backend $0 all

EOF
}

# Main execution
main() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        print_usage
        exit 0
    fi

    # Print banner
    echo ""
    log_info "╔════════════════════════════════════════════╗"
    log_info "║   Sparkle Integration Test Runner         ║"
    log_info "╚════════════════════════════════════════════╝"
    echo ""

    # Check if services are running
    check_services

    echo ""
    log_info "Starting test execution..."
    echo ""

    # Run tests based on type
    if [ "$TEST_TYPE" = "all" ]; then
        run_all_tests
    elif [ "$TEST_TYPE" = "websocket" ] || [ "$TEST_TYPE" = "grpc" ] || [ "$TEST_TYPE" = "notification" ] || [ "$TEST_TYPE" = "cache" ] || [ "$TEST_TYPE" = "auth" ]; then
        run_python_tests
    elif [ "$TEST_TYPE" = "plan_review" ]; then
        run_go_tests
    elif [ "$TEST_TYPE" = "e2e" ]; then
        run_flutter_tests
    else
        log_error "Unknown test type: $TEST_TYPE"
        print_usage
        exit 1
    fi

    echo ""
    log_info "Test execution completed!"
}

# Run main
main "$@"
