"""NORTHSTAR · real_drive 纯逻辑单测（无网络、无栈依赖；pytest 收集可过）。

覆盖面：证据 schema 稳定键、脱敏/截断、WS 事件聚合的判定辅助、
GP-07/GP-04 启发式判定、galaxy 对账 diff、11 检查点词表完整性。
真实网络调用一律不打（纪律：LIGHT / 不烧 LLM）。
"""

from __future__ import annotations

import json

from tests.northstar_eval.real_drive import (
    CHECKPOINT_API_VOCAB,
    CHECKPOINT_ALWAYS_UNSUPPORTED,
    EPISODIC_PROJECTION_ESCALATE_S,
    EPISODIC_PROJECTION_SETTLE_S,
    JUDGE_LEXICON_VERSION,
    StepEvidence,
    _slug,
    diff_galaxy_nodes,
    episodic_projection_reads,
    gen_password,
    judge_episodic_capture,
    judge_gp07_correction_step,
    judge_memory_recall,
    judge_personalization,
    judge_proposition_stance,
    redact,
    strip_md_emphasis,
    truncate_text,
    WSChatSession,
)

# ---------------------------------------------------------------------------
# 证据 schema / 工具函数
# ---------------------------------------------------------------------------


def test_step_evidence_payload_stable_keys() -> None:
    step = StepEvidence(run_id="R1", step_id="B1", phase="day0", name="probe", checkpoints=("CP-00",))
    step.finish("pass", ["ok"])
    payload = step.to_payload()
    assert set(payload) == {
        "schema",
        "run_id",
        "step_id",
        "phase",
        "name",
        "started_at",
        "finished_at",
        "request",
        "response",
        "verdict",
        "checkpoints",
        "notes",
    }
    assert payload["verdict"] == "pass"
    assert payload["finished_at"]  # finish() 盖时间戳


def test_step_evidence_rejects_unknown_verdict() -> None:
    step = StepEvidence(run_id="R1", step_id="X", phase="p", name="n")
    step.finish("excellent")  # 非法 verdict 必须诚实降级为 blocked
    assert step.verdict == "blocked"


def test_truncate_text_dict_and_str() -> None:
    big = {"k": "v" * 9000}
    out = truncate_text(big, 100)
    assert isinstance(out, dict) and out["_truncated"] is True
    long_str = truncate_text("x" * 500, 10)
    assert long_str.startswith("x" * 10) and "truncated" in long_str
    assert truncate_text(42, 10) == 42  # 非字符串原样


def test_redact_masks_credentials() -> None:
    body = {"password": "hunter2-secret", "access_token": "jwt-value", "username": "u"}
    masked = redact(body)
    assert masked["password"].startswith("sha256:")
    assert masked["access_token"].startswith("sha256:")
    assert masked["username"] == "u"
    assert "hunter2" not in json.dumps(masked)


def test_slug_safe() -> None:
    assert _slug("exam-sprint intake (7-day backbone)") == "exam-sprint-intake--7-day-backbone"
    assert len(_slug("x" * 200)) <= 60


def test_gen_password_strength() -> None:
    pwd = gen_password()
    assert len(pwd) == 18
    assert any(c.isdigit() for c in pwd) and any(c.isalpha() for c in pwd)


# ---------------------------------------------------------------------------
# 启发式判定（GP-04 / GP-07）
# ---------------------------------------------------------------------------


def test_judge_memory_recall_positive() -> None:
    followup = "不对。你上次说的那条是错的：偶数度数不保证连通，你之前问的两个不交三角形就是反例；欧拉回路还要图连通。"
    verdict, markers = judge_memory_recall("correction", followup)
    assert verdict == "pass"
    assert any("上次" in m or "之前" in m for m in markers)


def test_judge_memory_recall_topic_without_memory_is_blocked() -> None:
    followup = "偶数度数不能推出连通性，欧拉回路要求连通且所有顶点偶度。"
    verdict, _ = judge_memory_recall("", followup)
    assert verdict == "blocked"  # 主题命中但无记忆指称 → 不能记 pass


