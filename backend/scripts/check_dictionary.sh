#!/bin/bash
# 词典文件健康检查脚本
# Dictionary File Health Check Script

set -e

MDX_PATH="${MDX_DICTIONARY_PATH:-/app/data/dictionaries/oaldpe.mdx}"
MDD_PATH="${MDD_RESOURCES_PATH:-}"

echo "🔍 Checking dictionary files..."
echo "   MDX path: $MDX_PATH"

if [ -f "$MDX_PATH" ]; then
    FILE_SIZE=$(du -h "$MDX_PATH" | cut -f1)
    echo "✅ MDX dictionary found (${FILE_SIZE})"

    # 测试Python是否能导入MDX依赖
    python3 -c "
try:
    from readmdict import MDX
    from bs4 import BeautifulSoup
    print('✅ MDX dependencies available')
except ImportError as e:
    print('⚠️  MDX dependencies missing:', e)
    exit(1)
" 2>/dev/null || echo "⚠️  WARNING: MDX dependencies not fully functional"

    exit 0
else
    echo "⚠️  WARNING: MDX dictionary file NOT found"
    echo "   Expected location: $MDX_PATH"
    echo ""
    echo "   Impact: Vocabulary lookup will use fallback only (database or external API)"
    echo "   Fix: Ensure data/dictionaries/ directory exists with .mdx file"
    echo ""
    echo "   If using Git:"
    echo "   1. git pull origin main"
    echo "   2. Check that data/dictionaries/ was cloned"
    echo ""
    exit 0  # 不阻止启动，只是警告
fi
