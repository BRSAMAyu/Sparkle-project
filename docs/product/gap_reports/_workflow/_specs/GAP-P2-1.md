# GAP-P2-1: Source Tray 一等 UI 组件 — Implementation Spec

> **Mode**: spec->you | **Level**: L3 | **Effort**: XL (15-18 days)
> **Source**: 07 号报告 — Source Tray UI & Context Receipt Gap Analysis
> **Status**: Spec ready for user implementation

---

## 1. 目标 (Objectives)

将 Sparkle 后端已完成的 Source Tray 基础设施完整暴露到 Flutter 移动端，实现 SRC-009~012 四个需求的全部 UI。

### 核心目标
1. 将后端 `SourceTrayState` 通过新 API 端点提供给 Flutter，并用 Riverpod 状态管理层驱动 UI
2. 重建 Source Tray 组件：推荐状态、相关性评分、scope 排除、生命周期状态
3. 解析 `build_source_receipt()` 输出，在 `ContextReceiptBar` 和 `AuroraReceiptChip` 中展示完整回执
4. 集成 `EvidencePack` proto，在回执详情页展示证据片段
5. 实现素材排除流程：scope 选择器 + 原因选择器 + 后端同步

---

## 2. 现状评估 (Current State Assessment)

### 后端：全部完成

| 能力 | 文件 | 状态 |
|------|------|------|
| SourceAsset / SourceTraySelection / SourceTrayState 数据类 | `backend/app/signals/types.py` L919-1067 | 完整 |
| RetrievalDirective 数据类 | `backend/app/signals/types.py` L557-594 | 完整 |
| compute_retrieval_plan() | `backend/app/signals/source_tray_integration.py` L23-165 | 完整 |
| build_source_receipt() | `backend/app/signals/source_tray_integration.py` L168-226 | 完整 |
| validate_source_tray_selections() | `backend/app/signals/source_tray_integration.py` L229-250 | 完整 |
| SourceEffectivenessTracker (Redis-backed) | `backend/app/signals/source_tray_integration.py` L326-468 | 完整 |
| EvidencePack / EvidenceNode proto | `proto/sparkle/rag/v1/evidence.proto` | 完整 |
| EvidencePack Dart 生成代码 | `mobile/lib/gen/sparkle/rag/v1/evidence.pb.dart` | 完整 |
| 现有 sources.py API | `backend/app/api/v1/sources.py` | lifecycle 操作存在，无 tray/receipt 端点 |

### Flutter：部分实现，关键缺口

| 能力 | 文件 | 状态 |
|------|------|------|
| StudyMaterialsSheet (基础文档列表 + 本地 toggle) | `study_materials_sheet.dart` | 浅层实现，无 SourceTrayState 集成 |
| ContextReceiptBar (legacy context_receipt 格式) | `context_receipt_bar.dart` | 存在但未消费 build_source_receipt() |
| AuroraReceiptChip (memory/social/context 回执) | `aurora_receipt_chip.dart` | 存在，但 source 类型无 EvidencePack |
| EvidenceDrawer | `evidence_drawer.dart` | 存在但未集成 |
| SourceTrayState (Riverpod 状态管理) | 无 | 缺失 |
| SourceReceipt 模型 | 无 | 缺失 |
| SourceTrayWidget (推荐/scope/排除 UI) | 无 | 缺失 |
| EvidenceViewerSheet | 无 | 缺失 |
| Material 排除流程 (scope + reason picker) | 无 | 缺失 |

### 实际缺口

| # | 缺口 | 严重程度 | 描述 |
|---|------|---------|------|
| G1 | **无 SourceTrayState 数据通道** | 高 🔴 | 后端有完整数据，Flutter 无 API 端点或 provider 获取 |
| G2 | **StudyMaterialsSheet 未对接后端 SourceTrayState** | 高 🔴 | 使用本地 `_toggledOff` Set，不同步到后端 |
| G3 | **build_source_receipt() 输出未被消费** | 高 🔴 | Flutter 只解析 legacy `context_receipt` 格式 |
| G4 | **无 EvidencePack 集成** | 中 🟡 | EvidencePack Dart 代码已生成，但无 UI 消费 |
| G5 | **无 scope-based 排除流程** | 中 🟡 | 没有 this_turn/this_task/today/this_goal scope 选择器 |
| G6 | **无 SourceEffectivenessTracker Flutter 集成** | 中 🟡 | 用户纠正素材后无法同步到后端 Redis tracker |

---

