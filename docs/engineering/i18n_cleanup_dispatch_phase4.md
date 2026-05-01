# Phase 4 Dispatch: Python Backend

**3 Parallel Agents** — Sub-phases A/B/C

## !!! CRITICAL WARNING !!!
Previous agents introduced auto-generated l10n hash keys in Flutter. In Python, NEVER do this.
**Always use English string literals directly.** Do NOT add references to non-existent translation keys.

## Chinese Patterns in Python

The Python backend has ~8,800 Chinese occurrences across ~250 files. This phase is split into 3 sub-phases.

## Chinese Patterns in Python

1. **Docstrings/doc comments** — Chinese in `"""..."""` docstrings
2. **Error messages** — Chinese in `raise HTTPException(...)` or `return JSONResponse(...)`
3. **Log messages** — Chinese in `logger.info(...)` etc.
4. **Schema descriptions** — Chinese in Field(description="...")
5. **Tool descriptions** — Chinese in function/parameter descriptions for LLM tools
6. **Constants/Default values** — Chinese string literals

## Fix Rules for Python

### Docstrings
```python
# Before:
def func():
    """中文描述"""

# After:
def func():
    """English description"""
```

### Error Messages
```python
# Before:
raise HTTPException(status_code=400, detail="参数错误")

# After:
raise HTTPException(status_code=400, detail="Invalid parameters")
```

### Schema Descriptions
```python
# Before:
name: str = Field(description="用户名称")

# After:  
name: str = Field(description="User name")
```

### Log Messages
```python
# Before:
logger.info("用户登录成功")

# After:
logger.info("User login successful")
```

## Phase 4A: Core Infrastructure
- `backend/app/core/*.py` (all)
- `backend/app/config/*.py` (all)
- `backend/app/db/*.py` (all)
- `backend/app/models/*.py` (all)
- `backend/app/schemas/*.py` (all)

## Phase 4B: Services & Tools
- `backend/app/services/*.py` (all)
- `backend/app/tools/*.py` (all)

## Phase 4C: Agents & Orchestration
- `backend/app/agents/*.py` (all)
- `backend/app/orchestration/*.py` (all)
- `backend/app/signals/*.py` (all)
- `backend/app/tasks/*.py` (all)

## Phase 4D: Remaining
- `backend/app/adapters/*.py`
- `backend/app/semantic/*.py`
- `backend/app/scaffolding/*.py`
- `backend/app/sprint_packs/*.py`
