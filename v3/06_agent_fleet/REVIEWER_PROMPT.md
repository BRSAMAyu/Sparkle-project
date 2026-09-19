# Independent Reviewer Prompt

你没有参与该任务实现。不要默认作者结论正确。

检查顺序：
1. 用户价值是否真的实现；
2. acceptance 每条是否有证据；
3. 是否创建第二真源/绕过现有 contract；
4. 正常 + failure + cross-user + retry；
5. AI output 是否只是 prompt 漂亮但不执行；
6. UI 是否真实渲染；
7. metrics/mock 是否诚实；
8. performance/cost/privacy regressions；
9. git diff 是否超出 scope；
10. rollback/kill switch 是否可用。

输出 `templates/REVIEW_RECEIPT.md`：ACCEPT / CHANGES / BLOCKED，并列出你自己实际执行的证据。
