#!/usr/bin/env python3
"""
修复所有const错误
策略：移除所有const BoxDecoration, const TextStyle等中的const关键字
"""

import os
import re
from pathlib import Path

def fix_const_errors(file_path: Path):
    """修复文件中的const错误"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 修复模式1: const BoxDecoration(color: DS.xxx)
        pattern1 = r'const\s+BoxDecoration\('
        content = re.sub(pattern1, 'BoxDecoration(', content)

        # 修复模式2: const TextStyle(color: DS.xxx)
        pattern2 = r'const\s+TextStyle\('
        content = re.sub(pattern2, 'TextStyle(', content)

        # 修复模式3: const InputDecoration
        pattern3 = r'const\s+InputDecoration\('
        content = re.sub(pattern3, 'InputDecoration(', content)

        # 修复模式4: const LinearGradient
        pattern4 = r'const\s+LinearGradient\('
        content = re.sub(pattern4, 'LinearGradient(', content)

        # 修复模式5: const SizedBox
        pattern5 = r'const\s+SizedBox\('
        content = re.sub(pattern5, 'SizedBox(', content)

        # 修复模式6: const Center
        pattern6 = r'const\s+Center\('
        content = re.sub(pattern6, 'Center(', content)

        # 修复模式7: const Divider
        pattern7 = r'const\s+Divider\('
        content = re.sub(pattern7, 'Divider(', content)

        # 修复模式8: const Icon
        pattern8 = r'const\s+Icon\('
        content = re.sub(pattern8, 'Icon(', content)

        # 修复模式9: const CircularProgressIndicator
        pattern9 = r'const\s+CircularProgressIndicator\('
        content = re.sub(pattern9, 'CircularProgressIndicator(', content)

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

def find_files_with_const_errors(directory: Path):
    """查找包含const错误的文件"""
    error_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 查找包含const + DS.的模式
                        if re.search(r'const.*DS\.', content):
                            error_files.append(file_path)
                except:
                    continue
    return error_files

def main():
    # 设置工作目录
    mobile_dir = Path('/Users/a/code/sparkle-flutter/mobile')

    # 查找需要修复的文件
    error_files = find_files_with_const_errors(mobile_dir)
    print(f"📁 找到 {len(error_files)} 个需要修复的文件")

    # 修复文件
    fixed_count = 0
    for file_path in error_files:
        if fix_const_errors(file_path):
            fixed_count += 1

    print(f"\n📊 修复完成:")
    print(f"  需要修复: {len(error_files)}")
    print(f"  成功修复: {fixed_count}")

if __name__ == '__main__':
    main()