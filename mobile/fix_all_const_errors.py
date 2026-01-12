#!/usr/bin/env python3
"""
修复所有const错误
策略：移除所有包含 DS. 调用的 Widget 构造函数前的 const 关键字
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

        # 匹配 const Widget( 且内部包含 DS.
        # 这种复杂的正则可能不太稳，我们还是用简单的替换，把常见的 Widget 都过一遍
        
        widgets = [
            'BoxDecoration', 'TextStyle', 'InputDecoration', 'LinearGradient',
            'SizedBox', 'Center', 'Divider', 'Icon', 'CircularProgressIndicator',
            'Text', 'Row', 'Column', 'Expanded', 'Padding', 
            'Container', 'Stack', 'Positioned', 'SingleChildScrollView', 
            'ListView', 'IconButton', 'Transform', 'Opacity', 
            'AnimatedOpacity', 'InkWell', 'GestureDetector', 'Align',
            'EdgeInsets', 'BorderRadius', 'BorderSide', 'Border'
        ]
        
        for widget in widgets:
            # 替换 const Widget( 为 Widget(
            content = re.sub(rf'const\s+{widget}\(', f'{widget}(', content)
            # 替换 const Widget. 为 Widget.
            content = re.sub(rf'const\s+{widget}\.', f'{widget}.', content)

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
