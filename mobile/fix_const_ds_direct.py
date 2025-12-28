#!/usr/bin/env python3
"""
直接修复const + DS.错误
"""

import os
import re
from pathlib import Path

def fix_const_ds(file_path: Path):
    """修复文件中的const + DS.错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        modified = False
        new_lines = []

        for line in lines:
            original_line = line

            # 修复模式: const xxx = DS.brandPrimary;
            if 'const ' in line and 'DS.' in line:
                # 移除const关键字
                line = line.replace('const ', '', 1)
                # 将DS.xxx替换为DS.xxxConst
                line = re.sub(r'DS\.(\w+)(?!Const)', r'DS.\1Const', line)
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
    # 查找所有Dart文件
    mobile_dir = Path('/Users/a/code/sparkle-flutter/mobile')
    dart_files = []
    for root, dirs, files in os.walk(mobile_dir):
        for file in files:
            if file.endswith('.dart'):
                dart_files.append(Path(root) / file)

    print(f"📁 找到 {len(dart_files)} 个Dart文件")

    # 修复文件
    fixed_count = 0
    for dart_file in dart_files:
        if fix_const_ds(dart_file):
            fixed_count += 1

    print(f"\n📊 修复完成:")
    print(f"  总计文件: {len(dart_files)}")
    print(f"  修复文件: {fixed_count}")

if __name__ == '__main__':
    main()