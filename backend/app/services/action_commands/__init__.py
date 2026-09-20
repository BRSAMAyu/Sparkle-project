"""X-03 · Action 命令处理器注册面（封闭：与 ActionCommandType 一一对应）.

处理器实现按域分包（当前仅任务域 ``task_commands``）。新增命令域 = 契约变更：
1. ``app/core/action_command.py`` ActionCommandType 登记；
2. 域包实现 prepare/validate_subject/execute 三段协议；
3. 此处注册；
4. 冻结测试 bump。
"""

from app.services.action_commands.task_commands import (  # noqa: F401
    COMMAND_HANDLERS,
    TASK_FIELD_WHITELIST,
    get_command_handler,
)
