#!/bin/bash
# Load Test Orchestration Script
# 负载测试编排脚本
#
# Usage:
#   ./scripts/run-load-tests.sh [command] [options]
#
# Commands:
#   all     - Run all load tests
#   locust  - Run Locust tests
#   k6      - Run K6 tests
#   status  - Show test environment status
#   clean   - Clean up test results
#
# Options:
#   --users N         - Number of users (default: 100)
#   --duration M      - Test duration in minutes (default: 5)
#   --spawn-rate N    - Users per second (default: 10)
#   --headless        - Run without web UI
#   --save-baseline   - Save results as baseline
#   --compare-baseline- Compare with saved baseline

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
TESTS_DIR="$BACKEND_DIR/tests/load"
RESULTS_DIR="$TESTS_DIR/results"
BASELINE_FILE="$RESULTS_DIR/baseline.json"
LOG_DIR="$RESULTS_DIR/logs"

# Default values
USERS=100
DURATION=5
SPAWN_RATE=10
HEADLESS=false
SAVE_BASELINE=false
COMPARE_BASELINE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_directories() {
    mkdir -p "$RESULTS_DIR"
    mkdir -p "$LOG_DIR"
}

check_dependencies() {
    log_info "Checking dependencies..."

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi

    # Check Locust
    if ! command -v locust &> /dev/null; then
        log_warn "Locust not found. Installing..."
        pip install locust
    fi

    # Check K6 (optional)
    if ! command -v k6 &> /dev/null; then
        log_warn "K6 not found. K6 tests will be skipped."
    fi

    log_info "Dependencies checked."
}

check_services() {
    log_info "Checking service status..."

    # Check if services are running
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_error "Gateway is not responding. Start services with: make dev-all"
        exit 1
    fi

    log_info "Services are running."
}

run_locust() {
    log_info "Running Locust load tests..."

    local locust_cmd="locust -f $TESTS_DIR/locustfile.py --host=http://localhost:8080"

    if [ "$HEADLESS" = true ]; then
        locust_cmd="$locust_cmd --headless --users $USERS --spawn-rate $SPAWN_RATE --run-time ${DURATION}m"
        log_info "Running headless: $USERS users, $DURATION minutes"
    else
        log_info "Starting web UI at http://localhost:8089"
    fi

    # Create timestamped log file
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local log_file="$LOG_DIR/locust_$timestamp.log"

    # Run Locust
    cd "$BACKEND_DIR"
    eval $locust_cmd 2>&1 | tee "$log_file"

    # Save results if requested
    if [ "$SAVE_BASELINE" = true ]; then
        log_info "Saving baseline results..."
        # Extract metrics from log (simplified)
        cp "$log_file" "$BASELINE_FILE"
    fi
}

run_k6() {
    if ! command -v k6 &> /dev/null; then
        log_warn "K6 not found. Skipping K6 tests."
        return
    fi

    log_info "Running K6 load tests..."

    local k6_file="$TESTS_DIR/k6/scenarios.js"

    if [ ! -f "$k6_file" ]; then
        log_warn "K6 test file not found: $k6_file"
        return
    fi

    # Create timestamped log file
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local log_file="$LOG_DIR/k6_$timestamp.json"

    # Run K6
    k6 run --out json="$log_file" \
        --env VUS=$USERS \
        --env DURATION="${DURATION}m" \
        "$k6_file"
}

run_all_tests() {
    log_info "Running all load tests..."
    log_info "Configuration: $USERS users, $DURATION minutes"

    # Run Locust
    run_locust

    # Run K6
    run_k6

    log_info "All tests completed."
}

compare_baseline() {
    if [ ! -f "$BASELINE_FILE" ]; then
        log_error "Baseline file not found. Run with --save-baseline first."
        exit 1
    fi

    log_info "Comparing with baseline..."

    # Simplified comparison (in production, use proper diffing)
    local latest_log=$(ls -t "$LOG_DIR"/locust_*.log 2>/dev/null | head -1)

    if [ -z "$latest_log" ]; then
        log_error "No recent test results found."
        exit 1
    fi

    log_info "Baseline: $BASELINE_FILE"
    log_info "Current: $latest_log"
    log_warn "Comparison not implemented. Review logs manually."
}

show_status() {
    log_info "Load Test Environment Status"
    echo ""

    # Service status
    echo "Services:"
    curl -s http://localhost:8080/health && echo "  ✓ Gateway" || echo "  ✗ Gateway"
    echo ""

    # Recent results
    echo "Recent Test Results:"
    if [ -d "$RESULTS_DIR" ]; then
        ls -lh "$LOG_DIR" 2>/dev/null | tail -5 || echo "  No results found"
    else
        echo "  No results directory"
    fi
    echo ""

    # Disk space
    echo "Disk Space:"
    df -h "$RESULTS_DIR" 2>/dev/null | tail -1
}

clean_results() {
    log_info "Cleaning up test results..."

    if [ -d "$RESULTS_DIR" ]; then
        # Remove old logs (keep last 5)
        find "$LOG_DIR" -name "*.log" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null

        # Remove old JSON results
        find "$LOG_DIR" -name "*.json" -type f | sort -r | tail -n +6 | xargs rm -f 2>/dev/null

        log_info "Cleaned old results (kept last 5)."
    else
        log_info "No results to clean."
    fi
}

# Parse arguments
COMMAND=${1:-all}
shift

while [[ $# -gt 0 ]]; do
    case $1 in
        --users)
            USERS="$2"
            shift 2
            ;;
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --spawn-rate)
            SPAWN_RATE="$2"
            shift 2
            ;;
        --headless)
            HEADLESS=true
            shift
            ;;
        --save-baseline)
            SAVE_BASELINE=true
            shift
            ;;
        --compare-baseline)
            COMPARE_BASELINE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main execution
create_directories
check_dependencies

case $COMMAND in
    all)
        check_services
        run_all_tests
        ;;
    locust)
        check_services
        run_locust
        ;;
    k6)
        check_services
        run_k6
        ;;
    status)
        show_status
        ;;
    clean)
        clean_results
        ;;
    *)
        echo "Usage: $0 {all|locust|k6|status|clean} [options]"
        echo ""
        echo "Options:"
        echo "  --users N         Number of concurrent users (default: 100)"
        echo "  --duration M      Test duration in minutes (default: 5)"
        echo "  --spawn-rate N    Users spawned per second (default: 10)"
        echo "  --headless        Run without web UI"
        echo "  --save-baseline   Save results as baseline"
        echo "  --compare-baseline Compare current results with baseline"
        exit 1
        ;;
esac

if [ "$COMPARE_BASELINE" = true ]; then
    compare_baseline
fi

log_info "Done!"