## 3. 文件清单 (File Inventory)

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/app/api/v1/source_tray.py` | SourceTrayState 获取、selection 同步、素材排除、effectiveness 查询 API 端点 |
| `mobile/lib/features/chat/data/models/source_tray_models.dart` | SourceReceipt、SourceTrayState、SourceTraySelection、SourceAsset 等 Flutter 数据模型 |
| `mobile/lib/features/chat/data/repositories/source_tray_repository.dart` | Source tray API 调用封装 |
| `mobile/lib/features/chat/presentation/providers/source_tray_provider.dart` | SourceTrayNotifier (Riverpod StateNotifier) |
| `mobile/lib/features/chat/presentation/widgets/source_tray_widget.dart` | 完整 Source Tray UI：推荐徽章、相关性分数、scope 排除 toggle |
| `mobile/lib/features/chat/presentation/widgets/source_tray_row.dart` | Source Tray 单行组件：图标、标题、推荐状态、排除控件 |
| `mobile/lib/features/chat/presentation/widgets/source_receipt_detail_sheet.dart` | 完整 Context Receipt 详情页：loaded/skipped/excluded 列表 |
| `mobile/lib/features/chat/presentation/widgets/evidence_viewer_sheet.dart` | EvidencePack 片段查看 sheet |
| `mobile/lib/features/chat/presentation/widgets/exclusion_scope_picker.dart` | Scope 选择器 bottom sheet（Turn/Task/Today/Goal）+ 原因选择 |
| `mobile/test/features/chat/presentation/widgets/source_tray_widget_test.dart` | SourceTrayWidget widget test |
| `mobile/test/features/chat/presentation/providers/source_tray_provider_test.dart` | SourceTrayNotifier unit test |
| `mobile/test/features/chat/data/models/source_tray_models_test.dart` | 数据模型序列化/反序列化测试 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/api/v1/router.py` | 注册 source_tray router |
| `backend/app/api/v1/sources.py` | 添加 `GET /sources/tray`、`POST /sources/{id}/exclude`、`POST /sources/{id}/selection`、`GET /sources/effectiveness` 端点，或委托到新 source_tray.py |
| `mobile/lib/core/network/api_endpoints.dart` | 添加 sourceTray、sourceExclude、sourceSelection、sourceEffectiveness 路由常量 |
| `mobile/lib/features/chat/presentation/widgets/study_materials_sheet.dart` | 重构：从本地 `_toggledOff` 切换到 SourceTrayState provider + scope-based 排除 |
| `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart` | 解析 `source_receipt` metadata key (build_source_receipt 输出)；展示 loadedCount/skippedCount/excludedCount；传递 SourceReceipt 给详情页 |
| `mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart` | 在 source receipt 详情页中添加 "查看证据" 入口，消费 EvidencePack |
| `mobile/lib/features/chat/presentation/providers/chat_state.dart` | `DocumentContextMode` 枚举已存在，无需 schema 变更，但需确认 enum 值映射到 SourceTrayState.mode |
| `mobile/lib/l10n/app_en.arb` | 新增 30+ i18n key：source tray 标签、exclusion 流程、receipt 详情、evidence viewer |
| `mobile/lib/l10n/app_zh.arb` | 同上，中文翻译 |

---

## 4. 实现步骤 (Implementation Steps)

### Phase 1: Backend API Endpoints (1-2 days)

**Step 1.1**: 创建 `backend/app/api/v1/source_tray.py`

添加以下端点：

```python
# GET /sources/tray — 获取当前用户的 SourceTrayState
@router.get("/tray")
async def get_source_tray(
    user_id: UUID = Depends(...),
    target_nodes: list[str] | None = None,
    ...
) -> dict:  # SourceTrayState.to_dict()

# POST /sources/{source_id}/selection — 更新单个素材的 include/exclude/auto
@router.post("/{source_id}/selection")
async def set_source_selection(
    source_id: UUID,
    action: str,   # include / exclude / auto
    scope: str,    # this_turn / this_task / today / this_goal
    ...
) -> dict:

# POST /sources/{source_id}/exclude — 排除素材并记录纠正
@router.post("/{source_id}/exclude")
async def exclude_source(
    source_id: UUID,
    scope: str,
    reason: str,
    ...
) -> dict:  # 调用 SourceEffectivenessTracker.record_user_correction()

# GET /sources/effectiveness — 获取素材有效性统计
@router.get("/effectiveness")
async def get_source_effectiveness(
    user_id: UUID = Depends(...),
    source_id: UUID | None = None,
    ...
) -> dict:
```

**Step 1.2**: 在 `backend/app/api/v1/sources.py` 或 `backend/app/api/v1/router.py` 中注册新路由

在 `sources.py` 末尾添加导入和 router.include_router：
```python
from app.api.v1.source_tray import router as source_tray_router
router.include_router(source_tray_router)
```

**Step 1.3**: 验证 API 端点

```bash
# 测试 SourceTrayState 获取
curl -H "Authorization: Bearer $TOKEN" "$BASE/sources/tray?user_id=..."

# 测试 selection 更新
curl -X POST "$BASE/sources/{id}/selection" -d '{"action":"exclude","scope":"this_task"}'

# 测试素材排除
curl -X POST "$BASE/sources/{id}/exclude" -d '{"scope":"today","reason":"wrong_content"}'
```

