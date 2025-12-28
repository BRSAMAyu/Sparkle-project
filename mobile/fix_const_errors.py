#!/usr/bin/env python3
"""
批量修复const错误脚本
策略：定义时严谨，使用时灵活
1. 在const上下文中使用DS.xxxConst常量
2. 在非const上下文中使用DS.xxx getter
3. 移除不必要的const关键字
"""

import os
import re
from pathlib import Path

# 定义修复映射
# 格式: {原模式: (const模式, 非const模式)}
FIX_MAPPINGS = {
    # 颜色
    r'DS\.brandPrimary': ('DS.brandPrimaryConst', 'DS.brandPrimary'),
    r'DS\.brandSecondary': ('DS.brandSecondaryConst', 'DS.brandSecondary'),
    r'DS\.success': ('DS.successConst', 'DS.success'),
    r'DS\.warning': ('DS.warningConst', 'DS.warning'),
    r'DS\.error': ('DS.errorConst', 'DS.error'),
    r'DS\.info': ('DS.infoConst', 'DS.info'),

    # 间距
    r'DS\.xs': ('DS.xsConst', 'DS.xs'),
    r'DS\.sm': ('DS.smConst', 'DS.sm'),
    r'DS\.md': ('DS.mdConst', 'DS.md'),
    r'DS\.lg': ('DS.lgConst', 'DS.lg'),
    r'DS\.xl': ('DS.xlConst', 'DS.xl'),
    r'DS\.xxl': ('DS.xxlConst', 'DS.xxl'),
    r'DS\.xxxl': ('DS.xxxlConst', 'DS.xxxl'),

    # 圆角
    r'DS\.radiusSm': ('DS.radiusSmConst', 'DS.radiusSm'),
    r'DS\.radiusMd': ('DS.radiusMdConst', 'DS.radiusMd'),
    r'DS\.radiusLg': ('DS.radiusLgConst', 'DS.radiusLg'),
    r'DS\.radiusXl': ('DS.radiusXlConst', 'DS.radiusXl'),
    r'DS\.radiusFull': ('DS.radiusFullConst', 'DS.radiusFull'),
}

def is_in_const_context(line: str, file_content: str, line_index: int) -> bool:
    """
    判断一行代码是否在const上下文中
    """
    # 检查当前行是否包含const关键字
    if 'const ' in line:
        return True

    # 检查前几行是否有const声明
    for i in range(max(0, line_index - 3), line_index):
        prev_line = file_content[i].strip()
        if prev_line.startswith('const ') or prev_line.startswith('static const '):
            return True

    return False

def fix_file(file_path: Path):
    """修复单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        modified = False
        new_lines = []

        for i, line in enumerate(lines):
            original_line = line

            # 检查是否在const上下文中
            in_const = is_in_const_context(line, lines, i)

            # 应用修复映射
            for pattern, (const_replacement, non_const_replacement) in FIX_MAPPINGS.items():
                if re.search(pattern, line):
                    replacement = const_replacement if in_const else non_const_replacement
                    line = re.sub(pattern, replacement, line)
                    if line != original_line:
                        modified = True

            # 移除不必要的const关键字（如果使用了const模式）
            if in_const and any(pattern in line for pattern in FIX_MAPPINGS.keys()):
                # 检查是否应该移除const
                for pattern in FIX_MAPPINGS.keys():
                    if pattern in line and FIX_MAPPINGS[pattern][0] in line:
                        # 这是一个简单的const变量声明，可以移除const
                        line = line.replace('const ', '', 1)
                        modified = True

            new_lines.append(line)

        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"✅ 修复: {file_path}")
            return True
        else:
            print(f"⏭️ 跳过: {file_path} (无需修复)")
            return False

    except Exception as e:
        print(f"❌ 错误: {file_path} - {e}")
        return False

def find_dart_files(directory: Path):
    """查找所有Dart文件"""
    dart_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.dart'):
                dart_files.append(Path(root) / file)
    return dart_files

def main():
    # 设置工作目录
    mobile_dir = Path('mobile')
    if not mobile_dir.exists():
        print("❌ 错误: 找不到mobile目录")
        return

    # 查找所有Dart文件
    dart_files = find_dart_files(mobile_dir)
    print(f"📁 找到 {len(dart_files)} 个Dart文件")

    # 修复文件
    fixed_count = 0
    for dart_file in dart_files:
        if fix_file(dart_file):
            fixed_count += 1

    print(f"\n📊 修复完成:")
    print(f"  总计文件: {len(dart_files)}")
    print(f"  修复文件: {fixed_count}")
    print(f"  跳过文件: {len(dart_files) - fixed_count}")

if __name__ == '__main__':
    main()