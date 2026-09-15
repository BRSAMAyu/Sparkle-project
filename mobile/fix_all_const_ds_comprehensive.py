#!/usr/bin/env python3
"""
全面修复const + DS.错误
策略：使用时灵活 - 移除const关键字，使用DS.xxxConst
"""

import os
import re
from pathlib import Path

def fix_const_ds_in_file(file_path: Path):
    """修复单个文件中的const + DS.错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复模式：const Widget(..., color: DS.xxx, ...)
        # 移除const关键字，并将DS.xxx替换为DS.xxxConst

        # 常见Widget模式
        widget_patterns = [
            r'const\s+BoxDecoration\(',
            r'const\s+TextStyle\(',
            r'const\s+InputDecoration\(',
            r'const\s+LinearGradient\(',
            r'const\s+SizedBox\(',
            r'const\s+Center\(',
            r'const\s+Divider\(',
            r'const\s+Icon\(',
            r'const\s+CircularProgressIndicator\(',
            r'const\s+Padding\(',
            r'const\s+Container\(',
            r'const\s+Column\(',
            r'const\s+Row\(',
            r'const\s+Stack\(',
            r'const\s+Align\(',
            r'const\s+Positioned\(',
            r'const\s+Flexible\(',
            r'const\s+Expanded\(',
        ]

        for pattern in widget_patterns:
            content = re.sub(pattern, pattern.replace('const ', ''), content)

        # 将DS.xxx替换为DS.xxxConst（在const上下文中）
        # 但要注意：如果已经在非const上下文中，不要替换

        # 首先找到所有DS.xxx的实例
        ds_pattern = r'DS\.(\w+)(?!Const\b)'

        def replace_ds_const(match):
            ds_property = match.group(1)
            return f'DS.{ds_property}Const'

        # 应用替换
        content = re.sub(ds_pattern, replace_ds_const, content)

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")
        return False

def find_all_dart_files(directory: Path):
    """查找所有Dart文件"""
    dart_files = []
    for root, dirs, files in os.walk(directory):
        # 跳过测试目录
        if 'test' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.dart'):
                dart_files.append(Path(root) / file)
    return dart_files

def main():
    mobile_dir = Path('/Users/a/code/sparkle-flutter/mobile')

    # 查找所有Dart文件
    dart_files = find_all_dart_files(mobile_dir)
    print(f"📁 找到 {len(dart_files)} 个Dart文件")

    # 修复文件
    fixed_count = 0
    for i, dart_file in enumerate(dart_files, 1):
        print(f"🔍 处理 ({i}/{len(dart_files)}): {dart_file.relative_to(mobile_dir)}")
        if fix_const_ds_in_file(dart_file):
            fixed_count += 1

    print(f"\n📊 修复完成:")
    print(f"  总计文件: {len(dart_files)}")
    print(f"  修复文件: {fixed_count}")
    print(f"  跳过文件: {len(dart_files) - fixed_count}")

if __name__ == '__main__':
    main()