Sparkle 知识星图 (Knowledge Galaxy) 系统设计文档 v3.0
版本：v3.0 (完整版)
状态：Ready for Implementation
核心隐喻：能量源 (Flame) → 飞升 (Ascension) → 星辰 (Star) → 星座涌现 (Constellation Emergence)
技术栈：Flutter (GLSL Shader/CustomPaint) + FastAPI + PostgreSQL (pgvector) + LLM (Qwen/DeepSeek)
目录
核心概念与设计愿景
数据库设计
后端架构设计
前端架构与视觉实现
LLM 智能拓展系统
用户体验设计
系统集成与数据流
开发路线图
附录
1. 核心概念与设计愿景1.1 视觉隐喻：以火为核 (The Core)用户不仅是观测者，更是宇宙中心的能量源。每一次学习都是向宇宙注入能量的过程。元素隐喻视觉表现Flame Core (能量源)用户当下的专注力与生命力屏幕中心的 GLSL Shader 流体火焰The Galaxy (星域)不同维度的知识体系环绕火苗的 6+1 个有机星云Stars (星辰)具体的知识点不同亮度/大小的发光节点Ascension (飞升)任务完成的能量传递火花粒子从中心喷射点亮星辰Constellation (星座)知识点之间的关联星星之间的发光连线Emergence (涌现)LLM 拓展新知识新星从虚空中逐渐显现1.2 6+1 星域分类体系                    ★ WISDOM (智慧星域)
                         ↑
        COSMOS ←──── 🔥 ────→ TECH
       (理性星域)    FLAME    (造物星域)
                    CORE
        ART ←─────────┼─────────→ CIVILIZATION
     (灵感星域)       │        (文明星域)
                     ↓
                   LIFE (生活星域)
                     
            ～～～ VOID (暗物质区) ～～～
            星域代码名称主色调辉光色涵盖领域COSMOS理性星域#00BFFF#87CEEB数学、物理、化学、天文、逻辑学TECH造物星域#C0C0C0#E8E8E8计算机、工程、AI、建筑、制造ART灵感星域#FF00FF#FFB6C1设计、音乐、绘画、文学、ACGCIVILIZATION文明星域#FFD700#FFF8DC历史、经济、政治、社会学、法律LIFE生活星域#32CD32#90EE90健身、烹饪、医学、心理、理财WISDOM智慧星域#FFFFFF#F0F8FF哲学、宗教、方法论、元认知VOID暗物质区#2F4F4F#696969未归类、跨领域、新兴概念1.3 核心设计原则
渐进式揭示：知识宇宙从一片混沌开始，随学习逐渐点亮
有机生长：星图不是静态地图，而是会随用户学习自动拓展的生命体
情感连接：每颗星都承载用户的学习记忆，形成情感羁绊
遗忘可视化：长期不复习的知识会逐渐暗淡，提醒用户回顾
2. 数据库设计2.1 ER 关系图┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
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
         │
         ▼
┌─────────────────┐       ┌─────────────────┐
│  study_records  │       │    tasks        │
├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │
│ user_id (FK)    │       │ user_id (FK)    │
│ node_id (FK)    │       │ node_id (FK)    │◄── 任务关联知识点
│ study_minutes   │       │ title           │
│ mastery_delta   │       │ status          │
│ created_at      │       │ ...             │
└─────────────────┘       └─────────────────┘2.2 完整 SQL Schemasql-- ============================================
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
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS position_angle FLOAT; -- 星域基准角度 (0-360)
ALTER TABLE subjects ADD COLUMN IF NOT EXISTS icon_name VARCHAR(50); -- 星域图标

-- 创建星域枚举类型
DO $$ BEGIN
    CREATE TYPE sector_type AS ENUM ('COSMOS', 'TECH', 'ART', 'CIVILIZATION', 'LIFE', 'WISDOM', 'VOID');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- 3. 知识节点表 (核心表)
-- ============================================
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    parent_id UUID REFERENCES knowledge_nodes(id) ON DELETE SET NULL,
    
    -- 基础信息
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100), -- 英文名，用于国际化和搜索
    description TEXT,
    keywords TEXT[], -- 关键词数组，用于快速匹配
    
    -- 视觉属性
    importance_level INTEGER DEFAULT 1 CHECK (importance_level BETWEEN 1 AND 5),
    -- 1: 边缘概念 (小星)
    -- 2: 普通知识点
    -- 3: 重要概念 (中星)
    -- 4: 核心知识 (大星)
    -- 5: 领域支柱 (巨星)
    
    -- 节点来源
    is_seed BOOLEAN DEFAULT FALSE, -- 是否为种子库预置节点
    source_type VARCHAR(20) DEFAULT 'seed', -- seed | user_created | llm_expanded
    source_task_id UUID, -- 如果是从任务拓展而来，记录来源任务
    
    -- AI 属性
    embedding vector(1536), -- 文本向量 (用于语义搜索和自动归类)
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 向量索引 (HNSW 算法，余弦相似度)
CREATE INDEX IF NOT EXISTS idx_nodes_embedding 
ON knowledge_nodes USING hnsw (embedding vector_cosine_ops);

-- 父节点索引
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON knowledge_nodes(parent_id);

-- 学科索引
CREATE INDEX IF NOT EXISTS idx_nodes_subject ON knowledge_nodes(subject_id);

-- 关键词 GIN 索引 (用于快速搜索)
CREATE INDEX IF NOT EXISTS idx_nodes_keywords ON knowledge_nodes USING GIN(keywords);

