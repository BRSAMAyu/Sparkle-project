# Knowledge Galaxy (知识星图) Implementation Summary

## Completed Tasks ✅

### 1. Database Models & Migrations
- ✅ Updated `backend/app/models/subject.py` - Added galaxy-related fields (glow_color, position_angle, icon_name)
- ✅ Updated `backend/app/models/galaxy.py` - Added new models:
  - `NodeRelation` - 知识点关系
  - `StudyRecord` - 学习记录
  - `NodeExpansionQueue` - LLM拓展队列
  - Updated `KnowledgeNode` with embeddings and additional fields
  - Updated `UserNodeStatus` with mastery tracking
- ✅ Updated `backend/app/models/task.py` - Added `knowledge_node_id` field
- ✅ Created migration: `54e1f05154ad_add_galaxy_v2_tables.py`

### 2. Configuration
- ✅ Updated `backend/app/config.py`:
  - Added `LLM_PROVIDER` setting
  - Added `EMBEDDING_MODEL` and `EMBEDDING_DIM` settings

### 3. Core Services
- ✅ **LLM Client** (`backend/app/core/llm_client.py`)
  - Unified interface for Qwen, DeepSeek, OpenAI
  - Chat completion with JSON response support
  - Retry logic with tenacity

- ✅ **Embedding Service** (`backend/app/services/embedding_service.py`)
  - Text-to-vector conversion
  - Batch embedding support
  - OpenAI-compatible API format

- ✅ **Expansion Service** (`backend/app/services/expansion_service.py`)
  - LLM-powered knowledge graph expansion
  - Queue-based async processing
  - Automatic node creation and relation building
  - Deduplication logic

- ✅ **Galaxy Service** (`backend/app/services/galaxy_service.py`)
  - Get galaxy graph data
  - Spark nodes (点亮知识点)
  - Semantic search with vector similarity
  - Auto-classify tasks to knowledge nodes
  - Mastery score calculation
  - Review time calculation

- ✅ **Decay Service** (`backend/app/services/decay_service.py`)
  - Ebbinghaus forgetting curve implementation
  - Daily decay processing
  - Review suggestions
  - Pause/resume decay for specific nodes

### 4. Background Workers
- ✅ **Expansion Worker** (`backend/app/workers/expansion_worker.py`)
  - Polls `NodeExpansionQueue` every 30 seconds
  - Processes LLM expansion requests
  - Integrated into app lifespan management

### 5. API Endpoints
- ✅ **Galaxy Router** (`backend/app/api/v1/galaxy.py`)
  - `GET /api/v1/galaxy/graph` - Get user's knowledge galaxy
  - `POST /api/v1/galaxy/node/{node_id}/spark` - Light up a node
  - `GET /api/v1/galaxy/node/{node_id}` - Get node details
  - `POST /api/v1/galaxy/search` - Semantic search
  - `GET /api/v1/galaxy/review/suggestions` - Get review suggestions
  - `POST /api/v1/galaxy/node/{node_id}/decay/pause` - Pause decay
  - `GET /api/v1/galaxy/stats` - Get galaxy statistics

- ✅ Registered in `backend/app/api/v1/router.py`
- ✅ Integrated into `backend/app/main.py` with worker startup

### 6. Schemas
- ✅ **Galaxy Schemas** (`backend/app/schemas/galaxy.py`)
  - `SectorCode` enum (COSMOS, TECH, ART, CIVILIZATION, LIFE, WISDOM, VOID)
  - `NodeStatus` enum (locked, unlit, glimmer, shining, brilliant, mastered, collapsed)
  - Request models: `SparkRequest`, `SearchRequest`
  - Response models: `GalaxyGraphResponse`, `SparkResult`, `SearchResponse`, etc.
  - Node models: `NodeBase`, `UserStatusInfo`, `NodeWithStatus`
  - Utility models: `GalaxyUserStats`, `SparkEvent`, `ReviewSuggestion`

### 7. Seed Data
- ✅ Created seed data JSON files:
  - `backend/seed_data/nodes/tech.json` - Technology sector (Python, algorithms, web dev, databases)
  - `backend/seed_data/nodes/cosmos.json` - Cosmos sector (calculus, linear algebra, probability, statistics)
  - `backend/seed_data/nodes/wisdom.json` - Wisdom sector (Feynman technique, spaced repetition, deep work, goal setting)

