#!/usr/bin/env python3
"""
移除const关键字脚本
策略：使用时灵活 - 在UI代码中移除const关键字
"""

import os
import re
from pathlib import Path

def remove_const_keyword(file_path: Path):
    """从文件中移除const关键字"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 保存原始内容用于比较
        original_content = content

        # 模式1: const Color xxx = DS.brandPrimary;
        pattern1 = r'const\s+Color\s+(\w+)\s*=\s*DS\.\w+;'
        content = re.sub(pattern1, r'Color \1 = DS.brandPrimaryConst;', content)

        # 模式2: const Color xxx = DS.brandPrimary
        pattern2 = r'const\s+Color\s+(\w+)\s*=\s*DS\.\w+'
        content = re.sub(pattern2, r'Color \1 = DS.brandPrimaryConst', content)

        # 模式3: const xxx = DS.xxx (通用模式)
        pattern3 = r'const\s+(\w+)\s+(\w+)\s*=\s*DS\.(\w+);'
        def replace_const(match):
            type_name = match.group(1)
            var_name = match.group(2)
            ds_property = match.group(3)
            return f'{type_name} {var_name} = DS.{ds_property}Const;'
        content = re.sub(pattern3, replace_const, content)

        # 模式4: const xxx = DS.xxx (没有分号)
        pattern4 = r'const\s+(\w+)\s+(\w+)\s*=\s*DS\.(\w+)'
        def replace_const_no_semicolon(match):
            type_name = match.group(1)
            var_name = match.group(2)
            ds_property = match.group(3)
            return f'{type_name} {var_name} = DS.{ds_property}Const'
        content = re.sub(pattern4, replace_const_no_semicolon, content)

        # 模式5: const BorderRadius xxx = BorderRadius.circular(DS.xxx);
        pattern5 = r'const\s+BorderRadius\s+(\w+)\s*=\s*BorderRadius\.circular\(\s*DS\.(\w+)\s*\);'
        content = re.sub(pattern5, r'BorderRadius \1 = BorderRadius.circular(DS.\2Const);', content)

        # 模式6: const EdgeInsets xxx = EdgeInsets.all(DS.xxx);
        pattern6 = r'const\s+EdgeInsets\s+(\w+)\s*=\s*EdgeInsets\.all\(\s*DS\.(\w+)\s*\);'
        content = re.sub(pattern6, r'EdgeInsets \1 = EdgeInsets.all(DS.\2Const);', content)

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

def find_files_with_const_ds(directory: Path):
    """查找包含const + DS.的文件"""
    files_to_fix = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if re.search(r'const.*DS\.', content):
                            files_to_fix.append(file_path)
                except:
                    continue
    return files_to_fix

def main():
    # 设置工作目录
    mobile_dir = Path('mobile')
    if not mobile_dir.exists():
        print("❌ 错误: 找不到mobile目录")
        return

    # 查找需要修复的文件
    files_to_fix = find_files_with_const_ds(mobile_dir)
    print(f"📁 找到 {len(files_to_fix)} 个需要修复的文件")

    # 修复文件
    fixed_count = 0
    for file_path in files_to_fix:
        if remove_const_keyword(file_path):
            fixed_count += 1

    print(f"\n📊 修复完成:")
    print(f"  需要修复: {len(files_to_fix)}")
    print(f"  成功修复: {fixed_count}")
    print(f"  失败修复: {len(files_to_fix) - fixed_count}")

if __name__ == '__main__':
    main()