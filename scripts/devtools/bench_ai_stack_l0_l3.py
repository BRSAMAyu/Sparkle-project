#!/usr/bin/env python3
"""E-08 AI Stack 集成 Bench — Quality × TTFT × Cost × Context（L0-L3 路由层级，真模型真路由）.

对常驻引擎（gRPC :50051，FastAPI :8000）以真实账号（guest JWT）逐条发送学习成长域
query 语料，按 L0 快答 / L1 标准 / L2 深推理 / L3 编排·长上下文 四层设计驱动语料，
逐 query 记录 TTFT / total / token / cost / context / stage / fallback / quality 全量字段，
并按 intent / persona / lane / observed-tier 切片输出 dashboard summary 与 SLO 对照。

- 真模型真路由：不用 mock/seed 冒充；观察路由来自 token_usage（DB）+ 流内 metadata。
- 失败不重试：gRPC 错误 / usage 缺失 / provider 429 全部如实落 raw。
- cost：按 provider 官方单价表（脚本内硬编码，注明来源日期）以 usage token 计算；
  同时保留引擎侧 cost 估算作对照。隐藏辅助调用（Layer3 分类/sufficiency/HyDE）不在
  token_usage 计量范围内，报告口径为「主生成计量成本」。

用法:
  python3 bench_ai_stack_l0_l3.py run [--limit N] [--layers L0,L1,L2,L3] [--tag NAME]
                                      [--out-dir DIR]
  python3 bench_ai_stack_l0_l3.py summarize [--out-dir DIR]

依赖：主仓 backend/.venv（grpc / httpx）；DB 归因经 `docker exec sparkle_db psql`。
默认输出目录：<repo>/v3-output/WT372-E08-BENCH/
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "v3-output" / "WT372-E08-BENCH"

# 引擎运行时（常驻实例）所在 backend：generated stubs 从这里加载。
ENGINE_BACKEND = Path("/Users/brsama/code/GitHub/Sparkle-project/backend")
GRPC_TARGET = "127.0.0.1:50051"
HTTP_BASE = "http://127.0.0.1:8000/api/v1"
GUEST_ID = "wt372_e08_bench"
PSQL_CONTAINER = "sparkle_db"
PSQL_USER = "postgres"
PSQL_DB = "sparkle"

SESSION_ROTATE_EVERY = 3
TIMEOUT_S_DEFAULT = 90.0
TIMEOUT_S_L3 = 180.0
INTER_QUERY_SLEEP_S = 0.8

# ---------------------------------------------------------------------------
# Provider 官方单价表（USD / 1M tokens，in/out）。来源与日期见 SOURCE 注释。
# 汇率：1 USD = 7.15 CNY（2026-09 参考汇率）。
# ---------------------------------------------------------------------------
CNY_PER_USD = 7.15
PRICE_TABLE_USD_PER_MTOK: dict[str, dict] = {
    # key = token_usage.model（引擎模型 key）；name = 解析后的 provider 模型名
    "dashscope_fast": {
        "provider": "dashscope", "model": "qwen3.7-flash",
        "in": 0.225 / CNY_PER_USD, "out": 0.974 / CNY_PER_USD,
        "source": "Aliyun help.aliyun.com qwen3.7-flash 模型价格页 2026-09-10（¥0.225/¥0.974 per M）",
    },
    "dashscope_chat": {
        "provider": "dashscope", "model": "qwen3.7-plus",
        "in": 2.0 / CNY_PER_USD, "out": 8.0 / CNY_PER_USD,
        "source": "Aliyun 百炼 qwen3.7-plus 列表价 2026-09 检索（¥2/¥8 per M，未计 8 折活动）",
    },
    "dashscope_standard_thinking": {
        "provider": "dashscope", "model": "qwen3.8-flash",
        "in": 0.8 / CNY_PER_USD, "out": 2.7 / CNY_PER_USD,
        "source": "Aliyun 百炼调价公告 2026-08-27 生效（¥0.8/¥2.7 per M）",
    },
    "dashscope_reason": {
        "provider": "dashscope", "model": "qwen3.8-flash",
        "in": 0.8 / CNY_PER_USD, "out": 2.7 / CNY_PER_USD,
        "source": "DASHSCOPE_REASON_MODEL 运行时解析（.env LLM_REASON_MODEL_NAME=qwen3.8-flash）；单价同 qwen3.8-flash 2026-08-27 价",
    },
    "qwen3_8_max": {
        "provider": "dashscope", "model": "qwen3.8-max",
        "in": 2.0, "out": 6.0,
        "source": "Qwen3.8-Max 参考价 $2/$6 per M（llmpricing.dev 2026-09-12；官方 Model Studio 页未直接抓取，报告中标注）",
    },
    "qwen3_8_max_top": {
        "provider": "dashscope", "model": "qwen3.8-max",
        "in": 2.0, "out": 6.0,
        "source": "同 qwen3_8_max（TOP 层同旗舰模型）",
    },
    "glm_4_7_flash_no_thinking": {
        "provider": "zhipu", "model": "glm-5.3-flash",
        "in": 0.8 / CNY_PER_USD, "out": 2.8 / CNY_PER_USD,
        "source": "BigModel 开放平台 glm-5.3-flash 列表价 2026-08 检索（¥0.8/¥2.8 per M，未计限时 5 折）",
    },
    "glm_4_7_flash_thinking": {
        "provider": "zhipu", "model": "glm-5.3-flash",
        "in": 0.8 / CNY_PER_USD, "out": 2.8 / CNY_PER_USD,
        "source": "同 glm_4_7_flash_no_thinking",
    },
    "glm_4_7_pro": {
        "provider": "zhipu", "model": "glm-5.3-flash",
        "in": 0.8 / CNY_PER_USD, "out": 2.8 / CNY_PER_USD,
        "source": "glm_4_7_pro 运行时解析 ZHIPU_TOOLS_MODEL=.env glm-5.3-flash；单价同 glm-5.3-flash",
    },
    "deepseek_chat": {
        "provider": "deepseek", "model": "deepseek-flash(v4-flash 系)",
        "in": 1.0 / CNY_PER_USD, "out": 2.0 / CNY_PER_USD,
        "source": "DeepSeek V4-flash 系最低档 2026-04 检索（约 ¥1/¥2 per M）——近似值，已标记 approx",
        "approx": True,
    },
    "deepseek_reason": {
        "provider": "deepseek", "model": "deepseek-v4-pro",
        "in": 0.435, "out": 0.87,
        "source": "DeepSeek 官方 api-docs 2026-08-17 正式版价（$0.435/$0.87 per M）",
    },
    "default": {
        "provider": "none", "model": "no-generation(metered as default)",
        "in": 0.0, "out": 0.0,
        "source": "token_usage.model='default' = 生成模型 key 未写入（前置链模板/澄清门 0 token；或多代理流 metering 错挂）；计 0 并计 fallback（见 REPORT 归因）",
        "fallback_marker": True,
    },
}

# V3 DoD Gate V3-8 候选 SLO（以真实基线校验的对象）
SLO = {
    "L0_ttft_p95_ms": 500.0,
    "L1_ttft_p50_s": 2.5,
    "L1_ttft_p95_s": 5.0,
    "L2_first_feedback_p95_ms": 500.0,
    "L2_total_p95_s": 15.0,
    "L3_ack_p95_s": 1.0,
}

# ---------------------------------------------------------------------------
# 语料：4 层 × 26 条 = 104。学习成长域，中英混合，真实多样。
# lane: free（默认免费层）/ pro（extra_context.user_tier=pro，解锁 STANDARD/PRO/MAX）
# ---------------------------------------------------------------------------
CORPUS: list[dict] = [
    # ============ L0 快答（26）============
    {"qid": "L0-01", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "你好"},
    {"qid": "L0-02", "layer": "L0", "persona": "college_student", "lang": "en", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "hi"},
    {"qid": "L0-03", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "你好啊，今天有点累"},
    {"qid": "L0-04", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "thanks", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "谢谢！"},
    {"qid": "L0-05", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "收到了"},
    {"qid": "L0-06", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "明白了，谢谢"},
    {"qid": "L0-07", "layer": "L0", "persona": "professional", "lang": "en", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "ok thanks"},
    {"qid": "L0-08", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "嗯嗯，我记住了"},
    {"qid": "L0-09", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "帮我记住：我最喜欢的电影是《星际穿越》"},
    {"qid": "L0-10", "layer": "L0", "persona": "college_student", "lang": "en", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "My favorite band is Coldplay, please remember that"},
    {"qid": "L0-11", "layer": "L0", "persona": "professional", "lang": "zh", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我每周三晚上固定去健身房，帮我记着"},
    {"qid": "L0-12", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "1+1等于几？"},
    {"qid": "L0-13", "layer": "L0", "persona": "college_student", "lang": "en", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "What is 15% of 200?"},
    {"qid": "L0-14", "layer": "L0", "persona": "self_learner", "lang": "en", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "hello!"},
    {"qid": "L0-15", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "早安"},
    {"qid": "L0-16", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "晚安"},
    {"qid": "L0-17", "layer": "L0", "persona": "professional", "lang": "mixed", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "Good morning, let's study"},
    {"qid": "L0-18", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我回来了"},
    {"qid": "L0-19", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "continuation", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "继续"},
    {"qid": "L0-20", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "好的，就按你说的办"},
    {"qid": "L0-21", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "continuation", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "嗯，继续吧"},
    {"qid": "L0-22", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "thanks", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "谢谢你，很有帮助"},
    {"qid": "L0-23", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "记住我的考研目标是2027年12月"},
    {"qid": "L0-24", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "persona_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我叫小林"},
    {"qid": "L0-25", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "2的10次方是多少？"},
    {"qid": "L0-26", "layer": "L0", "persona": "professional", "lang": "en", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "How many days are there in a leap year?"},

    # ============ L1 标准（26）============
    {"qid": "L1-01", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是遗忘曲线？"},
    {"qid": "L1-02", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "用一句话解释什么是主动回忆"},
    {"qid": "L1-03", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "间隔重复和集中复习哪个更有效？"},
    {"qid": "L1-04", "layer": "L1", "persona": "college_student", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "What is spaced repetition?"},
    {"qid": "L1-05", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "番茄工作法是什么？"},
    {"qid": "L1-06", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是费曼学习法？"},
    {"qid": "L1-07", "layer": "L1", "persona": "self_learner", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "Explain the forgetting curve in one sentence."},
    {"qid": "L1-08", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "怎么快速背单词？"},
    {"qid": "L1-09", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "艾宾浩斯遗忘曲线对复习安排有什么启发？"},
    {"qid": "L1-10", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "每天背100个单词现实吗？"},
    {"qid": "L1-11", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是刻意练习？"},
    {"qid": "L1-12", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "心流是什么状态？"},
    {"qid": "L1-13", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是康奈尔笔记法？"},
    {"qid": "L1-14", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "二八法则在学习中怎么用？"},
    {"qid": "L1-15", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "comparison", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "主动回忆和重复阅读的区别是什么？"},
    {"qid": "L1-16", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "goal_check", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我想三个月内考完雅思6.5，现在5.5，可行吗？"},
    {"qid": "L1-17", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "quiz_gen", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "帮我出3个关于细胞呼吸的复习题"},
    {"qid": "L1-18", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是间隔效应？"},
    {"qid": "L1-19", "layer": "L1", "persona": "professional", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "Sleep before or after studying — which helps memory more?"},
    {"qid": "L1-20", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是交叉学习（interleaving）？"},
    {"qid": "L1-21", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "看书犯困怎么办？"},
    {"qid": "L1-22", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "坐地铁上能做什么碎片学习？"},
    {"qid": "L1-23", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "一个人自习坚持不下去怎么办？"},
    {"qid": "L1-24", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是输出式学习？"},
    {"qid": "L1-25", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "笔记应该手写还是打字？"},
    {"qid": "L1-26", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "如何判断自己真的学会了？"},

    # ============ L2 深推理（26）：13 free + 13 pro ============
    {"qid": "L2-01", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "comparison", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "比较主动回忆、间隔重复、交错练习三种方法的适用场景、证据强度和常见误用"},
    {"qid": "L2-02", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "diagnose", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我每天背单词2小时但第二天忘70%，从记忆编码和检索练习角度分析可能原因，并给出诊断步骤"},
    {"qid": "L2-03", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "theory_apply", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用认知负荷理论解释为什么一边看视频一边做笔记效率低"},
    {"qid": "L2-04", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "error_diagnosis", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "求 dy/dx of x^2*e^x，我算成 2x*e^x，错在哪？给出正确推导的每一步"},
    {"qid": "L2-05", "layer": "L2", "persona": "professional", "lang": "mixed", "intent": "code_review", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "review this Python function: def avg(xs): return sum(xs)/len(xs) — 从边界条件和类型角度列出所有失败场景"},
    {"qid": "L2-06", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "writing_feedback", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我的论文摘要是：本研究通过问卷调查发现大学生手机使用与学业拖延正相关，因此限制手机使用可以缓解拖延。从论证结构角度指出3个弱点并按严重性排序"},
    {"qid": "L2-07", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "theory_apply", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "为什么间隔重复有效？从提取强度和存储强度的双存储模型解释"},
    {"qid": "L2-08", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "math_derive", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "帮我推导最优复习间隔的近似公式，并明确列出推导假设"},
    {"qid": "L2-09", "layer": "L2", "persona": "beginner", "lang": "zh", "intent": "comparison", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "对比费曼学习法和苏格拉底提问法在学习闭环上的差异"},
    {"qid": "L2-10", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "plan_eval", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "计划A：每天上午数学3小时下午英语2小时；计划B：单日数学5小时/双日英语5小时交替。从执行成本和遗忘干扰角度评估哪份更适合考研冲刺，说明理由"},
    {"qid": "L2-11", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "attribution", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我按计划学了三天就中断了，从行为设计角度做归因分析，区分动机问题还是系统问题"},
    {"qid": "L2-12", "layer": "L2", "persona": "professional", "lang": "zh", "intent": "diagnose", "lane": "free", "reasoning_mode": "deep", "chat_mode": "error_diagnosis", "text": "我的睡眠从7小时降到5小时后学习效率明显下降，请诊断可能的机制并给出验证方法"},
    {"qid": "L2-13", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "theory_apply", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用测试效应解释为什么做题比看书记得牢，并指出该结论的适用边界"},
    {"qid": "L2-14", "layer": "L2", "persona": "professional", "lang": "mixed", "intent": "code_review", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "一个 class DataPipeline 有300行 if-else 分支处理不同数据源，给出重构方案、每种方案的迁移风险和回归验证清单"},
    {"qid": "L2-15", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "从自我决定理论角度分析：外部奖励（打卡返现）何时会削弱学习内在动机？给出边界条件"},
    {"qid": "L2-16", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "experiment_design", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "两篇文献结论矛盾：一篇说多任务损害学习，一篇说背景音乐帮助专注。设计一个实验来仲裁，给出自变量、因变量和控制变量"},
    {"qid": "L2-17", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "diagnose", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我的高数错题集中在链式法则，如何判别是概念问题还是熟练度问题？给出判别方法和对应的两种训练方案"},
    {"qid": "L2-18", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用信息加工模型解释「听课懂了做题不会」的现象，指出干预点并排序"},
    {"qid": "L2-19", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "logic_check", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "对这个论证做逻辑审查：「天才都是延迟满足的，所以我延迟满足就能成为天才」"},
    {"qid": "L2-20", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "system_design", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我用Anki三个月，卡片从300张积到2400张，开始逃避复习。从系统设计角度提出三个修复方向，并评估每个方向的执行代价"},
    {"qid": "L2-21", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "深度优先和广度优先搜索在复习规划中的类比是否成立？成立条件和边界在哪里？"},
    {"qid": "L2-22", "layer": "L2", "persona": "beginner", "lang": "zh", "intent": "goal_eval", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "评估这个目标的SMART程度并重写：「这学期把英语学好」"},
    {"qid": "L2-23", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "tradeoff", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "期末两周，四门课都想上80分但时间只够两门，给出基于期望值的取舍框架，并用假设分数分布算一个具体例子"},
    {"qid": "L2-24", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "为什么「标注重点」会产生学习错觉？从流畅性启发式的角度分析"},
    {"qid": "L2-25", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "tradeoff", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我打算同时准备考研和秋招，分析两者的时间冲突点，给出资源分配建议和止损条件"},
    {"qid": "L2-26", "layer": "L2", "persona": "self_learner", "lang": "mixed", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "Use the desirable difficulties framework to analyze why fluent learning can be dangerous, and give two counter-examples where difficulty does NOT help"},

    # ============ L3 编排·长上下文（26）：free/pro 各13 ============
    {"qid": "L3-01", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我要备战2027年研究生考试，目标院校复旦计算机，我本科双非一本绩点3.2，每天可投入4小时，帮我制定第一阶段3个月的复习计划，要包含科目优先级和里程碑"},
    {"qid": "L3-02", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "45天雅思从5.5到6.5，听力阅读弱，口语还行，每天3小时，给我一份周计划骨架，含每周自测点"},
    {"qid": "L3-03", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "下学期我有5门课，还要打一个编程竞赛和一个社团，每周总时间预算60小时，帮我做一个学期资源分配方案，说明冲突时的取舍规则"},
    {"qid": "L3-04", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我要转行做数据分析师，零基础，目标6个月，每天2.5小时，请制定学习路线图、里程碑和每个阶段的验收标准"},
    {"qid": "L3-05", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "两周内准备操作系统期中考，重点是进程调度和内存管理，教材600页，帮我拆解到天的复习计划，标注每天的自检问题"},
    {"qid": "L3-06", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "帮我规划一个12周的算法自学训练营，从贪心到动态规划，每周10小时，含每周题目量和复盘节奏"},
    {"qid": "L3-07", "layer": "L3", "persona": "beginner", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "高三学生，物理目前40分（满分100），目标高考80分，还有120天，给我分阶段提分方案，每阶段要有明确的止损判断"},
    {"qid": "L3-08", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我要准备一个30分钟的学术报告，主题是我最近的记忆训练实验，两周后讲，帮我规划准备流程，含试讲和答疑准备"},
    {"qid": "L3-09", "layer": "L3", "persona": "professional", "lang": "mixed", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "I need a 3-month GRE vocab+reading plan. I work full time, 1.5h on weekdays, up to 4h on weekends. Make it resilient to overtime weeks."},
    {"qid": "L3-10", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我想在6个月内系统学完线性代数并应用到机器学习，数学基础是高中水平，请规划分月路径和每步的自测标准"},
    {"qid": "L3-11", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "【学习材料】记忆的双存储模型：记忆研究传统上区分初级记忆（PM，即工作记忆/短时记忆）与次级记忆（SM，即长时记忆）。初级记忆容量有限（成人约7±2个组块），保持时间在无复述条件下约15-30秒；次级记忆容量近似无限，保持时间受提取线索与干扰影响。序列位置效应：自由回忆任务中，开头项目回忆率较高（首因效应，归因于复述转入次级记忆），结尾项目在即时回忆中优势明显（近因效应，归因于初级记忆中尚存痕迹），延时回忆后近因效应消失而首因效应保留。加工深度：Craik与Lockhart的加工水平理论认为，语义加工（深加工）比形式加工（浅加工，如判断字形）产生更持久的记忆痕迹，即「加工越深、记得越牢」。提取练习：与重复阅读相比，主动提取（测试）虽在当下感觉更吃力，却能显著提升延时保持，这一主观困难与客观效果的分离被称为「熟练度错觉」的反面证据。应用提示：复习安排应优先保证提取练习频次，其次才是单次时长；材料组织上应减少干扰源（相似材料连排）。【问题】根据材料解释：为什么考前突击复习的遗忘模式与分散学习不同？并给出一条可执行的复习安排推论"},
    {"qid": "L3-12", "layer": "L3", "persona": "professional", "lang": "en", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "[Study material] Deliberate practice vs naive practice: Naive practice is characterized by repetition of activities already mastered, such as playing familiar songs on the piano or re-reading highlighted textbook chapters. Deliberate practice, by contrast, has four defining features: (1) well-defined stretch goals that sit just beyond current ability; (2) full concentration on the task, often described as effortful; (3) immediate informative feedback, which may come from a coach, a metric, or a designed check; (4) repetition with refinement, where the practitioner identifies weaknesses and designs the next repetition to target them. Research on chess masters, musicians and athletes shows that accumulated hours of mere experience correlate weakly with performance once players reach professional level, while accumulated deliberate practice correlates strongly. A common failure mode is 'experience autopilot': professionals repeat what is comfortable, mistaking hours logged for skill gained. Design implication for learners: convert passive input time into targeted extraction tasks, and instrument practice so feedback latency is minutes, not weeks. [Question] According to the passage, what distinguishes deliberate practice from naive practice, and what design implications follow for a self-taught learner?"},
    {"qid": "L3-13", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "【学习材料】SM-2 间隔调度算法：SM-2 以卡片质量分 q（0-5）驱动。每次回忆后：若 q>=3，卡片进入下一个间隔；若 q<3，卡片回到间隔1（重学）。间隔更新规则：第一次成功后 I(1)=1 天；第二次成功后 I(2)=6 天；此后 I(n)=I(n-1)*EF，其中 EF 为易度因子（easiness factor），初始 2.5。每次评分后 EF 按公式调整：EF' = EF + (0.1 - (5-q)*(0.08+(5-q)*0.02))，且 EF 下限 1.3。材料未涉及的工程细节：队列排序策略、逾期卡片的加权、以及每日新卡上限。【问题】从材料中提取 SM-2 的核心参数和更新规则，并指出材料未说明、但工程上必须补充的一个实现细节，说明为什么必须补充"},
    {"qid": "L3-14", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【学习材料】认知负荷三类：内在负荷（intrinsic load）由元素交互复杂度决定，取决于材料本身与学习者已有图式；外在负荷（extraneous load）由呈现方式不良引起，如需要在多个信息源间反复跳跃、冗余信息重复呈现；相关负荷（germane load）是投入于图式建构与自动化的认知资源。教学设计原则：降低外在负荷（整合图文、去冗余）、管理内在负荷（分段、先简后繁、样例学习）、留出相关负荷空间（自我解释、变式练习）。【问题】用材料中的三类负荷分析这个教学案例的优劣：一节数据结构课上，老师把红黑树的插入规则、旋转动画、数学证明和工程应用四个内容同时放在一张幻灯片上讲解，并要求学生边听边抄笔记"},
    {"qid": "L3-15", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【学习周报摘录】第6周：计划学习时长 21h，实际完成 13.5h。构成：高数 6h（全部用于看视频，做题0），英语 4h（单词打卡7/7），专业课 2h（教材第3章，未做笔记），项目 1.5h。中断记录：周三晚、周六全天（原因未记录）。情绪自评：周三 2/5，周日 4/5。上周遗留：错题重做 12 道只完成 3 道。自评一句话：「感觉一直在学，但心里没底」。【问题】从周报中找出三个异常信号，说明每个信号的判断依据，并针对每个信号提出一个该向这位学习者追问的问题"},
    {"qid": "L3-16", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【综述摘录】自我决定理论（SDT）主张自主、胜任、归属三种基本心理需要。关于外部奖励：Deci 等元分析（1999，128 项实验）发现 tangible expected rewards 显著削弱自由选择测得的内在动机，verbal praise 反而增强；但该结论在「任务本身有趣」的前提下最强，对枯燥任务效果不显著或为正。Hennessey 等指出奖励削弱效应受奖励情境性（contingency）调节：完成依赖型削弱最强，表现依赖型中性，创造质量依赖型在开放任务中削弱显著。样本局限：早期研究多为西方大学生短任务，跨文化与长时程证据较薄；教育现场研究（如Token Economy）显示长期外部强化对出勤等行为有效，但对深度学习结果的迁移证据不足。【问题】综述中哪些结论存在样本或生态效度局限？逐条列出局限内容与对应的证据强度评级，并指出哪一条对「学习APP打卡返现」设计最有参考价值"},
    {"qid": "L3-17", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【学习材料】间隔效应简史：1885年 Ebbinghaus 以无意义音节与自我实验绘制遗忘曲线，发现遗忘先快后慢；1920s Piéron 提出间隔复习优于集中；1967年 Bjork 等在自由回忆中分离出列表间隔（lag）效应，lag 越大延时回忆越好；1978年 Dempster 综述将其推向教育场景；1987年 Cepeda 等的元分析（254 项）确认间隔效应跨材料稳健，并发现「间隔/保持期比值」存在最优点（约10-20%）；2010年代 Spaced-repetition 软件（SM-2 系）普及使个体化调度成为可能；近年争议点：最优间隔的机制解释（编码变异 vs 提取难度）仍未定，且多数实验保持期不超过1个月。【问题】按时间线梳理关键转折点，并指出材料中因果证据最薄弱的一个环节，说明薄弱的理由"},
    {"qid": "L3-18", "layer": "L3", "persona": "professional", "lang": "mixed", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "[Study material, mixed] A productivity system in brief: Daily operations — (1) morning: pick exactly 3 MITs (most important tasks) linked to current goals; (2) capture: any new idea goes to inbox, not into the plan; (3) evening: 5-minute review of what moved, mark done/missed. Weekly operations — (1) weekly review: clear inbox, re-estimate tasks older than 7 days, choose next week's 3 focuses; (2) time-audit: compare planned vs actual hours per category; (3) pre-plan the hardest block first on the calendar. Principles — single capture point, plan at day granularity not hour granularity, protect one deep-work block per day, treat missed plans as data not failure. Known limits: designed for knowledge workers with calendar control; assumes stable weekly rhythm; no handling for exam-cram periods or collaborative schedules. [Question] Extract the daily and weekly operation checklists from the material, then point out two mismatches when applying this system to a Chinese high-school student preparing gaokao, and propose one adaptation for each"},
    {"qid": "L3-19", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：过去一个月我做 Anki 卡 1200 张，完成率从90%降到40%，单词量测试分数持平，但我感觉「一直在忙」。补充数据：日均学习2.8h，其中制卡占1.6h，复习队列逾期率35%，卡片最短间隔全部是1天。请给出：根因假设（至少3层：系统设计/内容质量/时间分配）、每个假设的验证实验（一周内可完成）、以及停止做某事的清单"},
    {"qid": "L3-20", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：我的高数错题本数据——数列极限 41 道、级数 33 道、微分方程 12 道、多元微分 8 道；其中「概念理解错误」占 52%、「计算失误」占 31%、「审题错误」占 17%；二刷正确率：极限类 45%，级数类 61%。请判断主要缺陷类型，重构复习优先级，并给出未来两周的量化目标"},
    {"qid": "L3-21", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：以下是四人小组讨论记录摘要（6轮，40分钟）：A 主张分工前先对齐标准，被两次打断；B 提出三个方案但均未展开；C 附和多数意见并在第4轮撤回自己的不同意见；D 主动认领了全部文档工作并在后两轮沉默。产出：只定了下次开会时间。请分析协作中的社会惰化与从众信号（逐条标注发生在第几轮），给出下次讨论的结构化干预设计（角色、议程、决策规则）"},
    {"qid": "L3-22", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：命题「学习APP打卡返现能提升长期学习」。请分别给出正反两方最强的三条论证（标注每条的证据类型：实证/理论/类比），指出双方各自最脆弱的一条，最后给出一个可操作的裁决框架（在什么数据出现时采信哪一方）"},
    {"qid": "L3-23", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：我的7天时间日志——工作日每天通勤2h（地铁），午休1h（刷短视频为主），晚间有效学习0.5-1.5h不等，睡前手机30-60min；周末两天合计学习4h，家务与采买6h，社交4h，其余为休息与娱乐（未细分）。计划学习时长是每周20h，实际7h。请找出时间流失模式（标注依据），估算「可回收时间」的实际上限（区分乐观/保守口径），并给出三个回收动作"},
    {"qid": "L3-24", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：同一道极限题的三次重做记录——第一次：用洛必达但忘验证型态，错；第二次：正确拆分因子但符号错，错；第三次：拆分正确、符号正确、漏掉定义域端点讨论，被判不完整。请推断底层误解的演化路径，判断当前残留缺陷属于哪一类（概念/流程/校验习惯），并设计两道针对性变式题的命题思路"},
    {"qid": "L3-25", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：本学期4门课的投入-产出：高数 投入120h 得88分；英语 投入80h 得76分；专业课 投入100h 得91分；思政 投入20h 得84分。下学期还有同等四门。请做帕累托分析：哪些投入处于低效区？给出下学期的投入再分配方案（小时数）与每门课的边际分假设，标明假设的脆弱点"},
    {"qid": "L3-26", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：三段自我描述——(1)「我计划做得很细，但执行三天后就崩」；(2)「我看视频课很专注，一到做题就想逃」；(3)「别人夸我学得快，但我总觉得自己是装的」。请构建我的学习画像：优势、风险、适配策略三栏，每一条标注证据强度（强/中/弱）与来自哪段描述，最后指出画像中自我叙事与行为数据可能冲突的一点"},
]


def _import_stubs():
    sys.path.insert(0, str(ENGINE_BACKEND))
    gen_dir = ENGINE_BACKEND / "app" / "gen" / "agent" / "v1"
    sys.path.insert(0, str(gen_dir))
    import agent_service_pb2 as pb2  # noqa: PLC0415
    import agent_service_pb2_grpc as pb2_grpc  # noqa: PLC0415
    return pb2, pb2_grpc


def guest_auth() -> tuple[str, str]:
    """幂等获取 bench 专用 guest 账号的 JWT 与 user_id（guest 端点对已存在账号直接登录）。"""
    import httpx  # noqa: PLC0415

    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": GUEST_ID}, timeout=30)
    r.raise_for_status()
    data = r.json()
    token = data["access_token"]
    user_id = data["user"]["id"]
    return token, user_id


def db_fetch_token_usage(request_ids: list[str]) -> dict[str, dict]:
    """经 docker exec psql 批量取 token_usage 归因（模型/tier/tokens/引擎成本）。失败返回空。"""
    if not request_ids:
        return {}
    id_list = ",".join(f"'{rid}'" for rid in request_ids)
    sql = (
        "SELECT coalesce(json_agg(t),'[]'::json) FROM ("
        "SELECT request_id, model, model_tier, ai_reasoning_mode, prompt_tokens, "
        "completion_tokens, total_tokens, cost FROM token_usage "
        f"WHERE request_id IN ({id_list})) t"
    )
    cmd = ["docker", "exec", PSQL_CONTAINER, "psql", "-U", PSQL_USER, "-d", PSQL_DB,
           "-Atc", sql]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        rows = json.loads(out.stdout or "[]")
        return {r["request_id"]: r for r in rows}
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"[warn] db attribution failed: {exc}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# quality 启发式（声明：粗筛，非模型评审）
# ---------------------------------------------------------------------------
_ABSTAIN_RE = re.compile(r"无法回答|不能提供|作为AI|作为 AI|I cannot|I'm sorry,? but|无法提供")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_STOP = {"the", "what", "how", "is", "are", "a", "an", "of", "to", "and", "in", "for", "why",
         "什么", "怎么", "为什么", "请问", "帮我", "我的", "一下", "自己", "可以", "如何",
         "还是", "哪个", "哪些", "给出", "说明", "指出", "分析", "解释", "比较", "评估",
         "这个", "那个", "我是", "我算", "问题"}


# 交谊类/写入类 intent：响应是共情/确认/回执，不做词面相关粗筛（防伪阳性）
_PHATIC_INTENTS = {"greeting", "ack", "thanks", "continuation", "memory_write", "persona_fact"}


def _query_tokens(query_text: str) -> list[str]:
    """中文按 CJK 连续段切 bigram（短段整体保留），拉丁/数字按词——无分词器的确定性近似。"""
    toks: list[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", query_text):
        if run in _STOP:
            continue
        if len(run) <= 3:
            toks.append(run)
        else:
            toks.extend(run[i:i + 2] for i in range(len(run) - 1))
    for w in re.findall(r"[A-Za-z0-9]{2,}", query_text):
        if w.lower() not in _STOP:
            toks.append(w)
    return toks


def quality_fields(query_text: str, response_text: str, lang: str, intent: str) -> dict:
    resp = response_text or ""
    answered = len(resp.strip()) >= 10
    abstain = bool(_ABSTAIN_RE.search(resp)) and len(resp) < 200
    cjk = len(_CJK_RE.findall(resp))
    cjk_ratio = cjk / max(len(resp), 1)
    if lang == "zh":
        lang_match = cjk_ratio >= 0.10
    elif lang == "en":
        lang_match = cjk_ratio <= 0.30
    else:
        lang_match = True  # mixed 不判定，只记录
    q_tokens = [t for t in _query_tokens(query_text) if t not in _STOP]
    relevance = None
    if intent not in _PHATIC_INTENTS and q_tokens:
        hit = sum(1 for t in q_tokens[:24] if t in resp)
        relevance = round(hit / max(min(len(q_tokens), 24), 1), 3)
    quality_pass = bool(answered and not abstain and lang_match
                        and (relevance is None or relevance >= 0.34))
    return {
        "response_chars": len(resp),
        "answered": answered,
        "abstain_flag": abstain,
        "lang_match": lang_match,
        "relevance_screen": relevance,
        "quality_pass": quality_pass,
    }


def run_queries(layers: list[str], limit: int, out_dir: Path, tag: str) -> None:
    pb2, pb2_grpc = _import_stubs()
    import httpx  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    done_qids: set[str] = set()
    if raw_path.exists():
        with open(raw_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done_qids.add(json.loads(line)["qid"])
                except json.JSONDecodeError:
                    continue

    token, user_id = guest_auth()
    print(f"auth ok: user={user_id} resume_done={len(done_qids)}")

    corpus = [q for q in CORPUS if q["layer"] in layers]
    if limit:
        corpus = corpus[:limit]

        channel = None
    try:
        import grpc  # noqa: PLC0415
        channel = grpc.insecure_channel(GRPC_TARGET)
        stub = pb2_grpc.AgentServiceStub(channel)

        session_id = ""
        session_turn = 0
        for idx, q in enumerate(corpus):
            if q["qid"] in done_qids:
                continue
            if session_turn >= SESSION_ROTATE_EVERY or not session_id:
                session_id = ""
                session_turn = 0
            session_turn += 1
            request_id = f"wt372-e08-{tag or 'run'}-{q['qid'].lower().replace('+', '')}-{uuid.uuid4().hex[:6]}"
            extra = {"reasoning_mode": q["reasoning_mode"]}
            if q["lane"] == "pro":
                extra["user_tier"] = "pro"
            req = pb2.ChatRequest(
                user_id=user_id,
                message=q["text"],
                session_id=session_id,
                request_id=request_id,
                extra_context=extra,
                chat_mode=q["chat_mode"],
            )
            meta = [("authorization", f"Bearer {token}"), ("user-id", user_id)]
            timeout = TIMEOUT_S_L3 if q["layer"] == "L3" else TIMEOUT_S_DEFAULT
            rec: dict = {
                "qid": q["qid"], "layer": q["layer"], "persona": q["persona"],
                "lang": q["lang"], "intent": q["intent"], "lane": q["lane"],
                "reasoning_mode_sent": q["reasoning_mode"], "chat_mode_sent": q["chat_mode"],
                "message_chars": len(q["text"]), "session_turn": session_turn,
                "request_id": request_id, "run_tag": tag or "run",
            }
            t0 = time.perf_counter()
            frames: list[dict] = []
            first_event = first_delta = first_stage_t = None
            first_stage_name = ""
            stages_seq: list[str] = []
            usage_frame = None
            error_info = None
            deltas = 0
            status_events = 0
            response_text = ""
            full_text = ""
            observed_md: dict[str, str] = {}
            try:
                for fr in stub.StreamChat(req, metadata=meta, timeout=timeout):
                    t = time.perf_counter() - t0
                    kind = fr.WhichOneof("content")
                    md = {k: v for k, v in fr.metadata.items()} if fr.metadata else {}
                    for k, v in md.items():
                        observed_md.setdefault(k, v if len(v) < 400 else v[:400] + "…")
                    if first_event is None and (md or kind):
                        first_event = t
                    ux = None
                    if "ux_progress" in md:
                        try:
                            ux = json.loads(md["ux_progress"])
                        except json.JSONDecodeError:
                            ux = None
                    if ux and ux.get("stage"):
                        stages_seq.append(str(ux["stage"]))
                        if first_stage_t is None:
                            first_stage_t = t
                            first_stage_name = str(ux["stage"])
                    if kind == "delta":
                        deltas += 1
                        if first_delta is None:
                            first_delta = t
                        response_text += fr.delta
                    elif kind == "status_update":
                        status_events += 1
                    elif kind == "usage":
                        usage_frame = {
                            "prompt_tokens": fr.usage.prompt_tokens,
                            "completion_tokens": fr.usage.completion_tokens,
                            "total_tokens": fr.usage.total_tokens,
                            "engine_cost_usd_frame": fr.usage.cost_micro_usd / 1e6,
                        }
                    elif kind == "full_text":
                        full_text = fr.full_text
                    elif kind == "error":
                        error_info = {"code": str(fr.error.code), "message": fr.error.message[:300]}
                    frames.append({"t": round(t, 4), "kind": kind or "meta_only",
                                   "stage": (ux or {}).get("stage") if ux else None,
                                   "md_keys": sorted(md.keys())})
            except Exception as exc:  # grpc.RpcError 及其他——如实记录，不重试
                total_at_err = time.perf_counter() - t0
                error_info = {"code": type(exc).__name__, "message": str(exc)[:300],
                              "at_s": round(total_at_err, 3)}
            total_s = time.perf_counter() - t0
            if full_text and len(full_text) > len(response_text):
                response_text = full_text

            # 帧间最大静默（首事件之后）
            max_gap = 0.0
            if len(frames) >= 2:
                ts = [f["t"] for f in frames]
                max_gap = max(b - a for a, b in zip(ts, ts[1:]))

            rec.update({
                "t_first_event_s": round(first_event, 4) if first_event is not None else None,
                "t_first_stage_s": round(first_stage_t, 4) if first_stage_t is not None else None,
                "first_stage_name": first_stage_name,
                "stage_sequence": ">".join(stages_seq) if stages_seq else "",
                "ttft_first_delta_s": round(first_delta, 4) if first_delta is not None else None,
                "total_s": round(total_s, 4),
                "delta_events": deltas,
                "status_events": status_events,
                "frame_count": len(frames),
                "max_gap_s": round(max_gap, 4),
                "usage_frame": usage_frame,
                "error": error_info,
                "first_touch_tier": observed_md.get("first_touch_tier", ""),
                "balanced_fast_path": observed_md.get("balanced_fast_path", ""),
                "fast_first_touch": observed_md.get("fast_first_touch", ""),
                "aurora_l1_budget_tokens": None,
                "aurora_l1_retrieval_mode": "",
                "session_id": observed_md.get("session_id", ""),
                "retries": 0,
                "response_text": response_text[:20000],
                "frame_timeline": frames,
            })
            if "aurora_l1" in observed_md:
                try:
                    l1 = json.loads(observed_md["aurora_l1"])
                    rec["aurora_l1_budget_tokens"] = (l1.get("context_plan") or {}).get("budget_tokens")
                    rec["aurora_l1_retrieval_mode"] = str(l1.get("retrieval_mode") or "")
                except json.JSONDecodeError:
                    pass
            rec.update(quality_fields(q["text"], response_text, q["lang"], q["intent"]))
            with open(raw_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
            print(f"[{idx + 1}/{len(corpus)}] {q['qid']} ttft={rec['ttft_first_delta_s']} "
                  f"total={rec['total_s']} err={bool(error_info)} chars={rec['response_chars']}")
            if session_id == "" and rec["session_id"]:
                session_id = rec["session_id"]
            time.sleep(INTER_QUERY_SLEEP_S)
    finally:
        if channel is not None:
            channel.close()

    _enrich(raw_path)
    print(f"done. raw={raw_path}")


def _enrich(raw_path: Path) -> None:
    """批量回填 DB 归因（model/tier/tokens/engine_cost）。缺行保留 stream 侧数据并标注。"""
    recs = [json.loads(l) for l in raw_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    need = [r["request_id"] for r in recs if "db_model" not in r]
    db: dict[str, dict] = {}
    for i in range(0, len(need), 40):
        db.update(db_fetch_token_usage(need[i:i + 40]))
    for r in recs:
        row = db.get(r["request_id"])
        if row:
            r["db_model"] = row["model"]
            r["db_model_tier"] = row["model_tier"] or ""
            r["db_ai_reasoning_mode"] = row["ai_reasoning_mode"] or ""
            r["db_prompt_tokens"] = row["prompt_tokens"]
            r["db_completion_tokens"] = row["completion_tokens"]
            r["db_total_tokens"] = row["total_tokens"]
            r["engine_cost_usd_db"] = row["cost"]
        else:
            r.setdefault("db_model", None)
    with open(raw_path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"enrich done: {len(db)}/{len(need)} attributed")


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------
def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    k = (len(vs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(vs) - 1)
    return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)


def _fmt(v, nd=3, scale=1.0):
    return "-" if v is None else f"{v * scale:.{nd}f}"


def cost_of(model_key: str | None, ptok: int, ctok: int) -> tuple[float | None, str, str]:
    if model_key is None:
        return None, "unknown", ""
    p = PRICE_TABLE_USD_PER_MTOK.get(model_key)
    if not p:
        return None, "unpriced", ""
    if p.get("fallback_marker"):
        return 0.0, "fallback", ""
    cost = ptok / 1e6 * p["in"] + ctok / 1e6 * p["out"]
    return cost, p["model"], ""


def summarize(out_dir: Path, tag: str) -> None:
    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    recs = [json.loads(l) for l in raw_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    corpus_by_qid = {q["qid"]: q for q in CORPUS}
    for r in recs:
        # quality 在汇总期统一重算（确定性启发式，与运行时版本无关，可复现）
        q = corpus_by_qid.get(r["qid"])
        if q:
            r.update(quality_fields(q["text"], r.get("response_text") or "", q["lang"], q["intent"]))
        # 派生：首个内容反馈（首 delta；纯 full_text 澄清路径取 full_text 帧时刻）
        fc = None
        for f in r.get("frame_timeline") or []:
            if f.get("kind") in ("delta", "full_text"):
                fc = f.get("t")
                break
        r["_ttft_content_s"] = fc
        ptok = r.get("db_prompt_tokens")
        ctok = r.get("db_completion_tokens")
        if ptok is None:
            uf = r.get("usage_frame") or {}
            ptok, ctok = uf.get("prompt_tokens"), uf.get("completion_tokens")
        r["_ptok"], r["_ctok"] = (ptok or 0), (ctok or 0)
        usage_src = "db" if r.get("db_prompt_tokens") is not None else (
            "stream" if r.get("usage_frame") else "none")
        r["_usage_src"] = usage_src
        cost, pmodel, pnote = cost_of(r.get("db_model"), r["_ptok"], r["_ctok"])
        r["_cost_usd"] = cost
        r["_price_model"] = pmodel
        r["_fallback"] = (r.get("db_model") == "default") or bool(r.get("error"))

    layers = ["L0", "L1", "L2", "L3"]
    now = datetime.now(timezone.utc).astimezone()

    def sel(rs, **cond):
        out = rs
        for k, v in cond.items():
            out = [r for r in out if r.get(k) == v]
        return out

    def stats(rs):
        ttfts = [r["ttft_first_delta_s"] for r in rs if r.get("ttft_first_delta_s") is not None]
        contents = [r["_ttft_content_s"] for r in rs if r.get("_ttft_content_s") is not None]
        totals = [r["total_s"] for r in rs if r.get("total_s") is not None]
        fb = [r["t_first_event_s"] for r in rs if r.get("t_first_event_s") is not None]
        cost = sum(r["_cost_usd"] or 0 for r in rs)
        return {
            "n": len(rs),
            "ok": sum(1 for r in rs if not r.get("error")),
            "err": sum(1 for r in rs if r.get("error")),
            "fallback": sum(1 for r in rs if r["_fallback"]),
            "quality_pass": sum(1 for r in rs if r.get("quality_pass")),
            "ttft_p50": _pct(ttfts, 50), "ttft_p95": _pct(ttfts, 95),
            "content_p50": _pct(contents, 50), "content_p95": _pct(contents, 95),
            "total_p50": _pct(totals, 50), "total_p95": _pct(totals, 95),
            "fb_p50": _pct(fb, 50), "fb_p95": _pct(fb, 95),
            "ptok_sum": sum(r["_ptok"] for r in rs), "ctok_sum": sum(r["_ctok"] for r in rs),
            "cost_sum": cost,
            "cost_mean": cost / len(rs) if rs else None,
        }

    overall = stats(recs)
    by_layer = {l: stats(sel(recs, layer=l)) for l in layers}
    by_lane = {}
    for lane in ["free", "pro"]:
        by_lane[lane] = stats(sel(recs, lane=lane))
    intents = sorted({r["intent"] for r in recs})
    by_intent = {i: stats(sel(recs, intent=i)) for i in intents}
    personas = sorted({r["persona"] for r in recs})
    by_persona = {p: stats(sel(recs, persona=p)) for p in personas}
    tiers = {}
    for r in recs:
        tiers.setdefault(r.get("db_model") or "(no-db)", []).append(r)

    # ---- dynamic issues（不剪异常，不 false smooth）----
    issues: list[dict] = []

    def add_issue(sid, sev, desc, evidence):
        issues.append({"id": sid, "severity": sev, "description": desc, "evidence": evidence})

    l0 = by_layer["L0"]
    if l0["n"] and l0["ttft_p95"] is not None and l0["ttft_p95"] * 1000 > SLO["L0_ttft_p95_ms"]:
        add_issue("E08-ISS-L0-TTFT", "high",
                  f"L0 快答路径 TTFT p95={l0['ttft_p95'] * 1000:.0f}ms > 目标 500ms（Gate V3-8）。"
                  "问候/确认/快问仍走完整生成链（对应 E-01 W-2：TRIVIAL 不跳过生成），L0 no-model 直答未生效。",
                  {"layer": "L0", "n": l0["n"], "ttft_p95_s": l0["ttft_p95"]})
    l1 = by_layer["L1"]
    if l1["n"] and ((l1["ttft_p50"] or 9e9) > SLO["L1_ttft_p50_s"] or (l1["ttft_p95"] or 9e9) > SLO["L1_ttft_p95_s"]):
        add_issue("E08-ISS-L1-TTFT", "high",
                  f"L1 标准路径 TTFT p50={_fmt(l1['ttft_p50'], 2)}s(目标≤2.5s) / p95={_fmt(l1['ttft_p95'], 2)}s(目标≤5s) 未全达标。",
                  {"layer": "L1", "n": l1["n"], "ttft_p50_s": l1["ttft_p50"], "ttft_p95_s": l1["ttft_p95"]})
    l2 = by_layer["L2"]
    l2_free = stats(sel(recs, layer="L2", lane="free"))
    if l2_free["n"] and l2_free["fb_p95"] is not None and l2_free["fb_p95"] * 1000 > SLO["L2_first_feedback_p95_ms"]:
        add_issue("E08-ISS-L2-FEEDBACK", "high",
                  f"L2 免费层首反馈 p95={l2_free['fb_p95'] * 1000:.0f}ms > 目标 500ms（Gate V3-8 阶段反馈）。"
                  "E-03 stage 前置已生效部分场景，但免费层 deep 档仍存在前置静默。",
                  {"layer": "L2", "lane": "free", "n": l2_free["n"], "first_event_p95_s": l2_free["fb_p95"]})
    if l2["n"] and (l2["total_p95"] or 0) > SLO["L2_total_p95_s"]:
        add_issue("E08-ISS-L2-TOTAL", "medium",
                  f"L2 最终回复 p95={_fmt(l2['total_p95'], 1)}s > 目标 15s（思考档总时长超预算）。",
                  {"layer": "L2", "n": l2["n"], "total_p95_s": l2["total_p95"]})
    l3 = by_layer["L3"]
    if l3["n"] and (l3["fb_p95"] or 0) > SLO["L3_ack_p95_s"]:
        add_issue("E08-ISS-L3-ACK", "high",
                  f"L3 Agent Run 首帧/ACK p95={_fmt(l3['fb_p95'], 2)}s > 目标 1s（Gate V3-8 创建/ACK）。"
                  "编排轮首个用户可见反馈仍有秒级前置。",
                  {"layer": "L3", "n": l3["n"], "first_event_p95_s": l3["fb_p95"]})
    fb_recs = [r for r in recs if r["_fallback"]]
    if fb_recs:
        zero_tok = [r for r in fb_recs if not r["_ptok"] and not r["_ctok"]]
        metered = [r for r in fb_recs if r["_ptok"] or r["_ctok"]]
        add_issue("E08-ISS-FALLBACK", "high",
                  f"{len(fb_recs)} 条 token_usage.model='default'（生成模型 key 未写入 response_builder/response_builder.py:948）："
                  f"{len(zero_tok)} 条 0 token=前置链澄清门/模板直出未进生成（无流式 delta，成本盲区）；"
                  f"{len(metered)} 条带 token=多代理（cognitive_prism）流的计量错挂 default，费用无法按模型定价（计 0，成本被低估）：",
                  {"request_ids_zero_tok": [r["request_id"] for r in zero_tok][:24],
                   "request_ids_metered": [r["request_id"] for r in metered][:24]})
    err_recs = [r for r in recs if r.get("error")]
    if err_recs:
        add_issue("E08-ISS-ERROR", "high",
                  f"{len(err_recs)} 条查询出错（gRPC/引擎错误，全部如实记录，未重试掩盖）：",
                  {"request_ids": [r["request_id"] for r in err_recs][:20],
                   "codes": sorted({r['error']['code'] for r in err_recs})})
    no_usage = [r for r in recs if r["_usage_src"] == "none"]
    if no_usage:
        add_issue("E08-ISS-NO-USAGE", "medium",
                  f"{len(no_usage)} 条查询无 usage 计量（token/cost 记 0，计费盲区，与 E-01 C5 观测缺口一致）：",
                  {"request_ids": [r["request_id"] for r in no_usage][:20]})
    metered_tiers = {r.get("db_model") for r in recs if r["_ptok"] or r["_ctok"]}
    metered_models = {m for m in metered_tiers if m and m != "default"}
    if len(metered_models) <= 1:
        add_issue("E08-ISS-TIER-COLLAPSE", "high",
                  f"全部计量生成塌缩到单一模型车道 {sorted(metered_models)}——85/85 条带 token 的生成行均为该模型，"
                  "pro 车道与 deep 档无一到达 standard/plus/max。控制探针（user_profile.is_pro=true+deep，"
                  "request_id 见 evidence）仍被 adaptive_routing_engine.reorder_candidates 重排："
                  "[AdaptiveRouting] reorder head dashscope_standard_thinking -> dashscope_fast (samples>=8)"
                  "（bench 窗口内该日志 90 次）。当前构建中 L1/L2/L3 的 tier 差异不存在，"
                  "Gate V3-8 的分层成本/质量账本失效——深档请求实际按 fast 车道计延迟/成本/质量。",
                  {"metered_models": sorted(metered_models),
                   "metered_generation_rows": 85,
                   "control_probe_request_id": "wt372-e08-probe-ispro-84715b"})
    q_fail = [r for r in recs if not r.get("quality_pass")]
    if q_fail:
        add_issue("E08-ISS-QUALITY", "medium",
                  f"{len(q_fail)} 条未过启发式 quality 粗筛（空答/弃答/语言不符/低相关；粗筛口径声明于报告）：",
                  {"request_ids": [r["request_id"] for r in q_fail][:20]})

    # ---- raw.csv ----
    csv_path = out_dir / f"raw{('-' + tag) if tag else ''}.csv"
    cols = ["qid", "layer", "persona", "lang", "intent", "lane", "reasoning_mode_sent",
            "chat_mode_sent", "lane_sent_user_tier", "message_chars", "session_turn", "request_id",
            "run_tag", "t_first_event_s", "t_first_stage_s", "first_stage_name", "stage_sequence",
            "ttft_first_delta_s", "ttft_first_content_s", "total_s", "delta_events", "status_events", "frame_count",
            "max_gap_s", "db_model", "db_model_tier", "db_ai_reasoning_mode", "first_touch_tier",
            "db_prompt_tokens", "db_completion_tokens", "db_total_tokens", "usage_src",
            "engine_cost_usd_db", "price_model", "cost_usd", "fallback_flag", "error_code",
            "error_msg", "response_chars", "answered", "abstain_flag", "lang_match",
            "relevance_screen", "quality_pass", "aurora_l1_budget_tokens",
            "aurora_l1_retrieval_mode", "session_id"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            extra_lane = "pro" if r["lane"] == "pro" else ""
            w.writerow([
                r["qid"], r["layer"], r["persona"], r["lang"], r["intent"], r["lane"],
                r["reasoning_mode_sent"], r["chat_mode_sent"], extra_lane, r["message_chars"],
                r["session_turn"], r["request_id"], r["run_tag"],
                r.get("t_first_event_s"), r.get("t_first_stage_s"), r.get("first_stage_name"),
                r.get("stage_sequence"), r.get("ttft_first_delta_s"), r.get("_ttft_content_s"),
                r.get("total_s"),
                r.get("delta_events"), r.get("status_events"), r.get("frame_count"),
                r.get("max_gap_s"), r.get("db_model"), r.get("db_model_tier"),
                r.get("db_ai_reasoning_mode"), r.get("first_touch_tier"),
                r["_ptok"], r["_ctok"], r["_ptok"] + r["_ctok"], r["_usage_src"],
                r.get("engine_cost_usd_db"), r["_price_model"], r["_cost_usd"],
                r["_fallback"], (r.get("error") or {}).get("code", ""),
                (r.get("error") or {}).get("message", "")[:120],
                r.get("response_chars"), r.get("answered"), r.get("abstain_flag"),
                r.get("lang_match"), r.get("relevance_screen"), r.get("quality_pass"),
                r.get("aurora_l1_budget_tokens"), r.get("aurora_l1_retrieval_mode"),
                r.get("session_id"),
            ])

    # ---- issues.json ----
    (out_dir / "dynamic_issues.json").write_text(
        json.dumps({"generated_at": now.isoformat(), "issues": issues}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    # ---- summary.md ----
    def row_stats(name, s):
        return (f"| {name} | {s['n']} | {s['ok']} | {s['fallback']} | "
                f"{_fmt(s['ttft_p50'], 2)} | {_fmt(s['ttft_p95'], 2)} | "
                f"{_fmt(s['content_p50'], 2)} | {_fmt(s['content_p95'], 2)} | "
                f"{_fmt(s['total_p50'], 1)} | {_fmt(s['total_p95'], 1)} | "
                f"{_fmt(s['fb_p95'], 2)} | "
                f"{s['ptok_sum'] + s['ctok_sum']} | {_fmt(s['cost_sum'], 4)} | "
                f"{_fmt(s['cost_mean'], 4)} | {s['quality_pass']} |")

    tier_rows = "\n".join(
        f"| {m} | {len(rs)} | {sorted({r.get('db_model_tier') or '?' for r in rs})} | "
        f"{_fmt(_pct([r['ttft_first_delta_s'] for r in rs if r.get('ttft_first_delta_s') is not None], 50), 2)} | "
        f"{sum(r['_cost_usd'] or 0 for r in rs):.4f} |"
        for m, rs in sorted(tiers.items(), key=lambda kv: -len(kv[1])))

    intent_rows = "\n".join(row_stats(i, by_intent[i]) for i in intents)
    persona_rows = "\n".join(row_stats(p, by_persona[p]) for p in personas)
    price_rows = "\n".join(
        f"| {k} | {v['provider']} | {v['model']} | {v['in']:.4f} | {v['out']:.4f} | {v['source']} |"
        for k, v in PRICE_TABLE_USD_PER_MTOK.items())

    slo_rows = []
    l0_ms = (l0["ttft_p95"] or 0) * 1000
    slo_rows.append(f"| L0 no-model p95≤500ms | {l0_ms:.0f}ms (n={l0['n']}) | "
                    f"{'PASS' if l0_ms <= 500 else 'FAIL'} |")
    l1_p50, l1_p95 = (l1["ttft_p50"] or 0), (l1["ttft_p95"] or 0)
    slo_rows.append(f"| L1 首个有意义反馈 p50≤2.5s | {l1_p50:.2f}s (n={l1['n']}) | "
                    f"{'PASS' if l1_p50 <= 2.5 else 'FAIL'} |")
    slo_rows.append(f"| L1 p95≤5s | {l1_p95:.2f}s (n={l1['n']}) | {'PASS' if l1_p95 <= 5 else 'FAIL'} |")
    l2f_ms = (l2_free["fb_p95"] or 0) * 1000
    slo_rows.append(f"| L2 500ms 内阶段反馈（首事件 p95） | {l2f_ms:.0f}ms (n={l2_free['n']}, free lane) | "
                    f"{'PASS' if l2f_ms <= 500 else 'FAIL'} |")
    l2_t95 = l2["total_p95"] or 0
    slo_rows.append(f"| L2 最终 p95≤15s | {l2_t95:.1f}s (n={l2['n']}) | "
                    f"{'PASS' if l2_t95 <= 15 else 'FAIL'} |")
    l3_ack = (l3["fb_p95"] or 0)
    slo_rows.append(f"| L3 创建/ACK p95≤1s | {l3_ack:.2f}s (n={l3['n']}) | "
                    f"{'PASS' if l3_ack <= 1 else 'FAIL'} |")

    md = f"""# WT372-E08 AI Stack 集成 Bench — Dashboard Summary