### Phase 2: Flutter 数据模型与 Repository (1 day)

**Step 2.1**: 创建 `mobile/lib/features/chat/data/models/source_tray_models.dart`

所有数据模型均为纯 Dart 类（非 protobuf），使用 JSON 序列化，与后端 `to_dict()` / `from_dict()` 对齐：

```dart
class SourceSliceModel {
  final String sliceId;
  final String sourceId;
  final String location;
  final String summary;
  final List<String> concepts;
  final List<String> knowledgeNodes;
  final String evidenceType;  // definition_and_example / definition / worked_example / exercise / explanation
  final String noiseRisk;     // low / medium / high

  factory SourceSliceModel.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}

class SourceAssetModel {
  final String sourceId;
  final String title;
  final String sourceType;      // slides / textbook / notes / exam_paper / homework
  final String lifecycleStatus; // active / archived / revoked / orphaned
  final String parsedStatus;    // pending / parsed / failed
  final double qualityScore;    // 0.0 - 1.0
  final List<String>? mappedNodes;
  final List<SourceSliceModel>? slices;
  final List<String>? recommendedUses;
  final List<String>? notRecommendedUses;

  /// Computed: relevance for given target nodes
  double relevanceForNodes(List<String> targetNodes);

  /// Whether the source applies to the current task context
  bool get isRecommended => (recommendedUses ?? []).contains('current_task_rag');
  bool get isNotRecommended => (notRecommendedUses ?? []).contains('current_task_rag');
  String get recommendationStatus => isRecommended ? 'recommended' : (isNotRecommended ? 'not_recommended' : 'auto');

  factory SourceAssetModel.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}

class SourceTraySelectionModel {
  final String sourceId;
  final String action;           // include / exclude / auto
  final String scope;            // this_turn / this_task / today / this_goal
  final bool userInitiated;

  factory SourceTraySelectionModel.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}

class SourceTrayStateModel {
  final String mode;             // auto / manual_only / no_materials
  final List<SourceTraySelectionModel> selections;
  final List<SourceAssetModel> availableSources;

  List<String> get includedSourceIds;
  List<String> get excludedSourceIds;

  factory SourceTrayStateModel.fromJson(Map<String, dynamic> json);
  Map<String, dynamic> toJson();
}

/// Parsed from build_source_receipt() output in message metadata
class SourceReceiptModel {
  final List<_LoadedSource> loaded;
  final List<_SkippedSource> skipped;
  final List<_ExcludedSource> excluded;
  final String answerBasis;      // source_grounded / general_reasoning
  final String sourceUncertainty;
  final bool canCorrectSources;
  final String reasonForUser;
  final String correctionHint;

  factory SourceReceiptModel.fromJson(Map<String, dynamic> json);
}

class _LoadedSource { final String sourceId; final String title; final String reason; }
class _SkippedSource { final String sourceId; final String title; final String reason; }
class _ExcludedSource { final String sourceId; final String title; final String reason; }

/// Wraps EvidencePack proto with convenience accessors
class EvidencePackModel {
  final String requestId;
  final String traceId;
  final List<EvidenceNodeModel> nodes;
  final Map<String, String> metadata;

  factory EvidencePackModel.fromProto(EvidencePack pack);
  factory EvidencePackModel.fromJson(Map<String, dynamic> json);
}

class EvidenceNodeModel {
  final String nodeId;
  final String sourceId;
  final String snippet;
  final double score;
  final String sourceUri;
  final Map<String, String> metadata;
  final String sourceType;

  factory EvidenceNodeModel.fromProto(EvidenceNode node);
  factory EvidenceNodeModel.fromJson(Map<String, dynamic> json);
}
```

**Step 2.2**: 创建 `mobile/lib/features/chat/data/repositories/source_tray_repository.dart`

```dart
final sourceTrayRepositoryProvider = Provider<SourceTrayRepository>((ref) {
  return SourceTrayRepository(ref.watch(apiClientProvider).dio);
});

class SourceTrayRepository {
  final Dio _dio;

  /// Fetch current SourceTrayState from backend
  Future<SourceTrayStateModel> getSourceTray({List<String>? targetNodes});

  /// Update a single source selection (include/exclude/auto)
  Future<SourceTraySelectionModel> setSelection({
    required String sourceId,
    required String action,
    required String scope,
  });

  /// Exclude a source with reason, triggers SourceEffectivenessTracker
  Future<Map<String, dynamic>> excludeSource({
    required String sourceId,
    required String scope,
    required String reason,
  });

  /// Get source effectiveness stats
  Future<List<Map<String, dynamic>>> getEffectiveness({String? sourceId});
}
```

