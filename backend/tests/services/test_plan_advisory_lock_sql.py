"""F-3 回归守卫：text() SQL 内禁用 ":param::type" PG cast 写法。

SQLite 测试基座会跳过 postgresql-only 分支（dialect.name != "postgresql"），
因此 advisory-lock 语句的绑定参数解析错误只能靠静态断言守住：
SQLAlchemy text() 会把 ":param::type" 中的 ":type" 解析为第二个绑定参数，
asyncpg 随即收到裸 ":" 报 PostgresSyntaxError（plan 创建全量 500，F-3）。
正确写法是 CAST(:param AS type)。
"""

import inspect
import re

from app.services import plan_service


def test_no_postgres_cast_colon_syntax_in_text_sql():
    src = inspect.getsource(plan_service)
    offenders = []
    for m in re.finditer(r'text\(\s*"([^"]+)"', src):
        sql = m.group(1)
        # ":word::" 或 ":word ::" 形式：绑定参数后跟 PG cast
        if re.search(r":[A-Za-z_]\w*\s*::", sql):
            offenders.append(sql[:80])
    assert not offenders, (
        "text() SQL 使用了 ':param::type' PG cast —— SQLAlchemy 会把 ':type' "
        "解析成第二个绑定参数导致 asyncpg 语法错误。改用 CAST(:param AS type)：" 
        f"{offenders}"
    )


def test_advisory_lock_uses_cast_form():
    src = inspect.getsource(plan_service)
    assert "pg_advisory_xact_lock" in src
    assert re.search(
        r"pg_advisory_xact_lock\(hashtextextended\(CAST\(:user_id AS text\), 0\)\)", src
    ), "advisory lock 语句应保持 CAST(:user_id AS text) 形式"
