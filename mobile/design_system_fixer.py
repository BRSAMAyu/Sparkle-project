#!/usr/bin/env python3
"""
设计系统修复脚本

用于批量替换硬编码颜色和间距值
"""

import os
import re
from pathlib import Path

class DesignSystemFixer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)

        # 颜色替换映射
        self.color_replacements = {
            # Material Colors
            r'Colors\.white': 'DS.brandPrimary',  # 临时替换，实际需要根据上下文确定
            r'Colors\.black': 'DS.brandPrimary',
            r'Colors\.blue': 'DS.brandPrimary',
            r'Colors\.red': 'DS.error',
            r'Colors\.green': 'DS.success',
            r'Colors\.yellow': 'DS.warning',
            r'Colors\.grey': 'DS.brandPrimary',  # 临时替换

            # 硬编码颜色值
            r'Color\(0xFFFFFFFF\)': 'DS.brandPrimary',
            r'Color\(0xFF000000\)': 'DS.brandPrimary',
            r'Color\(0xFF2196F3\)': 'DS.info',
            r'Color\(0xFF4CAF50\)': 'DS.success',
            r'Color\(0xFFF44336\)': 'DS.error',
            r'Color\(0xFFFFA726\)': 'DS.warning',

            # Sparkle 主题颜色
            r'Color\(0xFFFF6B35\)': 'DS.brandPrimary',
            r'Color\(0xFF1A237E\)': 'DS.brandSecondary',
        }

        # 间距替换映射
        self.spacing_replacements = {
            r'EdgeInsets\.all\(4\)': 'EdgeInsets.all(DS.xs)',
            r'EdgeInsets\.all\(8\)': 'EdgeInsets.all(DS.sm)',
            r'EdgeInsets\.all\(12\)': 'EdgeInsets.all(DS.md)',
            r'EdgeInsets\.all\(16\)': 'EdgeInsets.all(DS.lg)',
            r'EdgeInsets\.all\(24\)': 'EdgeInsets.all(DS.xl)',
            r'EdgeInsets\.all\(32\)': 'EdgeInsets.all(DS.xxl)',
            r'EdgeInsets\.all\(48\)': 'EdgeInsets.all(DS.xxxl)',

            r'SizedBox\(height: 4\)': 'SizedBox(height: DS.xs)',
            r'SizedBox\(height: 8\)': 'SizedBox(height: DS.sm)',
            r'SizedBox\(height: 12\)': 'SizedBox(height: DS.md)',
            r'SizedBox\(height: 16\)': 'SizedBox(height: DS.lg)',
            r'SizedBox\(height: 24\)': 'SizedBox(height: DS.xl)',
            r'SizedBox\(height: 32\)': 'SizedBox(height: DS.xxl)',
            r'SizedBox\(height: 48\)': 'SizedBox(height: DS.xxxl)',

            r'SizedBox\(width: 4\)': 'SizedBox(width: DS.xs)',
            r'SizedBox\(width: 8\)': 'SizedBox(width: DS.sm)',
            r'SizedBox\(width: 12\)': 'SizedBox(width: DS.md)',
            r'SizedBox\(width: 16\)': 'SizedBox(width: DS.lg)',
            r'SizedBox\(width: 24\)': 'SizedBox(width: DS.xl)',
            r'SizedBox\(width: 32\)': 'SizedBox(width: DS.xxl)',
            r'SizedBox\(width: 48\)': 'SizedBox(width: DS.xxxl)',
        }

        # 需要导入DS的文件列表
        self.files_need_ds_import = set()

    def find_dart_files(self):
        """查找所有Dart文件"""
        dart_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 排除测试文件和生成的文件
            if 'test' in root or '.g.' in root or 'generated' in root:
                continue

            for file in files:
                if file.endswith('.dart'):
                    file_path = Path(root) / file
                    dart_files.append(file_path)

        return dart_files

    def fix_file(self, file_path):
        """修复单个文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        changes_made = False

        # 检查是否需要导入DS
        needs_ds_import = 'DS.' in content and 'import.*design_system' not in content

        # 替换硬编码颜色
        for pattern, replacement in self.color_replacements.items():
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changes_made = True
                if replacement.startswith('DS.'):
                    needs_ds_import = True

        # 替换硬编码间距
        for pattern, replacement in self.spacing_replacements.items():
            new_content, count = re.subn(pattern, replacement, content)
            if count > 0:
                content = new_content
                changes_made = True
                if replacement.startswith('DS.'):
                    needs_ds_import = True

        # 添加DS导入
        if needs_ds_import and 'import.*design_system' not in content:
            # 查找第一个import语句之后的位置
            import_match = re.search(r'^import\s+[\'\"].*[\'\"];', content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.end()
                # 查找import块结束的位置
                lines = content[:insert_pos].split('\n')
                last_import_line = -1
                for i, line in enumerate(lines):
                    if line.strip().startswith('import'):
                        last_import_line = i

                if last_import_line >= 0:
                    # 在最后一个import行后插入
                    lines.insert(last_import_line + 1, "import 'package:sparkle/core/design/design_system.dart';")
                    content = '\n'.join(lines) + content[insert_pos:]
                    changes_made = True

        if changes_made:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            if needs_ds_import:
                self.files_need_ds_import.add(str(file_path))

            return True

        return False

    def run(self):
        """运行修复"""
        print("=" * 80)
        print("设计系统修复脚本")
        print("=" * 80)

        dart_files = self.find_dart_files()
        print(f"找到 {len(dart_files)} 个Dart文件")

        fixed_files = []
        for file_path in dart_files:
            relative_path = file_path.relative_to(self.project_root)
            print(f"检查: {relative_path}", end='')

            try:
                if self.fix_file(file_path):
                    fixed_files.append(str(relative_path))
                    print(" ✅ 已修复")
                else:
                    print(" ✓ 无问题")
            except Exception as e:
                print(f" ❌ 错误: {e}")

        print("\n" + "=" * 80)
        print("修复完成!")
        print(f"修复了 {len(fixed_files)} 个文件:")

        for file in fixed_files:
            print(f"  • {file}")

        if self.files_need_ds_import:
            print(f"\n以下文件需要手动检查DS导入:")
            for file in self.files_need_ds_import:
                print(f"  • {file}")

        print("\n💡 注意事项:")
        print("  1. 某些颜色替换可能需要根据上下文手动调整")
        print("  2. 建议运行Flutter分析检查语法错误")
        print("  3. 建议手动测试修复后的UI")
        print("=" * 80)

def main():
    import sys

    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # 默认使用当前目录
        project_root = os.getcwd()

    fixer = DesignSystemFixer(project_root)
    fixer.run()

if __name__ == '__main__':
    main()