# Sparkle 知识星图 (Knowledge Galaxy) 系统设计文档 v3.0

> **版本**：v3.0 (完整版)  
> **状态**：Ready for Implementation  
> **核心隐喻**：能量源 (Flame) → 飞升 (Ascension) → 星辰 (Star) → 星座涌现 (Constellation Emergence)  
> **技术栈**：Flutter (GLSL Shader/CustomPaint) + FastAPI + PostgreSQL (pgvector) + LLM (Qwen/DeepSeek)

---

## 目录

1. [核心概念与设计愿景](#1-核心概念与设计愿景)
2. [数据库设计](#2-数据库设计)
3. [后端架构设计](#3-后端架构设计)
4. [前端架构与视觉实现](#4-前端架构与视觉实现)
5. [LLM 智能拓展系统](#5-llm-智能拓展系统)
6. [用户体验设计](#6-用户体验设计)
7. [系统集成与数据流](#7-系统集成与数据流)
8. [开发路线图](#8-开发路线图)
9. [附录](#9-附录)

---

## 1. 核心概念与设计愿景

### 1.1 视觉隐喻：以火为核 (The Core)

用户不仅是观测者，更是宇宙中心的能量源。每一次学习都是向宇宙注入能量的过程。

| 元素 | 隐喻 | 视觉表现 |
|-----|------|---------|
| **Flame Core (能量源)** | 用户当下的专注力与生命力 | 屏幕中心的 GLSL Shader 流体火焰 |
| **The Galaxy (星域)** | 不同维度的知识体系 | 环绕火苗的 6+1 个有机星云 |
| **Stars (星辰)** | 具体的知识点 | 不同亮度/大小的发光节点 |
| **Ascension (飞升)** | 任务完成的能量传递 | 火花粒子从中心喷射点亮星辰 |
| **Constellation (星座)** | 知识点之间的关联 | 星星之间的发光连线 |
| **Emergence (涌现)** | LLM 拓展新知识 | 新星从虚空中逐渐显现 |

### 1.2 6+1 星域分类体系

```
                    ★ WISDOM (智慧星域)
                         ↑
        COSMOS ←──── 🔥 ────→ TECH
       (理性星域)    FLAME    (造物星域)
                    CORE
        ART ←─────────┼─────────→ CIVILIZATION
     (灵感星域)       │        (文明星域)
                     ↓
                   LIFE (生活星域)
                     
            ～～～ VOID (暗物质区) ～～～
```

| 星域代码 | 名称 | 主色调 | 辉光色 | 涵盖领域 |
|---------|------|--------|-------|---------|
| `COSMOS` | 理性星域 | `#00BFFF` | `#87CEEB` | 数学、物理、化学、天文、逻辑学 |
| `TECH` | 造物星域 | `#C0C0C0` | `#E8E8E8` | 计算机、工程、AI、建筑、制造 |
| `ART` | 灵感星域 | `#FF00FF` | `#FFB6C1` | 设计、音乐、绘画、文学、ACG |
| `CIVILIZATION` | 文明星域 | `#FFD700` | `#FFF8DC` | 历史、经济、政治、社会学、法律 |
| `LIFE` | 生活星域 | `#32CD32` | `#90EE90` | 健身、烹饪、医学、心理、理财 |
| `WISDOM` | 智慧星域 | `#FFFFFF` | `#F0F8FF` | 哲学、宗教、方法论、元认知 |
| `VOID` | 暗物质区 | `#2F4F4F` | `#696969` | 未归类、跨领域、新兴概念 |

### 1.3 核心设计原则

1. **渐进式揭示**：知识宇宙从一片混沌开始，随学习逐渐点亮
2. **有机生长**：星图不是静态地图，而是会随用户学习自动拓展的生命体
3. **情感连接**：每颗星都承载用户的学习记忆，形成情感羁绊
4. **遗忘可视化**：长期不复习的知识会逐渐暗淡，提醒用户回顾

---

## 2. 数据库设计

### 2.1 ER 关系图

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │    subjects     │       │ knowledge_nodes │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │◄──────│ subject_id (FK) │
│ username        │       │ name            │       │ id (PK)         │
│ created_at      │       │ sector_code     │       │ parent_id (FK)  │──┐
└────────┬────────┘       │ hex_color       │       │ name            │  │
         │                │ position_angle  │       │ description     │  │
         │                └─────────────────┘       │ importance_level│  │
         │                                          │ embedding       │  │
         │                                          │ is_seed         │  │
         │                                          │ source_type     │  │
         ▼                                          └────────┬────────┘  │
┌─────────────────┐                                          │           │
│user_node_status │◄─────────────────────────────────────────┘           │
├─────────────────┤                                                      │
│ user_id (FK)    │       ┌─────────────────┐                           │
│ node_id (FK)    │       │  node_relations │◄──────────────────────────┘
│ mastery_score   │       ├─────────────────┤
│ total_minutes   │       │ source_node_id  │
│ is_unlocked     │       │ target_node_id  │
│ is_collapsed    │       │ relation_type   │
│ last_study_at   │       │ strength        │
│ decay_paused    │       └─────────────────┘
└─────────────────┘
```

### 2.2 完整 SQL Schema

```sql
-- ============================================
-- 1. 启用必要扩展
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. 扩展 subjects 表 (学科 → 星域映射)
-- ============================================
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS sector_code VARCHAR(20) DEFAULT 'VOID';
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS hex_color VARCHAR(10);
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS glow_color VARCHAR(10);
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS position_angle FLOAT;
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS icon_name VARCHAR(50);

-- ============================================
-- 3. 知识节点表 (核心表)
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    parent_id UUID REFERENCES knowledge_nodes(id) ON DELETE SET NULL,
    
    -- 基础信息
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    keywords TEXT[],
    
    -- 视觉属性 (1-5: 边缘概念→领域支柱)
    importance_level INTEGER DEFAULT 1 CHECK (importance_level BETWEEN 1 AND 5),
    
    -- 节点来源
    is_seed BOOLEAN DEFAULT FALSE,
    source_type VARCHAR(20) DEFAULT 'seed', -- seed | user_created | llm_expanded
    source_task_id UUID,
    
    -- AI 属性
    embedding vector(1536),
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 向量索引
CREATE INDEX IF NOT EXISTS idx_nodes_embedding 
ON knowledge_nodes USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON knowledge_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_subject ON knowledge_nodes(subject_id);
CREATE INDEX IF NOT EXISTS idx_nodes_keywords ON knowledge_nodes USING GIN(keywords);

-- ============================================
-- 4. 知识点关系表 (星座连线)
-- ============================================
CREATE TABLE IF NOT EXISTS node_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    
    -- 关系类型: prerequisite, related, application, composition, evolution
    relation_type VARCHAR(30) NOT NULL,
    strength FLOAT DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    
    created_by VARCHAR(20) DEFAULT 'seed',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(source_node_id, target_node_id, relation_type)
);

-- ============================================
-- 5. 用户节点状态表
-- ============================================
CREATE TABLE IF NOT EXISTS user_node_status (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    
    mastery_score FLOAT DEFAULT 0 CHECK (mastery_score BETWEEN 0 AND 100),
    total_study_minutes INTEGER DEFAULT 0,
    study_count INTEGER DEFAULT 0,
    
    is_unlocked BOOLEAN DEFAULT FALSE,
    is_collapsed BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    
    last_study_at TIMESTAMP WITH TIME ZONE,
    decay_paused BOOLEAN DEFAULT FALSE,
    next_review_at TIMESTAMP WITH TIME ZONE,
    first_unlock_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, node_id)
);

-- ============================================
-- 6. 学习记录表
-- ============================================
CREATE TABLE IF NOT EXISTS study_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    study_minutes INTEGER NOT NULL,
    mastery_delta FLOAT NOT NULL,
    record_type VARCHAR(20) DEFAULT 'task_complete',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 7. 节点拓展队列表
-- ============================================
CREATE TABLE IF NOT EXISTS node_expansion_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trigger_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    trigger_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    expansion_context TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    expanded_nodes JSONB,
    error_message TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- 8. 更新 tasks 表
-- ============================================
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS knowledge_node_id UUID REFERENCES knowledge_nodes(id);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS auto_expand_enabled BOOLEAN DEFAULT TRUE;
```

---

## 3. 后端架构设计

### 3.1 目录结构

```
backend/
├── app/
│   ├── api/v1/galaxy/
│   │   ├── router.py          # API 路由
│   │   └── schemas.py         # Pydantic 模型
│   ├── services/
│   │   ├── galaxy_service.py      # 星图核心服务
│   │   ├── expansion_service.py   # LLM 拓展服务
│   │   ├── decay_service.py       # 遗忘衰减服务
│   │   └── embedding_service.py   # 向量嵌入服务
│   ├── models/
│   │   ├── knowledge_node.py
│   │   ├── node_relation.py
│   │   └── user_node_status.py
│   └── jobs/
│       ├── decay_job.py           # 每日衰减任务
│       └── expansion_worker.py    # 拓展队列消费者
└── seeds/
    └── nodes/                     # 种子数据
```

### 3.2 GalaxyService (核心服务)

```python
# backend/app/services/galaxy_service.py

class GalaxyService:
    """知识星图核心服务"""
    
    BASE_MASTERY_POINTS = 5.0
    MAX_MASTERY = 100.0
    MEMORY_HALF_LIFE_DAYS = 7.0
    
    async def get_galaxy_graph(
        self, 
        user_id: UUID,
        sector_code: Optional[str] = None
    ) -> GalaxyGraphResponse:
        """获取用户的知识星图数据"""
        # 1. 查询知识节点 (带用户状态)
        query = select(KnowledgeNode, UserNodeStatus).outerjoin(...)
        
        # 2. 查询节点关系
        relations = await self._get_relations(node_ids)
        
        # 3. 组装响应
        return GalaxyGraphResponse(
            nodes=[...],
            relations=[...],
            user_stats=await self._calculate_user_stats(user_id)
        )

    async def spark_node(
        self,
        user_id: UUID,
        node_id: UUID,
        study_minutes: int,
        task_id: Optional[UUID] = None
    ) -> SparkResult:
        """点亮/增强知识点"""
        # 1. 获取或创建用户节点状态
        status = await self._get_or_create_status(user_id, node_id)
        
        # 2. 计算掌握度增量
        mastery_delta = self._calculate_mastery_delta(study_minutes, node.importance_level)
        
        # 3. 更新状态
        old_mastery = status.mastery_score
        is_first_unlock = not status.is_unlocked
        
        status.mastery_score = min(status.mastery_score + mastery_delta, self.MAX_MASTERY)
        status.total_study_minutes += study_minutes
        status.study_count += 1
        status.last_study_at = datetime.utcnow()
        status.is_unlocked = True
        status.next_review_at = self._calculate_next_review(status.mastery_score)
        
        # 4. 记录学习历史
        await self._create_study_record(...)
        
        # 5. 生成动画事件
        spark_event = SparkEvent(
            node_id=node_id,
            old_mastery=old_mastery,
            new_mastery=status.mastery_score,
            is_first_unlock=is_first_unlock,
            is_level_up=self._check_level_up(old_mastery, status.mastery_score)
        )
        
        # 6. 触发 LLM 拓展 (异步)
        if status.study_count >= 2:
            await self.expansion_service.queue_expansion(node_id, task_id, user_id)
        
        return SparkResult(spark_event=spark_event, ...)

    def _calculate_mastery_delta(self, study_minutes: int, importance_level: int) -> float:
        """计算掌握度增量"""
        time_factor = min(study_minutes / 30.0, 2.0)
        difficulty_factor = 1 + (importance_level - 1) * 0.1
        return self.BASE_MASTERY_POINTS * time_factor * difficulty_factor

    def _calculate_next_review(self, mastery_score: float) -> datetime:
        """根据掌握度计算下次复习时间"""
        if mastery_score >= 80: days = 14
        elif mastery_score >= 60: days = 7
        elif mastery_score >= 30: days = 3
        else: days = 1
        return datetime.utcnow() + timedelta(days=days)
```

### 3.3 DecayService (遗忘衰减)

```python
class DecayService:
    """遗忘曲线衰减服务 - 艾宾浩斯公式"""
    
    BASE_HALF_LIFE_DAYS = 7.0
    MIN_MASTERY = 5.0
    
    async def apply_daily_decay(self) -> dict:
        """每日遗忘衰减任务"""
        # 查询需要衰减的节点
        statuses = await self._get_decay_candidates()
        
        for status in statuses:
            days_elapsed = (now - status.last_study_at).days
            new_mastery = self._calculate_decay(status.mastery_score, days_elapsed)
            status.mastery_score = new_mastery
        
        await self.db.commit()
        return stats

    def _calculate_decay(self, current_mastery: float, days_elapsed: int) -> float:
        """
        艾宾浩斯遗忘曲线:
        - 高掌握度衰减更慢 (更稳定的记忆)
        - 最低不会降到 MIN_MASTERY
        """
        stability_factor = 1 + (current_mastery / 100) * 2  # 1-3 倍
        effective_half_life = self.BASE_HALF_LIFE_DAYS * stability_factor
        
        decay_rate = math.log(2) / effective_half_life
        retention = math.exp(-decay_rate * days_elapsed)
        
        return max(current_mastery * retention, self.MIN_MASTERY)
```

### 3.4 API 路由

```python
# backend/app/api/v1/galaxy/router.py

router = APIRouter(prefix="/galaxy", tags=["Knowledge Galaxy"])

@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    sector_code: Optional[str] = None,
    include_locked: bool = True,
    current_user = Depends(get_current_user),
    galaxy_service = Depends(get_galaxy_service)
):
    """获取用户的知识星图数据"""
    return await galaxy_service.get_galaxy_graph(...)

@router.post("/node/{node_id}/spark", response_model=SparkResult)
async def spark_node(node_id: UUID, request: SparkRequest, ...):
    """点亮/增强知识点 (任务完成时调用)"""
    return await galaxy_service.spark_node(...)

@router.post("/search", response_model=SearchResponse)
async def search_nodes(request: SearchRequest, ...):
    """语义搜索知识点"""
    return await galaxy_service.semantic_search(...)

@router.get("/review/suggestions", response_model=ReviewSuggestionsResponse)
async def get_review_suggestions(limit: int = 5, ...):
    """获取复习建议"""
    return await galaxy_service.decay_service.get_review_suggestions(...)
```

---

## 4. 前端架构与视觉实现

### 4.1 目录结构

```
lib/features/galaxy/
├── data/
│   ├── galaxy_repository.dart
│   └── galaxy_api.dart
├── domain/models/
│   ├── knowledge_node.dart
│   ├── node_relation.dart
│   └── spark_event.dart
├── presentation/
│   ├── screens/
│   │   ├── galaxy_screen.dart
│   │   └── node_detail_screen.dart
│   ├── widgets/
│   │   ├── galaxy_viewport.dart
│   │   ├── flame_core.dart          # Shader 火苗
│   │   ├── star_node.dart           # 星星节点
│   │   ├── constellation_lines.dart # 星座连线
│   │   └── particle_system.dart     # 粒子系统
│   └── painters/
│       └── deep_space_painter.dart
├── controllers/
│   └── galaxy_controller.dart
└── shaders/
    └── flame.frag
```

### 4.2 组件树结构

```
GalaxyScreen
└── Stack
    ├── DeepSpaceBackground (CustomPainter: 静态星尘)
    │
    ├── InteractiveViewer (可缩放平移)
    │   └── Stack (2000x2000 逻辑像素)
    │       ├── ConstellationLines (星座连线)
    │       ├── SectorClusters (6 个星域)
    │       │   └── StarNode (每个知识点)
    │       └── FlameCore (中心火苗, Shader)
    │
    ├── ParticleLayer (飞升粒子动画)
    │
    └── BottomSheet (节点详情面板)
```

### 4.3 FlameCore (Shader 火苗)

```dart
class FlameCore extends StatefulWidget {
  final Animation<double> animation;
  final double intensity;
  
  @override
  State<FlameCore> createState() => _FlameCoreState();
}

class _FlameCoreState extends State<FlameCore> {
  ui.FragmentShader? _shader;

  @override
  void initState() {
    super.initState();
    _loadShader();
  }

  Future<void> _loadShader() async {
    try {
      final program = await ui.FragmentProgram.fromAsset('shaders/flame.frag');
      _shader = program.fragmentShader();
      setState(() {});
    } catch (e) {
      // Shader 加载失败使用降级方案
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_shader == null) return _buildFallbackFlame();
    
    return AnimatedBuilder(
      animation: widget.animation,
      builder: (context, child) => CustomPaint(
        size: const Size(120, 160),
        painter: FlamePainter(
          shader: _shader!,
          time: widget.animation.value * 10,
          intensity: widget.intensity,
        ),
      ),
    );
  }

  Widget _buildFallbackFlame() {
    // 降级方案：渐变 + 动画
    return Container(
      decoration: BoxDecoration(
        gradient: RadialGradient(colors: [
          Colors.white,
          Colors.amber,
          Colors.orange,
          Colors.transparent,
        ]),
      ),
    );
  }
}
```

### 4.4 GLSL Shader (火焰效果)

```glsl
// assets/shaders/flame.frag
#version 460 core
#include <flutter/runtime_effect.glsl>

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_intensity;

// Simplex 噪声 + FBM 实现动态火焰
float snoise(vec2 v) { ... }
float fbm(vec2 st) { ... }

void main() {
    vec2 st = FlutterFragCoord().xy / u_resolution;
    
    // 火焰形状 (锥形)
    float shape = 1.0 - length(vec2(st.x * 1.5, st.y - 0.2));
    
    // 动态噪声扰动
    vec2 q = vec2(fbm(st + 0.1 * u_time), fbm(st + vec2(1.0)));
    float noise = fbm(st + q);
    
    // 合并形状和噪声
    float flame = shape * (0.5 + 0.5 * noise) * u_intensity;
    
    // 颜色渐变 (白 → 黄 → 橙 → 红)
    vec3 color = mix(vec3(0.1, 0.0, 0.0), vec3(1.0, 0.9, 0.7), pow(flame, 1.5));
    
    fragColor = vec4(color, flame);
}
```

### 4.5 StarNode (星星节点)

```dart
class StarNode extends StatefulWidget {
  final KnowledgeNode node;
  final UserNodeStatus? status;
  final VoidCallback onTap;
  
  @override
  State<StarNode> createState() => _StarNodeState();
}

class _StarNodeState extends State<StarNode> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  Widget build(BuildContext context) {
    final size = _calculateSize();
    final color = _getSectorColor(widget.node.sectorCode);
    final brightness = widget.status?.brightness ?? 0.2;
    
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _pulseController,
        builder: (context, child) {
          final scale = _shouldPulse ? 1.0 + 0.1 * _pulseController.value : 1.0;
          return Transform.scale(
            scale: scale,
            child: _buildStar(size, color, brightness),
          );
        },
      ),
    );
  }

  Widget _buildStar(double size, Color color, double brightness) {
    if (widget.status?.isCollapsed == true) {
      return _buildCollapsedStar(size);  // 黑色核心 + 红色脉冲
    }
    
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            Colors.white.withOpacity(brightness),
            color.withOpacity(brightness * 0.8),
            Colors.transparent,
          ],
        ),
        boxShadow: brightness > 0.5 ? [
          BoxShadow(color: color.withOpacity(0.6), blurRadius: size * 0.8),
        ] : null,
      ),
    );
  }

  double _calculateSize() {
    // 基础大小根据重要性 + 掌握度加成
    return 20.0 + widget.node.importanceLevel * 8.0 +
           (widget.status?.masteryScore ?? 0) / 100 * 10;
  }
}
```

### 4.6 ParticleSystem (飞升粒子)

```dart
class AscensionParticle {
  final Offset startPosition;  // 火苗中心
  final Offset endPosition;    // 目标节点
  final Color color;
  final Duration delay;
}

