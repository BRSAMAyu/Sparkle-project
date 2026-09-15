#!/usr/bin/env python3
"""
E2E Test Runner Script
======================

Convenient script to run all or specific E2E tests with proper setup and teardown.
Usage:
    python run_e2e_tests.py              # Run all E2E tests
    python run_e2e_tests.py --python     # Run only Python E2E tests
    python run_e2e_tests.py --go         # Run only Go integration tests
    python run_e2e_tests.py --flutter    # Run only Flutter integration tests
    python run_e2e_tests.py --smoke      # Run quick smoke tests
    python run_e2e_tests.py --report     # Generate test report
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")

    missing = []

    # Check Python
    try:
        result = subprocess.run(["python3", "--version"], capture_output=True)
        if result.returncode == 0:
            print_success(f"Python: {result.stdout.decode().strip()}")
        else:
            missing.append("Python 3")
    except FileNotFoundError:
        missing.append("Python 3")

    # Check Go
    try:
        result = subprocess.run(["go", "version"], capture_output=True)
        if result.returncode == 0:
            print_success(f"Go: {result.stdout.decode().strip()}")
        else:
            missing.append("Go")
    except FileNotFoundError:
        missing.append("Go")

    # Check Flutter
    try:
        result = subprocess.run(["flutter", "--version"], capture_output=True)
        if result.returncode == 0:
            version_info = result.stdout.decode().split('\n')[0]
            print_success(f"Flutter: {version_info}")
        else:
            missing.append("Flutter")
    except FileNotFoundError:
        missing.append("Flutter")

    # Check Docker (optional but recommended)
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True)
        if result.returncode == 0:
            print_success(f"Docker: {result.stdout.decode().strip()}")
        else:
            print_warning("Docker not found (optional)")
    except FileNotFoundError:
        print_warning("Docker not found (optional)")

    if missing:
        print_error(f"Missing dependencies: {', '.join(missing)}")
        return False

    return True


def setup_test_environment():
    """Setup test database and environment"""
    print_header("Setting Up Test Environment")

    # Set environment variables
    os.environ["SPARKLE_INTEGRATION"] = "true"
    os.environ["TEST_DATABASE_URL"] = "postgresql+asyncpg://sparkle:test@localhost:5432/sparkle_test"

    # Check if PostgreSQL is running
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", "sparkle-postgres-1"],
            capture_output=True,
        )
        if result.returncode == 0 and "true" in result.stdout.decode().lower():
            print_success("PostgreSQL container is running")
        else:
            print_warning("PostgreSQL container not running. Start with: make dev-all")
            return False
    except Exception as e:
        print_warning(f"Could not check PostgreSQL status: {e}")

    # Create test database
    print("Creating test database...")
    result = subprocess.run(
        [
            "docker", "exec", "-i", "sparkle-postgres-1",
            "psql", "-U", "sparkle", "-c",
            "DROP DATABASE IF EXISTS sparkle_test; CREATE DATABASE sparkle_test;"
        ],
        capture_output=True,
    )

    if result.returncode == 0:
        print_success("Test database created")
    else:
        print_error(f"Failed to create test database: {result.stderr.decode()}")
        return False

    # Run migrations
    print("Running migrations...")
    result = subprocess.run(
        ["alebic", "upgrade", "head"],
        cwd=Path(__file__).parent.parent / "backend",
        capture_output=True,
    )

    if result.returncode == 0:
        print_success("Migrations applied")
    else:
        print_error(f"Migration failed: {result.stderr.decode()}")
        return False

    return True


def run_python_tests(filters=None):
    """Run Python E2E tests"""
    print_header("Running Python E2E Tests")

    backend_dir = Path(__file__).parent.parent / "backend"
    cmd = ["pytest", "tests_e2e/", "-v", "--tb=short", "--cov=app", "--cov-report=term"]

    if filters:
        cmd.extend(["-k", filters])

    result = subprocess.run(cmd, cwd=backend_dir)

    if result.returncode == 0:
        print_success("Python E2E tests passed")
        return True
    else:
        print_error("Python E2E tests failed")
        return False


def run_go_tests(filters=None):
    """Run Go integration tests"""
    print_header("Running Go Integration Tests")

    gateway_dir = Path(__file__).parent.parent / "backend" / "gateway"
    cmd = ["go", "test", "./internal/handler/...", "-v", "-tags=integration", "-timeout=5m"]

    if filters:
        cmd.extend(["-run", filters])

    result = subprocess.run(cmd, cwd=gateway_dir)

    if result.returncode == 0:
        print_success("Go integration tests passed")
        return True
    else:
        print_error("Go integration tests failed")
        return False


def run_flutter_tests(filters=None):
    """Run Flutter integration tests"""
    print_header("Running Flutter Integration Tests")

    mobile_dir = Path(__file__).parent.parent / "mobile"
    cmd = [
        "flutter", "test", "integration_test/",
        "--dart-define=SPARKLE_INTEGRATION=true",
        "--timeout=5m"
    ]

    if filters:
        cmd.extend(["--name", filters])

    result = subprocess.run(cmd, cwd=mobile_dir)

    if result.returncode == 0:
        print_success("Flutter integration tests passed")
        return True
    else:
        print_error("Flutter integration tests failed")
        return False


def run_smoke_tests():
    """Run quick smoke tests"""
    print_header("Running Smoke Tests")

    results = []

    # Python smoke test
    print("Running Python smoke test...")
    result = run_python_tests("test_e2e_simple_chat_message_flow")
    results.append(("Python", result))

    # Go smoke test
    print("Running Go smoke test...")
    result = run_go_tests("TestE2E_CompleteChatFlow")
    results.append(("Go", result))

    # Print summary
    print_header("Smoke Test Results")
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"{status} | {name}")
        if not passed:
            all_passed = False

    return all_passed


def generate_report():
    """Generate test report"""
    print_header("Generating Test Report")

    report_dir = Path(__file__).parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)

    report_file = report_dir / f"e2e_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_file, "w") as f:
        f.write("# E2E Test Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write("## Test Coverage\n\n")
        f.write("### Python E2E Tests\n")
        f.write("- [x] Chat message flow\n")
        f.write("- [x] Plan creation\n")
        f.write("- [x] Task execution\n")
        f.write("- [x] Feedback loop\n\n")
        f.write("### Go Integration Tests\n")
        f.write("- [x] WebSocket lifecycle\n")
        f.write("- [x] gRPC communication\n")
        f.write("- [x] Request routing\n\n")
        f.write("### Flutter Integration Tests\n")
        f.write("- [x] UI interactions\n")
        f.write("- [x] State management\n")
        f.write("- [x] Offline mode\n")

    print_success(f"Report generated: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Run E2E tests")
    parser.add_argument("--python", action="store_true", help="Run Python E2E tests")
    parser.add_argument("--go", action="store_true", help="Run Go integration tests")
    parser.add_argument("--flutter", action="store_true", help="Run Flutter integration tests")
    parser.add_argument("--smoke", action="store_true", help="Run quick smoke tests")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    parser.add_argument("--no-setup", action="store_true", help="Skip environment setup")
    parser.add_argument("--filter", type=str, help="Filter tests by name")

    args = parser.parse_args()

    print_header("Sparkle E2E Test Runner")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Setup environment
    if not args.no_setup:
        if not setup_test_environment():
            print_error("Environment setup failed")
            sys.exit(1)

    # Run tests based on arguments
    results = {}

    if args.smoke:
        results["smoke"] = run_smoke_tests()
    elif args.python:
        results["python"] = run_python_tests(args.filter)
    elif args.go:
        results["go"] = run_go_tests(args.filter)
    elif args.flutter:
        results["flutter"] = run_flutter_tests(args.filter)
    elif args.report:
        generate_report()
        sys.exit(0)
    else:
        # Run all tests
        results["python"] = run_python_tests(args.filter)
        results["go"] = run_go_tests(args.filter)
        results["flutter"] = run_flutter_tests(args.filter)

    # Print summary
    print_header("Test Summary")
    all_passed = True
    for test_type, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"{status} | {test_type.capitalize()}")
        if not passed:
            all_passed = False

    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if all_passed:
        print_success("\nAll tests passed! ✓")
        sys.exit(0)
    else:
        print_error("\nSome tests failed! ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
