"""
End-to-End Translation API Test
================================

This script performs a complete E2E test of the translation system:
1. Test API endpoint directly
2. Verify response format matches Flutter expectations
3. Test with real SiliconFlow credentials
4. Verify timeout configuration

Run with: cd backend && python tests/test_e2e/translation_e2e_test.py
"""
import asyncio
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx
from app.tools.translation_tool import TranslateTextTool, TranslateTextParams
from app.services.translation_service import TranslationService
from app.db.session import get_db


# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_result(test_name: str, passed: bool, detail: str = ""):
    """Print test result with color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {test_name}")
    if detail:
        print(f"       {detail}")


async def test_translation_service_direct():
    """Test translation service directly"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 1: Direct Translation Service Call{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    from app.services.translation_service import TranslationSegment

    service = TranslationService()

    # Test cases - using segments format (requires id and text)
    test_cases = [
        {"segments": [TranslationSegment(id="1", text="Hello, world!")], "source": "en", "target": "zh-CN"},
        {"segments": [TranslationSegment(id="2", text="The quick brown fox jumps over the lazy dog.")], "source": "en", "target": "zh-CN"},
        {"segments": [TranslationSegment(id="3", text="机器学习是人工智能的一个分支")], "source": "zh-CN", "target": "en"},
    ]

    results = []
    for i, case in enumerate(test_cases, 1):
        start = time.time()
        try:
            # Returns TranslationResult object with segments list
            result = await service.translate(
                segments=case["segments"],
                source_lang=case["source"],
                target_lang=case["target"],
            )
            elapsed = time.time() - start
            has_translation = bool(result and result.segments and len(result.segments) > 0)
            is_timeout_ok = elapsed < 35  # Should complete within 30s timeout + buffer

            # Extract translation text from result
            translation_text = result.segments[0].translation if (result and result.segments) else ""

            passed = has_translation and is_timeout_ok and len(translation_text) > 0
            results.append(passed)
            print_result(
                f"Case {i}: {case['segments'][0].text[:30]}...",
                passed,
                f"Result: {translation_text[:50] if translation_text else 'EMPTY'}... | Time: {elapsed:.2f}s | Provider: {result.provider if result else 'N/A'}"
            )
        except Exception as e:
            results.append(False)
            print_result(f"Case {i}: {case['segments'][0].text[:30]}...", False, f"Error: {str(e)}")

    return all(results)


async def test_tool_layer():
    """Test the translation tool layer"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 2: Translation Tool Layer{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    tool = TranslateTextTool()

    params = TranslateTextParams(
        text="API integration test for translation system",
        source_lang="en",
        target_lang="zh-CN",
        domain="cs",
        style="natural",
    )

    start = time.time()
    try:
        result = await tool.execute(params=params, user_id="test-user", db_session=None)
        elapsed = time.time() - start

        passed = result.success and bool(result.data.get("translation"))
        print_result(
            "Tool execution with CS domain",
            passed,
            f"Result: {result.data.get('translation', '')[:50]}... | Time: {elapsed:.2f}s"
        )
        return passed
    except Exception as e:
        print_result("Tool execution", False, f"Error: {str(e)}")
        return False


async def test_api_http_call():
    """Test the HTTP API endpoint"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 3: HTTP API Endpoint{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Check if server is running
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            # Test health endpoint first
            try:
                health_resp = await client.get(f"{base_url}/health")
                print_result("Server is reachable", health_resp.status_code == 200)
            except Exception as e:
                print_result("Server connection", False, f"Cannot connect to {base_url}: {e}")
                return None  # Skip test if server not running

            # Test translation endpoint (may fail without auth)
            payload = {
                "text": "End-to-end integration test",
                "source_lang": "en",
                "target_lang": "zh-CN",
                "domain": "general"
            }

            try:
                resp = await client.post(
                    f"{base_url}/api/v1/translation/translate",
                    json=payload
                )

                # If 401, skip format check (FastAPI returns standard error format)
                if resp.status_code == 401:
                    print_result("API response format", None, "Skipped: 401 authentication required")
                    print_result("API translation", None, "Authentication required (expected)")
                    return None  # Skip

                # Check response format
                data = resp.json()
                has_success_field = "success" in data
                has_translation_field = "translation" in data
                has_meta_field = "meta" in data

                format_ok = has_success_field and has_translation_field and has_meta_field

                print_result(
                    "API response format",
                    format_ok,
                    f"Fields: success={has_success_field}, translation={has_translation_field}, meta={has_meta_field}"
                )

                if resp.status_code == 200 and data.get("success"):
                    print_result(
                        "API translation success",
                        True,
                        f"Translation: {data.get('translation', '')[:50]}..."
                    )
                else:
                    print_result(
                        "API translation",
                        False,
                        f"Status: {resp.status_code}, Response: {str(data)[:100]}"
                    )

                return format_ok
            except Exception as e:
                print_result("API translation call", False, f"Error: {str(e)}")
                return False

    except Exception as e:
        print_result("HTTP Client setup", False, f"Error: {str(e)}")
        return False


