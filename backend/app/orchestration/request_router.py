"""
Request Router - Phase 1 & Phase 2

Rule-based router for deciding execution mode.
Phase 1: All requests go to "direct" mode.
Phase 2: Introduces "langgraph" and "hybrid" modes for complex intents.

P2 Improvement: Added LLM-assisted intent classification for better accuracy.

Phase 1.1 Improvement: Added intent caching and progressive classification.
"""
from typing import Optional, Tuple
from loguru import logger

from app.orchestration.schemas import RouteDecision
from app.orchestration.intent_cache import IntentCache


class RequestRouter:
    """路由器 (Phase 1 & Phase 2)

    职责:
    1. 分析用户消息意图
    2. 评估请求风险等级
    3. 返回路由决策

    Phase 1 规则:
    - 所有请求走 direct 模式
    - 基于关键词进行意图分类
    - 简单风险评估

    Phase 2 规则:
    - 简单查询 → direct
    - 复杂规划 → langgraph
    - 高风险 → direct (安全优先)
    """

    # 简单工具列表 (适合 direct 模式)
    SIMPLE_TOOLS = {
        "get_task", "get_plan", "get_knowledge", "query_knowledge",
        "get_focus_stats", "get_user_context", "get_progress"
    }

    # 复杂意图关键词 (需要 LangGraph 规划) - Phase 2
    COMPLEX_INTENTS = {
        "学习计划", "study plan", "制定计划", "make a plan",
        "复习策略", "review strategy", "复习计划",
        "时间安排", "schedule", "时间管理", "time management",
        "考试预测", "exam prediction", "考试重点",
        "知识图谱", "knowledge graph", "知识关联",
        "多步骤", "multi-step", "一系列", "一系列任务"
    }

    # 多步骤模式关键词 - Phase 2
    MULTI_STEP_INDICATORS = {
        "然后", "接着", "之后",
        "and then", "after that", "next", "followed by",
        "第一步", "首先", "first"
    }

    # Vision: Translation Keywords (5c)
    TRANSLATION_KEYWORDS = {
        "翻译", "translate", "解释意思", "what does this mean",
        "怎么说", "in english", "in chinese", "是什么意思"
    }

    # Vision: Prism/Behavior Keywords (5b, 15) - P0 Fix: Expanded
    PRISM_KEYWORDS = {
        "行为分析", "behavior analysis", "我的画像", "user profile",
        "认知棱镜", "cognitive prism", "学习习惯", "study habits",
        "周报", "weekly report", "日报", "daily report",
        "画像", "profile", "分析", "analysis", "学习分析", "analyze",  # P0 Fix: Added analyze
    }

    # Vision: Sprint Keywords (5d) - P0 Fix: Expanded
    SPRINT_KEYWORDS = {
        "冲刺", "sprint", "专注模式", "focus mode",
        "突击", "cram", "考试冲刺",
        "专注", "focus", "集中", "concentrate", "集中注意力",  # P0 Fix: Added
    }

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.intent_cache = IntentCache(redis_client) if redis_client else None

    def _preprocess_voice_input(self, message: str) -> str:
        """P0 Fix: 预处理语音转文字输入

        处理语音识别的常见问题：
        - 省略号 (...) → 替换为逗号
        - 重复短语 ("帮我...帮我") → 去重
        - 多余空格 → 清理
        """
        import re

        # 移除省略号
        message = re.sub(r'\.\.+', '，', message)

        # 移除重复的短语的简单实现
        # "帮我...帮我" → "帮我"
        message = re.sub(r'(.{1,3})[，,]\s*\1', r'\1', message)
        # 处理 "...分隔..." 模式
        message = re.sub(r'(.{1,5})\.\.+(.{1,5})', r'\1，\2', message)

        # 移除多余的空格
        message = ' '.join(message.split())

        return message

    async def decide(
        self,
        message: str,
        user_id: str,
        session_id: str
    ) -> RouteDecision:
        """路由决策 (Phase 2)

        规则 (优先级顺序):
        1. 高风险 → direct (安全优先，最高优先级)
        2. 复杂规划 → langgraph
        3. 特殊功能 (Translation/Prism/Sprint) → direct (Specific Tools)
        4. 其他 → direct

        P2 Improvement: Uses confidence-scoring intent classification with LLM fallback.

        Args:
            message: 用户消息
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            RouteDecision: 路由决策
        """
        # 获取 context_version
        context_version = await self._get_context_version(user_id)

        # Phase 1.1: Check cache first (sub-millisecond)
        if self.intent_cache:
            cached_result = await self.intent_cache.get_cached_intent(message)
            if cached_result:
                intent, confidence = cached_result
                logger.info(f"Using cached intent: {intent} (conf={confidence:.2f})")
            else:
                # Cache miss: classify and cache result
                intent, confidence = await self._classify_intent_with_confidence(message)

                # Use progressive classification for low confidence
                if confidence < 0.65:
                    logger.info(f"Low confidence ({confidence:.2f}), using progressive classification")
                    intent, confidence = await self._progressive_classify(message, intent, confidence, user_id)

                # Cache the result
                source = "llm" if confidence < 0.65 else "keyword"
                await self.intent_cache.cache_intent(message, intent, confidence, source)
        else:
            # No cache: direct classification
            intent, confidence = await self._classify_intent_with_confidence(message)

            # Use progressive classification for low confidence
            if confidence < 0.65:
                logger.info(f"Low confidence ({confidence:.2f}), using progressive classification")
                intent, confidence = await self._progressive_classify(message, intent, confidence, user_id)

        # 风险评估
        risk_level = self._assess_risk(message, intent)

        # Phase 2: 根据风险优先级决定执行模式
        execution_mode = "direct"
        reason = f"Intent: {intent}, Phase 2 routing"

        # === 优先级1: 高风险操作 → direct (安全优先) ===
        if risk_level == "high":
            execution_mode = "direct"
            confidence = 0.9
            reason = f"Intent: {intent}, HIGH RISK - direct mode for safety"
            logger.info(f"High risk detected, forcing direct mode: {intent}")

        # === 优先级2: 复杂意图 → langgraph (仅在非高风险时) ===
        elif self._is_complex_intent(message) and intent not in ["translation", "sprint", "prism"]:
            # Note: Translation/Sprint might be complex, but usually handled by specific tools/flows better in Direct or specialized nodes.
            # For now, we prioritize specific intent detection.
            execution_mode = "langgraph"
            confidence = 0.8
            reason = f"Intent: {intent}, complex routing via LangGraph"
            logger.info(f"Complex intent detected, using LangGraph: {intent}")

        # === 优先级3: 特殊意图 → direct (with tool intent) ===
        elif intent in ["translation", "prism", "sprint"]:
            execution_mode = "direct"
            confidence = 0.85
            reason = f"Intent: {intent}, specialized feature routing"
            logger.info(f"Specialized intent detected: {intent}")

        # === 优先级4: 默认 → direct ===
        else:
            execution_mode = "direct"
            reason = f"Intent: {intent}, standard direct routing"

        return RouteDecision(
            execution_mode=execution_mode,
            reason=reason,
            risk_level=risk_level,
            confidence=confidence,
            context_version=context_version
        )

    def _classify_intent(self, message: str) -> str:
        """简单意图分类

        基于关键词的规则分类

        P2 Improvement: Added confidence scoring and LLM fallback for uncertain cases.
        """
        msg_lower = message.lower()

        # Specialized Intents (High Priority)
        if any(k in msg_lower for k in self.TRANSLATION_KEYWORDS):
            return "translation"
        if any(k in msg_lower for k in self.PRISM_KEYWORDS):
            return "prism"
        if any(k in msg_lower for k in self.SPRINT_KEYWORDS):
            return "sprint"

        # Standard Intents
        if any(k in msg_lower for k in ["创建", "create", "新建", "添加", "add", "new"]):
            return "create"
        if any(k in msg_lower for k in ["查询", "query", "获取", "get", "搜索", "search", "看看"]):
            return "query"
        if any(k in msg_lower for k in ["更新", "update", "修改", "edit", "改变", "change", "改"]):
            return "update"
        if any(k in msg_lower for k in ["删除", "delete", "remove", "移除"]):
            return "delete"
        if any(k in msg_lower for k in ["学习", "learn", "study", "练习", "practice"]):
            return "learn"
        if any(k in msg_lower for k in ["复习", "review", "复习"]):
            return "review"

        return "chat"

    async def _classify_intent_with_confidence(self, message: str) -> Tuple[str, float]:
        """意图分类（带置信度评分） - P0 Fix: Improved priority handling

        P2 Improvement: Returns intent with confidence score.
        Low confidence triggers LLM-assisted classification.

        P0 Fix: 组合模式优先级优化，解决"学习"误匹配问题
        """
        # P0 Fix: 预处理语音输入
        message = self._preprocess_voice_input(message)
        msg_lower = message.lower()
        scores = {}

        # === P0 Fix: 优先级1: 组合模式 (更高置信度 0.85) ===
        # Pattern: 动词 + 对象 (解决"帮我制定学习计划"被误判为learn的问题)
        if (any(k in msg_lower for k in ["创建", "制定", "安排", "make", "create", "schedule"]) and
            any(k in msg_lower for k in ["任务", "计划", "时间", "task", "plan", "time"])):
            scores["create"] = 0.85

        if (any(k in msg_lower for k in ["复习", "回顾", "review"]) and
            any(k in msg_lower for k in ["数学", "英语", "物理", "化学", "math", "english", "physics"])):
            scores["review"] = 0.85

        # === 优先级2: 特殊意图 (高置信度 0.8) ===
        # Prism (已扩展关键词)
        if any(k in msg_lower for k in self.PRISM_KEYWORDS):
            scores["prism"] = max(scores.get("prism", 0), 0.8)

        # Sprint (已扩展关键词)
        if any(k in msg_lower for k in self.SPRINT_KEYWORDS):
            scores["sprint"] = max(scores.get("sprint", 0), 0.8)

        # Translation
        if any(k in msg_lower for k in self.TRANSLATION_KEYWORDS):
            scores["translation"] = max(scores.get("translation", 0), 0.8)

        # === 优先级3: 标准意图 (中等置信度 0.7) ===
        if any(k in msg_lower for k in ["删除", "delete", "remove", "移除"]):
            scores["delete"] = max(scores.get("delete", 0), 0.8)

        if any(k in msg_lower for k in ["创建", "create", "新建", "添加", "add", "new"]):
            scores["create"] = max(scores.get("create", 0), 0.7)

        if any(k in msg_lower for k in ["更新", "update", "修改", "edit", "改变", "change", "改"]):
            scores["update"] = max(scores.get("update", 0), 0.7)

        if any(k in msg_lower for k in ["查询", "query", "获取", "get", "搜索", "search", "看看"]):
            scores["query"] = max(scores.get("query", 0), 0.7)

        # === P0 Fix: 优先级4: 单独"学习"关键词 (降低权重 0.5，避免覆盖create) ===
        # 只有在没有明确"创建/制定"时才匹配learn
        if ("学习" in msg_lower or "learn" in msg_lower or "study" in msg_lower):
            # P0 Fix: 检查是否有创建类动词，如果有则不增加learn分数
            has_create_verb = any(k in msg_lower for k in ["创建", "制定", "安排", "make", "create", "schedule"])
            if not has_create_verb:
                scores["learn"] = max(scores.get("learn", 0), 0.5)

        if any(k in msg_lower for k in ["复习", "review"]):
            scores["review"] = max(scores.get("review", 0), 0.6)

        if not scores:
            return "chat", 0.5

        # 返回得分最高的意图
        max_intent = max(scores, key=scores.get)
        confidence = scores[max_intent]

        return max_intent, confidence

    async def _get_user_intent_patterns(self, user_id: str) -> dict:
        """获取用户常用意图模式

        从Redis读取用户历史意图分布，用于个性化分类。

        Args:
            user_id: 用户ID

        Returns:
            dict: 用户意图模式 {"recent_intents": [...], "intent_counts": {...}}
        """
        if not self.redis:
            return {"recent_intents": [], "intent_counts": {}}

        try:
            import json
            key = f"user:intent:patterns:{user_id}"
            raw = await self.redis.get(key)

            if raw:
                return json.loads(raw)
            else:
                # 返回默认分布
                return {
                    "recent_intents": ["chat", "create", "query"],
                    "intent_counts": {"chat": 5, "create": 3, "query": 2}
                }
        except Exception as e:
            logger.warning(f"Failed to get user intent patterns: {e}")
            return {"recent_intents": [], "intent_counts": {}}

    def _get_candidate_intents(self, message: str) -> list:
        """预分析候选意图（通过关键词）

        用于缩小LLM分类的搜索空间，提高速度和准确性。

        Args:
            message: 用户消息

        Returns:
            list: 候选意图列表
        """
        msg_lower = message.lower()
        candidates = []

        # 检查各意图的关键词
        intent_keywords = {
            "translation": self.TRANSLATION_KEYWORDS,
            "prism": self.PRISM_KEYWORDS,
            "sprint": self.SPRINT_KEYWORDS,
            "create": ["创建", "create", "制定", "make", "计划", "plan"],
            "update": ["更新", "update", "修改", "edit", "改变", "change"],
            "delete": ["删除", "delete", "remove", "移除"],
            "query": ["查询", "query", "获取", "get", "搜索", "search"],
            "learn": ["学习", "learn", "study", "练习", "practice"],
            "review": ["复习", "review", "回顾"],
        }

        for intent, keywords in intent_keywords.items():
            if any(k in msg_lower for k in keywords):
                candidates.append(intent)

        # 如果没有候选，返回默认选项
        if not candidates:
            return ["chat", "query", "create"]

        return candidates

    async def _classify_intent_llm_assisted(self, message: str, user_id: str = None) -> str:
        """使用轻量级 LLM 进行意图分类（增强版）

        Phase 1.3 Improvement: Optimized with user patterns and candidate intents.
        Target: Reduce LLM call time from ~38s to ~15s.

        P2 Improvement: LLM-assisted intent classification for ambiguous cases.
        When keyword matching confidence is low, use LLM for better accuracy.
        """
        from app.services.llm_service import llm_service

        # Phase 1.3: 获取用户常用意图（从Redis）
        user_patterns = await self._get_user_intent_patterns(user_id) if user_id else {}
        recent_intents = user_patterns.get("recent_intents", [])

        # Phase 1.3: 预分析候选意图（通过关键词）
        candidate_intents = self._get_candidate_intents(message)

        # Phase 1.3: 优化prompt（减少token，提高速度）
        all_intents = ["chat", "create", "update", "delete", "query", "learn", "review", "translation", "prism", "sprint"]

        prompt = f"""你是一个意图分类专家。请快速分析用户意图。

用户常用意图: {', '.join(recent_intents[:3]) if recent_intents else '无'}

候选意图: {', '.join(candidate_intents[:5])}

用户消息: "{message}"

请从候选意图中选择最匹配的一个，直接返回意图名称（小写）。

可选意图: {', '.join(all_intents)}"""

        try:
            # Phase 1.3: 使用更快的模型参数
            response = await llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,  # 降低随机性，提高一致性
                max_tokens=10,  # 限制输出长度，减少延迟
            )
            intent = response.strip().lower()

            # 映射到标准意图
            intent_mapping = {
                "behavior analysis": "prism",
                "cognitive prism": "prism",
                "focus mode": "sprint",
                "study habits": "prism",
                "translate": "translation",
                "translating": "translation",
            }
            mapped_intent = intent_mapping.get(intent, intent)

            # 验证返回的意图是否在有效列表中
            if mapped_intent in all_intents:
                return mapped_intent
            else:
                logger.warning(f"LLM returned invalid intent: {intent}, falling back to keyword matching")
                return self._classify_intent(message)

        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}, falling back to keyword matching")
            return self._classify_intent(message)  # 降级到关键词匹配

    async def _progressive_classify(
        self,
        message: str,
        initial_intent: str,
        initial_confidence: float,
        user_id: str = None
    ) -> Tuple[str, float]:
        """渐进式意图分类 (Progressive Classification)

        Three-tier classification pipeline:
        1. Quick keyword match (<10ms) - already done in _classify_intent_with_confidence
        2. Medium pattern match (<50ms) - additional rules
        3. LLM classification (<5s) - only when necessary

        Target: Reduce LLM calls by 60% while maintaining accuracy.

        Args:
            message: User message
            initial_intent: Intent from quick match
            initial_confidence: Confidence from quick match
            user_id: User ID for personalized classification (Phase 1.3)

        Returns:
            (intent, confidence) tuple
        """
        import time
        start_time = time.time()

        # === Tier 2: Medium complexity patterns (<50ms) ===
        msg_lower = message.lower()

        # Pattern: Complex sentence structures with conjunctions
        # "帮我制定...然后..." -> likely create
        if "然后" in msg_lower or "接着" in msg_lower or "之后" in msg_lower:
            # Check if has create keywords
            if any(k in msg_lower for k in ["创建", "制定", "安排", "make", "create"]):
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Tier-2 classification: complex sentence structure -> create ({elapsed:.1f}ms)")
                return "create", 0.75

        # Pattern: Context-dependent queries
        # "那个计划" -> likely query/update (depends on context)
        if "那个" in msg_lower or "这个" in msg_lower:
            if any(k in msg_lower for k in ["修改", "改", "update", "change"]):
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Tier-2 classification: context-dependent update -> update ({elapsed:.1f}ms)")
                return "update", 0.70
            elif any(k in msg_lower for k in ["删除", "delete", "remove"]):
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Tier-2 classification: context-dependent delete -> delete ({elapsed:.1f}ms)")
                return "delete", 0.70

        # Pattern: Mixed language (Chinese + English)
        # "I want to study 数学" -> learn
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in message)
        has_english = any(c.isalpha() and ord(c) < 128 for c in message)
        if has_chinese and has_english:
            # Check for learning-related keywords
            if any(k in msg_lower for k in ["study", "learn", "学习", "学"]):
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Tier-2 classification: mixed language -> learn ({elapsed:.1f}ms)")
                return "learn", 0.70

        # === Tier 3: LLM classification (only if Tier 2 didn't resolve) ===
        if initial_confidence < 0.65:
            logger.info(f"Tier-3: Using LLM classification for low confidence case")
            try:
                intent = await self._classify_intent_llm_assisted(message, user_id)
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"Tier-3 LLM classification: {intent} ({elapsed:.1f}ms)")
                return intent, 0.85
            except Exception as e:
                logger.warning(f"Tier-3 LLM classification failed: {e}, using initial result")

        # Fallback: return initial classification
        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Progressive classification using initial: {initial_intent} ({elapsed:.1f}ms)")
        return initial_intent, initial_confidence

    def _assess_risk(self, message: str, intent: str) -> str:
        """风险评估

        基于意图和关键词的风险等级评估
        """
        msg_lower = message.lower()

        # High risk: 删除操作
        if intent == "delete":
            return "high"

        # High risk keywords
        high_risk_keywords = ["全部", "all", "所有", "清空", "clear"]
        if any(k in msg_lower for k in high_risk_keywords):
            return "high"

        # Medium risk: 创建和更新
        if intent in ["create", "update"]:
            return "medium"

        # Low risk: 查询和聊天
        return "low"

    async def _get_context_version(self, user_id: str) -> str:
        """获取当前 context version

        从 Redis 读取用户的 context version
        """
        if self.redis:
            from app.orchestration.orchestrator import CONTEXT_VERSION_KEY_PREFIX
            import json

            key = f"{CONTEXT_VERSION_KEY_PREFIX}{user_id}"
            try:
                raw = await self.redis.get(key)
                if raw:
                    versions = json.loads(raw)
                    return versions.get("tasks", "v0")
            except Exception as e:
                logger.warning(f"Failed to get context version: {e}")

        return "v0"

    def _is_complex_intent(self, message: str) -> bool:
        """检查是否为复杂意图 (Phase 2)

        复杂意图的判断标准:
        1. 包含复杂意图关键词
        2. 包含多步骤指示词
        3. 消息长度超过阈值（可能包含多个请求）

        Args:
            message: 用户消息

        Returns:
            bool: 是否为复杂意图
        """
        msg_lower = message.lower()

        # 1. 检查是否包含复杂意图关键词
        for keyword in self.COMPLEX_INTENTS:
            if keyword.lower() in msg_lower:
                logger.debug(f"Complex intent detected: {keyword}")
                return True

        # 2. 检查是否为多步骤任务
        for indicator in self.MULTI_STEP_INDICATORS:
            if indicator.lower() in msg_lower:
                logger.debug(f"Multi-step intent detected: {indicator}")
                return True

        # 3. 消息长度检查（简化实现）
        # 较长的消息可能包含多个请求或复杂描述
        if len(message) > 100:
            # 检查是否包含多个句子（可能表示多个任务）
            sentence_count = message.count('。') + message.count('.') + message.count('!') + message.count('?')
            if sentence_count >= 2:
                logger.debug(f"Multi-sentence intent detected: {sentence_count} sentences")
                return True

        return False
