"""
LangGraph-compatible Redis checkpointer.

Replaces MemorySaver with persistent Redis-backed checkpoint storage.
Survives service restarts — checkpoint state persists for the configured TTL.
"""

from __future__ import annotations

import base64
import json
from typing import Any, AsyncIterator, Iterator, Sequence

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    PendingWrite,
    get_checkpoint_id,
)
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from loguru import logger
from langchain_core.runnables import RunnableConfig


def _thread_key(thread_id: str, checkpoint_ns: str) -> str:
    return f"lg_chk:{thread_id}:{checkpoint_ns}"


def _blob_key(thread_id: str, checkpoint_ns: str, channel: str, version: str) -> str:
    return f"lg_blob:{thread_id}:{checkpoint_ns}:{channel}:{version}"


def _writes_key(thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
    return f"lg_writes:{thread_id}:{checkpoint_ns}:{checkpoint_id}"


class LangGraphRedisCheckpointer(BaseCheckpointSaver):
    """Persist LangGraph checkpoints to Redis with TTL-based expiry."""

    def __init__(
        self,
        redis_client: Any,
        ttl: int = 3600 * 24,
        serde: SerializerProtocol | None = None,
    ) -> None:
        super().__init__(serde=serde)
        self.redis = redis_client
        self.ttl = ttl

    # ---- async interface (LangGraph uses these) ----

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        c = checkpoint.copy()
        values: dict[str, Any] = c.pop("channel_values")  # type: ignore[misc]

        pipe = self.redis.pipeline()

        # Store blobs for each new channel version
        for k, v in new_versions.items():
            blob_data = self.serde.dumps_typed(values[k]) if k in values else ("empty", b"")
            bk = _blob_key(thread_id, checkpoint_ns, k, v)
            pipe.set(bk, json.dumps([blob_data[0], base64.b64encode(blob_data[1]).decode("ascii")]), ex=self.ttl)

        # Store checkpoint metadata (without channel_values, which are in blobs)
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        storage_key = _thread_key(thread_id, checkpoint_ns)

        entry = {
            "checkpoint": [c["v"], checkpoint_id, c["ts"], c.get("channel_versions", {}), c.get("versions_seen", {})],
            "metadata": metadata,
            "parent_checkpoint_id": parent_checkpoint_id,
        }
        pipe.hset(storage_key, checkpoint_id, json.dumps(entry, default=str))
        pipe.expire(storage_key, self.ttl)

        await pipe.execute()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        storage_key = _thread_key(thread_id, checkpoint_ns)

        if checkpoint_id := get_checkpoint_id(config):
            raw = await self.redis.hget(storage_key, checkpoint_id)
            if not raw:
                return None
            entry = json.loads(raw)
        else:
            all_entries = await self.redis.hgetall(storage_key)
            if not all_entries:
                return None
            latest_id = None
            latest_entry = None
            for cid, raw in all_entries.items():
                entry = json.loads(raw)
                if latest_entry is None or entry["checkpoint"][2] > latest_entry["checkpoint"][2]:
                    latest_id = cid
                    latest_entry = entry
            if latest_entry is None:
                return None
            checkpoint_id = latest_id
            entry = latest_entry

        cp_data = entry["checkpoint"]
        metadata = entry["metadata"]
        parent_checkpoint_id = entry.get("parent_checkpoint_id")

        channel_versions: ChannelVersions = cp_data[3] if len(cp_data) > 3 else {}
        channel_values: dict[str, Any] = {}
        for ch, ver in channel_versions.items():
            try:
                bk = _blob_key(thread_id, checkpoint_ns, ch, ver)
                blob_raw = await self.redis.get(bk)
                if blob_raw:
                    blob_parts = json.loads(blob_raw)
                    channel_values[ch] = self.serde.loads_typed((blob_parts[0], base64.b64decode(blob_parts[1])))
            except Exception as e:
                logger.warning(f"Failed to decode blob for channel {ch} (thread={thread_id}): {e}")

        checkpoint: Checkpoint = {
            "v": cp_data[0],
            "id": cp_data[1],
            "ts": cp_data[2],
            "channel_values": channel_values,
            "channel_versions": channel_versions,
            "versions_seen": cp_data[4] if len(cp_data) > 4 else {},
        }

        writes_raw = await self.redis.hgetall(_writes_key(thread_id, checkpoint_ns, checkpoint_id))
        pending_writes: list[PendingWrite] | None = None
        if writes_raw:
            pending_writes = []
            for wid, wdata in writes_raw.items():
                decoded = json.loads(wdata)
                pending_writes.append((decoded[0], decoded[1], decoded[2]))

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
            pending_writes=pending_writes,
        )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if config is None:
            return

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        storage_key = _thread_key(thread_id, checkpoint_ns)

        all_entries = await self.redis.hgetall(storage_key)
        if not all_entries:
            return

        before_ts = None
        if before and before.get("configurable", {}).get("checkpoint_id"):
            before_raw = await self.redis.hget(storage_key, before["configurable"]["checkpoint_id"])
            if before_raw:
                before_entry = json.loads(before_raw)
                before_ts = before_entry["checkpoint"][2]

        sorted_entries = []
        for cid, raw in all_entries.items():
            entry = json.loads(raw)
            ts = entry["checkpoint"][2]
            if before_ts and ts >= before_ts:
                continue
            if filter:
                meta = entry.get("metadata", {})
                if not all(meta.get(k) == v for k, v in filter.items()):
                    continue
            sorted_entries.append((cid, entry, ts))

        sorted_entries.sort(key=lambda x: x[2], reverse=True)

        count = 0
        for cid, entry, _ in sorted_entries:
            if limit is not None and count >= limit:
                break
            cp_data = entry["checkpoint"]
            channel_versions: ChannelVersions = cp_data[3] if len(cp_data) > 3 else {}
            channel_values: dict[str, Any] = {}
            for ch, ver in channel_versions.items():
                bk = _blob_key(thread_id, checkpoint_ns, ch, ver)
                blob_raw = await self.redis.get(bk)
                if blob_raw:
                    blob_parts = json.loads(blob_raw)
                    channel_values[ch] = self.serde.loads_typed((blob_parts[0], base64.b64decode(blob_parts[1])))

            checkpoint: Checkpoint = {
                "v": cp_data[0],
                "id": cp_data[1],
                "ts": cp_data[2],
                "channel_values": channel_values,
                "channel_versions": channel_versions,
                "versions_seen": cp_data[4] if len(cp_data) > 4 else {},
            }

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": cid,
                    }
                },
                checkpoint=checkpoint,
                metadata=entry.get("metadata", {}),
                parent_config=None,
                pending_writes=None,
            )
            count += 1

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"]["checkpoint_id"]

        writes_key = _writes_key(thread_id, checkpoint_ns, checkpoint_id)

        pipe = self.redis.pipeline()
        for idx, (channel, value) in enumerate(writes):
            wid = f"{task_id}:{task_path}:{idx}"
            pipe.hset(writes_key, wid, json.dumps([task_id, channel, value], default=str))
        pipe.expire(writes_key, self.ttl)
        await pipe.execute()
