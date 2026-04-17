# Phase 5: 结果富展示与LLM编排优化 — "从能用到好用"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 3个新文件, 5个修改文件 (Flutter + Python后端)
> **依赖**: Phase 1 + Phase 2 已完成

---

## 背景

Phase 1-2 建立了基础执行体验和AI链路。本阶段解决两个核心体验痛点:
1. **结果展示太粗**: parsedOutput是raw JSON, 用户看不懂
2. **LLM调用太贵太慢**: 每次classify都要调LLM, 模板prompt未优化

### 关键现有代码

- `ExecutionApprovalCard` (Phase 1创建) — 审批预览卡, 目前显示raw parsedOutput前200字
- `ExecutionResultInline` (Phase 2创建) — 聊天流内联结果, 同样显示raw文本
- `ExecutionService.classify_task()` — 每次调用ExecutionRouter
- `ExecutionTemplateService` — 5个模板的prompt尚未优化
- `ExecutionQualityService` — A/B实验框架已就绪

---

## 任务 5.1: Flutter — 创建结果内容渲染器

**创建文件**: `mobile/lib/features/task/presentation/widgets/execution_result_renderer.dart`

### 设计规格

根据parsedOutput的内容类型, 自动选择最佳渲染方式。

#### 构造函数
```dart
const ExecutionResultRenderer({
  required Map<String, dynamic> parsedOutput,
  List<Map<String, dynamic>>? artifacts,
  bool expanded = false,
  Key? key,
})
```

#### 内容类型检测与渲染

实现一个静态方法 `_detectContentType(Map<String, dynamic> output)` 返回枚举:

```dart
enum ResultContentType {
  plainText,    // 只有text字段
  structured,   // 有多个key-value字段
  markdown,     // text字段包含markdown标记(#, **, ```, -, |)
  codeBlock,    // text字段主体是代码
  linkList,     // 包含urls/links/sources字段
  mixed,        // 混合内容
}
```

检测逻辑:
```dart
static ResultContentType _detectContentType(Map<String, dynamic> output) {
  final text = output['text'] as String? ?? output['content'] as String? ?? '';
  final hasLinks = output.containsKey('urls') || output.containsKey('links') || output.containsKey('sources');
  final hasCode = text.contains('```') || text.contains('    ') && text.split('\n').where((l) => l.startsWith('    ')).length > 3;
  final hasMarkdown = text.contains('# ') || text.contains('**') || text.contains('- ') || text.contains('| ');

  if (hasLinks) return ResultContentType.linkList;
  if (hasCode && !hasMarkdown) return ResultContentType.codeBlock;
  if (hasMarkdown) return ResultContentType.markdown;
  if (output.keys.length > 2) return ResultContentType.structured;
  return ResultContentType.plainText;
}
```

#### 各类型渲染器

**plainText**: `SelectableText` + DS.textPrimary, fontSize 14

**structured**: 垂直列表, 每个key-value一行:
- key: `Text(key, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: DS.textSecondary))`
- value: `SelectableText(value.toString(), style: TextStyle(fontSize: 14, color: DS.textPrimary))`
- 行间距 DS.spacing8
- 如果字段数>5且!expanded, 只显示前5个 + "还有N个字段" TextButton

**markdown**: 使用Flutter的markdown渲染包。检查项目是否已依赖 `flutter_markdown` 或类似包:
- 如果有: 使用 `MarkdownBody(data: text, styleSheet: ...)` 配合Sparkle设计token
- 如果没有: 降级为 `SelectableText`, 但保留代码块用 `Container(color: DS.surfaceTertiary, padding: 12, borderRadius: 8)` 包裹
- **不要添加新依赖**, 如果项目没有markdown包, 用简单的富文本处理

**codeBlock**:
```dart
Container(
  width: double.infinity,
  padding: const EdgeInsets.all(DS.spacing12),
  decoration: BoxDecoration(
    color: DS.surfaceTertiary,
    borderRadius: BorderRadius.circular(8),
  ),
  child: SelectableText(
    codeContent,
    style: TextStyle(
      fontFamily: 'monospace',
      fontSize: 13,
      color: DS.textPrimary,
      height: 1.5,
    ),
  ),
)
```

**linkList**:
- 提取urls/links/sources列表
- 每个链接渲染为一行: 🔗图标 + 域名(蓝色) + 标题(如果有)
- 点击可复制链接(Clipboard.setData + SnackBar "已复制")
- 不尝试打开外部链接(安全考虑)

#### Artifact展示

如果 `artifacts` 非空且不为null:
- 在内容下方分隔线后渲染artifact列表
- 每个artifact: 文件图标(根据type推断: image→photo, pdf→picture_as_pdf, 其他→insert_drive_file) + 文件名 + 大小(如果有)
- 图片类型的artifact: 显示 `Image.network(artifact['url'])` 预览(高度限制120px, fit: BoxFit.cover, 圆角8)
  - 加载失败时显示placeholder图标
- 点击artifact: 暂时只显示SnackBar "附件预览即将推出"

---

## 任务 5.2: Flutter — 更新审批卡和内联结果使用新渲染器

**修改文件**: `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart` (Phase 1创建)

### 精确修改

找到显示parsedOutput摘要的区域(Phase 1中描述为"取前200字符"), 替换为:

```dart
// 替换原来的 Text(output前200字符) 为:
ExecutionResultRenderer(
  parsedOutput: record.parsedOutput ?? {},
  artifacts: record.artifacts,
  expanded: false,  // 审批卡中默认折叠
),
```

添加import:
```dart
import 'package:sparkle/features/task/presentation/widgets/execution_result_renderer.dart';
```

**修改文件**: `mobile/lib/features/chat/presentation/widgets/execution_result_inline.dart` (Phase 2创建)

同样替换内容展示区域, 使用 `ExecutionResultRenderer`:

```dart
// succeeded/partial状态的内容区域
if (record != null && record.parsedOutput != null)
  Padding(
    padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
    child: ExecutionResultRenderer(
      parsedOutput: record.parsedOutput!,
      artifacts: record.artifacts,
      expanded: false,
    ),
  ),