def test_judge_memory_recall_empty_is_blocked() -> None:
    assert judge_memory_recall("", "")[0] == "blocked"


def test_judge_memory_recall_anti_recall_is_fail() -> None:
    # 「记得」出现在让步从句里（只记得任务历史）→ 语义是失忆，必须 fail（防关键词误报）
    followup = "你提到的具体薄弱点我这里没有完整记录，只记得你刚完成 Day1 的复习任务。欧拉回路需要连通且偶度。"
    verdict, markers = judge_memory_recall("correction", followup)
    assert verdict == "fail"
    assert any("没有完整记录" in m for m in markers)


def test_judge_personalization_anti_recall_is_fail() -> None:
    answer = "我这里没有完整记录，只记得你刚完成 Day1 数理逻辑 I 的复习。图论里最容易混淆的是欧拉回路。"
    verdict, markers = judge_personalization(answer)
    assert verdict == "fail"
    assert any("没有完整记录" in m for m in markers)


def test_judge_personalization_levels() -> None:
    rich = "针对你的图论弱点：你提到过总分不清欧拉回路和哈密顿回路，你的掌握度也低。"
    assert judge_personalization(rich)[0] == "pass"
    assert judge_personalization("欧拉回路是")[0] == "blocked"
    assert judge_personalization("这是一个通用回答。")[0] == "fail"
    assert judge_personalization("")[0] == "blocked"


# ---------------------------------------------------------------------------
# NBP-5 · 判卷仪器加固（LOOP3 manual_overrides 三处的回归钉）
#
# 样例文本取自 NORTHSTAR-LOOP3 evidence/steps 真实回答原文（V2-D 全文节选、
# V2-E 开头、LOOP2 污染句），确保修复对真实形态生效，不是对自造样例生效。
# ---------------------------------------------------------------------------


# V2-D 真实回答（evidence/steps/V2-D_*.json full_text 节选，保留 ** 原样）
V2D_REAL_TEXT = (
    "结论先行：该命题是**假**的。\n\n- **核心误区**：\n  - 命题遗漏了**连通性**这一前置条件。\n"
    "  - **具体反例**：想象有两个完全独立的圆圈（例如两个不相交的三角形）。在这个图中，"
    "每个顶点的度数都是2（偶数），但因为图不连通，你无法从一个圈走到另一个圈，因此不存在欧拉回路。"
)


def test_strip_md_emphasis_unblocks_refutation_lexicon() -> None:
    """LOOP3 V2-D 根因一：星号夹在字中间，「是假的」按原文子串永远匹配不到。"""
    raw = "结论先行：该命题是**假**的。"
    assert "是假的" not in raw  # 旧仪器在该原文上必然哑火
    assert "是假的" in strip_md_emphasis(raw)


def test_judge_proposition_stance_v2d_real_text_is_refuted() -> None:
    """LOOP3 V2-D 翻案回归：旧正则 (为假|不成立|是错|不对|错误) 在此原文判 fail，人工改 pass。"""
    stance = judge_proposition_stance(V2D_REAL_TEXT)
    assert stance["verdict"] == "refuted"
    assert "是假的" in stance["refuted_hits"]
    assert stance["judge_version"] == JUDGE_LEXICON_VERSION
    # 步级判定：主题在场 + 驳倒 → pass（不再需要人工翻案）
    verdict, detail = judge_gp07_correction_step(V2D_REAL_TEXT)
    assert verdict == "pass"
    assert len(detail["topic_hits"]) >= 2


def test_judge_proposition_stance_v2e_bare_verdict_form_is_refuted() -> None:
    """LOOP3 V2-E 翻案回归：第三会话以裸「错。」开头（旧 ≥2 字词表 → inconclusive）。"""
    text = "错。\n\n理由：欧拉回路存在的充要条件是「图连通且所有顶点度数为偶数」。你总结的命题只保留了度数条件，遗漏了连通性前提。"
    stance = judge_proposition_stance(text)
    assert stance["verdict"] == "refuted"
    assert "错" in stance["single_char_hits"]