### Phase 3: Riverpod 状态管理 (1 day)

**Step 3.1**: 创建 `mobile/lib/features/chat/presentation/providers/source_tray_provider.dart`

```dart
class SourceTrayState {
  const SourceTrayState({
    this.tray = const AsyncValue.loading(),
    this.targetNodes = const [],
  });
  final AsyncValue<SourceTrayStateModel> tray;
  final List<String> targetNodes;

  SourceTrayState copyWith({...});
}

class SourceTrayNotifier extends StateNotifier<SourceTrayState> {
  SourceTrayNotifier(this._repository) : super(const SourceTrayState()) {
    loadSourceTray();
  }

  final SourceTrayRepository _repository;

  /// Fetch full SourceTrayState from backend
  Future<void> loadSourceTray({List<String>? targetNodes});

  /// Toggle include/exclude/auto for a source with given scope
  Future<void> toggleSource({
    required String sourceId,
    required String action,
    required String scope,
  });

  /// Exclude source with reason (opens flow: scope picker -> reason picker -> submit)
  Future<void> excludeSource({
    required String sourceId,
    required String scope,
    required String reason,
  });

  /// Refresh after chat response received
  Future<void> refresh();

  /// Optimistic update helper
  void _applyOptimisticSelection({...});
}

final sourceTrayProvider = StateNotifierProvider<SourceTrayNotifier, SourceTrayState>(
  (ref) => SourceTrayNotifier(ref.watch(sourceTrayRepositoryProvider)),
);
```

### Phase 4: 重建 Source Tray UI (3-4 days)

**Step 4.1**: 创建 `mobile/lib/features/chat/presentation/widgets/source_tray_row.dart`

单行 Source 组件，展示：
- 材料类型图标（slides/textbook/notes/exam_paper/homework，映射到 Icons）
- 标题 + source_type 标签
- 推荐状态徽章（绿色 "推荐" / 橙色 "不推荐" / 灰色 "自动"）
- 相关性分数条（0.0-1.0 可视化进度条，颜色从灰到绿）
- 生命周期状态指示器（archived/revoked 显示灰色警告图标）
- 解析状态指示器（failed 显示红色警告图标）
- Include/Exclude toggle（仅在 manual_only 模式下可切换）
- Scope 标签（this_turn/this_task/today/this_goal 显示当前排除 scope）

**Step 4.2**: 创建 `mobile/lib/features/chat/presentation/widgets/source_tray_widget.dart`

完整 Source Tray 容器：
- 模式选择器：Auto / User-Selected / Task / Off（映射到 SourceTrayState.mode）
- 推荐状态图例和模式说明
- 按相关性排序的 SourceTrayRow 列表（`ListView.builder` + `shrinkWrap`）
- 空状态："暂无可用资料" / "No materials available"
- 加载状态：骨架屏
- 错误状态：错误信息 + 重试按钮
- 从 `sourceTrayProvider` 消费状态
- 切换 mode 时调用 `chatProvider.setDocumentContextMode()`

**Step 4.3**: 重构 `mobile/lib/features/chat/presentation/widgets/study_materials_sheet.dart`

- 移除本地 `_toggledOff` Set 状态
- 改为从 `sourceTrayProvider` 读取 `SourceTrayState`
- 将 `DocumentLibraryItem` 列表替换为 `SourceAssetModel` 列表
- 对于每个 source，根据 `SourceTraySelectionModel` 决定是否 enabled
- 点击 toggle 时调用 `sourceTrayProvider.toggleSource()`
- 保留现有的 modal sheet 结构和 `_copy(zh:, en:)` i18n 模式

### Phase 5: 完整 Context Receipt 展示 (2-3 days)

**Step 5.1**: 更新 `mobile/lib/features/chat/presentation/widgets/context_receipt_bar.dart`

在 `_parseReceipts()` 中添加 `source_receipt` metadata key 解析：

```dart
// 新增：解析 build_source_receipt() 输出
_addReceipt(
  receipts,
  _withType(
    _parseSourceReceipt(metadata['source_receipt']),
    kSourceContextReceiptType,
    sourceKey: 'source_receipt',
    sourceKind: 'materials',
  ),
);

Map<String, dynamic>? _parseSourceReceipt(dynamic raw) {
  final decoded = _decode(raw);
  if (decoded is! Map) return null;
  final map = Map<String, dynamic>.from(decoded);
  final loaded = (map['loaded'] as List<dynamic>?) ?? [];
  final skipped = (map['skipped'] as List<dynamic>?) ?? [];
  final excluded = (map['excluded'] as List<dynamic>?) ?? [];
  return {
    'receipt_type': kSourceContextReceiptType,
    'source_kind': 'materials',
    'source_key': 'source_receipt',
    'summary': map['reason_for_user'] ?? '',
    'decision_reason': map['reason_for_user'],
    'used_names': loaded.map((e) => (e as Map)['title']?.toString() ?? '').toList(),
    'used_count': loaded.length,
    'excluded_names': excluded.map((e) => (e as Map)['title']?.toString() ?? '').toList(),
    'answer_basis': map['answer_basis'],
    'source_uncertainty': map['source_uncertainty'],
    'can_correct_sources': map['can_correct_sources'] ?? false,
    'correction_hint': map['correction_hint'],
    'full_receipt': map,  // 保存完整 receipt 供详情页使用
  };
}
```