```

---

## 任务 5.3: 后端 — 意图分类缓存

**修改文件**: `backend/app/services/execution_service.py`

### 修改目标

对classify_task的结果进行缓存, 避免相似任务重复调用Router。

### 精确修改

#### 1. 添加缓存逻辑

在 `ExecutionService.__init__` 中, 现有初始化代码之后添加:

```python
# Phase 5: classify缓存
self._classify_cache: dict[str, tuple[Any, float]] = {}  # key → (result, timestamp)
self._classify_cache_ttl = 300  # 5分钟TTL
```

#### 2. 修改classify_task方法

在现有 `classify_task` 方法的开头(路由逻辑之前), 添加缓存检查:

```python
async def classify_task(self, *, task_id: UUID, user_id: UUID) -> "RoutingDecision":
    import time
    import hashlib

    # Phase 5: 缓存检查
    # 获取task描述用于缓存key
    task = await self._get_task(task_id=task_id, user_id=user_id)
    cache_key = hashlib.md5(
        f"{task.task_type}:{task.title}:{task.description or ''}".encode()
    ).hexdigest()

    now = time.time()
    if cache_key in self._classify_cache:
        cached_result, cached_at = self._classify_cache[cache_key]
        if now - cached_at < self._classify_cache_ttl:
            return cached_result

    # 原有路由逻辑
    decision = self._router.classify(
        task_type=task.task_type or "general",
        task_description=task.description or task.title or "",
        has_side_effects=self._detect_side_effects(task),
        success_criteria=None,
    )

    # 写入缓存
    self._classify_cache[cache_key] = (decision, now)

    # 清理过期缓存 (简单策略: 超过100条时清理)
    if len(self._classify_cache) > 100:
        cutoff = now - self._classify_cache_ttl
        self._classify_cache = {
            k: (v, t) for k, (v, t) in self._classify_cache.items() if t > cutoff
        }

    return decision
