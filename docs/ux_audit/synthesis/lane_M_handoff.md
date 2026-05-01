# Lane M Handoff — Galaxy 节点复习 chat 体验

## 改动文件
- `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart` — initialContext 增加 mastery/study_count/related_error_count；mastery=0 按钮文案改为"开始学习"
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart` — 新增 `_ReviewNodeBanner` 组件，从 `initialExtraContext` 提取 review_node 信息显示"正在复习：X · 掌握度 Y%"
- `backend/app/aurora/runtime_v1/service.py` — `_review_focus_from_context` 接受 mastery/study_count/related_error_count；`_build_review_node_first_turn_message` 根据 mastery 水平定制开场白
- `backend/tests/aurora/test_review_focus_enrichment.py` — 10 条新测试
- `mobile/test/features/galaxy/widget/node_detail_sheet_test.dart` — 更新断言匹配新的 initialContext 字段 + mastery=0 按钮文案

## 用户可见效果
1. 进入复习 chat 后顶部显示持久 banner（"正在复习：TCP流量控制 · 掌握度 65%"）
2. Aurora 开场白根据掌握度定制（高→查漏补缺、中→趁热打铁、低→从头梳理、零→开始学习）
3. 有相关错题时开场白提及错题数量
4. mastery=0 时节点详情按钮显示"开始学习"而非"开始复习"

## 验证
- `pytest tests/aurora/test_review_focus_enrichment.py` — 10/10 passed
- `flutter test test/features/galaxy/widget/node_detail_sheet_test.dart` — 3/3 passed
- `flutter analyze` — 0 error, 0 warning（2 pre-existing info）

## 已知遗留
- description/keywords 未渲染：`galaxy_service.get_node_history` 不返回节点描述/关键词字段，需后续扩展 API。不在本 Lane M Bounds 内。