async def test_flutter_compatibility():
    """Test response format matches Flutter expectations"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 4: Flutter Response Format Compatibility{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Flutter expects these exact fields based on translator_tool.dart
    required_fields = ["success", "translation", "meta"]

    tool = TranslateTextTool()
    params = TranslateTextParams(
        text="Compatibility test for Flutter",
        source_lang="en",
        target_lang="zh-CN",
    )

    try:
        result = await tool.execute(params=params, user_id="test-flutter", db_session=None)

        if result.success:
            # Check if result has the expected structure
            has_translation = bool(result.data.get("translation"))
            has_meta = "meta" in result.data or any(k in result.data for k in ["provider", "cache_hit"])

            # Verify the structure matches what Flutter expects
            structure_ok = has_translation and has_meta

            print_result(
                "Response structure",
                structure_ok,
                f"Has translation: {has_translation}, Has metadata: {has_meta}"
            )

            # Check that translation field is populated (not translated_text)
            translation = result.data.get("translation", "")
            uses_correct_field = len(translation) > 0

            print_result(
                "Uses 'translation' field (not 'translated_text')",
                uses_correct_field,
                f"Field value: {translation[:50]}..."
            )

            return structure_ok and uses_correct_field
        else:
            print_result("Flutter compatibility", False, f"Tool failed: {result.error_message}")
            return False

    except Exception as e:
        print_result("Flutter compatibility", False, f"Error: {str(e)}")
        return False


def verify_timeout_config():
    """Verify timeout is configured"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 5: Timeout Configuration{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Read the service file and check for timeout
    service_path = Path(__file__).parent.parent.parent / "app/services/translation_service.py"
    content = service_path.read_text()

    has_timeout = "timeout=30.0" in content or "timeout=30" in content

    print_result(
        "AsyncOpenAI timeout configured",
        has_timeout,
        f"timeout=30.0 found in translation_service.py" if has_timeout else "Timeout not set!"
    )

    return has_timeout


def verify_flutter_fix():
    """Verify Flutter translator_tool.dart fix"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test 6: Flutter translator_tool.dart Fix{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    flutter_path = Path(__file__).parent.parent.parent.parent / "mobile/lib/features/tools/presentation/widgets/translator_tool.dart"

    if not flutter_path.exists():
        print_result("Flutter file exists", False, "File not found")
        return False

    content = flutter_path.read_text()

    # Check for the correct field access
    has_translation_field = "data['translation']" in content or "data[\"translation\"]" in content
    has_fallback = "data['translated_text']" in content or "data[\"translated_text\"]" in content

    # The correct pattern: prefer 'translation', fallback to 'translated_text'
    correct_pattern = has_translation_field and has_fallback

    print_result(
        "Flutter reads 'translation' field",
        has_translation_field,
        "Found data['translation'] access"
    )

    print_result(
        "Flutter has fallback compatibility",
        has_fallback,
        "Found data['translated_text'] fallback"
    )

    return correct_pattern


async def main():
    """Run all E2E tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   TRANSLATION E2E TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    # Get API key for verification
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if api_key:
        print(f"{GREEN}✓{RESET} SILICONFLOW_API_KEY is configured (length: {len(api_key)})")
    else:
        print(f"{YELLOW}⚠{RESET} SILICONFLOW_API_KEY not set in .env")

    base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    print(f"{BLUE}Base URL:{RESET} {base_url}")

    # Run tests
    results = {}

    # Static tests
    results["timeout_config"] = verify_timeout_config()
    results["flutter_fix"] = verify_flutter_fix()

    # Dynamic tests
    results["service_direct"] = await test_translation_service_direct()
    results["tool_layer"] = await test_tool_layer()
    results["flutter_compat"] = await test_flutter_compatibility()
    results["api_http"] = await test_api_http_call()  # May return None if server not running

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   TEST SUMMARY{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    for test_name, result in results.items():
        if result is None:
            status = f"{YELLOW}SKIP{RESET}"
        elif result:
            status = f"{GREEN}PASS{RESET}"
        else:
            status = f"{RED}FAIL{RESET}"
        print(f"{status} | {test_name}")

    # Calculate pass rate (excluding skipped)
    executable_results = [r for r in results.values() if r is not None]
    if executable_results:
        pass_count = sum(1 for r in executable_results if r)
        total = len(executable_results)
        rate = (pass_count / total) * 100

        print(f"\n{BLUE}Pass Rate:{RESET} {pass_count}/{total} ({rate:.1f}%)")

        if rate >= 100:
            print(f"\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}   ✓ ALL TESTS PASSED - E2E VERIFICATION COMPLETE{RESET}")
            print(f"{GREEN}{'='*60}{RESET}")
            return 0
        else:
            print(f"\n{YELLOW}{'='*60}{RESET}")
            print(f"{YELLOW}   ⚠ SOME TESTS FAILED - REVIEW NEEDED{RESET}")
            print(f"{YELLOW}{'='*60}{RESET}")
            return 1
    else:
        print(f"\n{YELLOW}⚠ No executable tests run{RESET}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