```

**注意**: 你需要找到 `classify_task` 中获取task对象的实际代码, 上面用 `self._get_task()` 作为占位符。看实际代码中是如何获取task信息的, 适配缓存key的构建。

---

## 任务 5.4: 后端 — 模板prompt优化

**修改文件**: `backend/app/services/execution_template_service.py`

### 修改目标

为每个内置模板配置精调的system prompt, 减少OpenClaw的试错步骤。

### 精确修改

找到5个模板的定义(搜索 `web_research_brief`, `document_digest` 等), 在每个模板的dict中增加 `optimized_prompt` 字段:

```python
# 在web_research_brief模板的dict中添加:
"optimized_prompt": (
    "Task: Web Research Brief\n"
    "Instructions:\n"
    "1. Search for the specified topic using browser tools\n"
    "2. Open the top 3-5 most relevant results\n"
    "3. Extract key facts, dates, and quotes\n"
    "4. Compile a structured brief with: Summary (2-3 sentences), "
    "Key Findings (bullet points), Sources (URLs with titles)\n"
    "5. Return result as JSON: {\"summary\": str, \"findings\": [str], \"sources\": [{\"url\": str, \"title\": str}]}\n"
    "Constraints: Do not navigate to login-required pages. Do not submit forms. Read-only browsing only."
),

# 在document_digest模板的dict中添加:
"optimized_prompt": (
    "Task: Document Digest\n"
    "Instructions:\n"
    "1. Read the provided document content\n"
    "2. Identify the document type (article, report, paper, etc.)\n"
    "3. Extract: Main thesis, Key arguments/sections, Important data/statistics, Conclusions\n"
    "4. Return result as JSON: {\"type\": str, \"title\": str, \"main_thesis\": str, "
    "\"key_points\": [str], \"statistics\": [str], \"conclusions\": str, \"word_count_estimate\": int}\n"
    "Constraints: Preserve factual accuracy. Do not add interpretation beyond what the document states."
),

# 在shell_diagnostics模板的dict中添加:
"optimized_prompt": (
    "Task: Shell Diagnostics\n"
    "Instructions:\n"
    "1. Run the specified diagnostic command(s) in the shell\n"
    "2. Capture stdout and stderr\n"
    "3. Analyze the output for errors, warnings, and anomalies\n"
    "4. Return result as JSON: {\"command\": str, \"exit_code\": int, \"stdout\": str, "
    "\"analysis\": str, \"issues_found\": [{\"severity\": str, \"description\": str}]}\n"
    "Constraints: Only run read-only diagnostic commands. Never run rm, mv, kill, or write commands. "
    "Never modify system state."
),

# 在browser_form_prepare模板的dict中添加:
"optimized_prompt": (
    "Task: Browser Form Preparation\n"
    "Instructions:\n"
    "1. Navigate to the specified URL\n"
    "2. Identify all form fields and their types\n"
    "3. Based on the user's goal, prepare draft values for each field\n"
    "4. DO NOT submit the form. Return the prepared data for user review.\n"
    "5. Return result as JSON: {\"form_url\": str, \"fields\": [{\"name\": str, \"type\": str, "
    "\"draft_value\": str, \"confidence\": float}], \"notes\": str}\n"
    "Constraints: Never click submit/send/confirm buttons. This is preparation only."
),

# 在cross_device_capture模板的dict中添加:
"optimized_prompt": (
    "Task: Cross-Device Capture\n"
    "Instructions:\n"
    "1. Use the specified device node to capture content (camera/screen/document)\n"
    "2. Process the captured content as specified\n"
    "3. Return result as JSON: {\"captured_at\": str, \"node_id\": str, "
    "\"content_type\": str, \"processed_output\": str, \"artifacts\": [{\"type\": str, \"url\": str}]}\n"
    "Constraints: Only capture from authorized nodes. Request user approval before sensitive captures."
),
```

#### 在dispatch时使用optimized_prompt

找到 `ExecutionService.dispatch()` 方法中构建OpenClaw请求的位置(调用 `IntentTranslator` 的地方), 在构建请求时将template的 `optimized_prompt` 注入到instructions中:

```python
# 在dispatch()中, 构建请求前
template_prompt = None
if intent.policy and intent.policy.get("template_id"):
    template = self._template_service.get_template(intent.policy["template_id"])
    if template and template.get("optimized_prompt"):
        template_prompt = template["optimized_prompt"]

# 将template_prompt作为system instruction注入
# 具体注入方式取决于IntentTranslator的API
if template_prompt:
    # 在翻译时传入
    request_body = self._translator.translate(
        intent=intent,
        config=self._config,
        system_prompt=template_prompt,  # 新增参数
    )