- ✅ **Seed Data Loader** (`backend/seed_data/load_seed_data.py`)
  - Loads nodes from JSON files
  - Creates subjects with sector colors and positions
  - Generates embeddings for each node
  - Handles duplicates

## Architecture Overview

```
┌─────────────────┐
│   FastAPI App   │
└────────┬────────┘
         │
    ┌────┴─────────────────────────────┐
    │                                  │
┌───▼──────────┐            ┌─────────▼────────┐
│ API Routers  │            │ Background Workers│
└───┬──────────┘            └─────────┬────────┘
    │                                  │
┌───▼──────────────┐        ┌─────────▼──────────┐
│  Galaxy Service  │◄──────►│ Expansion Worker   │
│  - get_graph     │        │ - process_queue    │
│  - spark_node    │        └────────────────────┘
│  - search        │
└────┬─────────────┘
     │
     ├──► DecayService (遗忘衰减)
     ├──► ExpansionService (LLM 拓展)
     ├──► EmbeddingService (向量嵌入)
     └──► LLMClient (LLM 调用)
```

## Data Flow: Spark Node (点亮知识点)

```
1. User completes a learning task
   │
2. Frontend calls: POST /api/v1/galaxy/node/{node_id}/spark
   │
3. GalaxyService.spark_node()
   │
   ├─► Update UserNodeStatus (mastery_score, study_count)
   ├─► Create StudyRecord
   ├─► Generate SparkEvent (animation data)
   │
4. If study_count >= 2:
   │
   └─► ExpansionService.queue_expansion()
       │
       └─► Create NodeExpansionQueue (status=pending)

5. ExpansionWorker (background) polls queue every 30s
   │
   ├─► Find pending tasks
   ├─► Call LLM with expansion prompt
   ├─► Parse JSON response
   ├─► Create new KnowledgeNodes
   └─► Create NodeRelations
```

## Key Features

### 1. Mastery Score Calculation
- Base points: 5.0 per session
- Time factor: study_minutes / 30 (capped at 2x)
- Difficulty factor: 1 + (importance_level - 1) * 0.1
- Max mastery: 100.0

### 2. Forgetting Curve (Ebbinghaus)
- Base half-life: 7 days
- Dynamic stability: Higher mastery = slower decay
- Decay formula: `mastery * e^(-decay_rate * days_elapsed)`
- Min mastery: 5.0 (never drops to 0)

### 3. Review Schedule
- Mastery >= 80: Review in 14 days
- Mastery >= 60: Review in 7 days
- Mastery >= 30: Review in 3 days
- Mastery < 30: Review in 1 day

### 4. Vector Search
- Uses pgvector extension
- Cosine distance for similarity
- Threshold: 0.3 (configurable)
- Embedding dimension: 1536

### 5. LLM Expansion
- Triggered after 2 study sessions
- Cooldown: 24 hours per node
- Max new nodes: 5 per expansion
- Relation types: prerequisite, related, application, evolution

## Environment Variables Required

```env
# LLM Service
LLM_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=your_api_key
LLM_MODEL_NAME=qwen-turbo
LLM_PROVIDER=qwen

# Embedding Service
EMBEDDING_MODEL=text-embedding-v2
EMBEDDING_DIM=1536

# Database (must support pgvector)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/sparkle
```

## Next Steps

### To Complete Implementation:

1. **Run Migration**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Load Seed Data**
   ```bash
   cd backend
   python seed_data/load_seed_data.py
   ```

3. **Start Server**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

4. **Test API**
   - Visit http://localhost:8000/docs
   - Test galaxy endpoints
   - Check expansion worker logs

### Future Enhancements:

1. **Frontend Implementation (Flutter)**
   - GLSL shader for flame core
   - CustomPaint for star rendering
   - Particle animations for sparking
   - Galaxy navigation UI

2. **Advanced Features**
   - SSE/WebSocket for real-time expansion notifications
   - Achievement system
   - Constellation detection (clustering)
   - Star collapse mechanism
   - Multi-user collaborative galaxies

3. **Optimization**
   - Vector index tuning
   - Batch embedding processing
   - LLM response caching
   - Lazy loading for large galaxies

## Notes

- All services use async/await for non-blocking I/O
- Retry logic implemented for LLM and embedding calls
- Idempotency middleware for API safety
- Error handling and logging throughout
- Type hints for better IDE support
- Pydantic models for validation

---

**Status**: ✅ Backend implementation complete and ready for testing
**Date**: 2025-12-16
**Next**: Run migrations → Load seed data → Test APIs → Frontend implementation