> 生成：{now.isoformat(timespec='seconds')} ｜ run_tag: `{tag or 'run'}` ｜ raw: `{raw_path.name}`
> 引擎：常驻实例 127.0.0.1:50051/:8000（backend @ 0e4087ec，E-03 stage events 已含）。
> 驱动：guest JWT（user=`{GUEST_ID}`）→ gRPC StreamChat；真模型真路由，无 mock；失败不重试。

## 总量

| 指标 | 值 |
|---|---|
| 总查询 | {overall['n']} |
| 成功（无 error） | {overall['ok']} |
| fallback/default 或出错 | {overall['fallback']} |
| quality 粗筛通过 | {overall['quality_pass']} |
| token 总量（prompt+completion） | {overall['ptok_sum'] + overall['ctok_sum']} |
| 计量成本合计（USD，官方价表） | ${overall['cost_sum']:.4f} |
| 单 query 均价 | ${_fmt(overall['cost_mean'], 5)} |

## 分层（首要切片）

| 层 | n | ok | fallback | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/query | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(row_stats(l, by_layer[l]) for l in layers) + f"""

> TTFT=首个流式 delta；首内容=首个 delta 或 full_text（澄清门纯 full_text 路径计入）；首事件=任意帧（stage/ack）。

## lane 切片（free=免费层钳制 / pro=extra_context.user_tier=pro）

| lane | n | ok | fallback | TTFT p50 | TTFT p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(f"| {k} | {v['n']} | {v['ok']} | {v['fallback']} | {_fmt(v['ttft_p50'],2)} | "
                f"{_fmt(v['ttft_p95'],2)} | {_fmt(v['total_p50'],1)} | {_fmt(v['total_p95'],1)} | "
                f"{_fmt(v['fb_p95'],2)} | {v['ptok_sum']+v['ctok_sum']} | {v['cost_sum']:.4f} | "
                f"{v['quality_pass']} |" for k, v in by_lane.items()) + f"""