**Step 5.2**: 创建 `mobile/lib/features/chat/presentation/widgets/source_receipt_detail_sheet.dart`

完整回执详情页：
- Loaded 区域（绿色 check_circle）：列出已加载素材 + 原因（user_selected / directive_selected / auto_selected）
- Excluded 区域（红色 cancel）：列出已排除素材 + 原因（user_excluded / directive_excluded）
- Skipped 区域（灰色 skip_next）：列出跳过的素材 + 原因（parse_failed / lifecycle_*/ not_loaded）
- Answer basis 指示器（source_grounded 或 general_reasoning 图标 + 说明）
- Source uncertainty 指示器
- Correction hint 提示文本
- 如果 `can_correct_sources == true`，显示 "标记此素材不相关" 按钮
- "查看决策链路" 链接（复用现有 `CausalTimelinePanel`）
- i18n: `isChinese ? '中文' : 'English'`

**Step 5.3**: 更新 `mobile/lib/features/chat/presentation/widgets/aurora_receipt_chip.dart`

在 `_AuroraReceiptDetailSheet` 的 source receipt 详情区域（现有 `usedNames`/`excludedNames` 显示之后）：
- 如果 receipt 包含 `full_receipt`，添加 "查看完整回执" 按钮
- 如果 receipt 的 metadata 中包含 `evidence_pack`，添加 "查看证据" 按钮
- 点击 "查看完整回执" 打开 `SourceReceiptDetailSheet`
- 点击 "查看证据" 打开 `EvidenceViewerSheet`

### Phase 6: Evidence Viewing (2 days)

**Step 6.1**: 创建 `mobile/lib/features/chat/presentation/widgets/evidence_viewer_sheet.dart`

```dart
class EvidenceViewerSheet extends StatelessWidget {
  const EvidenceViewerSheet({
    required this.evidencePack,  // EvidencePackModel
    super.key,
  });

  // Modal bottom sheet 入口
  static Future<void> show(BuildContext context, {required EvidencePackModel pack});
}
```

功能：
- 证据片段列表 (EvidenceNode)
- 每项显示：snippet 文本（带引号样式）、score（百分比或星级）、source_type 标签
- 长按 snippet 显示完整文本（如果被截断）
- source_uri 链接（可点击打开外部 URL）
- metadata 键值对折叠显示
- 空状态："暂无证据片段" / "No evidence snippets"
- i18n 双语覆盖

**Step 6.2**: 在 `aurora_receipt_chip.dart` 中集成 EvidencePack

在 `_AuroraReceiptDetailSheet.build()` 中，source receipt 详情区域添加：

```dart
// 在 usedNames/excludedNames 区域之后
if (_isSource && !isSocialSource) ...[
  // 现有：查看决策链路
  // 新增：查看证据
  if (_hasEvidencePack(receipt)) ...[
    const SizedBox(height: 12),
    _EvidenceLink(
      evidencePackRaw: receipt['evidence_pack'],
      responseId: receipt['response_id']?.toString(),
    ),
  ],
],
```

**Step 6.3**: 解析 EvidencePack 从 metadata

在 `aurora_receipt_chip.dart` 或 `context_receipt_bar.dart` 中添加：

```dart
EvidencePackModel? _parseEvidencePack(dynamic raw) {
  if (raw is Map) {
    return EvidencePackModel.fromJson(Map<String, dynamic>.from(raw));
  }
  if (raw is String) {
    try {
      final json = jsonDecode(raw);
      return EvidencePackModel.fromJson(json);
    } catch (_) {}
  }
  return null;
}
```

### Phase 7: 素材排除流程 (2 days)

**Step 7.1**: 创建 `mobile/lib/features/chat/presentation/widgets/exclusion_scope_picker.dart`

两步 bottom sheet 流程：

**第 1 步：Scope 选择器**
```dart
class ExclusionScopePicker extends StatelessWidget {
  // 选项：
  // - this_turn: 仅本轮对话 (默认)
  // - this_task: 当前任务期间
  // - today: 今天
  // - this_goal: 当前目标期间
}
```
- Radio list 或 chip 选择
- 每个选项有图标和中文/英文标签
- 默认选中 "仅本轮"
- "下一步" 按钮

