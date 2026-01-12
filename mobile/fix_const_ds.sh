#!/bin/bash

# 批量修复 const 中使用 DS getter 的问题

# DS spacing values
sed -i '' 's/const SizedBox(height: DS\.xs)/SizedBox(height: 4)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.sm)/SizedBox(height: 8)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.md)/SizedBox(height: 12)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.lg)/SizedBox(height: 16)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.xl)/SizedBox(height: 24)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.xxl)/SizedBox(height: 32)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(height: DS\.xxxl)/SizedBox(height: 48)/g' lib/**/*.dart

sed -i '' 's/const SizedBox(width: DS\.xs)/SizedBox(width: 4)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.sm)/SizedBox(width: 8)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.md)/SizedBox(width: 12)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.lg)/SizedBox(width: 16)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.xl)/SizedBox(width: 24)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.xxl)/SizedBox(width: 32)/g' lib/**/*.dart
sed -i '' 's/const SizedBox(width: DS\.xxxl)/SizedBox(width: 48)/g' lib/**/*.dart

# DS colors - 移除 const
sed -i '' 's/const Icon(\(.*\), color: DS\./Icon(\1, color: DS./g' lib/**/*.dart
sed -i '' 's/const TextStyle(\(.*\)color: DS\./TextStyle(\1color: DS./g' lib/**/*.dart

echo "修复完成"
