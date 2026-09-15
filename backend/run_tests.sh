#!/bin/bash
# Quick Test Runner for Sparkle AI Backend
# 快速测试运行脚本

set -e

echo "🧪 Sparkle AI Backend - Quick Test Runner"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found. Installing...${NC}"
    pip install pytest pytest-asyncio pytest-cov
fi

echo -e "${GREEN}✓ pytest installed${NC}"
echo ""

# Run new tests
echo -e "${GREEN}Running A/B Test Statistics Tests...${NC}"
pytest tests/unit/test_ab_test_statistics.py -v --tb=short || true

echo ""
echo -e "${GREEN}Running Transparency Generator Tests...${NC}"
pytest tests/unit/test_transparency_generator.py -v --tb=short || true

echo ""
echo -e "${GREEN}Running Memory Evolution Tests...${NC}"
pytest tests/unit/test_memory_evolution.py -v --tb=short || true

echo ""
echo -e "${GREEN}Running Content Quality Evaluator Tests...${NC}"
pytest tests/unit/test_content_quality_evaluator.py -v --tb=short || true

echo ""
echo -e "${GREEN}Running Budget Optimization Tests...${NC}"
pytest tests/unit/test_budget_optimization.py -v --tb=short || true

echo ""
echo -e "${GREEN}Running A/B Test Framework Tests...${NC}"
pytest tests/unit/test_ab_test_framework.py -v --tb=short || true

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Test execution complete!${NC}"
echo ""
echo "📊 To generate coverage report:"
echo "   pytest --cov=app.learning --cov=app.services --cov=app.orchestration --cov-report=html"
echo ""
