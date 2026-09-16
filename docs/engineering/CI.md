# CI 工作流说明（2026-09 重构版）

> 2026-09-16 CI 重构：从 17 个工作流精简到 6 个，修复了导致流水线连续三个月全红的三个硬伤（不存在的 `flutter-action@v3`、Docker 构建缺生成代码、镜像名大写）。本文说明保留集的设计与维护规则。

## 当前工作流

| 工作流 | 触发 | 作用 |
|---|---|---|
| **ci.yml**（主门禁） | push 到 main/develop、tag、PR | lint（Go/Python/Flutter）→ 规则守卫 → 后端测试（Go+Python+契约）→ journey smoke → Flutter 测试 → 安全扫描 → DB schema 漂移 → proto 校验 → 构建产物（仅 main push/tag：Go 二进制 + Docker 镜像 + APK） |
| ci-pr.yml | PR | PR 快速检查（ruff、单测、go、proto） |
| ui-lint.yml | PR 路径过滤（mobile UI 文件） | 设计令牌检查（`tool/ui_lint.sh`） |
| quality-baseline.yml | 每周一 + 手动 | 质量基线快照收集 |
| e2e-smoke.yml | **仅手动**（暂停中） | 全栈冒烟；主 CI 稳定绿后再恢复定时 |
| e2e-tests.yml | **仅手动**（暂停中） | 夜间跨层 E2E；同上 |

## 已删除的工作流（2026-09-16）

cd_k8s（无集群凭据）、deploy-prod（无生产环境）、build-and-push（与 ci.yml 构建作业重复）、chaos-drill / load-test / benchmark（每周定时失败的重型演练，对参赛项目无意义）、gemini-×5（无密钥的机器人，纯噪音）。需要时从本地归档 `~/code/GitHub/Sparkle-archive-20260915/` 找回。

## 设计规则

1. **不引入需要未配置 secrets 才能成功的步骤**。当前唯一凭据是自动的 `GITHUB_TOKEN`（构建作业推送 ghcr 镜像用）。
2. **advisory 与 blocking 分离**：Trivy/Gitleaks/safety 是安全告警（不挡合并），lint/测试/守卫/契约是硬门禁。schema diff 在 PR 上 advisory、在 main 上 blocking。
3. **生成代码在 CI 内再生成**：`gen/` 目录被 gitignore，任何 Go 构建（测试或 Docker）前先 `make proto-gen`；Python 侧用 `scripts/generate_python_protos.sh`。
4. **镜像名必须小写**：owner 名含大写时用 `${GITHUB_REPOSITORY_OWNER,,}`（已踩过坑：`ghcr.io/BRSAMAyu/...` 非法）。
5. **每个 job 有 `timeout-minutes`**；主 CI 有 concurrency 取消旧跑。
6. codecov 上传已移除（未配置账号）；如需恢复先配 `CODECOV_TOKEN`。

## 恢复暂停的 E2E

当主 CI 在 main 上连续绿两周后：把 e2e-smoke/e2e-tests 的 `on:` 加回 `push/pull_request/schedule` 触发器即可（文件保留，只是暂停）。