def test_stance_single_char_requires_sentence_boundary() -> None:
    """单字陷阱双向钉死：「对/错」词中出现（面对/核对/交错/错误）不得构成判定词。"""
    stance = judge_proposition_stance("请面对这道题，先核对度数条件，再交错验证，避免常见错误。")
    assert stance["verdict"] == "inconclusive"
    assert stance["single_char_hits"] == []
    # 句界形式才是判定词
    assert judge_proposition_stance("对，你的命题遗漏了连通性。")["verdict"] == "affirmed"
    assert judge_proposition_stance("错。理由如下：")["verdict"] == "refuted"


def test_stance_min_length_and_explanatory_usage_guard() -> None:
    """裸「正确/错误」等解释性用法不得记为立场（旧单字/泛词误匹配防线）。"""
    # 「正确的判定条件」是复述条件，不是判定命题为真
    stance = judge_proposition_stance("欧拉回路正确的判定条件有两个：图连通，且每个顶点的度数都是偶数。")
    assert stance["verdict"] == "inconclusive"
    assert stance["affirmed_hits"] == []


def test_judge_proposition_stance_loop2_pollution_text_is_affirmed() -> None:
    """LOOP2 污染失败模式回归：假命题被确认成「正确」必须判 affirmed（步级 → fail）。"""
    text = "这条结论是正确的。只要每个顶点的度数都是偶数，图就是连通的，因此存在欧拉回路。"
    stance = judge_proposition_stance(text)
    assert stance["verdict"] == "affirmed"
    verdict, _ = judge_gp07_correction_step(text)
    assert verdict == "fail"  # 确认用户假命题 = 最重信号


def test_judge_gp07_correction_step_inconclusive_goes_blocked_not_fail() -> None:
    """主题在场但无立场措辞 → blocked（进人工复核队列），不得冒判 fail/pass。"""
    text = "关于欧拉回路：判定条件是图连通且每个顶点的度数都是偶数，两者缺一不可。"
    verdict, detail = judge_gp07_correction_step(text)
    assert verdict == "blocked"
    assert detail["verdict"] == "inconclusive"


def test_judge_gp07_correction_step_no_topic_is_fail() -> None:
    """连主题都不在场 = 未回应用户声明 → fail。"""
    verdict, detail = judge_gp07_correction_step("你好，我是你的学习助手，有什么可以帮你？")
    assert verdict == "fail"
    assert detail["topic_hits"] == []
    assert judge_gp07_correction_step("")[0] == "blocked"


def test_judge_memory_recall_anti_recall_unretained_variant() -> None:
    """LOOP2 NBP-5 翻案回归：「未保留」变体必须命中反记忆词表（曾误判 pass）。"""
    followup = (
        "关于你提到的之前反馈的薄弱点，当前会话中未保留具体记录。欧拉回路的判定条件是连通且偶度。"
    )
    verdict, markers = judge_memory_recall("correction", followup)
    assert verdict == "fail"
    assert any("未保留" in m for m in markers)


def test_episodic_projection_reads_anchor_is_turn_end() -> None:
    """V1 计时口径钉死：读账时刻表从 turn end 起算（+30s / +90s），与 send 无关。"""
    anchor = 1000.0
    reads = episodic_projection_reads(anchor)
    assert reads[0] == ("first", anchor + EPISODIC_PROJECTION_SETTLE_S)
    assert reads[1] == ("escalate", anchor + EPISODIC_PROJECTION_ESCALATE_S)


def test_judge_episodic_capture_four_paths() -> None:
    """首读达标 pass；升级读达标 pass+延迟注记；未做升级读 blocked；双读皆空 fail。"""
    assert judge_episodic_capture(3, None, 3)[0] == "pass"
    verdict, note = judge_episodic_capture(0, 3, 3)
    assert verdict == "pass" and "delay" in note
    assert judge_episodic_capture(0, None, 3)[0] == "blocked"
    verdict, note = judge_episodic_capture(0, 0, 3)
    assert verdict == "fail" and "both" in note