**第 2 步：原因选择器**
```dart
class ExclusionReasonPicker extends StatelessWidget {
  // 预设原因：
  // - wrong_content: 内容不对
  // - outdated: 内容过时
  // - off_topic: 与当前话题无关
  // - custom: 自定义原因 (text field)
}
```
- Chip 选择 + 自定义输入框
- "确认排除" 按钮
- 提交后调用 `sourceTrayProvider.excludeSource()`

**Step 7.2**: 在 `SourceTrayRow` 中集成排除入口

长按 source row 或点击更多菜单显示选项：
- "排除此资料..." -> 打开 `ExclusionScopePicker`
- 排除后，row 显示为灰色 + 已排除 scope 标签

**Step 7.3**: 在 `SourceReceiptDetailSheet` 中集成纠正入口

在 loaded sources 列表中的每个 loaded source：
- "标记为不相关" 按钮 -> 快捷排除流程（scope 默认 this_turn，原因默认 wrong_content）

### Phase 8: i18n 更新 (0.5 day)

**Step 8.1**: 在 `app_en.arb` 和 `app_zh.arb` 中添加新 key

需要添加的 key 类型：
- Source tray 标签：`chatSourceTrayRecommendBadge`, `chatSourceTrayNotRecommendBadge`, `chatSourceTrayAutoBadge`
- Scope 选择器：`chatExclusionScopeThisTurn`, `chatExclusionScopeThisTask`, `chatExclusionScopeToday`, `chatExclusionScopeThisGoal`
- 原因选择器：`chatExclusionReasonWrongContent`, `chatExclusionReasonOutdated`, `chatExclusionReasonOffTopic`, `chatExclusionReasonCustom`
- Receipt 详情：`chatReceiptLoadedSection`, `chatReceiptExcludedSection`, `chatReceiptSkippedSection`, `chatReceiptAnswerBasis`, `chatReceiptSourceGrounded`, `chatReceiptGeneralReasoning`, `chatReceiptCanCorrectHint`
- Evidence viewer：`chatEvidenceViewerTitle`, `chatEvidenceViewerEmptyHint`, `chatEvidenceViewerScoreLabel`, `chatEvidenceViewerSourceTypeLabel`
- 通用：`chatSourceTrayEmptyHint`, `chatSourceTrayLifecycleArchived`, `chatSourceTrayLifecycleRevoked`, `chatSourceTrayParseFailed`
- 排除确认：`chatExclusionConfirmTitle`, `chatExclusionSuccessMessage`
- 共计约 30-35 个新 key

---

## 5. 测试计划 (Test Plan)

### Backend API Tests (5 tests)

| Test | 描述 |
|------|------|
| `test_get_source_tray_returns_state` | GET /sources/tray 返回正确的 SourceTrayState 结构 |
| `test_set_selection_updates_tray` | POST /sources/{id}/selection 更新后 GET /sources/tray 反映变更 |
| `test_exclude_source_records_correction` | POST /sources/{id}/exclude 调用 SourceEffectivenessTracker.record_user_correction() |
| `test_get_effectiveness_returns_stats` | GET /sources/effectiveness 返回 Redis 中的有效性数据 |
| `test_validate_stale_selections_removed` | 已删除的 source 的 include selection 被自动清除 |

### Flutter Unit Tests — 数据模型 (8 tests)

| Test | 描述 |
|------|------|
| `test_source_asset_from_json` | SourceAssetModel.fromJson() 正确解析所有字段 |
| `test_source_tray_state_from_json` | SourceTrayStateModel.fromJson() 递归解析 selections + available_sources |
| `test_source_receipt_from_json` | SourceReceiptModel.fromJson() 解析 build_source_receipt() 输出 |
| `test_evidence_pack_from_json` | EvidencePackModel.fromJson() 解析 evidence_pack metadata |
| `test_source_asset_relevance_for_nodes` | relevanceForNodes() 正确计算重叠率 |
| `test_source_tray_included_ids` | includedSourceIds getter 正确过滤 include action |
| `test_source_tray_excluded_ids` | excludedSourceIds getter 正确过滤 exclude action |
| `test_source_asset_recommendation_status` | recommendationStatus 正确返回 recommended/not_recommended/auto |

### Flutter Unit Tests — Provider (8 tests)

| Test | 描述 |
|------|------|
| `test_source_tray_notifier_loads_initial_state` | Notifier 创建后自动加载 SourceTrayState |
| `test_toggle_source_optimistic_update` | toggleSource() 立即更新本地状态，无需等待网络 |
| `test_toggle_source_syncs_to_backend` | toggleSource() 调用 repository.setSelection() |
| `test_exclude_source_calls_repository` | excludeSource() 调用 repository.excludeSource() |
| `test_refresh_reloads_from_backend` | refresh() 重新 fetch SourceTrayState |
| `test_set_target_nodes_updates_relevance` | 更新 targetNodes 后 relevance 重新计算 |
| `test_loading_state` | 初始状态 correct loading indicator |
| `test_error_state` | 网络错误时 state 正确标记 error |

