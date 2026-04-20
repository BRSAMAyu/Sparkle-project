# SPARKLE Aurora Stage 16 Read-Verify Report (2026-04-20)

> Workstream: `WS-MWL-READ-VERIFY`
> Purpose: prove inferred episodic records written into `EpisodicMemory` are actually visible to the standard chat prompt path.

## 1. Code Fact

- `backend/app/config/settings.py`
  `USE_CONTEXT_PACK = True`
- `backend/app/core/context_pack.py`
  `ContextPackBuilder.build()` still reads `MemoryService.list_recent_episodic()`
- `backend/app/orchestration/prompts.py`
  prompt rendering still injects `episodic_memories` into `【近期相关记忆】`

So Stage 16 does not need to invent a new read path. It only needs to ensure inferred records survive the same governed front door as other episodic memory.

## 2. Proof Test

Target test:

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_memory_inferred_write_lane.py::test_memory_inferred_revoke_hides_from_prompt_read_path \
  -q
```

What it proves:

1. a chat-derived inferred episodic record is written
2. `ContextPackBuilder` includes it in prompt context
3. `build_system_prompt(...)` renders the summary into the next-turn prompt
4. after user revoke, the same prompt path no longer sees it

## 3. Verdict

`WS-MWL-READ-VERIFY` is satisfied.

There is no remaining “I thought we were reading memory” ambiguity in the standard Stage 16 chat path.

This verdict is still bounded:

1. the read path is the existing governed context-pack front door
2. revoked inferred records disappear on the next prompt build
3. nothing in this report authorizes downstream Router / Push / Skill / Accountability consumption