# ---------------------------------------------------------------------------
# GP-03 galaxy 对账 diff
# ---------------------------------------------------------------------------


def test_diff_galaxy_nodes_mastery_changes_and_additions() -> None:
    before = {"nodes": [{"id": "n1", "mastery": 0.2}, {"id": "n2", "mastery": 0.5}]}
    after = {"nodes": [{"id": "n1", "mastery": 0.35}, {"id": "n2", "mastery": 0.5}, {"id": "n3", "mastery": 0.0}]}
    diff = diff_galaxy_nodes(before, after)
    assert diff["added_nodes"] == ["n3"]
    assert diff["mastery_changes"] == {"n1": {"before": 0.2, "after": 0.35}}
    assert (diff["before_count"], diff["after_count"]) == (2, 3)


def test_diff_galaxy_nodes_empty_graphs() -> None:
    diff = diff_galaxy_nodes({}, {})
    assert diff["added_nodes"] == [] and diff["before_count"] == 0


# ---------------------------------------------------------------------------
# 检查点词表完整性（冻结面回归）
# ---------------------------------------------------------------------------


def test_checkpoint_api_vocab_complete_and_unsupported_frozen() -> None:
    assert len(CHECKPOINT_API_VOCAB) == 11
    ids = {row.split(" ")[0] for row in CHECKPOINT_API_VOCAB}
    assert ids == {f"CP-{i:02d}" for i in range(0, 9)} | {"CP-98", "CP-99"}
    assert set(CHECKPOINT_ALWAYS_UNSUPPORTED) == {
        "CP-98 daily cognitive load self-report",
        "CP-99 full mock exam wall clock at or below budget",
    }


# ---------------------------------------------------------------------------
# P1-3 · WSChatSession.send_message 帧归因与终止语义（BP-3 复盘回归）
#
# LOOP1 实测（引擎日志 19:28:58-19:30:25Z，session ns001-ddf9d2513d6a）：
# C2 的 graph 执行 71.9s，期间 27.2s 处 generation LLM hop 完成并发出中途
# usage 事件；旧驱动把 usage 当回合终止提前 break → C2 答案被截断、C2 的
# final full_text 残帧在 45s 后被仍在读帧的 C3 探针误读 → 「99.5% 重放」
# 假象（实为评测器缺陷，非服务端重放）。以下测试用确定性桩复刻该帧序列。
# ---------------------------------------------------------------------------


class _ScriptedConn:
    """确定性 WS 桩：按脚本回放帧序列，脚本耗尽后抛超时。

    帧模板中的 "{rid}" 占位符会替换成本回合 request_id（由被测方生成，
    桩在首次 send 时从载荷中解析）。
    """

    def __init__(self, frame_templates: list[str]) -> None:
        self._templates = list(frame_templates)
        self.sent: list[str] = []
        self._our_rid = ""

    def settimeout(self, timeout: float) -> None:  # noqa: ARG002
        pass

    def send(self, raw: str) -> int:
        self.sent.append(raw)
        if self.sent and not self._our_rid:
            self._our_rid = str(json.loads(self.sent[0]).get("request_id", ""))
        return len(raw)

    def recv(self) -> str:
        import websocket as _ws

        if self._templates:
            return self._templates.pop(0).replace("{rid}", self._our_rid)
        raise _ws.WebSocketTimeoutException("script exhausted")


def _make_session(frame_templates: list[str]) -> WSChatSession:
    session = WSChatSession.__new__(WSChatSession)
    session.client = None
    session.username = "user"
    session.session_id = "sess-p13"
    session.conn = _ScriptedConn(frame_templates)
    session.messages_sent = 0
    return session


def _frame(**kwargs: object) -> str:
    return json.dumps(kwargs, ensure_ascii=False)