class _AnimatedParticle extends StatefulWidget {
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) => CustomPaint(
        painter: _ParticlePainter(
          position: _calculateBezierPosition(_progressAnimation.value),
          trail: _trail,
          color: widget.particle.color,
        ),
      ),
    );
  }

  Offset _calculateBezierPosition(double t) {
    // 二阶贝塞尔曲线 (弧线轨迹)
    final x = pow(1-t, 2) * start.dx + 2*(1-t)*t * control.dx + pow(t,2) * end.dx;
    final y = pow(1-t, 2) * start.dy + 2*(1-t)*t * control.dy + pow(t,2) * end.dy;
    return Offset(x, y);
  }
}
```

### 4.7 状态管理 (Riverpod)

```dart
final galaxyControllerProvider = StateNotifierProvider<GalaxyController, GalaxyState>((ref) {
  return GalaxyController(ref.watch(galaxyRepositoryProvider));
});

class GalaxyState {
  final List<KnowledgeNode> nodes;
  final List<NodeRelation> relations;
  final Map<UUID, UserNodeStatus> userStatuses;
  final GalaxyUserStats userStats;
  
  // 计算节点位置 (极坐标 + 噪声)
  Map<UUID, Offset> get nodePositions {
    final positions = <UUID, Offset>{};
    for (final node in nodes) {
      final sectorAngle = _getSectorBaseAngle(node.sectorCode);
      final baseRadius = 150.0 + (5 - node.importanceLevel) * 80.0;
      final noise = _perlinNoise(node.id);
      
      positions[node.id] = Offset(
        1000 + (baseRadius + noise.x) * cos(sectorAngle + noise.angle),
        1000 + (baseRadius + noise.y) * sin(sectorAngle + noise.angle),
      );
    }
    return positions;
  }
}

