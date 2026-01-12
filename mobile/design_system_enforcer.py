#!/usr/bin/env python3
"""
设计系统强制执行器 - 批量修复硬编码
"""

import re
import glob

# 颜色替换规则
COLOR_REPLACEMENTS = {
    r'Colors\.white(?!\.withValues)': 'AppDesignTokens.neutral50',
    r'Colors\.black(?!\.withValues)': 'AppDesignTokens.neutral900',
    r'Colors\.red(?!\.withValues)': 'AppDesignTokens.error',
    r'Colors\.blue(?!\.withValues)': 'AppDesignTokens.info',
    r'Colors\.green(?!\.withValues)': 'AppDesignTokens.success',
    r'Colors\.orange(?!\.withValues)': 'AppDesignTokens.warning',
    r'Colors\.grey(?!\.withValues)': 'AppDesignTokens.neutral500',
}

SKIP_FILES = [
    'design_tokens.dart',
    'design_system.dart',
    'color_token.dart',
    'theme_manager.dart',
]

def should_skip_file(file_path):
    return any(skip in file_path for skip in SKIP_FILES)

def enforce_design_system(file_path):
    if should_skip_file(file_path):
        return False, []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content
        changes = []

        for pattern, replacement in COLOR_REPLACEMENTS.items():
            matches = list(re.finditer(pattern, content))
            if matches:
                content = re.sub(pattern, replacement, content)
                changes.append(f'{pattern} → {replacement} ({len(matches)}处)')

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes

        return False, []

    except Exception as e:
        print(f'❌ 错误: {file_path}: {e}')
        return False, []

def main():
    print('=' * 80)
    print('设计系统强制执行器')
    print('=' * 80)

    dart_files = glob.glob('lib/**/*.dart', recursive=True)
    modified_files = 0

    for file_path in dart_files:
        modified, changes = enforce_design_system(file_path)
        if modified:
            modified_files += 1
            print(f'\n✅ {file_path}')
            for change in changes:
                print(f'   - {change}')

    print(f'\n修复完成! 修改了 {modified_files} 个文件')

if __name__ == '__main__':
    main()