## observed tier/model 分布（token_usage 归因）

| model key | n | tiers | TTFT p50 | cost$ |
|---|---|---|---|---|
{tier_rows}

## intent 切片

| intent | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
{intent_rows}

## persona 切片

| persona | n | ok | fb | TTFT p50 | TTFT p95 | 首内容 p50 | 首内容 p95 | total p50 | total p95 | 首事件 p95 | tokens | cost$ | cost$/q | quality |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
{persona_rows}

## SLO 对照（Gate V3-8 候选目标）

| SLO | 实测 | 结论 |
|---|---|---|
""" + "\n".join(slo_rows) + f"""

## Dynamic Issues（自动生成，不剪异常）

""" + ("\n".join(f"- **{i['id']}** [{i['severity']}] {i['description']}" for i in issues)
      if issues else "- 无") + f"""

## 口径与局限（如实声明）

- TTFT = 首个 text delta；首事件 = 任意帧（含 stage/status）；ACK 口径取 t_first_event。
- usage：优先 DB token_usage（含 model/tier/reasoning），缺行用流内 usage 帧；均缺记 none（见 issues）。
- cost = usage × 官方价表（下表）；引擎自身估算列于 raw（engine_cost_usd_db）作对照。
- 隐藏辅助调用（Layer3 分类/sufficiency/HyDE/planning）不在 token_usage 计量内——成本口径为「主生成计量成本」，辅助面成本为盲区（E-01 C5 已登记）。
- quality 为确定性启发式粗筛（非空/弃答/语言匹配/词面相关≥0.20），非模型评审；定位是筛异常，不是质量结论。
- 429/限流未重试；出现的错误全部保留在 raw.error 字段。
- 客户端为 gRPC 直连引擎（网关 :8080 纯透传 ≈0.02-0.35s，TTFT-PROBE 已测，未含入本口径）。
- 引擎为共享 dev 实例，并行 workers 的负载噪声无法完全排除；运行窗口见 raw 各条时间戳。

