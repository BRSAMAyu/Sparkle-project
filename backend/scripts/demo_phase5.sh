#!/bin/bash

# ========================================
# Phase 5 完整演示脚本
# 演示时间：< 2 分钟
# ========================================

set -e  # 遇到错误立即停止

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Phase 5: 稳定性与演进 完整演示${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python 未安装${NC}"
    exit 1
fi

# 检查是否在 backend 目录
if [ ! -f "app/config/__init__.py" ]; then
    echo -e "${YELLOW}⚠ 请在 backend 目录下运行此脚本${NC}"
    echo "cd backend && ./scripts/demo_phase5.sh"
    exit 1
fi

# ========================================
# Phase 5A: 稳定性护栏
# ========================================

echo -e "${GREEN}=== Phase 5A: 稳定性护栏 ===${NC}"
echo ""

# 测试 1: HyDE 超时降级
echo -e "${BLUE}[1/7] HyDE 超时降级测试${NC}"
echo "验证：HyDE 生成超过延迟预算时自动降级为 Raw Search"
python -m pytest tests/phase5/test_hyde_rag.py::test_hyde_timeout_degradation -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ HyDE 超时降级正常${NC}"
else
    echo -e "${RED}✗ HyDE 超时降级失败${NC}"
fi
echo ""

# 测试 2: 熔断器全局一致性
echo -e "${BLUE}[2/7] 熔断器全局一致性测试${NC}"
echo "验证：多 worker 环境下熔断器状态全局一致"
python -m pytest tests/phase5/test_circuit_breaker.py::test_circuit_breaker_multi_worker_consistency -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 熔断器全局一致${NC}"
else
    echo -e "${RED}✗ 熔断器测试失败${NC}"
fi
echo ""

# 测试 3: 熔断器自动恢复
echo -e "${BLUE}[3/7] 熔断器自动恢复测试${NC}"
echo "验证：熔断器在恢复超时后自动关闭"
python -m pytest tests/phase5/test_circuit_breaker.py::test_circuit_breaker_auto_recovery -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 熔断器自动恢复正常${NC}"
else
    echo -e "${RED}✗ 熔断器恢复测试失败${NC}"
fi
echo ""

# ========================================
# Phase 5B: 文档引擎
# ========================================

echo -e "${GREEN}=== Phase 5B: 可解释文档引擎 ===${NC}"
echo ""

# 测试 4: 质量门禁 - 乱码检测
echo -e "${BLUE}[4/7] 质量门禁：乱码检测${NC}"
echo "验证：高乱码率文档被拦截"
python -m pytest tests/phase5/test_document_quality.py::test_quality_check_high_garbled_ratio -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 乱码检测正常${NC}"
else
    echo -e "${RED}✗ 乱码检测失败${NC}"
fi
echo ""

# 测试 5: 质量门禁 - 学术文档容忍
echo -e "${BLUE}[5/7] 质量门禁：学术文档特殊处理${NC}"
echo "验证：学术论文的数学符号不被误判为乱码"
python -m pytest tests/phase5/test_document_quality.py::test_quality_check_academic_document -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 学术文档处理正确${NC}"
else
    echo -e "${YELLOW}⚠ 学术文档测试未完全通过（可能需要调整阈值）${NC}"
fi
echo ""

# 测试 6: 文档类型检测
echo -e "${BLUE}[6/7] 文档类型自动检测${NC}"
echo "验证：自动识别学术/代码/发票/通用文档"
python -m pytest tests/phase5/test_document_quality.py::test_document_type_detection -v -s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 文档类型检测正常${NC}"
else
    echo -e "${RED}✗ 文档类型检测失败${NC}"
fi
echo ""

# 测试 7: 数据迁移验证
echo -e "${BLUE}[7/7] 数据迁移验证${NC}"
echo "检查 page_number → page_numbers 迁移状态"

# 运行迁移脚本的验证部分
python -c "
from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 检查新列是否存在
    result = conn.execute(text('''
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'document_chunks'
        AND column_name = 'page_numbers'
    '''))

    if result.fetchone():
        print('✓ page_numbers 列存在')

        # 统计数据
        stats = conn.execute(text('''
            SELECT
                COUNT(*) as total,
                COUNT(page_numbers) as with_page_numbers
            FROM document_chunks
        '''))

        total, with_nums = stats.fetchone()
        print(f'总切片数：{total}')
        print(f'有页码数据：{with_nums}')

        if total == 0:
            print('⚠ 数据库为空，跳过验证')
        elif with_nums == total:
            print('✓ 所有记录都有页码数据')
        else:
            print(f'⚠ 有 {total - with_nums} 条记录缺失页码')
    else:
        print('✗ page_numbers 列不存在，迁移未执行')
        exit(1)
" || echo -e "${YELLOW}⚠ 数据库未初始化或迁移未执行${NC}"

echo ""

# ========================================
# 总结
# ========================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  演示完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${GREEN}Phase 5A 亮点：${NC}"
echo "  ✓ HyDE 延迟预算控制（1.5秒超时）"
echo "  ✓ 熔断器 Redis 全局一致（多 worker 同步）"
echo "  ✓ SSE 断点续传（Last-Event-ID）"
echo ""

echo -e "${GREEN}Phase 5B 亮点：${NC}"
echo "  ✓ 分层质量检测（乱码/语言/结构）"
echo "  ✓ 文档类型自适应阈值"
echo "  ✓ 可溯源的知识节点（草稿态）"
echo "  ✓ 安全的数据迁移"
echo ""

echo -e "${YELLOW}配置文件位置：${NC}"
echo "  backend/app/config/phase5_config.py"
echo ""

echo -e "${YELLOW}快速调整参数：${NC}"
echo "  export PHASE5_HYDE_LATENCY_BUDGET_SEC=2.0"
echo "  export PHASE5_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10"
echo "  export PHASE5_DOC_QUALITY_GARBLED_THRESHOLD=0.08"
echo ""

echo -e "${BLUE}如需完整测试报告，运行：${NC}"
echo "  cd backend && pytest tests/phase5/ -v --html=phase5_report.html"
echo ""
