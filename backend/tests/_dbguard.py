"""TEST-DBGUARD：pytest 数据库连接防泔染守卫（测试永不写演示库）。

背景（2026-09 两起同根事故）：主仓 ``.env`` 的 ``DATABASE_URL`` 指向演示/开发库
（``127.0.0.1:5432/sparkle``）时，pytest 的 integration ``db_session`` fixture、
迁移测试（alembic upgrade head）、全局 ``AsyncSessionLocal`` 直连演示库写入占位
数据（``journey_milestone_*`` 测试账号、``node-*`` 知识节点、``r2g2_p101_*`` 用户等）。

本模块是"演示库判定"的唯一事实源，零凭据、零连接：只做字符串解析与 .env 文件
键扫描，从不发起任何数据库连接。

判定标准（``is_demo_db_url``）：postgres 系 URL 且库名恰为 ``sparkle``
（docker-compose ``POSTGRES_DB`` 默认值，即演示/开发库）。测试库约定命名
``sparkle_test`` / ``*_test`` / ``*_e2e``。sqlite 串天然不在判定范围。

三层接入：

1. **会话门**（backend/tests/conftest.py ``pytest_configure``）：显式配置
   （环境变量或 .env 文件提供 DB 配置）的 DATABASE_URL 指向演示库 → 整个
   pytest 进程拒跑（``pytest.UsageError``，退出码 4）。
2. **域守卫**（integration conftest ``db_session`` / ``test_migrations`` /
   ``test_db_partitioning``）：真实建连入口在连接前复查，拒绝或跳过。
3. **tests_e2e 会话门**：独立 rootdir（不加载 backend/tests/conftest.py），
   在 tests_e2e/conftest.py 单独接入同一判定器。

worktree（无 .env、无环境变量）场景：Settings 会从 ``POSTGRES_*`` 默认值构造
出"演示库形状"的 URL，但密码为空、必然认证失败，且无任何显式配置——会话门
只打印提示横幅、**不改变任何既有行为**（该场景下需要真库的测试本就按原样
失败/跳过）。

显式白名单（仅限 CI 临时栈）：``SPARKLE_TEST_DB_ALLOW_NAMED_SPARKLE=1`` 把
会话门的拒绝降级为醒目告警。仅供 e2e-smoke 这类一次性容器栈（库名碰巧沿用
``sparkle``）使用；本地开发机禁止设置——那正是本守卫要拦的事故场景。
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

#: 演示/开发库的约定库名（docker-compose POSTGRES_DB 默认值）。
DEMO_DB_NAME = "sparkle"

#: 视为"显式提供了 DB 配置"的环境变量键。
_EXPLICIT_ENV_KEYS = (
    "DATABASE_URL",
    "POSTGRES_DB",
    "POSTGRES_HOST",
    "POSTGRES_PASSWORD",
    "DB_NAME",
    "DB_HOST",
    "DB_PASSWORD",
)

#: 视为"显式提供了 DB 配置"的 .env 文件键（与 app/config/settings.py 的
#: env_file 加载顺序一致：repo 根 → backend/ → backend/app/）。
_EXPLICIT_ENVFILE_KEYS = frozenset(_EXPLICIT_ENV_KEYS)

#: CI 临时栈显式白名单开关。
ALLOW_ENV_KEY = "SPARKLE_TEST_DB_ALLOW_NAMED_SPARKLE"

_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/
_REPO_ROOT = _BACKEND_ROOT.parent


def env_file_paths() -> list[Path]:
    """镜像 app/config/settings.py 的三个 env_file 路径。"""
    return [
        _REPO_ROOT / ".env",
        _BACKEND_ROOT / ".env",
        _BACKEND_ROOT / "app" / ".env",
    ]


def _env_files_define_db() -> bool:
    """任一 .env 文件里出现非空 DB 配置键即视为显式配置。"""
    for path in env_file_paths():
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, _, value = stripped.partition("=")
                if key.strip() in _EXPLICIT_ENVFILE_KEYS and value.strip().strip("\"'"):
                    return True
        except OSError:
            continue
    return False


def explicit_db_config() -> bool:
    """测试进程是否被**显式**配置了数据库（环境变量或 .env 文件）。

    均无时（裸 worktree 常态），Settings 从 POSTGRES_* 默认值构造的
    "sparkle 形状" URL 不算显式配置——那种串密码为空、无法认证，保持历史行为。
    """
    if any(os.environ.get(key) for key in _EXPLICIT_ENV_KEYS):
        return True
    return _env_files_define_db()


def parse_db_name(url: str) -> str | None:
    """从数据库 URL 解析库名；解析失败返回 None。"""
    if not url:
        return None
    try:
        path = urlparse(url).path or ""
    except ValueError:
        return None
    name = path.rsplit("/", 1)[-1]
    # 剥掉查询串残留（urlparse 已分离 query，这里仅防御异常写法）
    name = name.split("?", 1)[0]
    return name or None


def is_demo_db_url(url: str | None) -> bool:
    """URL 是否指向演示/开发库（postgres 系且库名 == sparkle）。"""
    if not url:
        return False
    scheme = url.split(":", 1)[0].strip().lower()
    if not scheme.startswith(("postgres", "postgresql")):
        return False
    return parse_db_name(url) == DEMO_DB_NAME


def allow_named_sparkle() -> bool:
    """CI 临时栈白名单是否打开。"""
    return os.environ.get(ALLOW_ENV_KEY, "").strip() == "1"


def demo_guard_message(url: str, context: str) -> str:
    """统一的拒绝/告警说明文案（含修复指引）。"""
    return (
        "TEST-DBGUARD：测试进程拒绝连接演示库\n"
        f"  位置: {context}\n"
        f"  DATABASE_URL = {url}\n"
        f"  判定: postgres 系 URL 且库名恰为 '{DEMO_DB_NAME}'（演示/开发库）。\n"
        "  事故背景: pytest 曾经由该 URL 向演示库写入占位数据\n"
        "  （journey_milestone_* 账号 / node-* 节点 / r2g2_p101_* 用户）。\n"
        "  修复（三选一）:\n"
        "    1. 把 DATABASE_URL 指向测试库（约定命名 *_test，如 sparkle_test）；\n"
        "    2. 在隔离 worktree 中运行（无 .env，测试自然落在 sqlite/跳过）；\n"
        "    3. 仅限 CI 一次性容器栈: 设置 SPARKLE_TEST_DB_ALLOW_NAMED_SPARKLE=1。\n"
        "  注意: 迁移测试/集成测试需要真库时，请自建专属测试库，绝不复用演示库。"
    )
