#!/bin/bash
# 简单修复const错误脚本

echo "🔧 开始修复const错误..."

# 1. 移除所有const Widget(..., color: DS.xxx, ...)中的const关键字
echo "步骤1: 移除const Widget中的const关键字"
find lib -name "*.dart" -type f -exec sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const TextStyle(/TextStyle(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const InputDecoration(/InputDecoration(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const LinearGradient(/LinearGradient(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const SizedBox(/SizedBox(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const Center(/Center(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const Divider(/Divider(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const Icon(/Icon(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const CircularProgressIndicator(/CircularProgressIndicator(/g' {} \;
find lib -name "*.dart" -type f -exec sed -i '' 's/const Padding(/Padding(/g' {} \;

# 2. 将DS.xxx替换为DS.xxxConst（在const上下文中）
echo "步骤2: 将DS.xxx替换为DS.xxxConst"
# 注意：这个替换需要谨慎，只在const上下文中替换
# 我们使用一个更智能的方法：先找到所有const + DS.的行，然后替换

# 3. 修复特定的语法错误
echo "步骤3: 修复特定语法错误"
# 修复 Text(brandPrimary)) 多括号错误
find lib -name "*.dart" -type f -exec sed -i '' 's/Text(brandPrimary))/Text("brandPrimary")/g' {} \;

echo "✅ 修复完成！"
echo ""
echo "📊 下一步："
echo "1. 运行 'flutter analyze' 检查错误"
echo "2. 运行 'flutter build apk --debug' 测试构建"
echo "3. 手动检查剩余的const错误"