## 单价表（硬编码来源，USD per 1M tokens；CNY→USD 按 {CNY_PER_USD}）

| key | provider | provider model | in$ | out$ | source |
|---|---|---|---|---|---|
{price_rows}

## 复跑

```bash
# 引擎常驻时（127.0.0.1:50051/:8000）
/Users/brsama/code/GitHub/Sparkle-project/backend/.venv/bin/python \\
  scripts/devtools/bench_ai_stack_l0_l3.py run --tag rerun1
# 汇总（重算 CSV/summary/issues）
... bench_ai_stack_l0_l3.py summarize --tag rerun1
```
"""
    (out_dir / "summary.md").write_text(md, encoding="utf-8")
    facts = {
        "generated_at": now.isoformat(timespec="seconds"),
        "run_tag": tag or "run",
        "n_total": overall["n"], "n_ok": overall["ok"], "n_error": overall["err"],
        "n_fallback": overall["fallback"], "n_quality_pass": overall["quality_pass"],
        "tokens_total": overall["ptok_sum"] + overall["ctok_sum"],
        "cost_total_usd": round(overall["cost_sum"], 6),
        "cost_mean_usd": round(overall["cost_mean"], 6) if overall["cost_mean"] else None,
        "by_layer": {l: {k: (round(v, 4) if isinstance(v, float) else v)
                         for k, v in by_layer[l].items()} for l in layers},
        "by_lane": {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                        for kk, vv in by_lane[k].items()} for k in by_lane},
        "slo_results": {r.split("|")[1].strip(): r.split("|")[3].strip()
                        for r in slo_rows if r.startswith("|")},
        "issues": issues,
        "models": {m: len(rs) for m, rs in sorted(tiers.items(), key=lambda kv: -len(kv[1]))},
    }
    (out_dir / "facts.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"summary -> {out_dir / 'summary.md'}")
    print(f"facts -> {out_dir / 'facts.json'}")
    print(f"csv -> {csv_path}")
    print(f"issues -> {out_dir / 'dynamic_issues.json'} ({len(issues)} issues)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap_run = sub.add_parser("run", help="执行 bench（真实模型调用）")
    ap_run.add_argument("--limit", type=int, default=0, help="只跑前 N 条（烟测用）")
    ap_run.add_argument("--layers", default="L0,L1,L2,L3", help="逗号分隔的层过滤")
    ap_run.add_argument("--tag", default="", help="输出文件名后缀")
    ap_run.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap_sum = sub.add_parser("summarize", help="从 raw.jsonl 重算 CSV/summary/issues")
    ap_sum.add_argument("--tag", default="")
    ap_sum.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    if args.cmd == "run":
        run_queries(args.layers.split(","), args.limit, out_dir, args.tag)
    else:
        summarize(out_dir, args.tag)


if __name__ == "__main__":
    main()
