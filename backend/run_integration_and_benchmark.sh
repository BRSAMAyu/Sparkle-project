#!/bin/bash
# Run Integration and Benchmark Tests for Sparkle AI
# 运行集成测试和性能基准测试

set -e

echo "🧪 Sparkle AI - Integration & Benchmark Tests"
echo "==========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check dependencies
echo -e "${YELLOW}📦 Checking dependencies...${NC}"

if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    pip install pytest pytest-asyncio pytest-benchmark
fi

if ! python -c "import numpy" &> /dev/null; then
    echo -e "${YELLOW}Installing numpy...${NC}"
    pip install numpy
fi

echo -e "${GREEN}✓ Dependencies ready${NC}"
echo ""

# Create results directory
RESULTS_DIR="test_results"
mkdir -p "$RESULTS_DIR"

# Integration Tests
echo -e "${GREEN}🔗 Running Integration Tests...${NC}"
echo ""

run_integration_test() {
    local test_file=$1
    local test_name=$2

    echo "  → $test_name"

    if pytest "$test_file" -v --tb=short > "$RESULTS_DIR/${test_name}.log" 2>&1; then
        echo -e "    ${GREEN}✓ PASSED${NC}"
        return 0
    else
        echo -e "    ${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Run integration tests
integration_tests=(
    "tests/integration/test_ab_test_lifecycle.py:A/B Test Experiment Lifecycle"
    "tests/integration/test_memory_evolution_workflow.py:Memory Evolution Workflow"
    "tests/integration/test_auto_seeding_workflow.py:Auto-Seeding Workflow"
)

integration_passed=0
integration_total=0

for test_info in "${integration_tests[@]}"; do
    IFS=':' read -r test_file test_name <<< "$test_info"
    if run_integration_test "$test_file" "$test_name"; then
        ((integration_passed++))
    fi
    ((integration_total++))
    echo ""
done

# Performance Benchmarks
echo -e "${GREEN}⚡ Running Performance Benchmarks...${NC}"
echo ""

run_benchmark() {
    local test_file=$1
    local test_name=$2

    echo "  → $test_name"

    if pytest "$test_file" -v --tb=short > "$RESULTS_DIR/${test_name}.log" 2>&1; then
        echo -e "    ${GREEN}✓ PASSED${NC}"
        return 0
    else
        echo -e "    ${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Run benchmarks
benchmarks=(
    "tests/benchmark/test_statistics_performance.py:Statistics Performance"
    "tests/benchmark/test_budget_optimization_performance.py:Budget Optimization Performance"
    "tests/benchmark/test_transparency_performance.py:Transparency Generator Performance"
)

benchmark_passed=0
benchmark_total=0

for test_info in "${benchmarks[@]}"; do
    IFS=':' read -r test_file test_name <<< "$test_info"
    if run_benchmark "$test_file" "$test_name"; then
        ((benchmark_passed++))
    fi
    ((benchmark_total++))
    echo ""
done

# Summary
echo "==========================================="
echo "📊 Test Results Summary"
echo "==========================================="
echo ""

echo -e "${YELLOW}Integration Tests:${NC}"
echo "  Passed: $integration_passed/$integration_total"
if [ $integration_passed -eq $integration_total ]; then
    echo -e "  ${GREEN}✓ All integration tests passed!${NC}"
else
    echo -e "  ${RED}✗ Some integration tests failed${NC}"
    echo "  Check logs in: $RESULTS_DIR/"
fi
echo ""

echo -e "${YELLOW}Performance Benchmarks:${NC}"
echo "  Passed: $benchmark_passed/$benchmark_total"
if [ $benchmark_passed -eq $benchmark_total ]; then
    echo -e "  ${GREEN}✓ All benchmarks passed!${NC}"
else
    echo -e "  ${RED}✗ Some benchmarks failed${NC}"
    echo "  Check logs in: $RESULTS_DIR/"
fi
echo ""

# Overall
total_tests=$((integration_total + benchmark_total))
total_passed=$((integration_passed + benchmark_passed))

echo "Total: $total_passed/$total_tests passed"

if [ $total_passed -eq $total_tests ]; then
    echo -e "${GREEN}🎉 All tests passed! System is production-ready.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Review logs for details.${NC}"
    exit 1
fi