class GalaxyController extends StateNotifier<GalaxyState> {
  Future<SparkEvent?> handleTaskCompleted(UUID taskId, UUID? nodeId, int minutes) async {
    final result = await _repository.sparkNode(nodeId: nodeId, studyMinutes: minutes);
    _updateNodeStatus(nodeId, result.updatedStatus);
    return result.sparkEvent;
  }
}
```

---

## 5. LLM 智能拓展系统

### 5.1 拓展机制概述

```
用户完成任务 → spark_node() → 检查拓展条件 → 加入队列
                                    ↓
                            ExpansionWorker (异步)
                                    ↓
                    收集上下文 → 构建 Prompt → 调用 LLM
                                    ↓
                    解析响应 → 去重验证 → 创建节点 → SSE 通知
                                    ↓
                            前端播放涌现动画
```

### 5.2 ExpansionService

```python
class ExpansionService:
    MAX_EXPANDED_NODES = 5
    MIN_STUDY_COUNT = 2
    COOLDOWN_HOURS = 24

    async def queue_expansion(self, trigger_node_id: UUID, user_id: UUID):
        if not await self._should_expand(trigger_node_id, user_id):
            return False
        
        context = await self._build_expansion_context(trigger_node_id, user_id)
        queue_item = NodeExpansionQueue(
            trigger_node_id=trigger_node_id,
            user_id=user_id,
            expansion_context=context,
            status='pending'
        )
        self.db.add(queue_item)
        return True

    async def process_expansion(self, queue_id: UUID) -> List[KnowledgeNode]:
        queue_item = await self.db.get(NodeExpansionQueue, queue_id)
        
        # 调用 LLM
        prompt = self._build_expansion_prompt(queue_item.expansion_context)
        response = await self.llm_client.chat_completion(messages=[...])
        
        # 解析并创建节点
        expanded_data = self._parse_response(response)
        new_nodes = await self._create_expanded_nodes(expanded_data, ...)
        
        # 通知前端
        await self.sse_manager.send_to_user(user_id, {
            "type": "nodes_expanded",
            "nodes": [{"id": str(n.id), "name": n.name} for n in new_nodes]
        })
        
        return new_nodes
