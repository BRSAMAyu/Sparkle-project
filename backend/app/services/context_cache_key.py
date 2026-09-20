"""C-07 · Context cache 版本键（单一权威模块）。

CONTEXT_COMPILER_V3.md §7：cache key 至少包含 user/tenant、decision type、
relevant object versions、memory_epoch、knowledge_version、policy_version、
model/capability version；写操作与纠偏请求不得用旧文本 cache 冒充新推理。

本模块只做两件事，不重建任何缓存层：

1. **版本解析** ``resolve_context_cache_versions`` —— 把既有的失效信号源
   （M-01/M-07 的 per-user ``memory_epoch``、偏好 ``preference_version``、
   A-05 的 ``policy_version``、E-05 的 ``knowledge_version``）一次性读出。
   全部为既有权威源，本卡**接入而非新造**。
2. **组合键** ``context_cache_key`` —— user 维度打头的版本化键；任一版本
   变化 → 键变 → 旧缓存条目自然孤儿化（E-05 version-key 模式，删除/纠正/
   权限收紧后零 stale 命中，不依赖 DEL 成功）。

fail-closed 纪律（M-07 epoch 读侧门同款）：任一版本读失败抛
``ContextCacheVersionError``，消费方必须当作 cache miss 处理（重建），
**不得**降级为无版本键继续命中——读不到版本就没有资格宣称新鲜。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

#: Context cache 载荷形态/能力版本（编译期常量）。载荷结构演进时 bump，
#: 旧条目随键变化孤儿化，等价于一次性全量失效。
CONTEXT_CACHE_SCHEMA_VERSION = "ctxcache.v1.c07"


class ContextCacheVersionError(RuntimeError):
    """版本解析失败（fail-closed：消费方必须绕过缓存重建）。"""


@dataclass(frozen=True)
class ContextCacheVersions:
    """一次 context cache 读写钉住的版本组（全部为既有权威源）。"""

    user_id: str
    #: M-01/M-07 per-user memory epoch（删除/纠正/supersede/权限收紧 → bump）
    memory_epoch: int
    #: 偏好中心版本（偏好 update/面板删除 → bump）
    preference_version: int
    #: A-05 active policy patch 集内容寻址版本（空集 = polpatch_none）
    policy_version: str
    #: E-05 知识图谱数据版本（知识写入/删除 → 变化；解析失败时 None）
    knowledge_version: str | None
    #: 载荷形态版本（编译期常量）
    schema_version: str = CONTEXT_CACHE_SCHEMA_VERSION

    def cache_key(self) -> str:
        return context_cache_key(self)


async def resolve_context_cache_versions(
    db: AsyncSession,
    user_id: UUID | str,
    *,
    redis_client: object | None = None,
) -> ContextCacheVersions:
    """读取当前用户的全部 context cache 版本信号（接入既有权威源）。

    任一信号读失败 → ``ContextCacheVersionError``（fail-closed）。
    ``knowledge_version`` 缺失（Redis 未初始化且计算为空）不算失败——
    E-05 消费方（graph_rag）同语义：None 参与键组合，不参与命中豁免。
    """
    uid = UUID(str(user_id))

    # 1. memory_epoch（M-01 契约；M-07 删除/纠正/权限管线统一 bump 点）
    from app.services.memory_service import MemoryService

    try:
        memory_epoch = await MemoryService(db).get_memory_epoch(uid)
    except Exception as exc:  # noqa: BLE001 — fail-closed：读失败不得静默降级
        raise ContextCacheVersionError(f"memory_epoch read failed: {exc}") from exc

    # 2. preference_version（偏好中心 DB 版本；update/删除路径递增）
    from app.services.personalization.preference_service import PreferenceService

    try:
        preference_version = int(await PreferenceService(db, redis_client).get_preference_version(uid) or 0)
    except Exception as exc:  # noqa: BLE001
        raise ContextCacheVersionError(f"preference_version read failed: {exc}") from exc

    # 3. policy_version（A-05 active patch 集内容寻址版本）
    from app.services.policy_patch_service import PolicyPatchService

    try:
        policy_version = await PolicyPatchService(db).policy_version(uid)
    except Exception as exc:  # noqa: BLE001
        raise ContextCacheVersionError(f"policy_version read failed: {exc}") from exc

    # 4. knowledge_version（E-05；Redis 缓存 + DB 计算，graph_rag 同源）
    knowledge_version: str | None = None
    try:
        from app.services.knowledge_service import KnowledgeService

        knowledge_version = await KnowledgeService(db).get_knowledge_version()
    except Exception:  # noqa: BLE001 — graph_rag 同语义：解析失败以 None 组键
        knowledge_version = None

    return ContextCacheVersions(
        user_id=str(uid),
        memory_epoch=int(memory_epoch),
        preference_version=int(preference_version),
        policy_version=str(policy_version),
        knowledge_version=knowledge_version,
    )


def context_cache_key(versions: ContextCacheVersions) -> str:
    """组合键：user 维度打头 + 全部版本尾。

    - 跨 user 结构性零碰撞：user_id 是键的第一段，版本尾不混入用户身份；
    - 删除/纠正/权限收紧 → memory_epoch bump → 键变 → 旧条目零命中；
    - 偏好/策略/知识任一变化同理。
    """
    tail = "|".join(
        (
            f"schema={versions.schema_version}",
            f"mepoch={versions.memory_epoch}",
            f"pv={versions.preference_version}",
            f"pol={versions.policy_version}",
            f"know={versions.knowledge_version or 'none'}",
        )
    )
    return f"{versions.user_id}|{tail}"