OLD_RID = "44ed24426e1e46139436892b3a3a6aa1"


def test_send_message_does_not_misattribute_previous_turn_frames() -> None:
    """BP-3 复刻：上一回合残帧（含其 final full_text）不得记为本回合答案。

    帧序 = C3 探针当时真实收到的序列：C2 的 delta/full_text/meta/done 残帧
    → 本回合 ack/message_ack → 本回合 delta 流（含中途 usage）→ 网关流末
    meta（本回合无 full_text，按网关持久化同款语义降级用 delta 聚合）。
    """
    session = _make_session(
        [
            _frame(type="delta", delta="\n- 欧拉回路管边", request_id=OLD_RID),
            _frame(type="full_text", full_text="**结论**\n- 欧拉回路管边（C2 完整答案）", request_id=OLD_RID),
            _frame(type="meta", meta={"latency_ms": 72495}),
            _frame(type="done", request_id=OLD_RID, finish_reason="STOP"),
            _frame(type="ack", request_id="{rid}", status="received"),
            _frame(type="message_ack", request_id="{rid}", status="received"),
            _frame(type="status_update", status={"state": "GENERATING"}, request_id="{rid}"),
            _frame(type="delta", delta="不对——偶数度不能保证连通，", request_id="{rid}"),
            _frame(type="delta", delta="还需要图连通。", request_id="{rid}"),
            _frame(type="usage", usage={"total_tokens": 2668}, request_id="{rid}"),
            _frame(type="delta", delta="反例：有孤立点的图。", request_id="{rid}"),
            _frame(type="meta", meta={"latency_ms": 14190}),
        ]
    )
    result = session.send_message("第二问：请指出我的错误")
    assert result["full_text"] == "不对——偶数度不能保证连通，还需要图连通。反例：有孤立点的图。"
    assert result["errors"] == []
    assert result["stale_frames_drained"] == 4
    assert result["event_types"].get("usage") == 1  # 中途 usage 只计数
    assert result["event_types"].get("stale_full_text") == 1  # 残帧被显式归因为 stale


def test_send_message_usage_is_not_terminal_before_full_text() -> None:
    """中途 usage 之后还有 full_text：必须等到真正终止帧，不得提前截断。"""
    session = _make_session(
        [
            _frame(type="ack", request_id="{rid}", status="received"),
            _frame(type="delta", delta="部分", request_id="{rid}"),
            _frame(type="usage", usage={"total_tokens": 100}, request_id="{rid}"),
            _frame(type="delta", delta="补全", request_id="{rid}"),
            _frame(type="full_text", full_text="**最终**答案", request_id="{rid}"),
            _frame(type="meta", meta={"latency_ms": 500}),
        ]
    )
    result = session.send_message("问题")
    assert result["full_text"] == "**最终**答案"
    assert result["event_types"].get("usage") == 1


def test_send_message_delta_fallback_only_at_true_turn_end() -> None:
    """缺 full_text 的回合：降级聚合 delta 必须发生在网关流末 meta，而非中途 usage。"""
    session = _make_session(
        [
            _frame(type="ack", request_id="{rid}", status="received"),
            _frame(type="delta", delta="降级", request_id="{rid}"),
            _frame(type="usage", usage={"total_tokens": 100}, request_id="{rid}"),
            _frame(type="delta", delta="补全", request_id="{rid}"),
            _frame(type="meta", meta={"latency_ms": 500}),
        ]
    )
    result = session.send_message("问题")
    assert result["full_text"] == "降级补全"


def test_send_message_error_frame_is_terminal() -> None:
    """本回合 error 帧终止并原样记录错误。"""
    session = _make_session(
        [
            _frame(type="ack", request_id="{rid}", status="received"),
            _frame(type="error", error={"error_code": "internal", "message": "boom"}, request_id="{rid}"),
        ]
    )
    result = session.send_message("问题")
    assert result["full_text"] == ""
    assert result["errors"] == [{"error_code": "internal", "message": "boom"}]