### Flutter Widget Tests (10 tests)

| Test | 描述 |
|------|------|
| `test_source_tray_widget_renders_sources` | SourceTrayWidget 正确渲染 SourceAsset 列表 |
| `test_source_tray_recommendation_badge` | 推荐状态徽章正确显示 |
| `test_source_tray_relevance_bar` | 相关性分数进度条正确渲染 |
| `test_source_tray_lifecycle_indicator` | archived/revoked 状态显示警告图标 |
| `test_source_tray_empty_state` | 无可用资料时显示空状态 |
| `test_source_tray_toggle_dispatches` | 点击 toggle 调用 provider.toggleSource() |
| `test_source_receipt_detail_renders_sections` | SourceReceiptDetailSheet 正确渲染 loaded/excluded/skipped |
| `test_evidence_viewer_renders_nodes` | EvidenceViewerSheet 显示 EvidenceNode 列表 |
| `test_exclusion_scope_picker_renders_options` | Scope 选择器显示 4 个 scope 选项 |
| `test_exclusion_flow_end_to_end_widget` | 完整排除流程：长按 source -> scope 选择 -> 原因选择 -> 确认 |

### Integration Tests (3 tests)

| Test | 描述 |
|------|------|
| `test_full_source_tray_flow` | 加载 SourceTray -> 切换 mode -> toggle include/exclude -> sync to backend |
| `test_full_exclusion_flow` | 选择 source -> 选 scope -> 选 reason -> 排除 -> source 在列表中变灰 -> tracker 记录 |
| `test_receipt_to_evidence_flow` | 聊天返回 source_receipt + evidence_pack -> ContextReceiptBar 显示 -> 点击查看回执 -> 点击查看证据 -> EvidenceViewerSheet 显示片段 |

---

## 6. 验收标准 (Acceptance Criteria)

### Functional: Source Tray (SRC-009)
- [ ] `GET /sources/tray` 返回完整的 SourceTrayState（含 available_sources 和 selections）
- [ ] Flutter `SourceTrayWidget` 显示所有 available_sources，按 relevance 降序排列
- [ ] 每个 source 显示推荐状态（recommended/not_recommended/auto）+ 相关性分数
- [ ] 每个 source 显示生命周期状态和解析状态
- [ ] 用户可在 manual_only 模式下切换 include/exclude
- [ ] Mode 选择器（Auto / User-Selected / Task / Off）正确映射到 SourceTrayState.mode
- [ ] Selection 变更通过 `POST /sources/{id}/selection` 同步到后端

### Functional: Context Receipt (SRC-010)
- [ ] `build_source_receipt()` 输出通过 `source_receipt` metadata key 传递到 Flutter
- [ ] `ContextReceiptBar` 显示 loadedCount / skippedCount / excludedCount
- [ ] `SourceReceiptDetailSheet` 列出 loaded（含 reason）、skipped（含 reason）、excluded（含 reason）
- [ ] 显示 answer_basis（source_grounded 或 general_reasoning）
- [ ] 显示 source_uncertainty
- [ ] 显示 can_correct_sources 标志 + correction_hint
- [ ] "标记此素材不相关" 按钮调用排除流程

### Functional: Evidence Viewing (SRC-011)
- [ ] `EvidencePack` 从 metadata['evidence_pack'] 解析
- [ ] `AuroraReceiptChip` 详情页显示 "查看证据" 按钮（当 evidence_pack 存在时）
- [ ] `EvidenceViewerSheet` 显示 EvidenceNode 列表
- [ ] 每个节点显示 snippet 文本、score、source_type 标签
- [ ] source_uri 可点击

### Functional: Material Exclusion (SRC-012)
- [ ] `ExclusionScopePicker` 显示 4 个 scope（this_turn/this_task/today/this_goal）
- [ ] `ExclusionReasonPicker` 显示 3 个预设原因 + 自定义输入
- [ ] 排除提交调用 `POST /sources/{id}/exclude`
- [ ] 后端调用 `SourceEffectivenessTracker.record_user_correction()`
- [ ] 排除成功后 source 在列表中变灰 + 显示 scope 标签

### Non-Functional
- [ ] SourceTrayState 加载 < 500ms (局域网)
- [ ] Selection 同步延迟 < 200ms
- [ ] EvidenceViewerSheet 打开 < 100ms
- [ ] 无内存泄漏（所有 Riverpod provider 正确 dispose）
- [ ] 所有 `_copy(zh:, en:)` i18n 正确覆盖新增文本

