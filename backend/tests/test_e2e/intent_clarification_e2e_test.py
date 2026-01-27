"""
End-to-End Intent Recognition & Clarification Test Suite
========================================================

This suite tests the complete "Understanding Loop":
1. Intent Recognition (Routing Accuracy)
2. Information Sufficiency Check (LLM Judge)
3. Multi-turn Clarification (Stop mechanism)
4. Special Mode Entry (Translation/Prism/Sprint)

Run with:
    cd backend && python tests/test_e2e/intent_clarification_e2e_test.py
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

# Import components to test
from app.orchestration.request_router import RequestRouter
from app.orchestration.sufficiency_checker import SufficiencyChecker, SufficiencyStatus
from app.orchestration.schemas import RouteDecision, StateSnapshot


# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


class E2ETestResult:
    """Test result tracking"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.details = []

    def add(self, test_name: str, passed: bool, detail: str = ""):
        """Add test result"""
        if passed:
            self.passed += 1
            status = f"{GREEN}✓ PASS{RESET}"
        else:
            self.failed += 1
            status = f"{RED}✗ FAIL{RESET}"

        print(f"{status} | {test_name}")
        if detail:
            print(f"       {detail}")
        self.details.append((test_name, passed, detail))

    def summary(self):
        """Print summary"""
        total = self.passed + self.failed
        if total == 0:
            print(f"\n{YELLOW}⚠ No tests run{RESET}")
            return 1

        rate = (self.passed / total) * 100
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}   TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        print(f"{GREEN}Pass: {self.passed}{RESET} | {RED}Fail: {self.failed}{RESET} | {YELLOW}Skip: {self.skipped}{RESET}")
        print(f"{BLUE}Rate: {rate:.1f}%{RESET}")

        if rate >= 100:
            print(f"\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}   ✓ ALL TESTS PASSED{RESET}")
            print(f"{GREEN}{'='*60}{RESET}")
            return 0
        elif rate >= 80:
            print(f"\n{YELLOW}{'='*60}{RESET}")
            print(f"{YELLOW}   ⚠ SOME TESTS FAILED{RESET}")
            print(f"{YELLOW}{'='*60}{RESET}")
            return 1
        else:
            print(f"\n{RED}{'='*60}{RESET}")
            print(f"{RED}   ✗ CRITICAL FAILURES{RESET}")
            print(f"{RED}{'='*60}{RESET}")
            return 2


