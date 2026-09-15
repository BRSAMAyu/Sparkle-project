#!/bin/bash
# 修复剩余的const错误

echo "🔧 修复剩余的const错误..."

# 修复calendar_stats_screen.dart中的const错误
echo "修复 calendar_stats_screen.dart..."
sed -i '' 's/const Text(/Text(/g' lib/presentation/screens/stats/calendar_stats_screen.dart
sed -i '' 's/const SizedBox(/SizedBox(/g' lib/presentation/screens/stats/calendar_stats_screen.dart
sed -i '' 's/const Divider(/Divider(/g' lib/presentation/screens/stats/calendar_stats_screen.dart

# 修复engagement_heatmap.dart
echo "修复 engagement_heatmap.dart..."
sed -i '' 's/const BoxDecoration(/BoxDecoration(/g' lib/presentation/widgets/charts/engagement_heatmap.dart

# 修复vocabulary_lookup_tool.dart
echo "修复 vocabulary_lookup_tool.dart..."
sed -i '' 's/const SizedBox(/SizedBox(/g' lib/presentation/widgets/tools/vocabulary_lookup_tool.dart
sed -i '' 's/const Center(/Center(/g' lib/presentation/widgets/tools/vocabulary_lookup_tool.dart

# 修复agent_reasoning_bubble_v2.dart中的AgentType枚举错误
echo "修复 agent_reasoning_bubble_v2.dart..."
# 这个需要手动修复，因为涉及switch语句

echo "✅ 批量修复完成！"
echo ""
echo "📊 注意：有些错误需要手动修复："
echo "1. agent_reasoning_bubble_v2.dart - AgentType枚举不完整"
echo "2. 检查所有DS.xxx是否已替换为DS.xxxConst"