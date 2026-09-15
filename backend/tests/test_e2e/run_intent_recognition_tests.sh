#!/bin/bash
# Intent Recognition E2E Test Runner
# ===================================
#
# This script runs comprehensive end-to-end tests for Core Chain 1:
# Intent Recognition & Dynamic Information Completion
#
# Usage:
#   ./run_intent_recognition_tests.sh          # Run all tests
#   ./run_intent_recognition_tests.sh unit     # Run unit tests only
#   ./run_intent_recognition_tests.sh e2e      # Run e2e tests only
#   ./run_intent_recognition_tests.sh perf     # Run performance benchmarks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BACKEND_DIR"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Core Chain 1 E2E Test Suite${NC}"
echo -e "${BLUE}Intent Recognition & Clarification${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Function to print section header
print_section() {
    echo ""
    echo -e "${BLUE}>>>> $1${NC}"
    echo ""
}

# Function to run test with summary
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    print_section "Running: $test_name"

    if eval "$test_cmd"; then
        echo -e "${GREEN}✓ $test_name PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name FAILED${NC}"
        return 1
    fi
}

# Parse command line arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    unit)
        print_section "Unit Tests"
        run_test "Intent Classification Unit Tests" \
            "pytest tests/test_exam_intent_detection.py -v"

        run_test "Sufficiency Checker Unit Tests" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteB -v"

        run_test "Voice Input Preprocessing Tests" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteC -v"
        ;;

    e2e)
        print_section "End-to-End Tests"

        run_test "Intent Recognition E2E" \
            "python tests/test_e2e/intent_clarification_e2e_test.py"

        run_test "Core Chain 1 Comprehensive E2E" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py -v"

        run_test "Real-world Scenarios" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteE -v"
        ;;

    perf)
        print_section "Performance Benchmarks"

        run_test "Classification Latency" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteD::test_classification_performance -v -s"

        run_test "Concurrent Classification" \
            "pytest tests/test_e2e/test_core_chain_1_intent_recognition.py::TestSuiteD::test_concurrent_classification -v -s"
        ;;

    all|*)
        print_section "Running Complete Test Suite"

        # Track overall results
        PASSED=0
        FAILED=0

        # Unit Tests
        if pytest tests/test_exam_intent_detection.py -v; then
            ((PASSED++))
        else
            ((FAILED++))
        fi

        # E2E Tests
        if pytest tests/test_e2e/test_core_chain_1_intent_recognition.py -v; then
            ((PASSED++))
        else
            ((FAILED++))
        fi

        # Standalone E2E Script
        if python tests/test_e2e/intent_clarification_e2e_test.py; then
            ((PASSED++))
        else
            ((FAILED++))
        fi

        # Print summary
        echo ""
        echo -e "${BLUE}======================================${NC}"
        echo -e "${BLUE}Test Summary${NC}"
        echo -e "${BLUE}======================================${NC}"
        echo -e "Passed: ${GREEN}$PASSED${NC}"
        echo -e "Failed: ${RED}$FAILED${NC}"

        if [ $FAILED -eq 0 ]; then
            echo -e "\n${GREEN}✓ ALL TESTS PASSED${NC}"
            exit 0
        else
            echo -e "\n${RED}✗ SOME TESTS FAILED${NC}"
            exit 1
        fi
        ;;
esac

echo ""
echo -e "${GREEN}Test run completed!${NC}"
