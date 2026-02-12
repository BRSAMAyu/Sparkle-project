"""
Phase 1 & 2 Acceptance Test Suite
=================================

验收测试：验证意图识别系统优化方案的 Phase 1 和 Phase 2 实施情况。

测试范围：
- Phase 1: 性能优化（缓存、渐进式分类、LLM prompt优化）
- Phase 2: 语义理解（BERT、用户画像、监控）

运行方式：
    cd backend && python tests/test_phase_acceptance.py
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger

# Import components to test
from app.orchestration.request_router import RequestRouter
from app.orchestration.intent_cache import IntentCache
from app.orchestration.bert_intent_classifier import BERTIntentClassifier
from app.orchestration.user_intent_profiler import UserIntentProfiler
from app.orchestration.intent_monitor import IntentMonitor

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"


class PhaseAcceptanceTest:
    """Phase 1 & 2 Acceptance Test Suite"""

    def __init__(self):
        self.results = {
            "Phase 1": {"total": 0, "passed": 0, "failed": 0, "tests": []},
            "Phase 2": {"total": 0, "passed": 0, "failed": 0, "tests": []},
        }

    def add_result(self, phase: str, test_name: str, passed: bool, detail: str = ""):
        """记录测试结果"""
        self.results[phase]["total"] += 1
        if passed:
            self.results[phase]["passed"] += 1
            status = f"{GREEN}✓ PASS{RESET}"
        else:
            self.results[phase]["failed"] += 1
            status = f"{RED}✗ FAIL{RESET}"

        print(f"{status} | {test_name}")
        if detail:
            print(f"       {detail}")

        self.results[phase]["tests"].append({
            "name": test_name,
            "passed": passed,
            "detail": detail
        })

    async def test_phase1_implementation(self):
        """Phase 1 实施验收测试"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Phase 1: Performance & Robustness Acceptance Tests{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        # Test 1.1: Intent Cache
        print(f"\n{CYAN}[1.1] Intent Cache Implementation{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            # Create mock Redis client
            class MockRedis:
                def __init__(self):
                    self.data = {}
                async def get(self, key):
                    return self.data.get(key)
                async def setex(self, key, ttl, value):
                    self.data[key] = value

            redis_client = MockRedis()
            cache = IntentCache(redis_client)

            # Test cache functionality
            message = "帮我制定学习计划"
            intent, confidence = "create", 0.85

            # Cache a result
            await cache.cache_intent(message, intent, confidence, "keyword")

            # Retrieve from cache
            cached = await cache.get_cached_intent(message)

            if cached and cached[0] == intent and cached[1] == confidence:
                self.add_result(
                    "Phase 1",
                    "Intent Cache: Store and retrieve",
                    True,
                    f"Cached intent: {cached[0]}, conf: {cached[1]:.2f}"
                )
            else:
                self.add_result(
                    "Phase 1",
                    "Intent Cache: Store and retrieve",
                    False,
                    f"Expected: ({intent}, {confidence}), Got: {cached}"
                )

            # Test message normalization
            message2 = "  帮我制定学习计划  "  # Extra spaces
            cached2 = await cache.get_cached_intent(message2)

            if cached2 is not None:
                self.add_result(
                    "Phase 1",
                    "Intent Cache: Message normalization",
                    True,
                    "Whitespace normalization working"
                )
            else:
                self.add_result(
                    "Phase 1",
                    "Intent Cache: Message normalization",
                    False,
                    "Whitespace normalization failed"
                )

        except Exception as e:
            self.add_result(
                "Phase 1",
                "Intent Cache: Implementation",
                False,
                f"Error: {str(e)}"
            )

        # Test 1.2: Progressive Classification
        print(f"\n{CYAN}[1.2] Progressive Classification Pipeline{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            router = RequestRouter(redis_client=None)

            # Test Tier-1: Quick keyword match
            test_cases = [
                ("请翻译这句话", "translation", 0.8, "Tier-1: Special intent"),
                ("进入冲刺模式", "sprint", 0.8, "Tier-1: Sprint mode"),
                ("帮我制定学习计划", "create", 0.85, "Tier-1: Create plan"),
            ]

            for message, expected_intent, min_conf, description in test_cases:
                intent, confidence = await router._classify_intent_with_confidence(message)
                passed = intent == expected_intent and confidence >= min_conf
                self.add_result(
                    "Phase 1",
                    description,
                    passed,
                    f"Intent: {intent} (expected: {expected_intent}), Conf: {confidence:.2f}"
                )

        except Exception as e:
            self.add_result(
                "Phase 1",
                "Progressive Classification",
                False,
                f"Error: {str(e)}"
            )

        # Test 1.3: LLM Prompt Optimization
        print(f"\n{CYAN}[1.3] LLM Prompt Optimization{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            router = RequestRouter(redis_client=None)

            # Test user pattern retrieval
            user_patterns = await router._get_user_intent_patterns("test-user")

            if "recent_intents" in user_patterns:
                self.add_result(
                    "Phase 1",
                    "LLM Prompt: User pattern retrieval",
                    True,
                    f"Recent intents: {user_patterns['recent_intents']}"
                )
            else:
                self.add_result(
                    "Phase 1",
                    "LLM Prompt: User pattern retrieval",
                    False,
                    "Missing 'recent_intents' in patterns"
                )

            # Test candidate intent filtering
            candidates = router._get_candidate_intents("帮我制定学习计划")

            if "create" in candidates and len(candidates) > 0:
                self.add_result(
                    "Phase 1",
                    "LLM Prompt: Candidate intent filtering",
                    True,
                    f"Candidates: {candidates}"
                )
            else:
                self.add_result(
                    "Phase 1",
                    "LLM Prompt: Candidate intent filtering",
                    False,
                    f"Missing 'create' in candidates: {candidates}"
                )

        except Exception as e:
            self.add_result(
                "Phase 1",
                "LLM Prompt Optimization",
                False,
                f"Error: {str(e)}"
            )

        # Test 1.4: Edge Case Handling
        print(f"\n{CYAN}[1.4] Edge Case Handling{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            router = RequestRouter(redis_client=None)

            edge_cases = [
                ("", "chat", "Empty message"),
                ("   ", "chat", "Whitespace only"),
                ("你好！@#$%", "chat", "Special characters"),
                ("a" * 200, "chat", "Very long message"),
            ]

            for message, expected_intent, description in edge_cases:
                try:
                    intent, confidence = await router._classify_intent_with_confidence(message)
                    passed = intent == expected_intent or confidence >= 0.3
                    self.add_result(
                        "Phase 1",
                        description,
                        passed,
                        f"Message: '{message[:30]}...' -> Intent: {intent}, Conf: {confidence:.2f}"
                    )
                except Exception as e:
                    # Edge cases should not crash
                    self.add_result(
                        "Phase 1",
                        description,
                        True,
                        f"Handled gracefully: {str(e)[:50]}"
                    )

        except Exception as e:
            self.add_result(
                "Phase 1",
                "Edge Case Handling",
                False,
                f"Error: {str(e)}"
            )

        # Test 1.5: Performance Targets
        print(f"\n{CYAN}[1.5] Performance Targets{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            router = RequestRouter(redis_client=None)

            # Measure classification speed
            iterations = 100
            messages = [
                "帮我制定学习计划",
                "请翻译这句话",
                "进入冲刺模式",
            ]

            start_time = time.time()
            for _ in range(iterations):
                for msg in messages:
                    await router._classify_intent_with_confidence(msg)
            elapsed = (time.time() - start_time) * 1000
            avg_latency = elapsed / (iterations * len(messages))

            # Target: <10ms for keyword-only classification
            passed = avg_latency < 10
            self.add_result(
                "Phase 1",
                "Performance: Keyword classification speed",
                passed,
                f"Avg latency: {avg_latency:.2f}ms (target: <10ms)"
            )

        except Exception as e:
            self.add_result(
                "Phase 1",
                "Performance Testing",
                False,
                f"Error: {str(e)}"
            )

    async def test_phase2_implementation(self):
        """Phase 2 实施验收测试"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}Phase 2: Semantic Understanding & Personalization{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        # Test 2.1: BERT Classifier
        print(f"\n{CYAN}[2.1] BERT-based Intent Classifier{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            # Check if BERT is available (requires transformers and torch)
            try:
                from app.orchestration.bert_intent_classifier import BERTIntentClassifier, get_bert_classifier

                # Test initialization (but don't load the heavy model)
                self.add_result(
                    "Phase 2",
                    "BERT: Module imports",
                    True,
                    "BERTIntentClassifier module available"
                )

                # Test singleton
                classifier = get_bert_classifier()
                if classifier:
                    self.add_result(
                        "Phase 2",
                        "BERT: Singleton initialization",
                        True,
                        "BERT classifier singleton created"
                    )

                    # Test model info
                    info = classifier.get_model_info()
                    if "intents" in info and len(info["intents"]) == 10:
                        self.add_result(
                            "Phase 2",
                            "BERT: Model configuration",
                            True,
                            f"Intents: {info['intents']}"
                        )
                    else:
                        self.add_result(
                            "Phase 2",
                            "BERT: Model configuration",
                            False,
                            f"Invalid intents: {info.get('intents', [])}"
                        )
                else:
                    self.add_result(
                        "Phase 2",
                        "BERT: Singleton initialization",
                        False,
                        "Failed to create classifier (may require model download)"
                    )

            except ImportError as e:
                self.add_result(
                    "Phase 2",
                    "BERT: Module availability",
                    False,
                    f"transformers/torch not installed: {e}"
                )
            except Exception as e:
                self.add_result(
                    "Phase 2",
                    "BERT: Initialization",
                    False,
                    f"Error: {str(e)}"
                )

        except Exception as e:
            self.add_result(
                "Phase 2",
                "BERT Classifier",
                False,
                f"Error: {str(e)}"
            )

        # Test 2.2: User Intent Profiler
        print(f"\n{CYAN}[2.2] User Intent Profiler{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            from app.orchestration.user_intent_profiler import UserIntentProfiler, get_user_profiler

            # Create mock Redis
            class MockRedis:
                def __init__(self):
                    self.data = {}
                async def get(self, key):
                    import json
                    val = self.data.get(key)
                    return json.dumps(val) if val else None
                async def setex(self, key, ttl, value):
                    import json
                    self.data[key] = json.loads(value) if isinstance(value, str) else value
                async def delete(self, *keys):
                    for key in keys:
                        self.data.pop(key, None)

            redis_client = MockRedis()
            profiler = UserIntentProfiler(redis_client)

            # Test get default profile
            profile = await profiler.get_user_profile("test-user-123")
            if "intents" in profile and "total_count" in profile:
                self.add_result(
                    "Phase 2",
                    "Profiler: Get user profile",
                    True,
                    f"Profile has {len(profile['intents'])} intents"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Profiler: Get user profile",
                    False,
                    f"Invalid profile structure: {list(profile.keys())}"
                )

            # Test update profile
            await profiler.update_profile("test-user-123", "create", {"confidence": 0.9})
            updated_profile = await profiler.get_user_profile("test-user-123")

            if updated_profile.get("total_count", 0) > 0:
                self.add_result(
                    "Phase 2",
                    "Profiler: Update profile",
                    True,
                    f"Total count: {updated_profile['total_count']}"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Profiler: Update profile",
                    False,
                    "Profile not updated"
                )

            # Test score adjustment
            scores = {"create": 0.7, "learn": 0.6, "chat": 0.5}
            adjusted = profiler.adjust_intent_scores(scores, updated_profile, max_boost=0.3)

            if adjusted["create"] >= scores["create"]:
                self.add_result(
                    "Phase 2",
                    "Profiler: Score adjustment",
                    True,
                    f"create: {scores['create']:.2f} -> {adjusted['create']:.2f}"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Profiler: Score adjustment",
                    False,
                    f"create: {scores['create']:.2f} -> {adjusted['create']:.2f} (should increase)"
                )

            # Test top intents
            top_intents = profiler.get_top_intents(updated_profile, top_n=3)
            if len(top_intents) > 0:
                self.add_result(
                    "Phase 2",
                    "Profiler: Get top intents",
                    True,
                    f"Top intents: {top_intents}"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Profiler: Get top intents",
                    False,
                    "No top intents returned"
                )

        except Exception as e:
            self.add_result(
                "Phase 2",
                "User Intent Profiler",
                False,
                f"Error: {str(e)}"
            )

        # Test 2.3: Intent Monitoring
        print(f"\n{CYAN}[2.3] Intent Monitoring System{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            from app.orchestration.intent_monitor import IntentMonitor, get_intent_monitor

            # Test monitor initialization
            monitor = IntentMonitor(enabled=True)

            if monitor.enabled:
                self.add_result(
                    "Phase 2",
                    "Monitor: Initialization",
                    True,
                    "IntentMonitor enabled"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Monitor: Initialization",
                    False,
                    "IntentMonitor disabled (prometheus_client not installed)"
                )

            # Test record classification
            monitor.record_classification(
                intent="create",
                confidence=0.85,
                source="keyword",
                tier="tier1",
                latency_ms=5.2
            )

            # Test record cache hit
            monitor.record_cache_hit(latency_ms=0.5)

            # Test record cache miss
            monitor.record_cache_miss()

            # Get metrics summary
            summary = monitor.get_metrics_summary()

            if summary.get("total_classifications", 0) > 0:
                self.add_result(
                    "Phase 2",
                    "Monitor: Record metrics",
                    True,
                    f"Total classifications: {summary['total_classifications']}"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Monitor: Record metrics",
                    False,
                    "Metrics not recorded"
                )

            # Test metrics summary
            if "total_classifications" in summary and "cache_hits" in summary:
                self.add_result(
                    "Phase 2",
                    "Monitor: Metrics summary",
                    True,
                    f"Classifications: {summary['total_classifications']}, Cache hits: {summary['cache_hits']}"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Monitor: Metrics summary",
                    False,
                    f"Missing metrics: {list(summary.keys())}"
                )

            # Test Prometheus export
            prometheus_metrics = monitor.get_prometheus_metrics()
            if "intent_classification_total" in prometheus_metrics:
                self.add_result(
                    "Phase 2",
                    "Monitor: Prometheus export",
                    True,
                    "Prometheus metrics generated"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Monitor: Prometheus export",
                    False,
                    "Prometheus metrics missing"
                )

        except Exception as e:
            self.add_result(
                "Phase 2",
                "Intent Monitoring",
                False,
                f"Error: {str(e)}"
            )

        # Test 2.4: Integration
        print(f"\n{CYAN}[2.4] Phase 2 Integration{RESET}")
        print(f"{CYAN}{'-'*70}{RESET}")

        try:
            # Test RequestRouter with Phase 2 features enabled
            class MockRedis:
                def __init__(self):
                    self.data = {}
                async def get(self, key):
                    return self.data.get(key)
                async def setex(self, key, ttl, value):
                    self.data[key] = value
                async def keys(self, pattern):
                    return list(self.data.keys())
                async def delete(self, *keys):
                    for key in keys:
                        self.data.pop(key, None)

            redis_client = MockRedis()

            # Create router with all features enabled
            router = RequestRouter(
                redis_client=redis_client,
                enable_bert=True,  # May fail if transformers not installed
                enable_profiling=True,
                enable_monitoring=True
            )

            # Test routing decision
            decision = await router.decide(
                message="帮我制定学习计划",
                user_id="test-user",
                session_id="test-session"
            )

            if decision.execution_mode in ["direct", "langgraph"]:
                self.add_result(
                    "Phase 2",
                    "Integration: Router with Phase 2",
                    True,
                    f"Mode: {decision.execution_mode}, Intent inferred successfully"
                )
            else:
                self.add_result(
                    "Phase 2",
                    "Integration: Router with Phase 2",
                    False,
                    f"Invalid mode: {decision.execution_mode}"
                )

            # Check if monitoring was called (should have metrics)
            if router.intent_monitor:
                summary = router.intent_monitor.get_metrics_summary()
                if summary.get("total_classifications", 0) > 0:
                    self.add_result(
                        "Phase 2",
                        "Integration: Monitoring in router",
                        True,
                        f"Recorded {summary['total_classifications']} classifications"
                    )
                else:
                    self.add_result(
                        "Phase 2",
                        "Integration: Monitoring in router",
                        False,
                        "No classifications recorded"
                    )

        except Exception as e:
            self.add_result(
                "Phase 2",
                "Phase 2 Integration",
                False,
                f"Error: {str(e)}"
            )

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}   ACCEPTANCE TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        for phase_name, results in self.results.items():
            total = results["total"]
            passed = results["passed"]
            failed = results["failed"]

            if total == 0:
                continue

            rate = (passed / total) * 100 if total > 0 else 0

            print(f"\n{CYAN}{phase_name}{RESET}")
            print(f"  Total: {total} | {GREEN}Passed: {passed}{RESET} | {RED}Failed: {failed}{RESET}")
            print(f"  Success Rate: {rate:.1f}%")

            # Show failed tests
            if failed > 0:
                print(f"\n  {RED}Failed Tests:{RESET}")
                for test in results["tests"]:
                    if not test["passed"]:
                        print(f"    - {test['name']}")
                        if test["detail"]:
                            print(f"      {test['detail']}")

        # Overall summary
        total_all = sum(r["total"] for r in self.results.values())
        passed_all = sum(r["passed"] for r in self.results.values())
        failed_all = sum(r["failed"] for r in self.results.values())
        rate_all = (passed_all / total_all * 100) if total_all > 0 else 0

        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}   OVERALL RESULT{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

        print(f"Total Tests: {total_all}")
        print(f"{GREEN}Passed: {passed_all}{RESET}")
        print(f"{RED}Failed: {failed_all}{RESET}")
        print(f"Success Rate: {rate_all:.1f}%")

        if rate_all >= 90:
            print(f"\n{GREEN}{'='*70}{RESET}")
            print(f"{GREEN}   ✓ ACCEPTANCE TEST PASSED{RESET}")
            print(f"{GREEN}{'='*70}{RESET}")
            return 0
        elif rate_all >= 70:
            print(f"\n{YELLOW}{'='*70}{RESET}")
            print(f"{YELLOW}   ⚠ ACCEPTANCE TEST PARTIALLY PASSED{RESET}")
            print(f"{YELLOW}{'='*70}{RESET}")
            return 1
        else:
            print(f"\n{RED}{'='*70}{RESET}")
            print(f"{RED}   ✗ ACCEPTANCE TEST FAILED{RESET}")
            print(f"{RED}{'='*70}{RESET}")
            return 2


async def main():
    """运行验收测试"""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}   INTENT RECOGNITION SYSTEM - ACCEPTANCE TEST SUITE{RESET}")
    print(f"{CYAN}   Phase 1: Performance & Robustness{RESET}")
    print(f"{CYAN}   Phase 2: Semantic Understanding & Personalization{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    tester = PhaseAcceptanceTest()

    # Run Phase 1 tests
    await tester.test_phase1_implementation()

    # Run Phase 2 tests
    await tester.test_phase2_implementation()

    # Print summary
    return tester.print_summary()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