```

### 5.3 拓展 Prompt 模板

```python
EXPANSION_PROMPT = """你是知识图谱拓展专家。用户正在学习"{node_name}"。

## 当前知识点
- 名称：{node_name}
- 描述：{description}
- 领域：{sector}

## 相邻知识点
{neighbors}

## 用户已学习
{learned}

## 任务
推荐 3-5 个相关知识点，包含：
1. 1-2 个深化节点（更细分或更高阶）
2. 1-2 个应用节点（实践或案例）
3. 0-1 个跨领域节点

## 输出格式 (JSON)
{
  "expanded_nodes": [{
    "name": "名称",
    "description": "描述",
    "importance_level": 3,
    "relation_to_trigger": "related",
    "relation_strength": 0.8,
    "keywords": ["关键词"]
  }]
}"""
```

---

## 6. 用户体验设计

### 6.1 用户旅程

```
首次打开 → 空状态引导 → 完成任务 → 首次点亮 → 持续学习 → 星图生长
                                        ↓
                                   复习提醒 ← 星星变暗
```

### 6.2 空状态设计

- 混沌背景 (更暗淡)
- 6 个星域轮廓 (虚线描边，低透明度)
- 中心小火苗 (intensity: 0.3)
- 引导文案：「你的知识宇宙刚刚诞生，完成第一个任务点亮第一颗星」
- 指向任务 Tab 的动画箭头

### 6.3 首次点亮动画序列

1. 火苗增强 (0.5s)
2. 粒子喷射 (1.5s，数量 ×1.5)
3. 星星点亮 + Bloom (0.8s)
4. 相机聚焦到新星 (0.5s)
5. 成就弹窗：🌟「第一颗星 - 你点亮了 XX」

### 6.4 节点详情面板内容

- 节点名称 + 状态指示器
- 掌握度进度条 + 升级提示
- 描述
- 学习统计（总时长、次数、首次点亮时间）
- 相关知识点
- 操作按钮：开始学习、详情

### 6.5 复习提醒

- 每日检查 next_review_at
- 卡片展示变暗的知识点
- 标记紧急程度（高：mastery < 20）
- 快速复习入口

### 6.6 成就系统

| 成就 | 描述 | 图标 |
|-----|------|-----|
| 第一颗星 | 点亮第一个知识点 | 🌟 |
| 领域先驱 | 在一个星域点亮 10 个 | 🚀 |
| 星座缔造者 | 形成 5+ 节点的星座 | ✨ |
| 知识探索者 | 解锁所有 6 个星域 | 🔭 |
| 精通追求者 | 一个知识点达到精通 | 💎 |
| 记忆守护者 | 连续 7 天复习 | 🛡️ |
| 星河建筑师 | 拥有 100 个知识点 | 🌌 |

### 6.7 反馈系统

| 事件 | 触觉 | 音效 |
|-----|------|------|
| 点亮新星 | 中等震动 | 叮咚 |
| 升级星星 | 强震动序列 | 升调和弦 |
| 星星坍缩 | 沉闷单次 | 低沉音 |
| 节点涌现 | 轻震动 | 涌现音 |

---

## 7. 系统集成与数据流

### 7.1 Task → Galaxy 完整流程

```
用户完成 Sprint Task
        │
        ▼
