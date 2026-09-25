# 09_evidence · 验收证据目录

U-02 卡验收收尾证据（wt399）：

- `u02_rubric/` — 双档核心屏真实渲染截图（8×PNG）+ contrast/hierarchy
  rubric 判定表（`RUBRIC_VERDICT.md`）+ 动效/装饰量化对照 +
  rubric 测试全量输出（`rubric_test_output.log`）。
  测试真源：`mobile/test/core/design/u02_contrast_hierarchy_rubric_test.dart`
  与 `mobile/test/goldens/u02_dual_mode_evidence_test.dart`
  （门控 `--dart-define=U02_CAPTURE_EVIDENCE=true`）。

登记规则：新增卡的证据在此建同名子目录（`<卡号>_<主题>/`），并同步本 README。
