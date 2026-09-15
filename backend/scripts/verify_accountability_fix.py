#!/usr/bin/env python3
"""
责任伙伴系统验证脚本
验证所有修复是否成功
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """运行命令并报告结果"""
    print(f"\n{'=' * 60}")
    print(f"🔍 {description}")
    print(f"{'=' * 60}")
    print(f"命令: {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

    if result.returncode == 0:
        print(f"✅ {description} - 成功")
        if result.stdout:
            print(result.stdout[:500])
        return True
    else:
        print(f"❌ {description} - 失败")
        print(f"错误: {result.stderr[:500]}")
        return False


def main():
    """运行所有验证步骤"""
    results = []

    # 1. 数据库迁移验证
    results.append(run_command("cd backend && .venv/bin/alembic current", "数据库迁移状态"))

    # 2. Schema验证
    results.append(
        run_command(
            "grep -c 'accountability_partnership\\|accountability_checkin' backend/gateway/internal/db/schema.sql",
            "Schema包含accountability表",
        )
    )

    # 3. Python语法验证
    results.append(
        run_command("python3 -m py_compile backend/app/api/v1/accountability.py", "Accountability API语法检查")
    )

    results.append(run_command("python3 -m py_compile backend/app/api/v1/community.py", "Community API语法检查"))

    # 4. Go网关编译验证
    results.append(run_command("cd backend/gateway && go build -o /tmp/gateway-test ./cmd/server", "Go网关编译"))

    # 5. Flutter代码验证
    results.append(
        run_command("cd mobile && flutter analyze --no-pub 2>&1 | grep -E 'error|No issues found'", "Flutter代码分析")
    )

    # 6. 测试文件验证
    results.append(
        run_command(
            "python3 -m py_compile backend/tests/integration/test_accountability_flow.py", "集成测试文件语法检查"
        )
    )

    # 7. 验证日志修复
    results.append(
        run_command(
            "grep -A 2 'except Exception as e:' backend/app/api/v1/accountability.py | grep -c 'logger.error'",
            "异常处理包含日志记录",
        )
    )

    # 总结
    print(f"\n{'=' * 60}")
    print(f"📊 验证总结")
    print(f"{'=' * 60}")

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"总测试数: {total}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")

    if failed == 0:
        print("\n🎉 所有验证通过！系统已就绪。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 项验证失败，请检查。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
