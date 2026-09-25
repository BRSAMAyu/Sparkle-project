#!/usr/bin/env python3
"""Q-06 分层性能/成本终验 bench — L0-L3 × free/pro，每层 100 真样本（wt406）.

对 wt406 worktree 引擎（gRPC :50061）以真实账号驱动学习成长域语料：
- 50 条/层 distinct 语料（E-08 26 条原样复用保可比 + 24 条新增），×2 reps = 100 样本/层；
- pro 车道走网关忠实形态（ChatRequest.user_profile.is_pro=True，不带 extra_context.user_tier），
  free 车道不声明 user_profile；wt392 服务端权威升档门由此可被真实检验；
- 逐条记录 TTFT/首内容/首事件/total/帧时间线/max_gap（抖动原样落盘，不剪异常不重试）；
- token/cost 经 redis db1 billing worker 落 token_usage 后批量归因（与 E-08 同口径）；
- p50/p95 仅在 n>=100 时报告（卡面验收），n<100 的层如实标 n 并不报 p95。

用法:
  python3 q06_perf_bench.py run [--layers L0,L1,L2,L3] [--reps 2] [--out-dir DIR]
  python3 q06_perf_bench.py summarize [--out-dir DIR]

依赖：主仓 backend/.venv；引擎 + billing worker（redis db1）在位；sparkle_db 容器。
默认输出：<worktree>/v3-output/WT406-Q06-PERF/
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "v3-output" / "WT406-Q06-PERF"

WORKTREE_BACKEND = Path("/Users/brsama/code/GitHub/Sparkle-sysrev/wt406-q06-perf/backend")
GRPC_TARGET = "127.0.0.1:50061"
HTTP_BASE = "http://127.0.0.1:8000/api/v1"
GUEST_FREE = "wt406_q06_bench_free"
GUEST_PRO = "wt406_q06_bench_pro"
PSQL = ["docker", "exec", "sparkle_db", "psql", "-U", "postgres", "-d", "sparkle", "-Atc"]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench_ai_stack_l0_l3 import (  # noqa: E402
    CORPUS as E08_CORPUS,
    PRICE_TABLE_USD_PER_MTOK,
    quality_fields,
)

SESSION_ROTATE_EVERY = 3
TIMEOUT_S_DEFAULT = 150.0
TIMEOUT_S_L3 = 240.0
INTER_QUERY_SLEEP_S = 0.8
REPS_DEFAULT = 2
TARGET_N_PER_LAYER = 100

# ---------------------------------------------------------------------------
# 新增语料：每层 24 条（与 E-08 26 条合流为 50 条/层 distinct）。
# 设计约束：学习成长域真实多样，intent/persona/lang 与 E-08 同谱系，主题换域
# （理化生/史地/编程/财经/天文/艺术），不复读 E-08 句式。
# ---------------------------------------------------------------------------
EXTRA_CORPUS: list[dict] = [
    # ============ L0 快答 新增 24 ============
    {"qid": "L0-27", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "下午好呀"},
    {"qid": "L0-28", "layer": "L0", "persona": "professional", "lang": "en", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "hey there"},
    {"qid": "L0-29", "layer": "L0", "persona": "researcher", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "懂了懂了"},
    {"qid": "L0-30", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "thanks", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "多谢指点"},
    {"qid": "L0-31", "layer": "L0", "persona": "exam_candidate", "lang": "en", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "got it"},
    {"qid": "L0-32", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "continuation", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "然后呢"},
    {"qid": "L0-33", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "帮我记住我养的猫叫汤圆"},
    {"qid": "L0-34", "layer": "L0", "persona": "professional", "lang": "en", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "Remember that I prefer studying in the early morning"},
    {"qid": "L0-35", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "水的沸点是多少？"},
    {"qid": "L0-36", "layer": "L0", "persona": "college_student", "lang": "en", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "How many continents are there?"},
    {"qid": "L0-37", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "光速大约是多少？"},
    {"qid": "L0-38", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "又见面啦"},
    {"qid": "L0-39", "layer": "L0", "persona": "researcher", "lang": "en", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "good evening"},
    {"qid": "L0-40", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "行，就这么定了"},
    {"qid": "L0-41", "layer": "L0", "persona": "professional", "lang": "zh", "intent": "persona_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我是做产品经理的"},
    {"qid": "L0-42", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "persona_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "我在准备高考复读"},
    {"qid": "L0-43", "layer": "L0", "persona": "self_learner", "lang": "en", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "What is 12 squared?"},
    {"qid": "L0-44", "layer": "L0", "persona": "exam_candidate", "lang": "zh", "intent": "quick_fact", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "一年有多少个星期？"},
    {"qid": "L0-45", "layer": "L0", "persona": "college_student", "lang": "zh", "intent": "thanks", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "好嘞谢谢啦"},
    {"qid": "L0-46", "layer": "L0", "persona": "researcher", "lang": "zh", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "明白了，继续"},
    {"qid": "L0-47", "layer": "L0", "persona": "professional", "lang": "mixed", "intent": "continuation", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "next one please"},
    {"qid": "L0-48", "layer": "L0", "persona": "beginner", "lang": "zh", "intent": "memory_write", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "记一下：我周二周四有课"},
    {"qid": "L0-49", "layer": "L0", "persona": "self_learner", "lang": "zh", "intent": "greeting", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "hi，我回来了"},
    {"qid": "L0-50", "layer": "L0", "persona": "exam_candidate", "lang": "en", "intent": "ack", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "sure thing"},

    # ============ L1 标准 新增 24 ============
    {"qid": "L1-27", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是光合作用？"},
    {"qid": "L1-28", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "用一句话解释供需关系"},
    {"qid": "L1-29", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "勾股定理是什么？"},
    {"qid": "L1-30", "layer": "L1", "persona": "self_learner", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "What is the CSS box model?"},
    {"qid": "L1-31", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "牛顿第三定律说的是什么？"},
    {"qid": "L1-32", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "怎么练习盲打？"},
    {"qid": "L1-33", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是复利效应？"},
    {"qid": "L1-34", "layer": "L1", "persona": "researcher", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "Explain standard deviation in one sentence."},
    {"qid": "L1-35", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "如何给文章列大纲？"},
    {"qid": "L1-36", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是化学平衡？"},
    {"qid": "L1-37", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "开会时怎么做笔记效率高？"},
    {"qid": "L1-38", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是经纬度？"},
    {"qid": "L1-39", "layer": "L1", "persona": "college_student", "lang": "en", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "How do I memorize music scales faster?"},
    {"qid": "L1-40", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是通货膨胀？"},
    {"qid": "L1-41", "layer": "L1", "persona": "researcher", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是样本量？"},
    {"qid": "L1-42", "layer": "L1", "persona": "exam_candidate", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "怎么快速记历史年代？"},
    {"qid": "L1-43", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是万有引力？"},
    {"qid": "L1-44", "layer": "L1", "persona": "professional", "lang": "en", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "What is opportunity cost?"},
    {"qid": "L1-45", "layer": "L1", "persona": "college_student", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "背古文有什么技巧？"},
    {"qid": "L1-46", "layer": "L1", "persona": "self_learner", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是机器学习中的过拟合？"},
    {"qid": "L1-47", "layer": "L1", "persona": "researcher", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是对照组实验？"},
    {"qid": "L1-48", "layer": "L1", "persona": "exam_candidate", "lang": "en", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "How to read a scientific paper efficiently?"},
    {"qid": "L1-49", "layer": "L1", "persona": "beginner", "lang": "zh", "intent": "howto", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "学吉他每天该练什么？"},
    {"qid": "L1-50", "layer": "L1", "persona": "professional", "lang": "zh", "intent": "concept_def", "lane": "free", "reasoning_mode": "fast", "chat_mode": "standard", "text": "什么是边际效用？"},

    # ============ L2 深推理 新增 24（free/pro 各12）============
    {"qid": "L2-27", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "comparison", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "对比经典力学与相对论在解释水星进动上的差异，说明各自适用边界"},
    {"qid": "L2-28", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "diagnose", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我学编程总在教程能懂、自己写就卡壳，从知识分层和迁移角度做归因诊断，给出验证方法"},
    {"qid": "L2-29", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "theory_apply", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用信号检测理论解释为什么考试时「感觉见过」的选项反而容易选错"},
    {"qid": "L2-30", "layer": "L2", "persona": "professional", "lang": "mixed", "intent": "code_review", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "review this SQL: SELECT * FROM orders WHERE user_id IN (SELECT id FROM users WHERE vip=1) — 列出性能与正确性风险并排序"},
    {"qid": "L2-31", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "error_diagnosis", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "解方程 2^x = 3x 我得到 x=1 和 x=3，验证时 x=1 不成立，找出我求解过程的漏洞"},
    {"qid": "L2-32", "layer": "L2", "persona": "beginner", "lang": "zh", "intent": "attribution", "lane": "free", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我制定的日计划从来完不成，从计划粒度、评估偏差和动机三个角度归因，指出最可能的根因"},
    {"qid": "L2-33", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "math_derive", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "推导为什么算术平均数对离群值敏感而中位数不敏感，给出一个数值例子和适用建议"},
    {"qid": "L2-34", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "comparison", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "比较有氧与无氧供能系统在力量训练和耐力训练中的角色差异，并指出常见科普误读"},
    {"qid": "L2-35", "layer": "L2", "persona": "professional", "lang": "zh", "intent": "plan_eval", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "两个背单词方案：A 每天300新词快速过；B 每天50词+复习队列。从编码深度和提取练习角度评估，给出可执行结论"},
    {"qid": "L2-36", "layer": "L2", "persona": "self_learner", "lang": "en", "intent": "logic_check", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "Critique this argument: \"Top students take notes by hand, so handwriting causes good grades.\" Identify the causal fallacy and design a test."},
    {"qid": "L2-37", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "diagnose", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我物理大题总是列对方程算错数，如何判别是计算熟练度、草稿习惯还是检验习惯问题？给出判别实验"},
    {"qid": "L2-38", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "experiment_design", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "「听古典乐提升专注」的说法争议很大，设计一个能区分因果与选择的实验，列出主要混淆变量"},
    {"qid": "L2-39", "layer": "L2", "persona": "beginner", "lang": "zh", "intent": "goal_eval", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "评估并改写这个目标：「今年要多读书」"},
    {"qid": "L2-40", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用双重加工理论解释为什么刷短视频后难以进入学习状态，指出两个可操作的干预点"},
    {"qid": "L2-41", "layer": "L2", "persona": "professional", "lang": "mixed", "intent": "code_review", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "一个爬虫脚本在数据量到10万条后内存暴涨，给出诊断步骤树和三个最可能原因的验证方法"},
    {"qid": "L2-42", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "tradeoff", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "在职学数据分析：SQL/统计/可视化三块只有每周6小时，给出优先级论证和止损条件"},
    {"qid": "L2-43", "layer": "L2", "persona": "exam_candidate", "lang": "zh", "intent": "system_design", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我的错题本按科目分册但从不重做，从习惯设计角度重构这套系统，给出最小改动方案"},
    {"qid": "L2-44", "layer": "L2", "persona": "researcher", "lang": "en", "intent": "writing_feedback", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "My thesis claim: \"Because engagement rose after redesign, the redesign caused learning gains.\" List three validity threats and rank them."},
    {"qid": "L2-45", "layer": "L2", "persona": "beginner", "lang": "zh", "intent": "comparison", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "对比「先学后练」与「先练后学」（production vs comprehension first）在语言学习中的证据"},
    {"qid": "L2-46", "layer": "L2", "persona": "college_student", "lang": "zh", "intent": "attribution", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "小组作业总是我一个人做，从任务分配、激励结构和个人边界三个角度归因并给出谈话策略"},
    {"qid": "L2-47", "layer": "L2", "persona": "professional", "lang": "zh", "intent": "theory_apply", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "用「必要难度」理论评估：把笔记做得极漂亮到底是帮助还是妨碍学习？给出边界条件"},
    {"qid": "L2-48", "layer": "L2", "persona": "self_learner", "lang": "zh", "intent": "diagnose", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "我练琴三个月会弹十首曲子但看谱仍困难，诊断是识谱能力缺失还是依赖记忆，给出验证路径"},
    {"qid": "L2-49", "layer": "L2", "persona": "exam_candidate", "lang": "en", "intent": "plan_eval", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "Plan A: 6h/day for 30 days cramming. Plan B: 2h/day for 90 days. Evaluate with spacing and fatigue research, give a decision rule."},
    {"qid": "L2-50", "layer": "L2", "persona": "researcher", "lang": "zh", "intent": "math_derive", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard", "text": "推导贝叶斯更新在「连续猜题自评」中的过信问题，说明为什么人类自评概率常极端化"},

    # ============ L3 编排·长上下文 新增 24（plan 9 / long_qa 8 / deep_analysis 7）============
    {"qid": "L3-27", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我要自学数据结构与算法冲击大厂后端岗，每天3小时，基础是会Python语法，帮我排4个月计划，标出每个阶段的检验项目"},
    {"qid": "L3-28", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "30岁转行做UX设计师，零基础，每天可投入2小时周末更多，给我9个月的转行路线图，含作品集里程碑和每个阶段的放弃判据"},
    {"qid": "L3-29", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "高考倒计时200天，我总分480目标560，弱科是英语和化学，帮我做分阶段的提分计划，每阶段说明为什么先攻这两科"},
    {"qid": "L3-30", "layer": "L3", "persona": "self_learner", "lang": "en", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "I want to learn Japanese to N3 in 8 months, 1h per day. I already know hiragana/katakana. Build a monthly plan with checkpoints and a fallback for busy weeks."},
    {"qid": "L3-31", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我需要三个月内完成硕士论文的开题到预答辩，同时每周有20小时实验任务，帮我倒排时间线，标注每步的依赖和风险缓冲"},
    {"qid": "L3-32", "layer": "L3", "persona": "beginner", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我想两个月内学会做20道家常菜，每周能下厨3次，帮我设计练习菜单（按难度递进）和每道的过关标准"},
    {"qid": "L3-33", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "备战9月的CPA会计+税法两科，每天4小时，零基础，帮我排90天计划，说明两科交替还是串行以及理由"},
    {"qid": "L3-34", "layer": "L3", "persona": "professional", "lang": "mixed", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "I have 10 weeks to prepare a tech talk (45min) plus a live demo. I can spend 5h/week. Plan the prep with rehearsal milestones and a cut-list if time runs short."},
    {"qid": "L3-35", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "planning", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "study_plan", "text": "我想半年内把摄影从全自动按快门提升到能接约拍的水平，每周实际可练习约6小时，给出分月能力目标和每周练习主题"},
    {"qid": "L3-36", "layer": "L3", "persona": "beginner", "lang": "zh", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "【学习材料】神经元工作原理：神经元通过树突接收信号，当膜电位去极化超过阈值（约-55mV）时在轴突起始段产生动作电位，遵循全或无法则；动作电位沿轴突传导至突触末梢，触发神经递质释放。有髓鞘纤维通过跳跃式传导大幅提高速度（可达120m/s），无髓鞘纤维仅约1m/s。突触可塑性：反复激活可增强突触传递效率（长时程增强LTP），被认为是学习与记忆的细胞基础。不应期：动作电位后存在绝对不应期与相对不应期，限制发放频率。【问题】根据材料解释：(1)为什么多发性硬化（髓鞘损伤）会同时影响速度与控制的精确性；(2)LTP为「重复学习」提供的机制学解释是什么"},
    {"qid": "L3-37", "layer": "L3", "persona": "professional", "lang": "en", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "[Study material] Spaced repetition scheduling in practice: Equal-interval review (e.g., every 3 days) is simple but wastes time on well-known items and starves weak ones. Expanding schedules (1d, 3d, 7d, 16d...) approximate the forgetting curve per item. Modern algorithms add per-item difficulty (ease factor) and inter-item interference modeling. Retrieval must be effortful but successful — failures too early harm motivation and encoding. Sleep consolidates encoding; reviews right before sleep show better retention. Load management: cap new items per day so that due reviews stay under ~30 minutes. [Question] Extract the design constraints a scheduling algorithm must satisfy, then point out which constraint conflicts with a hard daily 15-minute budget and propose a resolution"},
    {"qid": "L3-38", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "【学习材料】随机对照试验（RCT）要点：随机分组使已知与未知混杂因素在组间均衡；盲法减少安慰剂效应与观察者偏差；预注册防止结果选择性报告；意向性分析（ITT）保留随机化的保护。样本量由效应量、显著性水平和功效共同决定。内部效度威胁：流失（attrition）、交叉（crossover）、实施差异。外部效度：样本代表性、生态效度。【问题】一位教育研究者想在两个班级比较「检索练习 vs 重复阅读」对考试成绩的影响，但无法随机分配个体。给出一个尽量保留因果推断强度的设计，说明每个选择抵消了哪个内部效度威胁"},
    {"qid": "L3-39", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "long_context_qa", "lane": "free", "reasoning_mode": "balanced", "chat_mode": "standard",
     "text": "【学习材料】工程造价基本公式：总造价=直接费+间接费+利润+税金；直接费=人工费+材料费+机械费；措施项目费按分部分项工程费的费率计取。清单计价下，综合单价=人工+材料+机械+管理费+利润，风险幅度外的材料价差可调。规费与税金以分部分项+措施+其他项目费为基数。【问题】根据材料列出一个二线城市住宅项目的造价构成框架，指出材料涨价15%时哪部分最先失真、为什么，并说明清单计价与定额计价在风险分担上的差异"},
    {"qid": "L3-40", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【学习材料】电路基本定律：基尔霍夫电流定律（KCL）节点电流代数和为零；电压定律（KVL）回路电压代数和为零。戴维南定理：任何线性含源二端网络可等效为电压源串电阻。最大功率传输：负载电阻等于源内阻时获得最大功率，效率仅50%。RC电路时间常数τ=RC，经τ后电压达63.2%。【问题】用材料解释：(1)为什么音频功放设计不追求最大功率传输；(2)示波器探头1x/10x档位对RC时间常数测量的影响机制"},
    {"qid": "L3-41", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【学习周报摘录】第9周：计划25h，实际19h。构成：算法 8h（刷题20道，正确率55%）、系统设计 4h（只看视频未画图）、八股 5h、投递 2h（11家）。中断：周四加班、周日家庭事务。自评：周三 3/5，周日 2/5。遗留：上周计划的复盘未做。一句话：「刷题越刷越虚」。【问题】从周报找出四个异常信号并给出判断依据，针对每个信号设计一个下周就能做的对治实验，并指出哪个信号可能是伪信号"},
    {"qid": "L3-42", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "【综述摘录】测试增强学习（test-enhanced learning）元分析（Adesope等2017，272项）：检索练习相对重复阅读的效应g=0.50，且在延迟测试中更强（g=0.62 vs 即时0.37）；反馈的存在使效应翻倍；短答题优于选择题主效应有限。边界条件：材料复杂度高时初始检索失败可能有害（预测试效应在低先备知识者中减弱）；个体差异：工作记忆容量调节初始检索的成功率。机制争议：中介解释（提取改变语义整合 vs 强化检索路线）未收敛。【问题】按证据强度排序该领域可迁移到自学产品的三条设计建议，并为每条标注其效应量的调节因素"},
    {"qid": "L3-43", "layer": "L3", "persona": "self_learner", "lang": "mixed", "intent": "long_context_qa", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "standard",
     "text": "[Study material] Memory reconsolidation: A retrieved memory enters a labile state and must re-consolidate; interference during this window can update or weaken the memory. This explains why incorrectly recalled facts get strengthened if feedback is delayed. In education, immediate corrective feedback after retrieval exploits reconsolidation. Hypercorrection: high-confidence errors, once corrected, are better remembered than low-confidence errors — but only with prompt feedback. Spacing feedback 10 minutes after retrieval shows mixed results. [Question] Derive three concrete feedback-timing rules for a flashcard app from this material, mark each rule's evidence strength, and identify which claim rests on the thinnest evidence"},
    {"qid": "L3-44", "layer": "L3", "persona": "exam_candidate", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：我的模考成绩序列——数学 98/102/95/108/105（满分150），语文稳定110，英语 125→131，理综波动大 170-200。投入：数学每周10h，理综6h，英语3h，语文2h。距离高考还有150天。请分析各科的边际投入产出，判断理综波动的可能来源（知识面vs熟练度vs考试策略），给出150天的投入重分配和验证节点"},
    {"qid": "L3-45", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：我记录了30天的专注数据——日均专注时长2.1h，但上午10-12点占62%；下午专注成功率仅31%；使用番茄钟的日子平均多25分钟专注；咖啡摄入与夜间睡眠质量负相关（r=-0.4）。目标是无痛扩展到日均3.5h。请构建因果假设图，指出哪些相关可能是混杂，给出三个按证据强度排序的干预"},
    {"qid": "L3-46", "layer": "L3", "persona": "college_student", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：四人宿舍学习小组12周记录——固定参加4人→2人→3人波动；每周目标完成率平均41%；组内互相讲题环节留存率最高（87%出席）；微信群消息95%是闲聊。小组面临解散投票。请分析这个小组的实际功能与宣称功能的落差，保留/重组/解散三个选项的裁决框架，以及若重组的最小有效结构"},
    {"qid": "L3-47", "layer": "L3", "persona": "researcher", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：某学习APP的A/B实验数据——新推荐算法组DAU+8%（p<0.01），但7日留存-2%（p=0.04），完课率-11%（p<0.01），客服投诉「内容太浅」+40%。请分析短期参与指标与长期学习价值的冲突结构，判断该算法应全量/回滚/分段推出的证据充分性，并指出这个数据缺失了哪些关键分层"},
    {"qid": "L3-48", "layer": "L3", "persona": "self_learner", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：三段自述——(1)「收藏了200篇干货文章，一篇没读完」；(2)「买课如山倒，学课如抽丝，买了9门完成2门」；(3)「我知道该做什么，但总是等到deadline才爆发」。请构建囤积式学习的行为画像：每个行为的函数（它到底在奖励什么）、风险、替代动作，并指出哪一条与另外两条共享同一心理机制"},
    {"qid": "L3-49", "layer": "L3", "persona": "exam_candidate", "lang": "en", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "Deep analysis request: My IELTS history — Speaking 6.0→6.0→5.5 despite 40h of shadowing practice; Writing 5.5→6.5; Reading 8.0 stable; Listening 7.5→8.0. Budget: 6 weeks left, 10h/week. Analyze why speaking plateaued then dropped (practice quality vs anxiety vs examiner variance), reallocate hours with justification, and define what evidence would make you abandon the reallocation"},
    {"qid": "L3-50", "layer": "L3", "persona": "professional", "lang": "zh", "intent": "deep_analysis", "lane": "pro", "reasoning_mode": "deep", "chat_mode": "deep_analysis",
     "text": "深度分析请求：我的知识管理系统三代演进——第一代笔记本摘抄（废弃）、第二代双链笔记12000条（检索率<2%）、第三代周报模板（坚持14周）。每代迁移成本约20h。请分析三代系统的真实使用率与宣称价值，判断第四代该「继续建工具」还是「停止建工具」，给出判定所依据的行为证据清单"},
]

CORPUS = list(E08_CORPUS) + EXTRA_CORPUS
_BY_LAYER = {layer_name: [q for q in CORPUS if q["layer"] == layer_name] for layer_name in ("L0", "L1", "L2", "L3")}
for _lname, _qs in _BY_LAYER.items():
    assert len(_qs) == 50, f"layer {_lname} has {len(_qs)} distinct queries, expected 50"


def guest_auth(guest_id: str) -> tuple[str, str]:
    import httpx  # noqa: PLC0415

    r = httpx.post(f"{HTTP_BASE}/auth/guest", params={"guest_id": guest_id}, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data["user"]["id"]


def db_fetch_token_usage(request_ids: list[str]) -> dict[str, dict]:
    if not request_ids:
        return {}
    id_list = ",".join(f"'{rid}'" for rid in request_ids)
    sql = (
        "SELECT coalesce(json_agg(t),'[]'::json) FROM ("
        "SELECT request_id, model, model_tier, ai_reasoning_mode, prompt_tokens, "
        "completion_tokens, total_tokens, cost FROM token_usage "
        f"WHERE request_id IN ({id_list})) t"
    )
    try:
        out = subprocess.run(PSQL + [sql], capture_output=True, text=True, timeout=30, check=True)
        rows = json.loads(out.stdout or "[]")
        return {r["request_id"]: r for r in rows}
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"[warn] db attribution failed: {exc}", file=sys.stderr)
        return {}


def run_queries(layers: list[str], reps: int, out_dir: Path, tag: str, run_limit: int = 0) -> None:
    sys.path.insert(0, str(WORKTREE_BACKEND))
    gen_dir = WORKTREE_BACKEND / "app" / "gen" / "agent" / "v1"
    sys.path.insert(0, str(gen_dir))
    import agent_service_pb2 as pb2  # noqa: PLC0415
    import agent_service_pb2_grpc as pb2_grpc  # noqa: PLC0415
    import grpc  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    done: set[str] = set()
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["run_key"])
            except (json.JSONDecodeError, KeyError):
                continue

    tok_free, uid_free = guest_auth(GUEST_FREE)
    tok_pro, uid_pro = guest_auth(GUEST_PRO)
    print(f"auth ok: free={uid_free} pro={uid_pro} resume_done={len(done)}")

    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = pb2_grpc.AgentServiceStub(channel)
    try:
        for rep in range(1, reps + 1):
            for layer in layers:
                corpus = _BY_LAYER[layer]
                if run_limit:
                    corpus = corpus[:run_limit]
                session_id = ""
                session_turn = 0
                for q in corpus:
                    run_key = f"{q['qid']}#r{rep}"
                    if run_key in done:
                        continue
                    if session_turn >= SESSION_ROTATE_EVERY or not session_id:
                        session_id = ""
                        session_turn = 0
                    session_turn += 1
                    is_pro = q["lane"] == "pro"
                    token, uid = (tok_pro, uid_pro) if is_pro else (tok_free, uid_free)
                    request_id = (
                        f"wt406q06-{q['qid'].lower()}-r{rep}-{uuid.uuid4().hex[:6]}"
                    )
                    req = pb2.ChatRequest(
                        user_id=uid, message=q["text"], session_id=session_id,
                        request_id=request_id, chat_mode=q["chat_mode"],
                    )
                    if is_pro:
                        req.user_profile.is_pro = True
                    if q["reasoning_mode"]:
                        req.extra_context["reasoning_mode"] = q["reasoning_mode"]
                    meta = [("authorization", f"Bearer {token}"), ("user-id", uid)]
                    timeout = TIMEOUT_S_L3 if layer == "L3" else TIMEOUT_S_DEFAULT
                    rec: dict = {
                        "run_key": run_key, "rep": rep,
                        "qid": q["qid"], "layer": layer, "persona": q["persona"],
                        "lang": q["lang"], "intent": q["intent"], "lane": q["lane"],
                        "reasoning_mode_sent": q["reasoning_mode"], "chat_mode_sent": q["chat_mode"],
                        "pro_signal": "user_profile.is_pro=true" if is_pro else "none",
                        "message_chars": len(q["text"]), "session_turn": session_turn,
                        "request_id": request_id, "run_tag": tag or "run",
                        "ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    t0 = time.perf_counter()
                    frames: list[dict] = []
                    first_event = first_delta = first_stage_t = None
                    first_stage_name = ""
                    stages_seq: list[str] = []
                    usage_frame = None
                    error_info = None
                    deltas = 0
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
                            elif kind == "usage":
                                usage_frame = {
                                    "prompt_tokens": fr.usage.prompt_tokens,
                                    "completion_tokens": fr.usage.completion_tokens,
                                    "total_tokens": fr.usage.total_tokens,
                                }
                            elif kind == "full_text":
                                full_text = fr.full_text
                            elif kind == "error":
                                error_info = {"error_code": str(fr.error.error_code), "message": fr.error.message[:300], "retryable": bool(fr.error.retryable)}
                            frames.append({"t": round(t, 4), "kind": kind or "meta_only",
                                           "stage": (ux or {}).get("stage") if ux else None})
                    except Exception as exc:  # noqa: BLE001
                        error_info = {"code": type(exc).__name__, "message": str(exc)[:300],
                                      "at_s": round(time.perf_counter() - t0, 3)}
                    total_s = time.perf_counter() - t0
                    if full_text and len(full_text) > len(response_text):
                        response_text = full_text
                    max_gap = 0.0
                    if len(frames) >= 2:
                        ts = [f["t"] for f in frames]
                        max_gap = max(b - a for a, b in zip(ts, ts[1:]))
                    rec.update({
                        "t_first_event_s": round(first_event, 4) if first_event is not None else None,
                        "t_first_stage_s": round(first_stage_t, 4) if first_stage_t is not None else None,
                        "first_stage_name": first_stage_name,
                        "stage_sequence": ">".join(stages_seq[:24]),
                        "ttft_first_delta_s": round(first_delta, 4) if first_delta is not None else None,
                        "total_s": round(total_s, 4),
                        "delta_events": deltas,
                        "frame_count": len(frames),
                        "max_gap_s": round(max_gap, 4),
                        "usage_frame": usage_frame,
                        "error": error_info,
                        "first_touch_tier": observed_md.get("first_touch_tier", ""),
                        "session_id": observed_md.get("session_id", ""),
                        "response_text": response_text[:20000],
                    })
                    rec.update(quality_fields(q["text"], response_text, q["lang"], q["intent"]))
                    with open(raw_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        f.flush()
                    print(f"[r{rep} {idx_tag(q['qid'])}] {q['qid']} lane={q['lane']} ttft={rec['ttft_first_delta_s']} "
                          f"total={rec['total_s']} err={bool(error_info)} chars={rec['response_chars']}", flush=True)
                    if session_id == "" and rec["session_id"]:
                        session_id = rec["session_id"]
                    time.sleep(INTER_QUERY_SLEEP_S)
    finally:
        channel.close()

    time.sleep(12)  # billing worker flush 间隔余量，避免归因缺行
    enrich(raw_path)
    print(f"done. raw={raw_path}")


def idx_tag(qid: str) -> str:
    return qid.split("-")[1] if "-" in qid else qid


def enrich(raw_path: Path) -> None:
    recs = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
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


def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    k = (len(vs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(vs) - 1)
    return vs[lo] + (vs[hi] - vs[lo]) * (k - lo)


def _fmt(v, nd=3):
    return "-" if v is None else f"{v:.{nd}f}"


def cost_of(model_key: str | None, ptok: int, ctok: int) -> tuple[float | None, str]:
    if model_key is None:
        return None, "unknown"
    p = PRICE_TABLE_USD_PER_MTOK.get(model_key)
    if not p:
        return None, "unpriced"
    if p.get("fallback_marker"):
        return 0.0, "fallback"
    return ptok / 1e6 * p["in"] + ctok / 1e6 * p["out"], p["model"]


def summarize(out_dir: Path, tag: str, reps: int) -> None:
    raw_path = out_dir / f"raw{('-' + tag) if tag else ''}.jsonl"
    recs = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    corpus_by_qid = {q["qid"]: q for q in CORPUS}
    for r in recs:
        q = corpus_by_qid.get(r["qid"])
        if q:
            r.update(quality_fields(q["text"], r.get("response_text") or "", q["lang"], q["intent"]))
        fc = None
        for f in r.get("frame_timeline") or []:
            if f.get("kind") in ("delta", "full_text"):
                fc = f.get("t")
                break
        if fc is None:
            fc = r.get("ttft_first_delta_s")
        r["_ttft_content_s"] = fc
        ptok = r.get("db_prompt_tokens")
        ctok = r.get("db_completion_tokens")
        if ptok is None:
            uf = r.get("usage_frame") or {}
            ptok, ctok = uf.get("prompt_tokens"), uf.get("completion_tokens")
        r["_ptok"], r["_ctok"] = (ptok or 0), (ctok or 0)
        r["_usage_src"] = "db" if r.get("db_prompt_tokens") is not None else (
            "stream" if r.get("usage_frame") else "none")
        cost, pmodel = cost_of(r.get("db_model"), r["_ptok"], r["_ctok"])
        r["_cost_usd"] = cost
        r["_price_model"] = pmodel
        r["_fallback"] = (r.get("db_model") in (None, "default")) or bool(r.get("error"))

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
        gaps = [r["max_gap_s"] for r in rs if r.get("max_gap_s") is not None]
        cost = sum(r["_cost_usd"] or 0 for r in rs)
        n = len(rs)
        # 卡面验收：p50/p95 only if n>=100
        reportable = n >= TARGET_N_PER_LAYER
        return {
            "n": n, "ok": sum(1 for r in rs if not r.get("error")),
            "err": sum(1 for r in rs if r.get("error")),
            "fallback": sum(1 for r in rs if r["_fallback"]),
            "quality_pass": sum(1 for r in rs if r.get("quality_pass")),
            "ttft_p50": _pct(ttfts, 50) if reportable else None,
            "ttft_p95": _pct(ttfts, 95) if reportable else None,
            "content_p50": _pct(contents, 50) if reportable else None,
            "content_p95": _pct(contents, 95) if reportable else None,
            "total_p50": _pct(totals, 50) if reportable else None,
            "total_p95": _pct(totals, 95) if reportable else None,
            "fb_p50": _pct(fb, 50) if reportable else None,
            "fb_p95": _pct(fb, 95) if reportable else None,
            "gap_p95": _pct(gaps, 95) if reportable else None,
            "ptok_sum": sum(r["_ptok"] for r in rs), "ctok_sum": sum(r["_ctok"] for r in rs),
            "cost_sum": cost, "cost_mean": cost / n if n else None,
            "_reportable": reportable,
        }

    layers = ["L0", "L1", "L2", "L3"]
    by_layer = {ln: stats(sel(recs, layer=ln)) for ln in layers}
    by_lane_layer = {(ln, lane): stats(sel(recs, layer=ln, lane=lane))
                     for ln in layers for lane in ("free", "pro")}
    tiers: dict[str, list] = {}
    for r in recs:
        tiers.setdefault(str(r.get("db_model")), []).append(r)
    now = datetime.now(timezone.utc).astimezone()

    # SLO 判定（Gate V3-8；n<100 的层不判 p95 → 结论=NOT_REPORTABLE）
    slo: list[dict] = []

    def judge(name: str, measured, target, ok, n):
        slo.append({"slo": name, "measured": measured, "target": target,
                    "n": n, "verdict": ("PASS" if ok else "FAIL") if n >= TARGET_N_PER_LAYER else "NOT_REPORTABLE"})

    l0 = by_layer["L0"]
    v = l0["ttft_p95"]
    judge("L0 no-model 路径 p95<=500ms（口径：L0 TTFT p95；无 no-model 直答时为全生成链）",
          f"{v * 1000:.0f}ms" if v is not None else None, "500ms", bool(v is not None and v * 1000 <= 500), l0["n"])
    l1 = by_layer["L1"]
    v50, v95 = l1["content_p50"], l1["content_p95"]
    judge("L1 first meaningful feedback p50<=2.5s", f"{v50:.2f}s" if v50 else None, "2.5s",
          bool(v50 is not None and v50 <= 2.5), l1["n"])
    judge("L1 p95<=5s", f"{v95:.2f}s" if v95 else None, "5s",
          bool(v95 is not None and v95 <= 5), l1["n"])
    l2f = by_lane_layer[("L2", "free")]
    l2all = by_layer["L2"]
    v = l2f["fb_p95"]
    judge("L2 500ms 内阶段反馈（首事件 p95, free lane）", f"{v * 1000:.0f}ms" if v else None, "500ms",
          bool(v is not None and v * 1000 <= 500), l2f["n"])
    v = l2all["fb_p95"]
    judge("L2 500ms 内阶段反馈（首事件 p95, 全 lane 参考，语料 lane 配比非 1:1）",
          f"{v * 1000:.0f}ms" if v else None, "500ms",
          bool(v is not None and v * 1000 <= 500), l2all["n"])
    l2 = by_layer["L2"]
    v = l2["total_p95"]
    judge("L2 最终 p95<=15s", f"{v:.1f}s" if v else None, "15s", bool(v is not None and v <= 15), l2["n"])
    l3 = by_layer["L3"]
    v = l3["fb_p95"]
    judge("L3 Agent Run 创建/ACK p95<=1s（首事件口径）", f"{v:.2f}s" if v else None, "1s",
          bool(v is not None and v <= 1), l3["n"])

    # tier 账本（分层是否真实在跑）
    tier_rows = {m: {"n": len(rs),
                     "tiers": sorted({str(r.get("db_model_tier") or "?") for r in rs}),
                     "ptok": sum(r["_ptok"] for r in rs), "ctok": sum(r["_ctok"] for r in rs),
                     "cost": sum(r["_cost_usd"] or 0 for r in rs),
                     "ttft_p50": _pct([r["ttft_first_delta_s"] for r in rs if r.get("ttft_first_delta_s") is not None], 50)}
                for m, rs in tiers.items()}

    metered_models = {m for m, s in tier_rows.items() if m not in ("None", "default") and (s["ptok"] or s["ctok"])}

    facts = {
        "generated_at": now.isoformat(timespec="seconds"), "reps": reps,
        "n_total": len(recs), "by_layer": by_layer, "by_lane_layer": {f"{k0}-{k1}": v for (k0, k1), v in by_lane_layer.items()},
        "tier_ledger": tier_rows, "slo": slo,
        "metered_models": sorted(metered_models),
        "errors": [r["error"] for r in recs if r.get("error")],
    }
    (out_dir / f"facts{('-' + tag) if tag else ''}.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")

    csv_path = out_dir / f"raw{('-' + tag) if tag else ''}.csv"
    cols = ["run_key", "rep", "qid", "layer", "lane", "pro_signal", "persona", "lang", "intent",
            "reasoning_mode_sent", "chat_mode_sent", "request_id", "ts_utc",
            "t_first_event_s", "t_first_stage_s", "ttft_first_delta_s", "_ttft_content_s", "total_s",
            "delta_events", "frame_count", "max_gap_s", "db_model", "db_model_tier", "db_ai_reasoning_mode",
            "db_prompt_tokens", "db_completion_tokens", "_cost_usd", "_price_model", "_usage_src",
            "error", "response_chars", "quality_pass", "first_touch_tier", "session_id"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            w.writerow([r.get(c) if c != "error" else (r.get("error") or {}).get("error_code", "") for c in cols])

    suffix = ("-" + tag) if tag else ""
    print(f"facts -> {out_dir / ('facts' + suffix + '.json')}")
    print(f"csv -> {csv_path}")
    print("slo: " + " | ".join(f"{s['verdict']}" for s in slo))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap_run = sub.add_parser("run", help="执行 bench（真模型真服务）")
    ap_run.add_argument("--layers", default="L0,L1,L2,L3")
    ap_run.add_argument("--reps", type=int, default=REPS_DEFAULT)
    ap_run.add_argument("--limit", type=int, default=0, help="每层只跑前 N 条 distinct（烟测用）")
    ap_run.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap_sum = sub.add_parser("summarize", help="从 raw 重算 facts/csv")
    ap_sum.add_argument("--reps", type=int, default=REPS_DEFAULT)
    ap_sum.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    if args.cmd == "run":
        run_queries(args.layers.split(","), args.reps, out_dir, "bench", args.limit)
    else:
        summarize(out_dir, "bench", args.reps)


if __name__ == "__main__":
    main()