### Quality Gates
- [ ] 所有 backend API tests 通过
- [ ] 所有 Flutter unit + widget + integration tests 通过
- [ ] `flutter analyze` 无新增 warning
- [ ] 现有 StudyMaterialsSheet 功能无回归（向后兼容）
- [ ] 现有 ContextReceiptBar 功能无回归（legacy receipt format 仍工作）
- [ ] 现有 AuroraReceiptChip 功能无回归
- [ ] 无硬编码 secrets/tokens/URLs
- [ ] i18n 双语覆盖所有新增 UI 文本
- [ ] API 端点有正确的 auth 依赖

---

## 7. 设计决策 (Design Decisions)

| 决策 | 选择 | 理由 |
|------|------|------|
| SourceTrayState 传输格式 | JSON（非 protobuf） | 后端已经有成熟的 to_dict()/from_dict()；Dart 的 fromJson 更轻量；不需要 proto 编译 |
| EvidencePack 传输格式 | JSON from metadata 或 proto 解码均可 | generated Dart EvidencePack 已存在且 fromJson 可用；metadata 中是 JSON 方便直接解析 |
| Selection sync 策略 | 乐观更新 + 后台同步 | 与现有 ChatState copyWith 模式一致；避免 UI 卡顿 |
| Scope 选择器 UI | Bottom sheet 两步流程（scope -> reason） | 减少单页信息密度；scope 选择先于 reason 更自然 |
| SourceReceipt 展示 | 在 SourceReceiptDetailSheet（新 widget）而非扩展现有 aurora_receipt_chip | AuroraReceiptChip 详情页已较复杂（memory/social/source 三合一）；receipt 详情有独立信息架构 |
| StudyMaterialsSheet 重构 | 渐进式：保留现有 widget 签名，内部切换到 SourceTrayState provider | 不破坏现有调用方（chat screen 已有 widget 实例化）；向后兼容 |
| 后端 API | 新建 source_tray.py 而非扩展 sources.py | sources.py 已负责 lifecycle 操作；职责分离 |
| 与 DocumentLibraryItem 关系 | SourceAssetModel 是独立数据流（来自 SourceTrayState），不与 DocumentLibraryItem 互转 | 两条数据流服务于不同目的（tray selection vs. library management） |
| Mode 枚举映射 | DocumentContextMode.userSelected -> mode "manual_only"; DocumentContextMode.auto -> mode "auto" | 与后端 SourceTrayState.mode 枚举对齐 |

---

## 8. 依赖与阻塞 (Dependencies)

- Phase 2 (Flutter models) 依赖 Phase 1（backend API 端点 schema 稳定）
- Phase 4 (Source Tray UI) 依赖 Phase 3 (Riverpod provider)
- Phase 5 (Context Receipt) 依赖 Phase 2 (SourceReceiptModel) 和 chat message metadata 包含 `source_receipt` key
- Phase 6 (Evidence Viewer) 依赖 chat message metadata 包含 `evidence_pack` key
- Phase 7 (Exclusion Flow) 依赖 Phase 1（exclude endpoint）和 Phase 3（sourceTrayProvider）
- Phase 8 (i18n) 可与 Phase 4-7 并行
- 无外部依赖阻塞（所有依赖均为项目内部）

关键：Python backend 需要在 chat response 的 metadata 中包含 `source_receipt` 和 `evidence_pack` 两个 key。如果当前 chat pipeline 尚未注入这两个 key，需要先确认或修改 orchestrator/composer 代码——这是一个前置条件。

---

## 9. 开放问题 (Open Questions)

1. **Chat metadata 注入点**：当前 `build_source_receipt()` 和 `EvidencePack` 是否已经被注入到 chat response metadata？还是需要修改 `orchestration/composer.py` 或 chat pipeline？如果是后者，Phase 1 需要增加 backend pipeline 修改。

2. **SourceTrayState 持久化**：`SourceTrayState.selections` 是否持久化到 Redis/DB？当前 types.py 显示纯 in-memory 数据类。刷新后 selections 是否会丢失？

3. **WebSocket 实时更新**：SourceTrayState 选择变更后，是否通过 WebSocket 推送更新到其他客户端（如 Web 端）？当前设计是 Flutter 轮询或手动刷新。

4. **SourceAsset vs DocumentLibraryItem 数据源**：`SourceTrayState.available_sources` 的后端数据源是什么？是从 `SourceAsset` 构造还是从文件库查询？需要在 source_tray.py API 中明确。

5. **Scope 的语义范围**：`this_goal` scope 的到期条件是什么？goal 关闭时所有 `this_goal` scope 的排除是否自动撤销？

6. **排除后的 UI 反馈**：素材排除后，已显示的 chat 消息中的 evidence snippet 是否应该标记为"已排除"？

---

*Spec generated 2026-05-06 by claude-B (GAP Closer Agent)*
