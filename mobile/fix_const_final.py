#!/usr/bin/env python3
"""
最终修复脚本：移除const关键字并将DS.xxx替换为DS.xxxConst
"""

import os
import re
from pathlib import Path

def fix_file(file_path: Path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        modified = False
        new_lines = []

        for line in lines:
            original_line = line

            # 如果行中包含DS.并且前面有const，移除const并将DS.xxx替换为DS.xxxConst
            if 'const ' in line and 'DS.' in line:
                # 移除const关键字
                line = line.replace('const ', '', 1)
                # 将DS.xxx替换为DS.xxxConst
                line = re.sub(r'DS\.(\w+)(?!Const\b)', r'DS.\1Const', line)
                if line != original_line:
                    modified = True

            new_lines.append(line)

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")
        return False

def main():
    # 从构建错误中获取需要修复的文件列表
    error_files = [
        # 从构建错误中提取的文件
        'lib/presentation/widgets/tools/breathing_tool.dart',
        'lib/presentation/widgets/tools/calculator_tool.dart',
        'lib/presentation/widgets/tools/flash_capsule_tool.dart',
        'lib/presentation/widgets/tools/focus_stats_tool.dart',
        'lib/presentation/widgets/tools/notes_tool.dart',
        'lib/presentation/widgets/tools/translator_tool.dart',
        'lib/presentation/widgets/tools/vocabulary_lookup_tool.dart',
        'lib/presentation/widgets/tools/wordbook_tool.dart',
        'lib/presentation/screens/profile/password_reset_screen.dart',
        'lib/presentation/screens/profile/unified_settings_screen.dart',
        'lib/presentation/screens/community/friends_screen.dart',
        'lib/presentation/screens/stats/calendar_stats_screen.dart',
        'lib/presentation/widgets/home/calendar_heatmap_card.dart',
    ]

    mobile_dir = Path('/Users/a/code/sparkle-flutter/mobile')

    fixed_count = 0
    for rel_path in error_files:
        file_path = mobile_dir / rel_path
        if file_path.exists():
            if fix_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️  文件不存在: {file_path}")

    print(f"\n📊 修复完成:")
    print(f"  需要修复: {len(error_files)}")
    print(f"  成功修复: {fixed_count}")

if __name__ == '__main__':
    main()