TaskService.complete_task()
├── 更新 task.status
├── 获取 knowledge_node_id (有则用，无则 auto_classify)
└── 调用 GalaxyService.spark_node()
        │
        ▼
GalaxyService.spark_node()
├── 更新 UserNodeStatus
├── 创建 StudyRecord
├── 生成 SparkEvent
└── 队列 LLM 拓展
        │
        ├─────────────────────────────┐
        ▼                             ▼
    SSE 推送 SparkEvent          ExpansionWorker (异步)
        │                             │
        ▼                             ▼
    前端播放飞升动画              LLM 生成新节点
                                      │
                                      ▼
                              SSE 推送 nodes_expanded
                                      │
                                      ▼
                              前端播放涌现动画
```

### 7.2 SSE 事件类型

| 类型 | 数据 | 前端动作 |
|-----|------|---------|
| spark | node_id, old/new_mastery, is_first_unlock | 播放飞升动画 |
| nodes_expanded | nodes[] | 播放涌现动画 |
| decay_applied | affected_nodes[] | 更新星星亮度 |

---

## 8. 开发路线图

### Week 1-2: 基础星图
- [ ] 数据库迁移 (knowledge_nodes, relations, status)
- [ ] 种子数据 (6 星域核心结构)
- [ ] GET /galaxy/graph API
- [ ] GalaxyScreen 基础框架
- [ ] StarNode 组件
- [ ] 极坐标布局算法

### Week 3-4: 核心循环
- [ ] spark_node() 实现
- [ ] SparkEvent 生成
- [ ] 火苗组件 (Lottie 降级)
- [ ] 粒子系统
- [ ] SSE 事件监听
- [ ] 飞升动画

### Week 5-6: 智能拓展
- [ ] ExpansionService
- [ ] Prompt 设计调优
- [ ] ExpansionWorker
- [ ] EmbeddingService
- [ ] 涌现动画
- [ ] 星座连线

### Week 7-8: 遗忘与打磨
- [ ] DecayService
- [ ] 每日衰减定时任务
- [ ] 复习提醒
- [ ] Shader 火苗
- [ ] 性能优化
- [ ] 成就系统

---

## 9. 附录

### 9.1 颜色系统

```dart
class GalaxyColors {
  static const deepSpace = Color(0xFF0A0A1A);
  static const cosmos = Color(0xFF00BFFF);
  static const tech = Color(0xFFC0C0C0);
  static const art = Color(0xFFFF00FF);
  static const civilization = Color(0xFFFFD700);
  static const life = Color(0xFF32CD32);
  static const wisdom = Color(0xFFFFFFFF);
  static const void_ = Color(0xFF2F4F4F);
}
```

### 9.2 节点状态映射

| 状态 | mastery | 视觉 | 动画 |
|-----|---------|------|------|
| Locked | - | 透明度 0.2 | 无 |
| Glimmer | 1-29 | 透明度 0.5 | 微弱闪烁 |
| Shining | 30-79 | 透明度 0.8 + 发光 | 稳定发光 |
| Brilliant | 80-94 | 透明度 1.0 + Bloom | 脉冲发光 |
| Mastered | 95-100 | 白色核心 + 光环 | 持续脉冲 |
| Collapsed | 任意 | 黑色 + 红边 | 警告脉冲 |

### 9.3 遗忘曲线参数

- 基础半衰期：7 天
- 稳定性系数：1 + (mastery/100) × 2
- 实际半衰期：7 × 稳定性系数 (7-21 天)
- 最低掌握度：5%

### 9.4 性能指标目标

| 指标 | 目标 |
|-----|------|
| 星图首次加载 | < 2s |
| 节点支持数量 | 500+ @ 60fps |
| 飞升动画帧率 | 60fps |
| SSE 延迟 | < 500ms |
| LLM 拓展响应 | < 10s |
| 内存占用 | < 150MB |

---

**文档版本**：v3.0  
**状态**：Ready for Implementation