class IntentRecognitionSuite:
    """Test Suite 1: Intent Recognition & Routing Accuracy"""

    def __init__(self, router: RequestRouter):
        self.router = router

    async def test_chitchat_vs_task_routing(self):
        """Test 1.1: Distinguish chitchat from complex tasks"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 1.1: Chitchat vs Complex Task Routing{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Test cases: (message, expected_intent, description)
        test_cases = [
            # Chitchat cases
            ("你好", "chat", "Simple greeting"),
            ("今天天气怎么样", "chat", "Weather small talk"),
            ("谢谢", "chat", "Gratitude"),
            ("哈哈很好笑", "chat", "Laughter"),

            # Complex task cases (should NOT be classified as chat)
            ("帮我制定学习计划", "create", "Learning plan request"),
            ("我想复习数学", "review", "Math review request"),
            ("创建一个复习计划", "create", "Review plan creation"),
            ("帮我安排学习时间", "create", "Time scheduling"),
        ]

        for message, expected_intent, description in test_cases:
            try:
                intent, confidence = await self.router._classify_intent_with_confidence(message)
                passed = intent == expected_intent

                # For complex tasks, confidence should be reasonable (>0.5)
                if expected_intent in ["create", "review"]:
                    passed = passed and confidence > 0.5

                results.add(
                    f"{description}: '{message[:20]}...'",
                    passed,
                    f"Intent: {intent} (expected: {expected_intent}), Confidence: {confidence:.2f}"
                )
            except Exception as e:
                results.add(
                    f"{description}: '{message[:20]}...'",
                    False,
                    f"Error: {str(e)}"
                )

        return results

    async def test_special_mode_detection(self):
        """Test 1.2: Special mode entry detection (5b, 5c, 5d)"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 1.2: Special Mode Detection{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Translation mode (5c)
        translation_cases = [
            ("请翻译这句话", "translation", "Explicit translation"),
            ("what does this mean in Chinese", "translation", "Implicit translation"),
            ("怎么说英语", "translation", "Language query"),
        ]

        # Prism/Behavior mode (5b)
        prism_cases = [
            ("我的学习画像", "prism", "User profile request"),
            ("查看我的认知棱镜", "prism", "Explicit prism"),
            ("生成周报", "prism", "Weekly report"),
        ]

        # Sprint/Focus mode (5d)
        sprint_cases = [
            ("进入冲刺模式", "sprint", "Sprint mode"),
            ("开始专注", "sprint", "Focus mode"),
            ("我要突击复习", "sprint", "Cramming"),
        ]

        all_cases = [
            ("Translation", translation_cases),
            ("Prism", prism_cases),
            ("Sprint", sprint_cases),
        ]

        for mode_name, cases in all_cases:
            for message, expected_intent, description in cases:
                try:
                    intent, confidence = await self.router._classify_intent_with_confidence(message)
                    passed = intent == expected_intent and confidence > 0.7

                    results.add(
                        f"[{mode_name}] {description}",
                        passed,
                        f"Message: '{message}' -> Intent: {intent} (conf: {confidence:.2f})"
                    )
                except Exception as e:
                    results.add(
                        f"[{mode_name}] {description}",
                        False,
                        f"Error: {str(e)}"
                    )

        return results

    async def test_multimodal_compatibility(self):
        """Test 1.3: Voice-to-text semantic understanding"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 1.3: Multimodal (Voice) Compatibility{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Simulate voice-to-text output characteristics:
        # - Fillers (嗯, 啊, 那个)
        # - Repetitions
        # - Informal phrasing

        voice_cases = [
            ("嗯，帮我制定学习计划", "create", "With filler"),
            ("那个，我想复习数学", "review", "With filler 'that'"),
            ("啊，进入冲刺模式", "sprint", "With filler 'ah'"),
            ("帮我...帮我安排时间", "create", "With repetition"),
            ("今天怎么样今天不错", "chat", "Repetitive chitchat"),
        ]

        for message, expected_intent, description in voice_cases:
            try:
                intent, confidence = await self.router._classify_intent_with_confidence(message)
                passed = intent == expected_intent

                results.add(
                    f"{description}",
                    passed,
                    f"Voice input: '{message}' -> Intent: {intent} (conf: {confidence:.2f})"
                )
            except Exception as e:
                results.add(
                    f"{description}",
                    False,
                    f"Error: {str(e)}"
                )

        return results


class SufficiencyCheckerSuite:
    """Test Suite 2: Information Sufficiency & Clarification Loop"""

    def __init__(self, checker: SufficiencyChecker):
        self.checker = checker

    async def test_required_field_detection(self):
        """Test 2.1: Detect missing required fields"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 2.1: Required Field Detection{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        test_cases = [
            {
                "name": "Create task without title",
                "intent": "create_task",
                "entities": {"task_type": "study"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["task_title"],
            },
            {
                "name": "Create plan without title",
                "intent": "create_plan",
                "entities": {"plan_type": "sprint"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["plan_title"],
            },
            {
                "name": "Update task without ID",
                "intent": "update_task",
                "entities": {"new_status": "in_progress"},
                "expected_status": SufficiencyStatus.NEED_CLARIFICATION,
                "expected_missing": ["task_id"],
            },
            {
                "name": "Complete task creation",
                "intent": "create_task",
                "entities": {"task_title": "Study math", "task_type": "study"},
                "expected_status": SufficiencyStatus.SUFFICIENT,
                "expected_missing": [],
            },
        ]

        for case in test_cases:
            try:
                result = await self.checker.check(
                    intent=case["intent"],
                    extracted_entities=case["entities"],
                    conversation_context=[],
                )

                status_match = result.status == case["expected_status"]
                missing_match = set(result.missing_fields) == set(case["expected_missing"])

                passed = status_match and missing_match

                results.add(
                    case["name"],
                    passed,
                    f"Status: {result.status} (expected: {case['expected_status']}), "
                    f"Missing: {result.missing_fields}"
                )
            except Exception as e:
                results.add(
                    case["name"],
                    False,
                    f"Error: {str(e)}"
                )

        return results

    async def test_clarification_question_generation(self):
        """Test 2.2: Generate appropriate clarification questions"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 2.2: Clarification Question Generation{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Test that questions are generated for missing fields
        test_cases = [
            ("task_title", "create_task", "asks for task title"),
            ("plan_type", "create_plan", "asks for plan type"),
            ("due_date", "create_task", "asks for due date"),
            ("subject_id", "knowledge_query", "asks for subject"),
        ]

        for field, intent, description in test_cases:
            try:
                result = await self.checker.check(
                    intent=intent,
                    extracted_entities={},  # Empty to trigger missing
                    conversation_context=[],
                )

                has_question = len(result.clarification_questions) > 0
                question_relevant = any(
                    field.lower() in q.lower() or
                    any(keyword in q for keyword in ["请问", "什么", "哪个", "什么时候"])
                    for q in result.clarification_questions
                )

                passed = has_question and question_relevant

                results.add(
                    description,
                    passed,
                    f"Questions: {result.clarification_questions[:2]}"
                )
            except Exception as e:
                results.add(
                    description,
                    False,
                    f"Error: {str(e)}"
                )

        return results

    async def test_context_inference(self):
        """Test 2.3: Infer information from conversation context"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 2.3: Context Inference{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Test context inference for estimated_minutes
        conversation_with_time = [
            {"role": "user", "content": "我要学习30分钟"},
            {"role": "assistant", "content": "好的，创建任务"},
            {"role": "user", "content": "帮我创建学习任务"},
        ]

        try:
            result = await self.checker.check(
                intent="create_task",
                extracted_entities={"task_title": "Study math"},
                conversation_context=conversation_with_time,
            )

            # In strict mode, should still ask for clarification
            # In non-strict mode (default), should be sufficient
            passed = result.status == SufficiencyStatus.SUFFICIENT

            results.add(
                "Infer duration from context",
                passed,
                f"Status: {result.status}, Inferred from: '我要学习30分钟'"
            )
        except Exception as e:
            results.add(
                "Infer duration from context",
                False,
                f"Error: {str(e)}"
            )

        return results

    async def test_stop_mechanism(self):
        """Test 2.4: Clarification stop mechanism (防止无限追问)"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 2.4: Clarification Stop Mechanism{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Simulate multi-turn clarification
        # Turn 1: User says "create task" -> Ask for title
        try:
            result1 = await self.checker.check(
                intent="create_task",
                extracted_entities={},
                conversation_context=[],
            )

            turn1_pass = (
                result1.status == SufficiencyStatus.NEED_CLARIFICATION and
                len(result1.clarification_questions) > 0
            )

            results.add(
                "Turn 1: Ask for missing info",
                turn1_pass,
                f"Questions: {result1.clarification_questions}"
            )

            # Turn 2: User provides title -> Should be sufficient now
            result2 = await self.checker.check(
                intent="create_task",
                extracted_entities={"task_title": "Study math"},
                conversation_context=[
                    {"role": "assistant", "content": result1.clarification_questions[0]},
                    {"role": "user", "content": "Study math"},
                ],
            )

            turn2_pass = result2.status == SufficiencyStatus.SUFFICIENT

            results.add(
                "Turn 2: Stop asking when info sufficient",
                turn2_pass,
                f"Status: {result2.status} (should be SUFFICIENT)"
            )

            # Turn 3: Verify no infinite loop
            # With title already provided, should NOT ask again
            result3 = await self.checker.check(
                intent="create_task",
                extracted_entities={"task_title": "Study math"},
                conversation_context=[
                    {"role": "assistant", "content": result1.clarification_questions[0]},
                    {"role": "user", "content": "Study math"},
                    {"role": "assistant", "content": "任务已创建"},
                ],
            )

            turn3_pass = result3.status == SufficiencyStatus.SUFFICIENT

            results.add(
                "Turn 3: No infinite追问loop",
                turn3_pass,
                f"Status: {result3.status} (should still be SUFFICIENT)"
            )

        except Exception as e:
            results.add("Stop mechanism test", False, f"Error: {str(e)}")

        return results

    async def test_high_risk_confirmation(self):
        """Test 2.5: High-risk operations require confirmation"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 2.5: High-Risk Confirmation{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Delete operations require confirmation
        try:
            result = await self.checker.check(
                intent="delete_task",
                extracted_entities={"task_id": "task123", "task_title": "My Task"},
                conversation_context=[],
            )

            passed = (
                result.status == SufficiencyStatus.NEED_CONFIRMATION and
                result.confirmation_message is not None and
                "确定" in result.confirmation_message or "删除" in result.confirmation_message
            )

            results.add(
                "Delete task requires confirmation",
                passed,
                f"Status: {result.status}, Message: {result.confirmation_message}"
            )
        except Exception as e:
            results.add("Delete task requires confirmation", False, f"Error: {str(e)}")

        return results


class RoutingDecisionSuite:
    """Test Suite 3: End-to-End Routing Decisions"""

    def __init__(self, router: RequestRouter):
        self.router = router

    async def test_execution_mode_routing(self):
        """Test 3.1: Routing to correct execution mode"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 3.1: Execution Mode Routing{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        test_cases = [
            # (message, expected_mode, expected_intent, description)
            ("你好", "direct", "chat", "Simple chitchat -> direct"),
            ("帮我制定学习计划", "langgraph", "create", "Complex plan -> langgraph"),
            ("翻译这个", "direct", "translation", "Translation -> direct (specialized)"),
            ("我的学习画像", "direct", "prism", "Prism -> direct (specialized)"),
            ("删除所有任务", "direct", "delete", "High-risk -> direct (safety)"),
            ("创建一个任务然后规划复习", "langgraph", "create", "Multi-step -> langgraph"),
        ]

        for message, expected_mode, expected_intent, description in test_cases:
            try:
                decision = await self.router.decide(
                    message=message,
                    user_id="test-user",
                    session_id="test-session",
                )

                mode_match = decision.execution_mode == expected_mode
                intent_ok = expected_intent in decision.reason.lower() or expected_intent == "chat"

                passed = mode_match and intent_ok

                results.add(
                    description,
                    passed,
                    f"Message: '{message}' -> Mode: {decision.execution_mode} "
                    f"(expected: {expected_mode}), Reason: {decision.reason}"
                )
            except Exception as e:
                results.add(
                    description,
                    False,
                    f"Error: {str(e)}"
                )

        return results

    async def test_confidence_scoring(self):
        """Test 3.2: Confidence scoring for ambiguous inputs"""
        print(f"\n{CYAN}{'='*60}{RESET}")
        print(f"{CYAN}Test 3.2: Confidence Scoring{RESET}")
        print(f"{CYAN}{'='*60}{RESET}\n")

        results = E2ETestResult()

        # Clear intent (high confidence)
        clear_cases = [
            ("请翻译这句话", "translation", 0.7),
            ("进入冲刺模式", "sprint", 0.7),
        ]

        # Ambiguous intent (lower confidence, should trigger LLM assist)
        ambiguous_cases = [
            ("那个，今天", "chat", 0.5),
            ("我想", "chat", 0.5),
        ]

        all_cases = [
            ("Clear", clear_cases),
            ("Ambiguous", ambiguous_cases),
        ]

        for category, cases in all_cases:
            for message, expected_intent, min_confidence in cases:
                try:
                    intent, confidence = await self.router._classify_intent_with_confidence(message)

                    passed = intent == expected_intent and confidence >= min_confidence

                    results.add(
                        f"[{category}] '{message}'",
                        passed,
                        f"Intent: {intent}, Confidence: {confidence:.2f} (min: {min_confidence})"
                    )
                except Exception as e:
                    results.add(
                        f"[{category}] '{message}'",
                        False,
                        f"Error: {str(e)}"
                    )

        return results


async def main():
    """Run all E2E test suites"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}   INTENT RECOGNITION & CLARIFICATION E2E TEST SUITE{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Initialize components
    router = RequestRouter(redis_client=None)
    checker = SufficiencyChecker(strict_mode=False)

    # Track overall results
    all_results = E2ETestResult()

    # Run Test Suite 1: Intent Recognition
    print(f"\n{BLUE}[Suite 1/3] Intent Recognition{RESET}")
    suite1 = IntentRecognitionSuite(router)
    result1 = await suite1.test_chitchat_vs_task_routing()
    all_results.passed += result1.passed
    all_results.failed += result1.failed
    all_results.skipped += result1.skipped

    result2 = await suite1.test_special_mode_detection()
    all_results.passed += result2.passed
    all_results.failed += result2.failed
    all_results.skipped += result2.skipped

    result3 = await suite1.test_multimodal_compatibility()
    all_results.passed += result3.passed
    all_results.failed += result3.failed
    all_results.skipped += result3.skipped

    # Run Test Suite 2: Sufficiency Checker
    print(f"\n{BLUE}[Suite 2/3] Sufficiency Checker{RESET}")
    suite2 = SufficiencyCheckerSuite(checker)
    result4 = await suite2.test_required_field_detection()
    all_results.passed += result4.passed
    all_results.failed += result4.failed
    all_results.skipped += result4.skipped

    result5 = await suite2.test_clarification_question_generation()
    all_results.passed += result5.passed
    all_results.failed += result5.failed
    all_results.skipped += result5.skipped

    result6 = await suite2.test_context_inference()
    all_results.passed += result6.passed
    all_results.failed += result6.failed
    all_results.skipped += result6.skipped

    result7 = await suite2.test_stop_mechanism()
    all_results.passed += result7.passed
    all_results.failed += result7.failed
    all_results.skipped += result7.skipped

    result8 = await suite2.test_high_risk_confirmation()
    all_results.passed += result8.passed
    all_results.failed += result8.failed
    all_results.skipped += result8.skipped

    # Run Test Suite 3: Routing Decisions
    print(f"\n{BLUE}[Suite 3/3] Routing Decisions{RESET}")
    suite3 = RoutingDecisionSuite(router)
    result9 = await suite3.test_execution_mode_routing()
    all_results.passed += result9.passed
    all_results.failed += result9.failed
    all_results.skipped += result9.skipped

    result10 = await suite3.test_confidence_scoring()
    all_results.passed += result10.passed
    all_results.failed += result10.failed
    all_results.skipped += result10.skipped

    # Print overall summary
    return all_results.summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