-- ============================================
-- 4. 知识点关系表 (星座连线)
-- ============================================
CREATE TABLE IF NOT EXISTS node_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    
    -- 关系类型
    relation_type VARCHAR(30) NOT NULL,
    -- prerequisite: 前置知识 (A → B 表示学 B 需要先学 A)
    -- related: 相关联 (双向)
    -- application: 应用关系 (理论 → 实践)
    -- composition: 组成关系 (整体 → 部分)
    -- evolution: 演化关系 (旧 → 新)
    
    -- 关系强度 (影响连线视觉)
    strength FLOAT DEFAULT 0.5 CHECK (strength BETWEEN 0 AND 1),
    
    -- 元数据
    created_by VARCHAR(20) DEFAULT 'seed', -- seed | user | llm
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 防止重复关系
    UNIQUE(source_node_id, target_node_id, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON node_relations(source_node_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON node_relations(target_node_id);

-- ============================================
-- 5. 用户节点状态表 (个人星图状态)
-- ============================================
CREATE TABLE IF NOT EXISTS user_node_status (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    
    -- 掌握度 (决定星星亮度)
    mastery_score FLOAT DEFAULT 0 CHECK (mastery_score BETWEEN 0 AND 100),
    
    -- 学习统计
    total_study_minutes INTEGER DEFAULT 0,
    study_count INTEGER DEFAULT 0, -- 学习次数
    
    -- 状态标记
    is_unlocked BOOLEAN DEFAULT FALSE, -- 是否解锁 (首次学习后解锁)
    is_collapsed BOOLEAN DEFAULT FALSE, -- 是否坍缩 (错误过多)
    is_favorite BOOLEAN DEFAULT FALSE, -- 用户标记为重点
    
    -- 遗忘曲线相关
    last_study_at TIMESTAMP WITH TIME ZONE, -- 最后学习时间
    decay_paused BOOLEAN DEFAULT FALSE, -- 暂停衰减 (用户可手动暂停)
    next_review_at TIMESTAMP WITH TIME ZONE, -- 建议下次复习时间
    
    -- 元数据
    first_unlock_at TIMESTAMP WITH TIME ZONE, -- 首次点亮时间 (里程碑)
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, node_id)
);

CREATE INDEX IF NOT EXISTS idx_user_status_user ON user_node_status(user_id);
CREATE INDEX IF NOT EXISTS idx_user_status_mastery ON user_node_status(mastery_score);
CREATE INDEX IF NOT EXISTS idx_user_status_review ON user_node_status(next_review_at);

-- ============================================
-- 6. 学习记录表 (详细学习历史)
-- ============================================
CREATE TABLE IF NOT EXISTS study_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    
    -- 学习数据
    study_minutes INTEGER NOT NULL,
    mastery_delta FLOAT NOT NULL, -- 本次学习增加的掌握度
    
    -- 学习类型
    record_type VARCHAR(20) DEFAULT 'task_complete',
    -- task_complete: 完成任务
    -- review: 复习
    -- exploration: 主动探索
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_records_user ON study_records(user_id);
CREATE INDEX IF NOT EXISTS idx_records_node ON study_records(node_id);
CREATE INDEX IF NOT EXISTS idx_records_time ON study_records(created_at);

-- ============================================
-- 7. 节点拓展队列表 (LLM 拓展任务队列)
-- ============================================
CREATE TABLE IF NOT EXISTS node_expansion_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- 触发信息
    trigger_node_id UUID NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    trigger_task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- 拓展请求
    expansion_context TEXT NOT NULL, -- 发送给 LLM 的上下文
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',
    -- pending: 等待处理
    -- processing: 处理中
    -- completed: 已完成
    -- failed: 失败
    
    -- 结果
    expanded_nodes JSONB, -- LLM 返回的新节点
    error_message TEXT,
    
    -- 元数据
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_expansion_status ON node_expansion_queue(status);
CREATE INDEX IF NOT EXISTS idx_expansion_user ON node_expansion_queue(user_id);

-- ============================================
-- 8. 更新 tasks 表 (添加知识节点关联)
-- ============================================
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS knowledge_node_id UUID REFERENCES knowledge_nodes(id);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS auto_expand_enabled BOOLEAN DEFAULT TRUE;

-- ============================================
-- 9. 触发器：自动更新 updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_knowledge_nodes_updated_at
    BEFORE UPDATE ON knowledge_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_node_status_updated_at
    BEFORE UPDATE ON user_node_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();2.3 种子数据示例sql-- ============================================
-- 种子数据：星域配置
-- ============================================
UPDATE subjects SET 
    sector_code = 'COSMOS', 
    hex_color = '#00BFFF', 
    glow_color = '#87CEEB',
    position_angle = 300,
    icon_name = 'atom'
WHERE name IN ('数学', '物理', '化学');

UPDATE subjects SET 
    sector_code = 'TECH', 
    hex_color = '#C0C0C0', 
    glow_color = '#E8E8E8',
    position_angle = 60,
    icon_name = 'cpu'
WHERE name IN ('计算机科学', '软件工程', '人工智能');

-- ... 其他星域配置

-- ============================================
-- 种子数据：核心知识节点 (以计算机科学为例)
-- ============================================
INSERT INTO knowledge_nodes (id, subject_id, name, name_en, description, importance_level, is_seed, keywords) VALUES
-- 计算机科学核心节点
('11111111-1111-1111-1111-111111111101', 
 (SELECT id FROM subjects WHERE name = '计算机科学'),
 '算法与数据结构', 'Algorithms and Data Structures',
 '计算机科学的基石，研究如何高效地组织和处理数据',
 5, TRUE, ARRAY['算法', '数据结构', 'algorithm', 'data structure']),

('11111111-1111-1111-1111-111111111102',
 (SELECT id FROM subjects WHERE name = '计算机科学'),
 '数组与链表', 'Arrays and Linked Lists',
 '最基础的线性数据结构',
 3, TRUE, ARRAY['数组', '链表', 'array', 'linked list']),

('11111111-1111-1111-1111-111111111103',
 (SELECT id FROM subjects WHERE name = '计算机科学'),
 '排序算法', 'Sorting Algorithms',
 '将数据按特定顺序排列的算法集合',
 4, TRUE, ARRAY['排序', '快速排序', '归并排序', 'sorting', 'quicksort']),

('11111111-1111-1111-1111-111111111104',
 (SELECT id FROM subjects WHERE name = '计算机科学'),
 '树与图', 'Trees and Graphs',
 '非线性数据结构，用于表示层级和网络关系',
 4, TRUE, ARRAY['二叉树', '图', 'tree', 'graph', 'binary tree']),

('11111111-1111-1111-1111-111111111105',
 (SELECT id FROM subjects WHERE name = '计算机科学'),
 '操作系统', 'Operating Systems',
 '管理计算机硬件和软件资源的系统软件',
 5, TRUE, ARRAY['操作系统', 'OS', '进程', '内存管理']);

-- 建立知识点关系
INSERT INTO node_relations (source_node_id, target_node_id, relation_type, strength, created_by) VALUES
-- 数组与链表 是 算法与数据结构 的组成部分
('11111111-1111-1111-1111-111111111102', '11111111-1111-1111-1111-111111111101', 'composition', 0.8, 'seed'),
-- 排序算法 依赖 数组与链表
('11111111-1111-1111-1111-111111111102', '11111111-1111-1111-1111-111111111103', 'prerequisite', 0.9, 'seed'),
-- 树与图 是 算法与数据结构 的组成部分
('11111111-1111-1111-1111-111111111104', '11111111-1111-1111-1111-111111111101', 'composition', 0.8, 'seed'),
-- 操作系统 应用 算法与数据结构
('11111111-1111-1111-1111-111111111101', '11111111-1111-1111-1111-111111111105', 'application', 0.7, 'seed');3. 后端架构设计3.1 服务架构图┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│                    /api/v1/galaxy/*                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│  GalaxyService  │ │ TaskService │ │ ExpansionService│
│  ─────────────  │ │ ─────────── │ │ ───────────────│
│ • get_graph()   │ │ • complete()│ │ • expand_nodes()│
│ • spark_node()  │ │ • create()  │ │ • process_queue│
│ • search()      │ │             │ │                 │
│ • apply_decay() │ └──────┬──────┘ └────────┬────────┘
└────────┬────────┘        │                 │
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Event Bus (Redis)                            │
│  • task_completed  • node_expanded  • decay_applied              │
└─────────────────────────────────────────────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + pgvector                         │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Service (Qwen/DeepSeek)                   │
│  • Embedding API  • Chat Completion (节点拓展)                    │
└─────────────────────────────────────────────────────────────────┘3.2 目录结构backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── galaxy/
│   │       │   ├── __init__.py
│   │       │   ├── router.py      # API 路由
│   │       │   ├── schemas.py     # Pydantic 模型
│   │       │   └── dependencies.py
│   │       └── ...
│   ├── services/
│   │   ├── galaxy_service.py      # 星图核心服务
│   │   ├── expansion_service.py   # LLM 拓展服务
│   │   ├── decay_service.py       # 遗忘衰减服务
│   │   └── embedding_service.py   # 向量嵌入服务
│   ├── models/
│   │   ├── knowledge_node.py
│   │   ├── node_relation.py
│   │   ├── user_node_status.py
│   │   └── study_record.py
│   ├── jobs/
│   │   ├── decay_job.py           # 每日衰减任务
│   │   └── expansion_worker.py    # 拓展队列消费者
│   └── core/
│       └── llm_client.py          # LLM 客户端封装
└── seeds/
    ├── sectors.json               # 星域配置
    └── nodes/
        ├── cosmos.json            # 理性星域种子
        ├── tech.json              # 造物星域种子
        └── ...3.3 核心服务实现3.3.1 GalaxyService (星图核心服务)python# backend/app/services/galaxy_service.py

from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeNode, UserNodeStatus, NodeRelation, StudyRecord
from app.services.embedding_service import EmbeddingService
from app.services.expansion_service import ExpansionService
from app.schemas.galaxy import (
    GalaxyGraphResponse, NodeWithStatus, SparkEvent, 
    SparkResult, SearchResult
)


class GalaxyService:
    """知识星图核心服务"""
    
    # 掌握度计算常量
    BASE_MASTERY_POINTS = 5.0
    MAX_MASTERY = 100.0
    
    # 遗忘曲线常量 (艾宾浩斯)
    MEMORY_HALF_LIFE_DAYS = 7.0  # 记忆半衰期
    DECAY_THRESHOLD = 10.0       # 低于此值星星变暗
    
    def __init__(
        self, 
        db: AsyncSession,
        embedding_service: EmbeddingService,
        expansion_service: ExpansionService
    ):
        self.db = db
        self.embedding_service = embedding_service
        self.expansion_service = expansion_service

    # ==========================================
    # 1. 获取星图数据
    # ==========================================
    async def get_galaxy_graph(
        self, 
        user_id: UUID,
        sector_code: Optional[str] = None,
        include_locked: bool = True
    ) -> GalaxyGraphResponse:
        """
        获取用户的知识星图数据
        
        Args:
            user_id: 用户 ID
            sector_code: 可选，筛选特定星域
            include_locked: 是否包含未解锁的节点
        
        Returns:
            GalaxyGraphResponse: 包含节点、关系、用户状态的完整星图数据
        """
        # 1. 查询知识节点 (带用户状态)
        query = (
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id
                )
            )
        )
        
        if sector_code:
            query = query.join(Subject).where(Subject.sector_code == sector_code)
        
        result = await self.db.execute(query)
        nodes_with_status = result.all()
        
        # 2. 过滤未解锁节点 (如果需要)
        if not include_locked:
            nodes_with_status = [
                (node, status) for node, status in nodes_with_status
                if status and status.is_unlocked
            ]
        
        # 3. 查询节点关系
        node_ids = [node.id for node, _ in nodes_with_status]
        relations_query = select(NodeRelation).where(
            NodeRelation.source_node_id.in_(node_ids),
            NodeRelation.target_node_id.in_(node_ids)
        )
        relations_result = await self.db.execute(relations_query)
        relations = relations_result.scalars().all()
        
        # 4. 组装响应
        return GalaxyGraphResponse(
            nodes=[
                NodeWithStatus.from_orm(node, status)
                for node, status in nodes_with_status
            ],
            relations=[rel.to_dict() for rel in relations],
            user_stats=await self._calculate_user_stats(user_id)
        )

    # ==========================================
    # 2. 点亮知识点 (Spark)
    # ==========================================
    async def spark_node(
        self,
        user_id: UUID,
        node_id: UUID,
        study_minutes: int,
        task_id: Optional[UUID] = None,
        trigger_expansion: bool = True
    ) -> SparkResult:
        """
        点亮/增强知识点 (任务完成时调用)
        
        Args:
            user_id: 用户 ID
            node_id: 知识节点 ID
            study_minutes: 学习时长 (分钟)
            task_id: 关联的任务 ID
            trigger_expansion: 是否触发 LLM 拓展
        
        Returns:
            SparkResult: 包含动画事件和拓展状态
        """
        # 1. 获取或创建用户节点状态
        status = await self._get_or_create_status(user_id, node_id)
        
        # 2. 计算掌握度增量
        node = await self.db.get(KnowledgeNode, node_id)
        mastery_delta = self._calculate_mastery_delta(study_minutes, node.importance_level)
        
        # 3. 记录旧状态 (用于判断是否首次点亮/升级)
        old_mastery = status.mastery_score
        is_first_unlock = not status.is_unlocked
        
        # 4. 更新状态
        status.mastery_score = min(status.mastery_score + mastery_delta, self.MAX_MASTERY)
        status.total_study_minutes += study_minutes
        status.study_count += 1
        status.last_study_at = datetime.utcnow()
        status.is_unlocked = True
        
        if is_first_unlock:
            status.first_unlock_at = datetime.utcnow()
        
        # 计算下次复习时间
        status.next_review_at = self._calculate_next_review(status.mastery_score)
        
        # 5. 记录学习历史
        record = StudyRecord(
            user_id=user_id,
            node_id=node_id,
            task_id=task_id,
            study_minutes=study_minutes,
            mastery_delta=mastery_delta,
            record_type='task_complete'
        )
        self.db.add(record)
        
        await self.db.commit()
        
        # 6. 生成动画事件
        spark_event = SparkEvent(
            node_id=node_id,
            node_name=node.name,
            sector_code=node.subject.sector_code if node.subject else 'VOID',
            old_mastery=old_mastery,
            new_mastery=status.mastery_score,
            is_first_unlock=is_first_unlock,
            is_level_up=self._check_level_up(old_mastery, status.mastery_score)
        )
        
        # 7. 触发 LLM 拓展 (异步)
        expansion_queued = False
        if trigger_expansion and status.study_count >= 2:  # 学习 2 次后开始拓展
            await self.expansion_service.queue_expansion(
                trigger_node_id=node_id,
                trigger_task_id=task_id,
                user_id=user_id
            )
            expansion_queued = True
        
        return SparkResult(
            spark_event=spark_event,
            expansion_queued=expansion_queued,
            updated_status=status
        )

    # ==========================================
    # 3. 语义搜索
    # ==========================================
    async def semantic_search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        """
        使用向量相似度搜索知识点
        
        Args:
            user_id: 用户 ID
            query: 搜索查询
            limit: 返回数量限制
            threshold: 相似度阈值 (越小越严格)
        
        Returns:
            List[SearchResult]: 匹配的知识点列表
        """
        # 1. 获取查询向量
        query_embedding = await self.embedding_service.get_embedding(query)
        
        # 2. 向量搜索
        query = (
            select(
                KnowledgeNode,
                KnowledgeNode.embedding.cosine_distance(query_embedding).label('distance')
            )
            .where(KnowledgeNode.embedding.isnot(None))
            .order_by('distance')
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        matches = result.all()
        
        # 3. 过滤并格式化结果
        search_results = []
        for node, distance in matches:
            if distance <= threshold:
                search_results.append(SearchResult(
                    node=node,
                    similarity=1 - distance,  # 转换为相似度
                    user_status=await self._get_user_status(user_id, node.id)
                ))
        
        return search_results

    # ==========================================
    # 4. 任务自动归类
    # ==========================================
    async def auto_classify_task(
        self, 
        task_title: str, 
        task_description: Optional[str] = None
    ) -> Optional[UUID]:
        """
        根据任务标题自动匹配知识点
        
        Args:
            task_title: 任务标题
            task_description: 任务描述 (可选)
        
        Returns:
            Optional[UUID]: 匹配的知识节点 ID，无匹配返回 None
        """
        # 1. 构建搜索文本
        search_text = task_title
        if task_description:
            search_text += f" {task_description}"
        
        # 2. 尝试向量匹配
        try:
            embedding = await self.embedding_service.get_embedding(search_text)
            
            query = (
                select(KnowledgeNode.id)
                .where(KnowledgeNode.embedding.isnot(None))
                .order_by(KnowledgeNode.embedding.cosine_distance(embedding))
                .limit(1)
            )
            
            result = await self.db.execute(query)
            node_id = result.scalar_one_or_none()
            
            return node_id
            
        except Exception as e:
            # 降级：关键词匹配
            return await self._fallback_keyword_match(search_text)

    async def _fallback_keyword_match(self, text: str) -> Optional[UUID]:
        """关键词匹配降级策略"""
        query = (
            select(KnowledgeNode.id)
            .where(KnowledgeNode.keywords.overlap(text.split()))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ==========================================
    # 5. 私有辅助方法
    # ==========================================
    def _calculate_mastery_delta(self, study_minutes: int, importance_level: int) -> float:
        """计算掌握度增量"""
        # 基础分 * 时间系数 * 难度系数
        time_factor = min(study_minutes / 30.0, 2.0)  # 30 分钟为标准，最多 2 倍
        difficulty_factor = 1 + (importance_level - 1) * 0.1  # 重要性越高，增长越多
        
        return self.BASE_MASTERY_POINTS * time_factor * difficulty_factor

    def _check_level_up(self, old_mastery: float, new_mastery: float) -> bool:
        """检查是否升级 (跨越等级阈值)"""
        thresholds = [30, 60, 80, 95]  # 等级阈值
        for threshold in thresholds:
            if old_mastery < threshold <= new_mastery:
                return True
        return False

    def _calculate_next_review(self, mastery_score: float) -> datetime:
        """根据掌握度计算下次复习时间"""
        # 掌握度越高，复习间隔越长
        if mastery_score >= 80:
            days = 14
        elif mastery_score >= 60:
            days = 7
        elif mastery_score >= 30:
            days = 3
        else:
            days = 1
        
        return datetime.utcnow() + timedelta(days=days)

    async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        """获取或创建用户节点状态"""
        query = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == node_id
        )
        result = await self.db.execute(query)
        status = result.scalar_one_or_none()
        
        if not status:
            status = UserNodeStatus(user_id=user_id, node_id=node_id)
            self.db.add(status)
        
        return status

    async def _calculate_user_stats(self, user_id: UUID) -> dict:
        """计算用户统计数据"""
        # 统计各状态节点数量
        query = (
            select(
                func.count().filter(UserNodeStatus.is_unlocked == True).label('unlocked_count'),
                func.count().filter(UserNodeStatus.mastery_score >= 80).label('mastered_count'),
                func.sum(UserNodeStatus.total_study_minutes).label('total_minutes')
            )
            .where(UserNodeStatus.user_id == user_id)
        )
        result = await self.db.execute(query)
        row = result.one()
        
        return {
            'unlocked_count': row.unlocked_count or 0,
            'mastered_count': row.mastered_count or 0,
            'total_study_minutes': row.total_minutes or 0
        }3.3.2 DecayService (遗忘衰减服务)python# backend/app/services/decay_service.py

import math
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserNodeStatus, KnowledgeNode


class DecayService:
    """
    遗忘曲线衰减服务
    
    基于艾宾浩斯遗忘曲线：
    Retention = e^(-t/S)
    其中 t 为时间间隔，S 为记忆稳定性 (与掌握度相关)
    """
    
    # 衰减参数
    BASE_HALF_LIFE_DAYS = 7.0    # 基础半衰期 (天)
    MIN_MASTERY = 5.0            # 最低掌握度 (不会降到 0)
    DECAY_CHECK_INTERVAL = 1     # 检查间隔 (天)
    
    # 掌握度阈值
    THRESHOLD_DIM = 20.0         # 低于此值星星变暗
    THRESHOLD_COLLAPSE = 10.0    # 低于此值可能坍缩
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_daily_decay(self) -> dict:
        """
        每日遗忘衰减任务
        
        Returns:
            dict: 衰减统计 {processed: int, dimmed: int, collapsed: int}
        """
        stats = {'processed': 0, 'dimmed': 0, 'collapsed': 0}
        now = datetime.utcnow()
        
        # 1. 查询需要衰减的节点状态
        # 条件：已解锁 + 未暂停衰减 + 上次学习超过 1 天
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.is_unlocked == True,
                UserNodeStatus.decay_paused == False,
                UserNodeStatus.last_study_at < now - timedelta(days=self.DECAY_CHECK_INTERVAL),
                UserNodeStatus.mastery_score > self.MIN_MASTERY
            )
        )
        
        result = await self.db.execute(query)
        statuses = result.scalars().all()
        
        # 2. 逐个应用衰减
        for status in statuses:
            old_mastery = status.mastery_score
            
            # 计算衰减
            days_elapsed = (now - status.last_study_at).days
            new_mastery = self._calculate_decay(
                current_mastery=status.mastery_score,
                days_elapsed=days_elapsed
            )
            
            # 更新状态
            status.mastery_score = new_mastery
            stats['processed'] += 1
            
            # 检查状态变化
            if old_mastery >= self.THRESHOLD_DIM > new_mastery:
                stats['dimmed'] += 1
            
            if new_mastery < self.THRESHOLD_COLLAPSE and not status.is_collapsed:
                # 标记坍缩风险 (但不自动坍缩)
                stats['collapsed'] += 1
        
        await self.db.commit()
        
        return stats

    def _calculate_decay(self, current_mastery: float, days_elapsed: int) -> float:
        """
        计算衰减后的掌握度
        
        使用修改的艾宾浩斯公式：
        - 高掌握度节点衰减更慢 (更稳定的记忆)
        - 最低不会降到 MIN_MASTERY
        """
        # 动态半衰期：掌握度越高，半衰期越长
        stability_factor = 1 + (current_mastery / 100) * 2  # 1-3 倍
        effective_half_life = self.BASE_HALF_LIFE_DAYS * stability_factor
        
        # 指数衰减
        decay_rate = math.log(2) / effective_half_life
        retention = math.exp(-decay_rate * days_elapsed)
        
        # 计算新掌握度
        decayed_mastery = current_mastery * retention
        
        return max(decayed_mastery, self.MIN_MASTERY)

    async def get_review_suggestions(self, user_id: UUID, limit: int = 5) -> List[dict]:
        """
        获取复习建议
        
        Returns:
            List[dict]: 建议复习的知识点列表
        """
        now = datetime.utcnow()
        
        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode)
            .where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.is_unlocked == True,
                    UserNodeStatus.next_review_at <= now
                )
            )
            .order_by(UserNodeStatus.mastery_score.asc())  # 优先复习低掌握度
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                'node_id': node.id,
                'node_name': node.name,
                'sector_code': node.subject.sector_code if node.subject else 'VOID',
                'current_mastery': status.mastery_score,
                'days_since_study': (now - status.last_study_at).days,
                'urgency': 'high' if status.mastery_score < self.THRESHOLD_DIM else 'normal'
            }
            for status, node in rows
        ]

    async def pause_decay(self, user_id: UUID, node_id: UUID, pause: bool = True):
        """暂停/恢复特定节点的衰减"""
        query = select(UserNodeStatus).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.node_id == node_id
        )
        result = await self.db.execute(query)
        status = result.scalar_one_or_none()
        
        if status:
            status.decay_paused = pause
            await self.db.commit()3.3.3 EmbeddingService (向量嵌入服务)python# backend/app/services/embedding_service.py

from typing import List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class EmbeddingService:
    """
    文本向量嵌入服务
    
    支持多个 LLM 提供商：
    - Qwen (通义千问)
    - DeepSeek
    - OpenAI (备用)
    """
    
    EMBEDDING_DIM = 1536
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER  # 'qwen' | 'deepseek' | 'openai'
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本的向量表示
        
        Args:
            text: 输入文本
        
        Returns:
            List[float]: 1536 维向量
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            if self.provider == 'qwen':
                return await self._qwen_embedding(client, text)
            elif self.provider == 'deepseek':
                return await self._deepseek_embedding(client, text)
            else:
                return await self._openai_embedding(client, text)

    async def _qwen_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """通义千问 Embedding API"""
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "text-embedding-v2",
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def _deepseek_embedding(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """DeepSeek Embedding API"""
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "deepseek-embedding",
                "input": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]

    async def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取向量"""
        # 大多数 API 支持批量请求
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": "text-embedding-v2",
                    "input": texts
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # 按顺序返回
            embeddings = [None] * len(texts)
            for item in data["data"]:
                embeddings[item["index"]] = item["embedding"]
            
            return embeddings3.4 API 路由定义python# backend/app/api/v1/galaxy/router.py

from fastapi import APIRouter, Depends, Query, HTTPException
from uuid import UUID
from typing import Optional

from app.api.deps import get_current_user, get_galaxy_service
from app.services.galaxy_service import GalaxyService
from app.schemas.galaxy import (
    GalaxyGraphResponse, SparkRequest, SparkResult,
    SearchRequest, SearchResponse, NodeDetailResponse,
    ReviewSuggestionsResponse
)

router = APIRouter(prefix="/galaxy", tags=["Knowledge Galaxy"])


@router.get("/graph", response_model=GalaxyGraphResponse)
async def get_galaxy_graph(
    sector_code: Optional[str] = Query(None, description="筛选特定星域"),
    include_locked: bool = Query(True, description="是否包含未解锁节点"),
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取用户的知识星图数据
    
    返回所有知识节点、关系和用户状态，用于前端渲染完整星图。
    """
    return await galaxy_service.get_galaxy_graph(
        user_id=current_user.id,
        sector_code=sector_code,
        include_locked=include_locked
    )


@router.post("/node/{node_id}/spark", response_model=SparkResult)
async def spark_node(
    node_id: UUID,
    request: SparkRequest,
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    点亮/增强知识点
    
    通常在任务完成时由 TaskService 调用，也可手动触发复习。
    返回动画事件数据供前端播放飞升动画。
    """
    return await galaxy_service.spark_node(
        user_id=current_user.id,
        node_id=node_id,
        study_minutes=request.study_minutes,
        task_id=request.task_id,
        trigger_expansion=request.trigger_expansion
    )


@router.get("/node/{node_id}", response_model=NodeDetailResponse)
async def get_node_detail(
    node_id: UUID,
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取知识点详情
    
    包括：基础信息、关联节点、用户学习历史、推荐资源
    """
    return await galaxy_service.get_node_detail(
        user_id=current_user.id,
        node_id=node_id
    )


@router.post("/search", response_model=SearchResponse)
async def search_nodes(
    request: SearchRequest,
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    语义搜索知识点
    
    使用向量相似度搜索，支持自然语言查询。
    """
    results = await galaxy_service.semantic_search(
        user_id=current_user.id,
        query=request.query,
        limit=request.limit,
        threshold=request.threshold
    )
    return SearchResponse(results=results, query=request.query)


@router.get("/review/suggestions", response_model=ReviewSuggestionsResponse)
async def get_review_suggestions(
    limit: int = Query(5, ge=1, le=20),
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取复习建议
    
    基于遗忘曲线，返回最需要复习的知识点。
    """
    suggestions = await galaxy_service.decay_service.get_review_suggestions(
        user_id=current_user.id,
        limit=limit
    )
    return ReviewSuggestionsResponse(suggestions=suggestions)


@router.post("/node/{node_id}/pause-decay")
async def toggle_decay_pause(
    node_id: UUID,
    pause: bool = Query(True),
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    暂停/恢复知识点的遗忘衰减
    
    用户可以手动暂停某些重要知识点的衰减。
    """
    await galaxy_service.decay_service.pause_decay(
        user_id=current_user.id,
        node_id=node_id,
        pause=pause
    )
    return {"success": True, "decay_paused": pause}


@router.get("/stats")
async def get_galaxy_stats(
    current_user = Depends(get_current_user),
    galaxy_service: GalaxyService = Depends(get_galaxy_service)
):
    """
    获取星图统计数据
    
    返回：解锁节点数、掌握节点数、各星域分布等
    """
    return await galaxy_service.get_user_stats(current_user.id)3.5 Pydantic Schemaspython# backend/app/schemas/galaxy.py

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class SectorCode(str, Enum):
    COSMOS = "COSMOS"
    TECH = "TECH"
    ART = "ART"
    CIVILIZATION = "CIVILIZATION"
    LIFE = "LIFE"
    WISDOM = "WISDOM"
    VOID = "VOID"


class NodeStatus(str, Enum):
    LOCKED = "locked"       # 未解锁
    UNLIT = "unlit"         # 已解锁但未学习
    GLIMMER = "glimmer"     # 微光 (0-30)
    SHINING = "shining"     # 闪耀 (30-80)
    BRILLIANT = "brilliant" # 璀璨 (80-95)
    MASTERED = "mastered"   # 精通 (95-100)
    COLLAPSED = "collapsed" # 坍缩


# ==========================================
# 请求模型
# ==========================================
class SparkRequest(BaseModel):
    study_minutes: int = Field(..., ge=1, le=480, description="学习时长(分钟)")
    task_id: Optional[UUID] = Field(None, description="关联的任务ID")
    trigger_expansion: bool = Field(True, description="是否触发知识拓展")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(10, ge=1, le=50)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


# ==========================================
# 响应模型
# ==========================================
class NodeBase(BaseModel):
    id: UUID
    name: str
    name_en: Optional[str]
    description: Optional[str]
    importance_level: int
    sector_code: SectorCode
    is_seed: bool
    
    class Config:
        from_attributes = True


class UserStatusInfo(BaseModel):
    mastery_score: float
    total_study_minutes: int
    study_count: int
    is_unlocked: bool
    is_collapsed: bool
    is_favorite: bool
    last_study_at: Optional[datetime]
    next_review_at: Optional[datetime]
    decay_paused: bool
    
    # 计算属性
    status: NodeStatus
    brightness: float  # 0-1，用于前端渲染


class NodeWithStatus(NodeBase):
    """节点 + 用户状态"""
    user_status: Optional[UserStatusInfo]
    
    # 布局信息
    position_angle: float  # 在星域中的角度
    position_radius: float # 距离中心的半径
    
    @classmethod
    def from_orm(cls, node, status):
        user_status = None
        if status:
            # 计算视觉状态
            visual_status = cls._calculate_status(status)
            brightness = cls._calculate_brightness(status)
            
            user_status = UserStatusInfo(
                mastery_score=status.mastery_score,
                total_study_minutes=status.total_study_minutes,
                study_count=status.study_count,
                is_unlocked=status.is_unlocked,
                is_collapsed=status.is_collapsed,
                is_favorite=status.is_favorite,
                last_study_at=status.last_study_at,
                next_review_at=status.next_review_at,
                decay_paused=status.decay_paused,
                status=visual_status,
                brightness=brightness
            )
        
        return cls(
            id=node.id,
            name=node.name,
            name_en=node.name_en,
            description=node.description,
            importance_level=node.importance_level,
            sector_code=node.subject.sector_code if node.subject else SectorCode.VOID,
            is_seed=node.is_seed,
            user_status=user_status,
            position_angle=node.subject.position_angle if node.subject else 0,
            position_radius=100 + node.importance_level * 30  # 简化计算
        )
    
    @staticmethod
    def _calculate_status(status) -> NodeStatus:
        if status.is_collapsed:
            return NodeStatus.COLLAPSED
        if not status.is_unlocked:
            return NodeStatus.LOCKED
        
        score = status.mastery_score
        if score >= 95:
            return NodeStatus.MASTERED
        elif score >= 80:
            return NodeStatus.BRILLIANT
        elif score >= 30:
            return NodeStatus.SHINING
        elif score > 0:
            return NodeStatus.GLIMMER
        else:
            return NodeStatus.UNLIT
    
    @staticmethod
    def _calculate_brightness(status) -> float:
        if not status.is_unlocked:
            return 0.2
        if status.is_collapsed:
            return 0.1
        return 0.3 + (status.mastery_score / 100) * 0.7


class NodeRelationInfo(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    relation_type: str
    strength: float


class GalaxyUserStats(BaseModel):
    total_nodes: int
    unlocked_count: int
    mastered_count: int
    total_study_minutes: int
    sector_distribution: dict  # {sector_code: count}
    streak_days: int  # 连续学习天数


class GalaxyGraphResponse(BaseModel):
    """星图完整数据响应"""
    nodes: List[NodeWithStatus]
    relations: List[NodeRelationInfo]
    user_stats: GalaxyUserStats


class SparkEvent(BaseModel):
    """点亮动画事件"""
    node_id: UUID
    node_name: str
    sector_code: SectorCode
    old_mastery: float
    new_mastery: float
    is_first_unlock: bool  # 首次点亮 (播放特殊动画)
    is_level_up: bool      # 升级 (跨越阈值)
    
    # 前端动画参数
    particle_count: int = 20
    animation_duration_ms: int = 1500


class SparkResult(BaseModel):
    spark_event: SparkEvent
    expansion_queued: bool
    expanded_nodes: Optional[List[NodeBase]] = None  # 如果同步返回


class SearchResultItem(BaseModel):
    node: NodeBase
    similarity: float
    user_status: Optional[UserStatusInfo]


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_count: int


class ReviewSuggestion(BaseModel):
    node_id: UUID
    node_name: str
    sector_code: SectorCode
    current_mastery: float
    days_since_study: int
    urgency: str  # 'high' | 'normal'


class ReviewSuggestionsResponse(BaseModel):
    suggestions: List[ReviewSuggestion]
    next_review_count: int  # 未来 7 天需要复习的总数4. 前端架构与视觉实现4.1 目录结构lib/
├── features/
│   └── galaxy/
│       ├── data/
│       │   ├── galaxy_repository.dart      # 数据仓库
│       │   └── galaxy_api.dart             # API 调用
│       ├── domain/
│       │   ├── models/
│       │   │   ├── knowledge_node.dart
│       │   │   ├── node_relation.dart
│       │   │   ├── user_node_status.dart
│       │   │   └── spark_event.dart
│       │   └── galaxy_state.dart
│       ├── presentation/
│       │   ├── screens/
│       │   │   ├── galaxy_screen.dart      # 主屏幕
│       │   │   └── node_detail_screen.dart # 节点详情
│       │   ├── widgets/
│       │   │   ├── galaxy_viewport.dart    # 可交互视口
│       │   │   ├── flame_core.dart         # Shader 火苗
│       │   │   ├── star_node.dart          # 星星节点
│       │   │   ├── constellation_lines.dart# 星座连线
│       │   │   ├── particle_system.dart    # 粒子系统
│       │   │   └── sector_label.dart       # 星域标签
│       │   └── painters/
│       │       ├── deep_space_painter.dart # 深空背景
│       │       └── node_painter.dart       # 节点绘制
│       ├── controllers/
│       │   ├── galaxy_controller.dart      # 主控制器
│       │   └── animation_controller.dart   # 动画控制
│       └── shaders/
│           ├── flame.frag                  # 火焰 Shader
│           └── glow.frag                   # 发光效果
├── core/
│   └── theme/
│       └── galaxy_colors.dart              # 颜色常量
└── shared/
    └── widgets/
        └── animated_counter.dart           # 数字动画4.2 组件树结构GalaxyScreen
├── Scaffold
│   ├── AppBar (半透明，显示统计)
│   └── Stack
│       ├── DeepSpaceBackground (CustomPainter: 静态星尘)
│       │
│       ├── GalaxyViewport (InteractiveViewer)
│       │   └── Stack (size: 2000x2000 逻辑像素)
│       │       ├── ConstellationLines (CustomPainter: 连线)
│       │       ├── for each sector:
│       │       │   └── SectorCluster
│       │       │       ├── SectorLabel (星域名称)
│       │       │       └── for each node in sector:
│       │       │           └── StarNode (GestureDetector + AnimatedWidget)
│       │       └── FlameCore (ShaderMask, 始终居中)
│       │
│       ├── ParticleLayer (飞升粒子动画，positioned: full screen)
│       │
│       └── BottomSheet (节点详情面板，可拖拽展开)
│
└── FloatingActionButton (搜索/创建)4.3 核心组件实现4.3.1 GalaxyScreen (主屏幕)dart// lib/features/galaxy/presentation/screens/galaxy_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class GalaxyScreen extends ConsumerStatefulWidget {
  const GalaxyScreen({super.key});

  @override
  ConsumerState<GalaxyScreen> createState() => _GalaxyScreenState();
}

class _GalaxyScreenState extends ConsumerState<GalaxyScreen>
    with TickerProviderStateMixin {
  final TransformationController _transformController = TransformationController();
  late AnimationController _flameAnimController;
  
  // 粒子系统
  final List<AscensionParticle> _particles = [];
  
  @override
  void initState() {
    super.initState();
    _flameAnimController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();
    
    // 初始化时居中到火苗位置
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _centerToFlame();
    });
  }

  void _centerToFlame() {
    final screenSize = MediaQuery.of(context).size;
    final scale = 1.0;
    
    // 居中到 (1000, 1000) - 火苗位置
    _transformController.value = Matrix4.identity()
      ..translate(
        screenSize.width / 2 - 1000 * scale,
        screenSize.height / 2 - 1000 * scale,
      )
      ..scale(scale);
  }

  @override
  Widget build(BuildContext context) {
    final galaxyState = ref.watch(galaxyControllerProvider);
    
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A1A), // 深空黑
      extendBodyBehindAppBar: true,
      appBar: _buildAppBar(galaxyState),
      body: Stack(
        children: [
          // 1. 深空背景 (静态)
          const DeepSpaceBackground(),
          
          // 2. 可交互的星图视口
          InteractiveViewer(
            transformationController: _transformController,
            minScale: 0.3,
            maxScale: 3.0,
            boundaryMargin: const EdgeInsets.all(500),
            child: SizedBox(
              width: 2000,
              height: 2000,
              child: Stack(
                children: [
                  // 星座连线
                  if (galaxyState.relations.isNotEmpty)
                    ConstellationLines(
                      relations: galaxyState.relations,
                      nodes: galaxyState.nodePositions,
                    ),
                  
                  // 星域和节点
                  ...galaxyState.sectors.map((sector) => SectorCluster(
                    sector: sector,
                    nodes: galaxyState.getNodesInSector(sector.code),
                    onNodeTap: _handleNodeTap,
                  )),
                  
                  // 中心火苗
                  Positioned(
                    left: 1000 - 60, // 居中
                    top: 1000 - 80,
                    child: FlameCore(
                      animation: _flameAnimController,
                      intensity: galaxyState.flameIntensity,
                    ),
                  ),
                ],
              ),
            ),
          ),
          
          // 3. 粒子层 (飞升动画)
          if (_particles.isNotEmpty)
            ParticleLayer(
              particles: _particles,
              onParticleComplete: _handleParticleComplete,
            ),
          
          // 4. 底部统计面板
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: GalaxyStatsBar(stats: galaxyState.userStats),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _showSearchDialog,
        backgroundColor: Colors.white.withOpacity(0.1),
        child: const Icon(Icons.search, color: Colors.white),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(GalaxyState state) {
    return AppBar(
      backgroundColor: Colors.transparent,
      elevation: 0,
      title: Row(
        children: [
          const Icon(Icons.auto_awesome, color: Colors.amber, size: 20),
          const SizedBox(width: 8),
          Text(
            '知识星图',
            style: TextStyle(
              color: Colors.white.withOpacity(0.9),
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
      actions: [
        // 复习提醒徽章
        if (state.reviewSuggestions.isNotEmpty)
          IconButton(
            icon: Badge(
              label: Text('${state.reviewSuggestions.length}'),
              child: const Icon(Icons.notifications_outlined, color: Colors.white70),
            ),
            onPressed: _showReviewSuggestions,
          ),
      ],
    );
  }

  void _handleNodeTap(KnowledgeNode node) {
    // 显示节点详情底部面板
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => NodeDetailSheet(node: node),
    );
  }

  /// 播放飞升动画
  void playAscension(SparkEvent event) {
    final targetNode = ref.read(galaxyControllerProvider).getNode(event.nodeId);
    if (targetNode == null) return;
    
    setState(() {
      // 生成粒子
      for (int i = 0; i < event.particleCount; i++) {
        _particles.add(AscensionParticle(
          id: UniqueKey(),
          startPosition: const Offset(1000, 1000), // 火苗中心
          endPosition: targetNode.position,
          color: _getSectorColor(event.sectorCode),
          delay: Duration(milliseconds: i * 50),
        ));
      }
    });
  }

  void _handleParticleComplete(AscensionParticle particle) {
    setState(() {
      _particles.remove(particle);
    });
    
    // 触发目标节点的 Bloom 动画
    ref.read(galaxyControllerProvider.notifier).triggerNodeBloom(particle.targetNodeId);
  }

  Color _getSectorColor(String sectorCode) {
    return switch (sectorCode) {
      'COSMOS' => const Color(0xFF00BFFF),
      'TECH' => const Color(0xFFC0C0C0),
      'ART' => const Color(0xFFFF00FF),
      'CIVILIZATION' => const Color(0xFFFFD700),
      'LIFE' => const Color(0xFF32CD32),
      'WISDOM' => const Color(0xFFFFFFFF),
      _ => const Color(0xFF2F4F4F),
    };
  }

  void _showSearchDialog() {
    showDialog(
      context: context,
      builder: (context) => GalaxySearchDialog(
        onNodeSelected: (node) {
          Navigator.pop(context);
          _focusOnNode(node);
        },
      ),
    );
  }

  void _focusOnNode(KnowledgeNode node) {
    // 平滑移动到目标节点
    final screenSize = MediaQuery.of(context).size;
    final targetMatrix = Matrix4.identity()
      ..translate(
        screenSize.width / 2 - node.position.dx,
        screenSize.height / 2 - node.position.dy,
      )
      ..scale(1.5); // 放大
    
    // TODO: 使用动画过渡
    _transformController.value = targetMatrix;
  }

  @override
  void dispose() {
    _flameAnimController.dispose();
    _transformController.dispose();
    super.dispose();
  }
}4.3.2 FlameCore (Shader 火苗)dart// lib/features/galaxy/presentation/widgets/flame_core.dart

import 'package:flutter/material.dart';
import 'dart:ui' as ui;

class FlameCore extends StatefulWidget {
  final Animation<double> animation;
  final double intensity; // 0-1，影响火焰大小和亮度
  
  const FlameCore({
    super.key,
    required this.animation,
    this.intensity = 0.7,
  });

  @override
  State<FlameCore> createState() => _FlameCoreState();
}

class _FlameCoreState extends State<FlameCore> {
  ui.FragmentProgram? _program;
  ui.FragmentShader? _shader;
  bool _shaderLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadShader();
  }

  Future<void> _loadShader() async {
    try {
      _program = await ui.FragmentProgram.fromAsset('shaders/flame.frag');
      _shader = _program!.fragmentShader();
      setState(() => _shaderLoaded = true);
    } catch (e) {
      debugPrint('Shader loading failed: $e');
      // Shader 加载失败时使用降级方案
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_shaderLoaded) {
      // 降级方案：使用渐变 + 动画模拟火焰
      return _buildFallbackFlame();
    }
    
    return AnimatedBuilder(
      animation: widget.animation,
      builder: (context, child) {
        return CustomPaint(
          size: const Size(120, 160),
          painter: FlamePainter(
            shader: _shader!,
            time: widget.animation.value * 10,
            intensity: widget.intensity,
          ),
        );
      },
    );
  }

  Widget _buildFallbackFlame() {
    return AnimatedBuilder(
      animation: widget.animation,
      builder: (context, child) {
        final scale = 0.9 + 0.1 * (0.5 + 0.5 * 
            (widget.animation.value * 6.28).sin());
        
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 120,
            height: 160,
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0, 0.5),
                radius: 0.8,
                colors: [
                  Colors.white,
                  Colors.amber.shade300,
                  Colors.orange,
                  Colors.deepOrange,
                  Colors.transparent,
                ],
                stops: const [0.0, 0.2, 0.4, 0.7, 1.0],
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.orange.withOpacity(0.6),
                  blurRadius: 40,
                  spreadRadius: 20,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}


class FlamePainter extends CustomPainter {
  final ui.FragmentShader shader;
  final double time;
  final double intensity;

  FlamePainter({
    required this.shader,
    required this.time,
    required this.intensity,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 设置 uniform 变量
    shader.setFloat(0, size.width);   // u_resolution.x
    shader.setFloat(1, size.height);  // u_resolution.y
    shader.setFloat(2, time);         // u_time
    shader.setFloat(3, intensity);    // u_intensity
    
    // 颜色混合 (RGB)
    shader.setFloat(4, 1.0);  // r
    shader.setFloat(5, 0.6);  // g
    shader.setFloat(6, 0.2);  // b

    final paint = Paint()..shader = shader;
    canvas.drawRect(
      Rect.fromLTWH(0, 0, size.width, size.height),
      paint,
    );
  }

  @override
  bool shouldRepaint(FlamePainter oldDelegate) {
    return oldDelegate.time != time || oldDelegate.intensity != intensity;
  }
}4.3.3 GLSL Shader (火焰效果)glsl// assets/shaders/flame.frag

#version 460 core

#include <flutter/runtime_effect.glsl>

precision mediump float;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_intensity;
uniform vec3 u_color;

out vec4 fragColor;

// Simplex 噪声函数
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec3 permute(vec3 x) { return mod289(((x*34.0)+1.0)*x); }

float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                       -0.577350269189626, 0.024390243902439);
    vec2 i  = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                            + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy),
                           dot(x12.zw,x12.zw)), 0.0);
    m = m*m;
    m = m*m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
    vec3 g;
    g.x  = a0.x  * x0.x  + h.x  * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
}

// FBM (分形布朗运动)
float fbm(vec2 st) {
    float value = 0.0;
    float amplitude = 0.5;
    float frequency = 1.0;
    
    for (int i = 0; i < 5; i++) {
        value += amplitude * snoise(st * frequency);
        frequency *= 2.0;
        amplitude *= 0.5;
    }
    
    return value;
}

void main() {
    vec2 st = FlutterFragCoord().xy / u_resolution;
    
    // 调整坐标系，火焰根部在底部中心
    st.x = st.x * 2.0 - 1.0;  // -1 to 1
    st.y = 1.0 - st.y;        // 翻转 Y
    
    // 火焰形状 (锥形)
    float shape = 1.0 - length(vec2(st.x * 1.5, st.y - 0.2));
    shape = smoothstep(0.0, 0.8 * u_intensity, shape);
    
    // 动态噪声扰动
    vec2 q = vec2(0.0);
    q.x = fbm(st + 0.1 * u_time);
    q.y = fbm(st + vec2(1.0));
    
    vec2 r = vec2(0.0);
    r.x = fbm(st + 1.0 * q + vec2(1.7, 9.2) + 0.15 * u_time);
    r.y = fbm(st + 1.0 * q + vec2(8.3, 2.8) + 0.126 * u_time);
    
    float noise = fbm(st + r);
    
    // 合并形状和噪声
    float flame = shape * (0.5 + 0.5 * noise);
    flame = smoothstep(0.1, 0.9, flame);
    
    // 颜色渐变 (白 → 黄 → 橙 → 红)
    vec3 color = mix(
        vec3(0.1, 0.0, 0.0),       // 边缘暗红
        vec3(1.0, 0.9, 0.7),       // 核心亮白
        pow(flame, 1.5)
    );
    
    color = mix(color, u_color, 0.3); // 混入自定义颜色
    
    // 发光效果
    float glow = exp(-3.0 * length(st - vec2(0.0, 0.3))) * u_intensity;
    color += vec3(1.0, 0.6, 0.2) * glow * 0.5;
    
    fragColor = vec4(color, flame);
}4.3.4 StarNode (星星节点)dart// lib/features/galaxy/presentation/widgets/star_node.dart

import 'package:flutter/material.dart';

class StarNode extends StatefulWidget {
  final KnowledgeNode node;
  final UserNodeStatus? status;
  final VoidCallback onTap;
  
  const StarNode({
    super.key,
    required this.node,
    this.status,
    required this.onTap,
  });

  @override
  State<StarNode> createState() => _StarNodeState();
}

class _StarNodeState extends State<StarNode> 
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  bool _isHovered = false;
  
  // 正在播放 Bloom 动画
  bool _blooming = false;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    
    // 根据状态决定是否播放脉冲动画
    if (_shouldPulse) {
      _pulseController.repeat(reverse: true);
    }
  }

  bool get _shouldPulse {
    if (widget.status == null) return false;
    // 高掌握度节点持续脉冲
    return widget.status!.masteryScore >= 80;
  }

  @override
  Widget build(BuildContext context) {
    final size = _calculateSize();
    final color = _calculateColor();
    final brightness = widget.status?.brightness ?? 0.2;
    
    return GestureDetector(
      onTap: widget.onTap,
      child: MouseRegion(
        onEnter: (_) => setState(() => _isHovered = true),
        onExit: (_) => setState(() => _isHovered = false),
        child: AnimatedBuilder(
          animation: _pulseController,
          builder: (context, child) {
            final pulseScale = _shouldPulse 
                ? 1.0 + 0.1 * _pulseController.value 
                : 1.0;
            final hoverScale = _isHovered ? 1.2 : 1.0;
            
            return Transform.scale(
              scale: pulseScale * hoverScale * (_blooming ? 1.5 : 1.0),
              child: _buildStar(size, color, brightness),
            );
          },
        ),
      ),
    );
  }

  Widget _buildStar(double size, Color color, double brightness) {
    // 坍缩状态特殊处理
    if (widget.status?.isCollapsed == true) {
      return _buildCollapsedStar(size);
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
            color.withOpacity(brightness * 0.4),
            Colors.transparent,
          ],
          stops: const [0.0, 0.3, 0.6, 1.0],
        ),
        boxShadow: brightness > 0.5 ? [
          BoxShadow(
            color: color.withOpacity(0.6),
            blurRadius: size * 0.8,
            spreadRadius: size * 0.2,
          ),
        ] : null,
      ),
      child: _isHovered ? _buildLabel() : null,
    );
  }

  Widget _buildCollapsedStar(double size) {
    // 坍缩星：黑色核心 + 红色脉冲边缘
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                Colors.black,
                Colors.red.withOpacity(0.3 + 0.3 * _pulseController.value),
                Colors.transparent,
              ],
              stops: const [0.3, 0.6, 1.0],
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.red.withOpacity(0.5),
                blurRadius: size * 0.5,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildLabel() {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.black.withOpacity(0.7),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          widget.node.name,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 10,
            fontWeight: FontWeight.w500,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
      ),
    );
  }

  double _calculateSize() {
    // 基础大小根据重要性等级
    final baseSize = 20.0 + widget.node.importanceLevel * 8.0;
    
    // 掌握度影响大小
    final masteryBonus = (widget.status?.masteryScore ?? 0) / 100 * 10;
    
    return baseSize + masteryBonus;
  }

  Color _calculateColor() {
    return switch (widget.node.sectorCode) {
      'COSMOS' => const Color(0xFF00BFFF),
      'TECH' => const Color(0xFFC0C0C0),
      'ART' => const Color(0xFFFF00FF),
      'CIVILIZATION' => const Color(0xFFFFD700),
      'LIFE' => const Color(0xFF32CD32),
      'WISDOM' => const Color(0xFFFFFFFF),
      _ => const Color(0xFF2F4F4F),
    };
  }

  /// 触发 Bloom 动画 (粒子到达时调用)
  void triggerBloom() {
    setState(() => _blooming = true);
    
    Future.delayed(const Duration(milliseconds: 500), () {
      if (mounted) {
        setState(() => _blooming = false);
      }
    });
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }
}4.3.5 ParticleSystem (飞升粒子动画)dart// lib/features/galaxy/presentation/widgets/particle_system.dart

import 'package:flutter/material.dart';
import 'dart:math' as math;

class AscensionParticle {
  final Key id;
  final Offset startPosition;
  final Offset endPosition;
  final Color color;
  final Duration delay;
  final UUID targetNodeId;
  
  AscensionParticle({
    required this.id,
    required this.startPosition,
    required this.endPosition,
    required this.color,
    required this.targetNodeId,
    this.delay = Duration.zero,
  });
}


class ParticleLayer extends StatelessWidget {
  final List<AscensionParticle> particles;
  final void Function(AscensionParticle) onParticleComplete;
  
  const ParticleLayer({
    super.key,
    required this.particles,
    required this.onParticleComplete,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: particles.map((particle) => 
        _AnimatedParticle(
          key: particle.id,
          particle: particle,
          onComplete: () => onParticleComplete(particle),
        ),
      ).toList(),
    );
  }
}


class _AnimatedParticle extends StatefulWidget {
  final AscensionParticle particle;
  final VoidCallback onComplete;

  const _AnimatedParticle({
    super.key,
    required this.particle,
    required this.onComplete,
  });

  @override
  State<_AnimatedParticle> createState() => _AnimatedParticleState();
}

class _AnimatedParticleState extends State<_AnimatedParticle>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _progressAnimation;
  late Animation<double> _opacityAnimation;
  
  // 贝塞尔曲线控制点
  late Offset _controlPoint;
  
  // 拖尾位置历史
  final List<Offset> _trail = [];
  static const int _maxTrailLength = 10;

  @override
  void initState() {
    super.initState();
    
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    
    _progressAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOutCubic,
    );
    
    _opacityAnimation = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.7, 1.0, curve: Curves.easeOut),
      ),
    );
    
    // 计算贝塞尔控制点 (在路径中垂线上随机偏移)
    _calculateControlPoint();
    
    // 延迟后开始动画
    Future.delayed(widget.particle.delay, () {
      if (mounted) {
        _controller.forward().whenComplete(widget.onComplete);
      }
    });
    
    // 监听动画更新拖尾
    _controller.addListener(_updateTrail);
  }

  void _calculateControlPoint() {
    final start = widget.particle.startPosition;
    final end = widget.particle.endPosition;
    
    // 中点
    final midPoint = Offset(
      (start.dx + end.dx) / 2,
      (start.dy + end.dy) / 2,
    );
    
    // 路径向量
    final direction = end - start;
    
    // 垂直向量 (归一化后乘以偏移量)
    final perpendicular = Offset(-direction.dy, direction.dx);
    final normalizedPerp = perpendicular / perpendicular.distance;
    
    // 随机偏移 (正负随机)
    final random = math.Random();
    final offsetMagnitude = direction.distance * 0.3 * (random.nextBool() ? 1 : -1);
    
    _controlPoint = midPoint + normalizedPerp * offsetMagnitude;
  }

  void _updateTrail() {
    final currentPos = _calculatePosition(_progressAnimation.value);
    _trail.add(currentPos);
    
    if (_trail.length > _maxTrailLength) {
      _trail.removeAt(0);
    }
  }

  Offset _calculatePosition(double t) {
    final start = widget.particle.startPosition;
    final end = widget.particle.endPosition;
    final control = _controlPoint;
    
    // 二阶贝塞尔曲线
    final x = math.pow(1 - t, 2) * start.dx +
              2 * (1 - t) * t * control.dx +
              math.pow(t, 2) * end.dx;
    final y = math.pow(1 - t, 2) * start.dy +
              2 * (1 - t) * t * control.dy +
              math.pow(t, 2) * end.dy;
    
    return Offset(x, y);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          size: Size.infinite,
          painter: _ParticlePainter(
            position: _calculatePosition(_progressAnimation.value),
            trail: List.from(_trail),
            color: widget.particle.color,
            opacity: _opacityAnimation.value,
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}


class _ParticlePainter extends CustomPainter {
  final Offset position;
  final List<Offset> trail;
  final Color color;
  final double opacity;

  _ParticlePainter({
    required this.position,
    required this.trail,
    required this.color,
    required this.opacity,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // 绘制拖尾
    if (trail.length >= 2) {
      final trailPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;
      
      for (int i = 1; i < trail.length; i++) {
        final progress = i / trail.length;
        trailPaint
          ..strokeWidth = 3.0 * progress
          ..color = color.withOpacity(opacity * progress * 0.5);
        
        canvas.drawLine(trail[i - 1], trail[i], trailPaint);
      }
    }
    
    // 绘制粒子主体
    final particlePaint = Paint()
      ..color = Colors.white.withOpacity(opacity)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 4);
    
    canvas.drawCircle(position, 6, particlePaint);
    
    // 绘制发光
    final glowPaint = Paint()
      ..color = color.withOpacity(opacity * 0.6)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 12);
    
    canvas.drawCircle(position, 10, glowPaint);
  }

  @override
  bool shouldRepaint(_ParticlePainter oldDelegate) => true;
}4.3.6 ConstellationLines (星座连线)dart// lib/features/galaxy/presentation/widgets/constellation_lines.dart

import 'package:flutter/material.dart';

class ConstellationLines extends StatelessWidget {
  final List<NodeRelation> relations;
  final Map<UUID, Offset> nodePositions;
  
  const ConstellationLines({
    super.key,
    required this.relations,
    required this.nodePositions,
  });

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size.infinite,
      painter: _ConstellationPainter(
        relations: relations,
        nodePositions: nodePositions,
      ),
    );
  }
}


class _ConstellationPainter extends CustomPainter {
  final List<NodeRelation> relations;
  final Map<UUID, Offset> nodePositions;

  _ConstellationPainter({
    required this.relations,
    required this.nodePositions,
  });

  @override
  void paint(Canvas canvas, Size size) {
    for (final relation in relations) {
      final startPos = nodePositions[relation.sourceNodeId];
      final endPos = nodePositions[relation.targetNodeId];
      
      if (startPos == null || endPos == null) continue;
      
      _drawConnection(canvas, startPos, endPos, relation);
    }
  }

  void _drawConnection(
    Canvas canvas, 
    Offset start, 
    Offset end, 
    NodeRelation relation
  ) {
    final color = _getRelationColor(relation.relationType);
    final opacity = relation.strength * 0.6;
    
    // 主线
    final linePaint = Paint()
      ..color = color.withOpacity(opacity)
      ..strokeWidth = 1.0 + relation.strength
      ..style = PaintingStyle.stroke;
    
    canvas.drawLine(start, end, linePaint);
    
    // 发光效果
    final glowPaint = Paint()
      ..color = color.withOpacity(opacity * 0.3)
      ..strokeWidth = 4.0
      ..style = PaintingStyle.stroke
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, 3);
    
    canvas.drawLine(start, end, glowPaint);
    
    // 如果是前置关系，绘制箭头
    if (relation.relationType == 'prerequisite') {
      _drawArrow(canvas, start, end, color.withOpacity(opacity));
    }
  }

  void _drawArrow(Canvas canvas, Offset start, Offset end, Color color) {
    final direction = (end - start);
    final normalized = direction / direction.distance;
    
    // 箭头位置 (在线段 70% 处)
    final arrowPos = start + direction * 0.7;
    
    // 箭头大小
    const arrowSize = 8.0;
    
    // 计算箭头两翼
    final perpendicular = Offset(-normalized.dy, normalized.dx);
    final arrowLeft = arrowPos - normalized * arrowSize + perpendicular * arrowSize * 0.5;
    final arrowRight = arrowPos - normalized * arrowSize - perpendicular * arrowSize * 0.5;
    
    final arrowPath = Path()
      ..moveTo(arrowPos.dx, arrowPos.dy)
      ..lineTo(arrowLeft.dx, arrowLeft.dy)
      ..lineTo(arrowRight.dx, arrowRight.dy)
      ..close();
    
    canvas.drawPath(arrowPath, Paint()..color = color);
  }

  Color _getRelationColor(String relationType) {
    return switch (relationType) {
      'prerequisite' => Colors.cyan,
      'related' => Colors.purple,
      'application' => Colors.green,
      'composition' => Colors.orange,
      'evolution' => Colors.amber,
      _ => Colors.grey,
    };
  }

  @override
  bool shouldRepaint(_ConstellationPainter oldDelegate) {
    return oldDelegate.relations != relations ||
           oldDelegate.nodePositions != nodePositions;
  }
}4.4 状态管理 (Riverpod)dart// lib/features/galaxy/controllers/galaxy_controller.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';

final galaxyControllerProvider = StateNotifierProvider<GalaxyController, GalaxyState>((ref) {
  final repository = ref.watch(galaxyRepositoryProvider);
  return GalaxyController(repository);
});


class GalaxyState {
  final List<KnowledgeNode> nodes;
  final List<NodeRelation> relations;
  final Map<UUID, UserNodeStatus> userStatuses;
  final GalaxyUserStats userStats;
  final List<ReviewSuggestion> reviewSuggestions;
  final bool isLoading;
  final String? error;
  
  // 计算属性
  Map<UUID, Offset> get nodePositions => _calculatePositions();
  double get flameIntensity => _calculateFlameIntensity();
  
  List<Sector> get sectors => SectorCode.values
      .map((code) => Sector(code: code))
      .toList();
  
  List<KnowledgeNode> getNodesInSector(SectorCode code) {
    return nodes.where((n) => n.sectorCode == code).toList();
  }
  
  KnowledgeNode? getNode(UUID id) {
    return nodes.firstWhereOrNull((n) => n.id == id);
  }
  
  GalaxyState({
    this.nodes = const [],
    this.relations = const [],
    this.userStatuses = const {},
    this.userStats = const GalaxyUserStats(),
    this.reviewSuggestions = const [],
    this.isLoading = false,
    this.error,
  });
  
  GalaxyState copyWith({...}) => GalaxyState(...);
  
  Map<UUID, Offset> _calculatePositions() {
    final positions = <UUID, Offset>{};
    final random = math.Random(42); // 固定种子保证一致性
    
    for (final node in nodes) {
      // 获取星域基准角度
      final sectorAngle = _getSectorBaseAngle(node.sectorCode);
      
      // 根据重要性确定半径层级
      final baseRadius = 150.0 + (5 - node.importanceLevel) * 80.0;
      
      // 添加噪声
      final noiseAngle = (random.nextDouble() - 0.5) * 50;
      final noiseRadius = (random.nextDouble() - 0.5) * 40;
      
      final angle = (sectorAngle + noiseAngle) * math.pi / 180;
      final radius = baseRadius + noiseRadius;
      
      // 转换为笛卡尔坐标 (以 1000,1000 为中心)
      positions[node.id] = Offset(
        1000 + radius * math.cos(angle),
        1000 + radius * math.sin(angle),
      );
    }
    
    return positions;
  }
  
  double _getSectorBaseAngle(SectorCode code) {
    return switch (code) {
      SectorCode.COSMOS => 300,
      SectorCode.TECH => 60,
      SectorCode.ART => 180,
      SectorCode.CIVILIZATION => 0,
      SectorCode.LIFE => 240,
      SectorCode.WISDOM => 330,
      SectorCode.VOID => 120,
    };
  }
  
  double _calculateFlameIntensity() {
    // 根据今日学习情况计算火焰强度
    if (userStats.totalStudyMinutes == 0) return 0.3;
    
    // 今日学习时长影响强度 (30分钟为基准)
    final todayMinutes = userStats.todayStudyMinutes;
    return (0.3 + 0.7 * (todayMinutes / 60).clamp(0.0, 1.0));
  }
}


class GalaxyController extends StateNotifier<GalaxyState> {
  final GalaxyRepository _repository;
  
  GalaxyController(this._repository) : super(GalaxyState()) {
    loadGalaxy();
  }

  Future<void> loadGalaxy({String? sectorCode}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final response = await _repository.getGalaxyGraph(sectorCode: sectorCode);
      
      state = state.copyWith(
        nodes: response.nodes,
        relations: response.relations,
        userStatuses: {for (var n in response.nodes) 
          if (n.userStatus != null) n.id: n.userStatus!},
        userStats: response.userStats,
        isLoading: false,
      );
      
      // 加载复习建议
      await loadReviewSuggestions();
      
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadReviewSuggestions() async {
    try {
      final suggestions = await _repository.getReviewSuggestions();
      state = state.copyWith(reviewSuggestions: suggestions);
    } catch (e) {
      // 非关键错误，静默处理
      debugPrint('Failed to load review suggestions: $e');
    }
  }

  /// 处理任务完成事件
  Future<SparkEvent?> handleTaskCompleted(UUID taskId, UUID? nodeId, int studyMinutes) async {
    if (nodeId == null) return null;
    
    try {
      final result = await _repository.sparkNode(
        nodeId: nodeId,
        studyMinutes: studyMinutes,
        taskId: taskId,
      );
      
      // 更新本地状态
      _updateNodeStatus(nodeId, result.updatedStatus);
      
      return result.sparkEvent;
      
    } catch (e) {
      debugPrint('Failed to spark node: $e');
      return null;
    }
  }

  void _updateNodeStatus(UUID nodeId, UserNodeStatus newStatus) {
    final updatedStatuses = Map<UUID, UserNodeStatus>.from(state.userStatuses);
    updatedStatuses[nodeId] = newStatus;
    
    state = state.copyWith(userStatuses: updatedStatuses);
  }

  /// 触发节点 Bloom 动画 (粒子到达时)
  void triggerNodeBloom(UUID nodeId) {
    // 通过 GlobalKey 或事件通知对应的 StarNode
    // 这里简化处理，实际可用事件总线
  }

  /// 语义搜索
  Future<List<SearchResultItem>> search(String query) async {
    return await _repository.searchNodes(query);
  }
}5. LLM 智能拓展系统5.1 拓展机制概述用户完成任务 "学习快速排序算法"
        │
        ▼
GalaxyService.spark_node()
        │
        ├── 更新掌握度
        │
        └── 触发拓展检查
                │
                ▼
        ExpansionService.should_expand()
        条件：study_count >= 2 && last_expansion > 1 day
                │
                ▼ (满足条件)
        加入拓展队列 expansion_queue
                │
                ▼ (后台 Worker)
        ExpansionWorker.process()
                │
                ├── 1. 收集上下文 (当前节点 + 相邻节点 + 用户学习历史)
                │
                ├── 2. 构建 Prompt
                │
                ├── 3. 调用 LLM
                │
                ├── 4. 解析响应 → 新节点列表
                │
                ├── 5. 去重 & 验证
                │
                ├── 6. 写入数据库
                │
                └── 7. SSE 通知前端 → 播放"涌现"动画5.2 ExpansionService 实现python# backend/app/services/expansion_service.py

import json
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeNode, NodeExpansionQueue, NodeRelation
from app.core.llm_client import LLMClient
from app.services.embedding_service import EmbeddingService


class ExpansionService:
    """
    LLM 知识拓展服务
    
    当用户深入学习某个知识点后，自动拓展相关知识节点，
    实现知识星图的有机生长。
    """
    
    # 拓展限制
    MAX_EXPANDED_NODES_PER_REQUEST = 5  # 每次最多拓展 5 个节点
    MIN_STUDY_COUNT_FOR_EXPANSION = 2   # 至少学习 2 次才触发拓展
    EXPANSION_COOLDOWN_HOURS = 24       # 同一节点拓展冷却时间
    
    def __init__(
        self,
        db: AsyncSession,
        llm_client: LLMClient,
        embedding_service: EmbeddingService
    ):
        self.db = db
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    async def queue_expansion(
        self,
        trigger_node_id: UUID,
        trigger_task_id: Optional[UUID],
        user_id: UUID
    ) -> bool:
        """
        将拓展请求加入队列
        
        Returns:
            bool: 是否成功加入队列
        """
        # 1. 检查是否满足拓展条件
        if not await self._should_expand(trigger_node_id, user_id):
            return False
        
        # 2. 收集拓展上下文
        context = await self._build_expansion_context(trigger_node_id, user_id)
        
        # 3. 创建队列任务
        queue_item = NodeExpansionQueue(
            trigger_node_id=trigger_node_id,
            trigger_task_id=trigger_task_id,
            user_id=user_id,
            expansion_context=context,
            status='pending'
        )
        
        self.db.add(queue_item)
        await self.db.commit()
        
        return True

    async def _should_expand(self, node_id: UUID, user_id: UUID) -> bool:
        """检查是否应该触发拓展"""
        # 检查最近是否已拓展过
        cooldown_time = datetime.utcnow() - timedelta(hours=self.EXPANSION_COOLDOWN_HOURS)
        
        query = select(NodeExpansionQueue).where(
            NodeExpansionQueue.trigger_node_id == node_id,
            NodeExpansionQueue.user_id == user_id,
            NodeExpansionQueue.created_at > cooldown_time
        )
        
        result = await self.db.execute(query)
        recent_expansion = result.scalar_one_or_none()
        
        return recent_expansion is None

    async def _build_expansion_context(self, node_id: UUID, user_id: UUID) -> str:
        """构建发送给 LLM 的拓展上下文"""
        # 获取触发节点
        node = await self.db.get(KnowledgeNode, node_id)
        
        # 获取相邻节点
        neighbors = await self._get_neighbor_nodes(node_id)
        
        # 获取用户已学习的节点 (避免重复推荐)
        learned_nodes = await self._get_user_learned_nodes(user_id)
        
        context = {
            "trigger_node": {
                "name": node.name,
                "description": node.description,
                "sector": node.subject.sector_code if node.subject else "VOID",
            },
            "neighbor_nodes": [
                {"name": n.name, "relation": rel}
                for n, rel in neighbors
            ],
            "already_learned": [n.name for n in learned_nodes],
        }
        
        return json.dumps(context, ensure_ascii=False)

    async def _get_neighbor_nodes(self, node_id: UUID, limit: int = 10):
        """获取节点的邻居节点"""
        query = (
            select(KnowledgeNode, NodeRelation.relation_type)
            .join(
                NodeRelation,
                (NodeRelation.source_node_id == node_id) | 
                (NodeRelation.target_node_id == node_id)
            )
            .where(KnowledgeNode.id != node_id)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.all()

    async def process_expansion(self, queue_id: UUID) -> List[KnowledgeNode]:
        """
        处理拓展请求 (由 Worker 调用)
        
        Returns:
            List[KnowledgeNode]: 新创建的知识节点
        """
        # 1. 获取队列任务
        queue_item = await self.db.get(NodeExpansionQueue, queue_id)
        if not queue_item or queue_item.status != 'pending':
            return []
        
        # 2. 标记为处理中
        queue_item.status = 'processing'
        await self.db.commit()
        
        try:
            # 3. 调用 LLM
            prompt = self._build_expansion_prompt(queue_item.expansion_context)
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # 4. 解析响应
            expanded_data = self._parse_expansion_response(response)
            
            # 5. 创建新节点
            new_nodes = await self._create_expanded_nodes(
                expanded_data,
                trigger_node_id=queue_item.trigger_node_id,
                user_id=queue_item.user_id
            )
            
            # 6. 更新队列状态
            queue_item.status = 'completed'
            queue_item.expanded_nodes = json.dumps([
                {"id": str(n.id), "name": n.name} for n in new_nodes
            ])
            queue_item.processed_at = datetime.utcnow()
            await self.db.commit()
            
            return new_nodes
            
        except Exception as e:
            queue_item.status = 'failed'
            queue_item.error_message = str(e)
            await self.db.commit()
            raise

    def _build_expansion_prompt(self, context_json: str) -> str:
        """构建拓展 Prompt"""
        context = json.loads(context_json)
        
        return f"""你是一个知识图谱拓展专家。用户正在学习"{context['trigger_node']['name']}"这个知识点。

## 当前知识点信息
- 名称：{context['trigger_node']['name']}
- 描述：{context['trigger_node']['description']}
- 所属领域：{context['trigger_node']['sector']}

## 相邻知识点
{chr(10).join([f"- {n['name']} ({n['relation']})" for n in context['neighbor_nodes']])}

## 用户已学习的知识点
{', '.join(context['already_learned'][:20])}

## 任务
请推荐 3-5 个与"{context['trigger_node']['name']}"相关的、用户可能感兴趣的知识点。

要求：
1. 不要推荐用户已学习的知识点
2. 推荐的知识点应该是渐进式的，从简单到复杂
3. 包含理论深化和实际应用两个方向
4. 每个知识点需要说明与触发知识点的关系

## 输出格式 (JSON)
```json{{
"expanded_nodes": [
{{
"name": "知识点名称",
"name_en": "English Name",
"description": "简要描述 (50字以内)",
"importance_level": 3,  // 1-5
"relation_to_trigger": "prerequisite|related|application|evolution",
"relation_strength": 0.8,  // 0-1
"keywords": ["关键词1", "关键词2"]
}}
]
}}

    def _parse_expansion_response(self, response: str) -> dict:
        """解析 LLM 响应"""
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            raise ValueError("Failed to parse LLM response as JSON")

    async def _create_expanded_nodes(
        self,
        expanded_data: dict,
        trigger_node_id: UUID,
        user_id: UUID
    ) -> List[KnowledgeNode]:
        """创建拓展的知识节点"""
        trigger_node = await self.db.get(KnowledgeNode, trigger_node_id)
        new_nodes = []
        
        for item in expanded_data.get('expanded_nodes', [])[:self.MAX_EXPANDED_NODES_PER_REQUEST]:
            # 检查是否已存在 (通过名称去重)
            existing = await self._find_existing_node(item['name'])
            if existing:
                # 如果已存在，只创建关系
                await self._ensure_relation(trigger_node_id, existing.id, item)
                continue
            
            # 创建新节点
            node = KnowledgeNode(
                subject_id=trigger_node.subject_id,
                parent_id=trigger_node_id if item['relation_to_trigger'] == 'composition' else None,
                name=item['name'],
                name_en=item.get('name_en'),
                description=item.get('description'),
                importance_level=item.get('importance_level', 2),
                is_seed=False,
                source_type='llm_expanded',
                keywords=item.get('keywords', []),
            )
            
            # 生成 embedding
            embed_text = f"{node.name} {node.description or ''}"
            node.embedding = await self.embedding_service.get_embedding(embed_text)
            
            self.db.add(node)
            await self.db.flush()  # 获取 ID
            
            # 创建与触发节点的关系
            relation = NodeRelation(
                source_node_id=trigger_node_id,
                target_node_id=node.id,
                relation_type=item.get('relation_to_trigger', 'related'),
                strength=item.get('relation_strength', 0.5),
                created_by='llm'
            )
            self.db.add(relation)
            
            new_nodes.append(node)
        
        await self.db.commit()
        return new_nodes

    async def _find_existing_node(self, name: str) -> Optional[KnowledgeNode]:
        """查找是否存在同名节点"""
        query = select(KnowledgeNode).where(KnowledgeNode.name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _ensure_relation(self, source_id: UUID, target_id: UUID, item: dict):
        """确保关系存在"""
        query = select(NodeRelation).where(
            NodeRelation.source_node_id == source_id,
            NodeRelation.target_node_id == target_id
        )
        result = await self.db.execute(query)
        if not result.scalar_one_or_none():
            relation = NodeRelation(
                source_node_id=source_id,
                target_node_id=target_id,
                relation_type=item.get('relation_to_trigger', 'related'),
                strength=item.get('relation_strength', 0.5),
                created_by='llm'
            )
            self.db.add(relation)5.3 拓展 Worker (后台任务)python# backend/app/jobs/expansion_worker.py

import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NodeExpansionQueue
from app.services.expansion_service import ExpansionService
from app.core.sse import SSEManager


class ExpansionWorker:
    """
    知识拓展后台 Worker
    
    持续处理拓展队列中的任务
    """
    
    POLL_INTERVAL = 5  # 秒
    BATCH_SIZE = 10
    
    def __init__(
        self,
        db_session_factory,
        expansion_service_factory,
        sse_manager: SSEManager
    ):
        self.db_session_factory = db_session_factory
        self.expansion_service_factory = expansion_service_factory
        self.sse_manager = sse_manager
        self._running = False

    async def start(self):
        """启动 Worker"""
        self._running = True
        print("Expansion Worker started")
        
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                print(f"Expansion Worker error: {e}")
            
            await asyncio.sleep(self.POLL_INTERVAL)

    async def stop(self):
        """停止 Worker"""
        self._running = False
        print("Expansion Worker stopped")

    async def _process_batch(self):
        """处理一批拓展任务"""
        async with self.db_session_factory() as db:
            # 获取待处理任务
            query = (
                select(NodeExpansionQueue)
                .where(NodeExpansionQueue.status == 'pending')
                .order_by(NodeExpansionQueue.created_at)
                .limit(self.BATCH_SIZE)
            )
            
            result = await db.execute(query)
            pending_tasks = result.scalars().all()
            
            if not pending_tasks:
                return
            
            expansion_service = self.expansion_service_factory(db)
            
            for task in pending_tasks:
                try:
                    new_nodes = await expansion_service.process_expansion(task.id)
                    
                    if new_nodes:
                        # 通过 SSE 通知前端
                        await self._notify_expansion(task.user_id, new_nodes)
                        
                except Exception as e:
                    print(f"Failed to process expansion {task.id}: {e}")

    async def _notify_expansion(self, user_id, new_nodes):
        """通知前端新节点已创建"""
        event_data = {
            "type": "nodes_expanded",
            "nodes": [
                {
                    "id": str(node.id),
                    "name": node.name,
                    "sector_code": node.subject.sector_code if node.subject else "VOID",
                }
                for node in new_nodes
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.sse_manager.send_to_user(user_id, event_data)5.4 前端涌现动画dart// lib/features/galaxy/presentation/widgets/emergence_animation.dart

import 'package:flutter/material.dart';

/// 新节点涌现动画
/// 
/// 当 LLM 拓展出新知识点时，播放从虚空中显现的动画
class EmergenceAnimation extends StatefulWidget {
  final KnowledgeNode node;
  final Offset position;
  final VoidCallback onComplete;
  
  const EmergenceAnimation({
    super.key,
    required this.node,
    required this.position,
    required this.onComplete,
  });

  @override
  State<EmergenceAnimation> createState() => _EmergenceAnimationState();
}

class _EmergenceAnimationState extends State<EmergenceAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    );
    
    // 缩放：从 0 到 1.2 再到 1
    _scaleAnimation = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.0, end: 1.3)
            .chain(CurveTween(curve: Curves.easeOutBack)),
        weight: 60,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.3, end: 1.0)
            .chain(CurveTween(curve: Curves.easeInOut)),
        weight: 40,
      ),
    ]).animate(_controller);
    
    // 透明度：渐入
    _opacityAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0.0, 0.5, curve: Curves.easeIn),
      ),
    );
    
    // 光晕：脉冲效果
    _glowAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 30),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.3), weight: 70),
    ]).animate(_controller);
    
    _controller.forward().whenComplete(widget.onComplete);
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: widget.position.dx - 40,
      top: widget.position.dy - 40,
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          return Transform.scale(
            scale: _scaleAnimation.value,
            child: Opacity(
              opacity: _opacityAnimation.value,
              child: _buildEmergingNode(),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmergingNode() {
    final color = _getSectorColor(widget.node.sectorCode);
    
    return Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            Colors.white,
            color,
            color.withOpacity(0.5),
            Colors.transparent,
          ],
          stops: const [0.0, 0.3, 0.6, 1.0],
        ),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(_glowAnimation.value * 0.8),
            blurRadius: 30 * _glowAnimation.value,
            spreadRadius: 10 * _glowAnimation.value,
          ),
        ],
      ),
      child: Center(
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 500),
          opacity: _controller.value > 0.5 ? 1.0 : 0.0,
          child: Text(
            widget.node.name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
    );
  }

  Color _getSectorColor(String sectorCode) {
    return switch (sectorCode) {
      'COSMOS' => const Color(0xFF00BFFF),
      'TECH' => const Color(0xFFC0C0C0),
      'ART' => const Color(0xFFFF00FF),
      'CIVILIZATION' => const Color(0xFFFFD700),
      'LIFE' => const Color(0xFF32CD32),
      'WISDOM' => const Color(0xFFFFFFFF),
      _ => const Color(0xFF2F4F4F),
    };
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}6. 用户体验设计6.1 用户旅程地图第一次打开星图                  完成第一个任务                 持续学习
     │                              │                          │
     ▼                              ▼                          ▼
┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│  空状态引导  │              │  首次点亮    │              │  星图生长   │
│             │              │             │              │             │
│ • 混沌宇宙  │ ──任务完成──→│ • 飞升动画  │ ──持续学习──→│ • 节点拓展  │
│ • 中心火苗  │              │ • 首星闪耀  │              │ • 星座连线  │
│ • 引导提示  │              │ • 成就弹窗  │              │ • 领域扩展  │
└─────────────┘              └─────────────┘              └─────────────┘
                                    │
                                    ▼
                             ┌─────────────┐
                             │  复习提醒   │
                             │             │
                             │ • 星星变暗  │
                             │ • 复习建议  │
                             │ • 重新点亮  │
                             └─────────────┘6.2 空状态设计dart// 首次进入星图时的体验

class GalaxyEmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // 1. 混沌背景 (比正常更暗淡)
        DeepSpaceBackground(opacity: 0.3),
        
        // 2. 6 个星域轮廓 (低透明度，虚线描边)
        ...SectorCode.values.map((sector) => 
          SectorOutline(
            sector: sector,
            opacity: 0.2,
            style: BorderStyle.dashed,
          ),
        ),
        
        // 3. 中心火苗 (较小，较暗)
        Center(
          child: FlameCore(
            intensity: 0.3,
            size: Size(80, 100),
          ),
        ),
        
        // 4. 引导文案
        Positioned(
          bottom: 200,
          left: 0,
          right: 0,
          child: Column(
            children: [
              Text(
                '你的知识宇宙刚刚诞生',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.9),
                  fontSize: 20,
                  fontWeight: FontWeight.w500,
                ),
              ),
              SizedBox(height: 8),
              Text(
                '完成第一个学习任务，点亮你的第一颗星',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.6),
                  fontSize: 14,
                ),
              ),
              SizedBox(height: 24),
              // 指向任务 Tab 的箭头动画
              AnimatedArrow(
                direction: AxisDirection.down,
                color: Colors.amber,
              ),
            ],
          ),
        ),
      ],
    );
  }
}6.3 首次点亮体验dart// 首次点亮一颗星时的特殊动画序列

class FirstSparkCelebration extends StatefulWidget {
  final SparkEvent event;
  final VoidCallback onComplete;
  
  @override
  State<FirstSparkCelebration> createState() => _FirstSparkCelebrationState();
}

class _FirstSparkCelebrationState extends State<FirstSparkCelebration> {
  int _step = 0;  // 动画步骤

  @override
  void initState() {
    super.initState();
    _playSequence();
  }

  Future<void> _playSequence() async {
    // Step 1: 火苗增强 (0.5s)
    setState(() => _step = 1);
    await Future.delayed(Duration(milliseconds: 500));
    
    // Step 2: 粒子喷射 (1.5s)
    setState(() => _step = 2);
    await Future.delayed(Duration(milliseconds: 1500));
    
    // Step 3: 星星点亮 + Bloom (0.8s)
    setState(() => _step = 3);
    await Future.delayed(Duration(milliseconds: 800));
    
    // Step 4: 相机聚焦到新星 (0.5s)
    setState(() => _step = 4);
    await Future.delayed(Duration(milliseconds: 500));
    
    // Step 5: 成就弹窗
    setState(() => _step = 5);
    
    // 显示成就弹窗
    _showAchievementDialog();
  }

  void _showAchievementDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AchievementDialog(
        title: '🌟 第一颗星',
        subtitle: '你点亮了 "${widget.event.nodeName}"',
        description: '继续探索更多知识领域，让你的宇宙更加璀璨！',
        onDismiss: () {
          Navigator.pop(context);
          widget.onComplete();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // 根据 _step 返回对应动画组件
    return Stack(
      children: [
        // 火苗增强
        if (_step >= 1)
          FlameCore(intensity: _step >= 2 ? 1.0 : 0.7),
        
        // 粒子喷射
        if (_step >= 2)
          ParticleLayer(
            particles: _generateFirstSparkParticles(),
            count: 30,  // 首次点亮更多粒子
          ),
        
        // 屏幕闪光
        if (_step == 3)
          AnimatedOpacity(
            duration: Duration(milliseconds: 200),
            opacity: _step == 3 ? 0.3 : 0.0,
            child: Container(color: Colors.white),
          ),
      ],
    );
  }
}6.4 节点详情面板dart// 点击星星后显示的底部面板

class NodeDetailSheet extends StatelessWidget {
  final KnowledgeNode node;
  
  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.4,
      minChildSize: 0.2,
      maxChildSize: 0.9,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: Color(0xFF1A1A2E),
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
            boxShadow: [
              BoxShadow(
                color: _getSectorColor(node.sectorCode).withOpacity(0.3),
                blurRadius: 20,
                offset: Offset(0, -5),
              ),
            ],
          ),
          child: ListView(
            controller: scrollController,
            padding: EdgeInsets.all(20),
            children: [
              // 拖动指示器
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white30,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              SizedBox(height: 20),
              
              // 节点标题
              Row(
                children: [
                  // 状态指示器
                  _StatusIndicator(status: node.userStatus?.status),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          node.name,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (node.nameEn != null)
                          Text(
                            node.nameEn!,
                            style: TextStyle(
                              color: Colors.white60,
                              fontSize: 14,
                            ),
                          ),
                      ],
                    ),
                  ),
                  // 收藏按钮
                  IconButton(
                    icon: Icon(
                      node.userStatus?.isFavorite == true
                          ? Icons.star
                          : Icons.star_border,
                      color: Colors.amber,
                    ),
                    onPressed: () => _toggleFavorite(context),
                  ),
                ],
              ),
              SizedBox(height: 16),
              
              // 掌握度进度
              if (node.userStatus != null) ...[
                _MasteryProgress(
                  status: node.userStatus!,
                  sectorColor: _getSectorColor(node.sectorCode),
                ),
                SizedBox(height: 16),
              ],
              
              // 描述
              if (node.description != null) ...[
                Text(
                  node.description!,
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                    height: 1.6,
                  ),
                ),
                SizedBox(height: 16),
              ],
              
              // 学习统计
              if (node.userStatus?.isUnlocked == true)
                _StudyStats(status: node.userStatus!),
              
              // 相关知识点
              SizedBox(height: 24),
              _RelatedNodes(nodeId: node.id),
              
              // 操作按钮
              SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: () => _startStudy(context, node),
                      icon: Icon(Icons.play_arrow),
                      label: Text('开始学习'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _getSectorColor(node.sectorCode),
                        padding: EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                  SizedBox(width: 12),
                  OutlinedButton.icon(
                    onPressed: () => _showDetails(context, node),
                    icon: Icon(Icons.info_outline),
                    label: Text('详情'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white70,
                      side: BorderSide(color: Colors.white30),
                      padding: EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}


class _MasteryProgress extends StatelessWidget {
  final UserNodeStatus status;
  final Color sectorColor;
  
  @override
  Widget build(BuildContext context) {
    final nextLevel = _getNextLevelInfo(status.masteryScore);
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '掌握度',
              style: TextStyle(color: Colors.white60, fontSize: 12),
            ),
            Text(
              '${status.masteryScore.toInt()}%',
              style: TextStyle(
                color: sectorColor,
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        SizedBox(height: 8),
        Stack(
          children: [
            // 背景
            Container(
              height: 8,
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            // 进度
            FractionallySizedBox(
              widthFactor: status.masteryScore / 100,
              child: Container(
                height: 8,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [sectorColor.withOpacity(0.7), sectorColor],
                  ),
                  borderRadius: BorderRadius.circular(4),
                  boxShadow: [
                    BoxShadow(
                      color: sectorColor.withOpacity(0.5),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        SizedBox(height: 8),
        if (nextLevel != null)
          Text(
            nextLevel,
            style: TextStyle(color: Colors.white38, fontSize: 11),
          ),
      ],
    );
  }
  
  String? _getNextLevelInfo(double score) {
    if (score < 30) return '再学习 ${((30 - score) / 5).ceil()} 次达到「闪耀」';
    if (score < 80) return '再学习 ${((80 - score) / 5).ceil()} 次达到「璀璨」';
    if (score < 95) return '再学习 ${((95 - score) / 5).ceil()} 次达到「精通」';
    return '已达到最高境界 ✨';
  }
}6.5 复习提醒系统dart// 复习提醒卡片

class ReviewReminderCard extends StatelessWidget {
  final List<ReviewSuggestion> suggestions;
  
  @override
  Widget build(BuildContext context) {
    if (suggestions.isEmpty) return SizedBox.shrink();
    
    return Card(
      color: Color(0xFF1A1A2E),
      margin: EdgeInsets.all(16),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.wb_twilight, color: Colors.amber, size: 20),
                SizedBox(width: 8),
                Text(
                  '知识需要温故',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Spacer(),
                Text(
                  '${suggestions.length} 个知识点变暗了',
                  style: TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ],
            ),
            SizedBox(height: 12),
            
            // 显示前 3 个需要复习的知识点
            ...suggestions.take(3).map((s) => _ReviewItem(suggestion: s)),
            
            if (suggestions.length > 3) ...[
              SizedBox(height: 8),
              TextButton(
                onPressed: () => _showAllReviews(context),
                child: Text('查看全部 ${suggestions.length} 个'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}


class _ReviewItem extends StatelessWidget {
  final ReviewSuggestion suggestion;
  
  @override
  Widget build(BuildContext context) {
    final isUrgent = suggestion.urgency == 'high';
    
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          // 暗淡的星星图标
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _getSectorColor(suggestion.sectorCode).withOpacity(0.3),
            ),
            child: Center(
              child: Icon(
                Icons.star,
                size: 14,
                color: isUrgent ? Colors.red[300] : Colors.grey,
              ),
            ),
          ),
          SizedBox(width: 12),
          
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  suggestion.nodeName,
                  style: TextStyle(color: Colors.white, fontSize: 14),
                ),
                Text(
                  '${suggestion.daysSinceStudy} 天前学习 · 掌握度 ${suggestion.currentMastery.toInt()}%',
                  style: TextStyle(color: Colors.white38, fontSize: 11),
                ),
              ],
            ),
          ),
          
          // 快速复习按钮
          TextButton(
            onPressed: () => _quickReview(context, suggestion),
            child: Text(
              '复习',
              style: TextStyle(
                color: isUrgent ? Colors.amber : Colors.white60,
              ),
            ),
          ),
        ],
      ),
    );
  }
}6.6 成就系统设计dart// 成就定义

enum GalaxyAchievement {
  firstStar(
    id: 'first_star