```

**注意**: IntentTranslator.translate()可能需要增加 `system_prompt` 参数。检查其实际签名, 适配方式:
- 如果translate接受额外kwargs, 直接传入
- 如果不接受, 需要在translate方法签名中增加 `system_prompt: str | None = None`, 然后在构建请求体时将其作为system instruction

---

## 任务 5.5: 后端 — 结果自检机制

**创建文件**: `backend/app/services/execution_result_validator.py`

### 设计规格

在OpenClaw结果返回后、进入Ingestor之前, 用轻量级规则检查结果质量, 对低质量结果添加warning标记。

```python
"""Lightweight result quality pre-validator.

Runs before TrustEngine, adds quality warnings without blocking ingestion.
No LLM calls — pure rule-based checks for speed.
"""

from __future__ import annotations

from typing import Any


class ResultQualityWarning:
    __slots__ = ("code", "message", "severity")

    def __init__(self, code: str, message: str, severity: str = "info"):
        self.code = code
        self.message = message
        self.severity = severity  # "info" | "warning" | "error"

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


class ExecutionResultValidator:
    """Rule-based pre-validator for execution results."""

    def validate(
        self,
        *,
        parsed_output: dict[str, Any],
        success_criteria: dict[str, Any] | None,
        template_id: str | None,
        duration_ms: int | None,
    ) -> list[ResultQualityWarning]:
        warnings: list[ResultQualityWarning] = []

        # Rule 1: 空结果检测
        if not parsed_output or (
            len(parsed_output) == 1 and
            not str(parsed_output.get("text", "")).strip()
        ):
            warnings.append(ResultQualityWarning(
                "empty_result", "执行结果为空或仅包含空白内容", "warning",
            ))

        # Rule 2: 结果过短 (< 50字符 for text-based results)
        text_content = str(parsed_output.get("text", ""))
        if text_content and len(text_content.strip()) < 50 and template_id in (
            "web_research_brief", "document_digest"
        ):
            warnings.append(ResultQualityWarning(
                "result_too_short",
                f"结果文本仅{len(text_content.strip())}字符, 可能不够完整",
                "warning",
            ))

        # Rule 3: 缺少预期字段 (基于模板的result_contract)
        if success_criteria and "required_fields" in success_criteria:
            required = success_criteria["required_fields"]
            missing = [f for f in required if f not in parsed_output]
            if missing:
                warnings.append(ResultQualityWarning(
                    "missing_fields",
                    f"缺少预期字段: {', '.join(missing)}",
                    "warning",
                ))

        # Rule 4: 异常长执行时间 (> 5分钟)
        if duration_ms and duration_ms > 300_000:
            warnings.append(ResultQualityWarning(
                "long_execution",
                f"执行耗时{duration_ms // 1000}秒, 超过预期",
                "info",
            ))

        # Rule 5: 检测到错误关键词
        all_text = str(parsed_output).lower()
        error_keywords = ["error", "failed", "exception", "timeout", "denied", "forbidden"]
        found_errors = [kw for kw in error_keywords if kw in all_text]
        if found_errors and parsed_output.get("success", True):
            warnings.append(ResultQualityWarning(
                "contradictory_success",
                f"结果声称成功但包含错误关键词: {', '.join(found_errors)}",
                "warning",
            ))

        return warnings
```

### 集成到ExecutionIngestor

**修改文件**: `backend/app/services/execution_ingestor.py`

在 `__init__` 中添加:
```python
from app.services.execution_result_validator import ExecutionResultValidator
self._result_validator = ExecutionResultValidator()
```

在 `ingest()` 方法中, 在调用 `self._parser.parse()` 之后、`self._evaluate()` 之前, 添加:

```python
# Phase 5: 结果预验证
quality_warnings = self._result_validator.validate(
    parsed_output=parsed.get("parsed_output", {}),
    success_criteria=intent.success_criteria,
    template_id=(intent.policy or {}).get("template_id"),
    duration_ms=parsed.get("duration_ms"),
)
if quality_warnings:
    # 将warnings附加到parsed结果中, 供TrustEngine和前端使用
    parsed["quality_warnings"] = [w.to_dict() for w in quality_warnings]
```

---

## 任务 5.6: Flutter — 质量警告展示

**修改文件**: `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`

### 精确修改

在审批卡的指标区和操作区之间, 添加质量警告展示:

```dart
// 提取warnings
final warnings = record.rawResponse?['quality_warnings'] as List<dynamic>?;

