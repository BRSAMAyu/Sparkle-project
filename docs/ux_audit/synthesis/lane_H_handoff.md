## Lane H Handoff

改动文件：`error_book_service.py`、`error_book_mastery_sync_service.py`、`schemas/error_book.py`、Flutter 错题模型与 `error_list_screen.dart`，并补充对应测试。

用户现在拍照录入错题时，只要有图片就会 OCR；若已有手输题干，OCR 文本会作为补充参与分析，不覆盖原文。LLM 失败后的 fallback 会按英文语法、词汇、阅读等场景分类，不再把英文题一律落到 `knowledge_gap`。当错题分析后仍没有关联知识节点，后端会写入 `linking_hint`，错题列表会显示“补充学科/章节或关联课程”的引导卡。

验证：已通过 4 个后端聚焦测试与 `flutter test test/features/error_book/presentation/screens/error_list_screen_test.dart`。已知遗留：`flutter pub run build_runner build` 被现有 `galaxy_screen.dart:2759` 语法错误阻断，但本次 `error_record` 生成文件已产出。
