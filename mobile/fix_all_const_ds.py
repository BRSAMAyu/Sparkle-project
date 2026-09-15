#!/usr/bin/env python3
import re
import glob

# 递归查找所有dart文件
dart_files = glob.glob('lib/**/*.dart', recursive=True)

for file_path in dart_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original = content

        # 修复 const SizedBox with DS spacing
        content = re.sub(r'const SizedBox\((height|width): DS\.(xs|sm|md|lg|xl|xxl|xxxl)\)',
                        lambda m: f'SizedBox({m.group(1)}: DS.{m.group(2)})', content)

        # 修复 const EdgeInsets.all(DS.xx)
        content = re.sub(r'const EdgeInsets\.all\(DS\.(xs|sm|md|lg|xl|xxl|xxxl)\)',
                        lambda m: f'EdgeInsets.all(DS.{m.group(1)})', content)

        # 修复 const Icon with DS color
        content = re.sub(r'const Icon\(([^)]+), color: DS\.([a-zA-Z0-9_]+)',
                        lambda m: f'Icon({m.group(1)}, color: DS.{m.group(2)}', content)

        # 修复 const Text with DS color
        content = re.sub(r'const Text\s*\([^)]*style:\s*const\s*TextStyle\([^)]*color:\s*DS\.',
                        lambda m: m.group(0).replace('const TextStyle(', 'TextStyle(').replace('const Text', 'Text'), content)

        # 修复 const TextStyle(..., color: DS.xx)
        content = re.sub(r'const TextStyle\(([^)]*color:\s*DS\.[a-zA-Z0-9_]+[^)]*)\)',
                        lambda m: f'TextStyle({m.group(1)})', content)

        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Fixed: {file_path}')
    except Exception as e:
        print(f'Error processing {file_path}: {e}')

print('Done!')