// 在指标区后面添加
if (warnings != null && warnings.isNotEmpty) ...[
  const SizedBox(height: DS.spacing8),
  ...warnings.map((w) {
    final warning = w as Map<String, dynamic>;
    final severity = warning['severity'] as String? ?? 'info';
    final color = severity == 'error' ? DS.semanticError
        : severity == 'warning' ? DS.semanticWarning
        : DS.info;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing4),
      child: Row(
        children: [
          Icon(
            severity == 'error' ? Icons.error_rounded
                : severity == 'warning' ? Icons.warning_amber_rounded
                : Icons.info_outline_rounded,
            size: 14,
            color: color,
          ),
          const SizedBox(width: DS.spacing6),
          Expanded(
            child: Text(
              warning['message'] as String? ?? '',
              style: TextStyle(fontSize: 12, color: color),
            ),
          ),
        ],
      ),
    );
  }),
],
```

**注意**: 需要确认 `ExecutionRecordModel` 是否有 `rawResponse` 字段能访问quality_warnings。如果没有, 需要在model中添加 `qualityWarnings` 字段, 并在fromJson中从response中提取。

---

## 验收标准

### Flutter验收

```bash
cd mobile && flutter analyze --no-fatal-infos
```

### 后端验收

```bash
cd backend && python -m pytest tests/ -x -q
```

### 新增测试

在 `backend/tests/unit/` 创建 `test_result_validator.py`:

```python
"""Test ExecutionResultValidator rule-based checks."""

from app.services.execution_result_validator import ExecutionResultValidator

validator = ExecutionResultValidator()


def test_empty_result_warns():
    warnings = validator.validate(
        parsed_output={"text": ""},
        success_criteria=None,
        template_id="web_research_brief",
        duration_ms=5000,
    )
    assert any(w.code == "empty_result" for w in warnings)


def test_short_result_warns_for_research():
    warnings = validator.validate(
        parsed_output={"text": "Found some stuff."},
        success_criteria=None,
        template_id="web_research_brief",
        duration_ms=5000,
    )
    assert any(w.code == "result_too_short" for w in warnings)


def test_short_result_no_warn_for_shell():
    warnings = validator.validate(
        parsed_output={"text": "OK"},
        success_criteria=None,
        template_id="shell_diagnostics",
        duration_ms=5000,
    )
    assert not any(w.code == "result_too_short" for w in warnings)


def test_missing_fields_warns():
    warnings = validator.validate(
        parsed_output={"text": "hello"},
        success_criteria={"required_fields": ["summary", "sources"]},
        template_id=None,
        duration_ms=5000,
    )
    assert any(w.code == "missing_fields" for w in warnings)


def test_contradictory_success_warns():
    warnings = validator.validate(
        parsed_output={"text": "Error: connection timeout", "success": True},
        success_criteria=None,
        template_id=None,
        duration_ms=5000,
    )
    assert any(w.code == "contradictory_success" for w in warnings)


def test_clean_result_no_warnings():
    warnings = validator.validate(
        parsed_output={
            "summary": "A comprehensive analysis of the topic...",
            "findings": ["Point 1", "Point 2", "Point 3"],
            "sources": [{"url": "https://example.com", "title": "Source"}],
            "text": "A comprehensive analysis of the topic with detailed findings across multiple dimensions.",
        },
        success_criteria={"required_fields": ["summary", "findings"]},
        template_id="web_research_brief",
        duration_ms=15000,
    )
    assert len(warnings) == 0
```

### 功能验收 (人工)

1. [ ] 审批卡中的parsedOutput以格式化方式展示(markdown/结构化/代码块), 而非raw JSON
2. [ ] 链接类结果显示为可点击的域名列表
3. [ ] 聊天流中的内联结果同样使用格式化渲染
4. [ ] Artifact预览: 图片显示缩略图, 其他文件显示图标+文件名
5. [ ] 质量警告: 短结果/缺字段/矛盾成功状态时显示黄色/红色警告行
6. [ ] 分类缓存: 同一任务5分钟内第二次classify不触发新的路由计算
7. [ ] 模板prompt: 每个模板都有optimized_prompt, 并在dispatch时注入
