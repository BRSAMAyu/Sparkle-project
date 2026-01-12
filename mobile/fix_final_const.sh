#!/bin/bash
# 最终const错误修复脚本

echo "🔧 修复最终const错误..."

# 1. 修复notes_tool.dart中的Color[]错误
echo "修复 notes_tool.dart..."
sed -i '' 's/color: DS\.brandPrimary\[200\]/color: DS.brandPrimary200/g' lib/presentation/widgets/tools/notes_tool.dart

# 2. 修复flash_capsule_tool.dart
echo "修复 flash_capsule_tool.dart..."
sed -i '' 's/const InputDecoration(/InputDecoration(/g' lib/presentation/widgets/tools/flash_capsule_tool.dart
sed -i '' 's/const LinearGradient(/LinearGradient(/g' lib/presentation/widgets/tools/flash_capsule_tool.dart

# 3. 修复daily_detail_screen.dart
echo "修复 daily_detail_screen.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/screens/calendar/daily_detail_screen.dart

# 4. 修复knowledge_detail_screen.dart
echo "修复 knowledge_detail_screen.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/screens/knowledge/knowledge_detail_screen.dart

# 5. 修复engagement_heatmap.dart
echo "修复 engagement_heatmap.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/widgets/charts/engagement_heatmap.dart

# 6. 修复sprint_card.dart
echo "修复 sprint_card.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/widgets/home/sprint_card.dart
sed -i '' 's/const LinearGradient(/LinearGradient(/g' lib/presentation/widgets/home/sprint_card.dart

# 7. 修复prism_card.dart
echo "修复 prism_card.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/widgets/home/prism_card.dart
sed -i '' 's/const LinearGradient(/LinearGradient(/g' lib/presentation/widgets/home/prism_card.dart

# 8. 修复next_actions_card.dart
echo "修复 next_actions_card.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/widgets/home/next_actions_card.dart

# 9. 将DS.xxx替换为DS.xxxConst
echo "将DS.xxx替换为DS.xxxConst..."
# 使用更智能的替换，避免替换已经正确的
find lib -name "*.dart" -type f -exec grep -l "DS\." {} \; | while read file; do
  echo "处理: $file"
  # 只在const上下文中替换
  sed -i '' 's/color: DS\.brandPrimary,/color: DS.brandPrimaryConst,/g' "$file"
  sed -i '' 's/color: DS\.brandPrimary10,/color: DS.brandPrimary10Const,/g' "$file"
  sed -i '' 's/color: DS\.brandPrimary38,/color: DS.brandPrimary38Const,/g' "$file"
  sed -i '' 's/color: DS\.brandPrimary70,/color: DS.brandPrimary70Const,/g' "$file"
  sed -i '' 's/colors: \[DS\./colors: [DS./g' "$file"  # 移除const后不需要Const后缀
done

echo "✅ 最终修复完成！"