# WT280-fix-ci-images — CI 镜像发布链修复报告

> 2026-09-22 ｜ worktree: `wt280-fix-ci-images` ｜ 状态：修复完成，静态验证通过，待主会话 push 触发真实发布

## 一、根因（带日志证据）

**镜像发布从未成功的根因不在 `build` job 本身，而在流水线第一关 lint job 的工具链镜像构建失败，整条 `needs` 链被堵死——`build` job（发布 ghcr 镜像的 job）从未被执行过。**

证据链：

1. **三次失败 run 同因同位**（35408239335 / 35408173361 / 35406493327）：全部死在 `Code Quality & Linting` job 的 `Generate Go Proto Code` 步骤（该步骤执行 `make proto-tools-build && make proto-gen`），job 51s–1m9s 即败；其余 9 个 job 全部 0s skipped（`build` 的 `needs` 传递依赖 lint）。
2. **失败日志关键行**（run 35408239335，`gh run view --log-failed`）：
   ```
   #11 0.655 The current Dart SDK version is 3.6.1.
   #11 0.655 Because pub global activate depends on protoc_plugin >=22.5.0 which requires SDK version >=3.7.0 <4.0.0, version solving failed.
   #11 ERROR: process "/bin/sh -c dart --disable-analytics && dart pub global activate protoc_plugin 25.1.0 ..." did not complete successfully: exit code: 1
   make: *** [Makefile:223: proto-tools-build] Error 1
   ##[error]Process completed with exit code 2.
   ```
3. **引入历史（半完成的配对修复）**：
   - `e8a0a33b` "Bump toolchain Dart SDK to 3.6.1 for protoc_plugin compatibility"——当时插件是 22.x，3.6.1 够用；
   - `3b339db8` "pin protoc_plugin 25.1.0 pairing with protobuf 6.1.0"（M6-01）——把 `protoc_plugin 22.3.0 → 25.1.0`，**但没有同步升 Dart SDK**，留下 `DART_SDK_VERSION=3.6.1` × `protoc_plugin 25.1.0` 这个必败组合；
   - pub.dev API 实测核实：protoc_plugin 25.1.0 的 pubspec `environment.sdk = ^3.7.0`。
4. **ci.yml 全史零成功**：`gh run list --workflow=ci.yml --status success` 为空——发布链从未通过任何一次门。

定性：**「门本身坏」**（工具链镜像版本配对断裂），不是「门该过而红」（业务代码问题）。因此只修工具链钉版，不动 lint 门结构、不放宽任何门。

## 二、修法（diff 摘要）

仅改一处：`docker/proto-toolchain.Dockerfile`

```diff
-ARG DART_SDK_VERSION=3.6.1
+# WT280: protoc_plugin 25.1.0 的 pubspec 约束是 sdk >=3.7.0 <4.0.0，Dart 3.6.1 会使
+# 本镜像构建失败并堵死整条 CI（lint 首步即 make proto-tools-build）。配对三元组:
+# Dart >=3.7.0 ↔ protoc_plugin 25.1.0 ↔ protobuf 6.1.0（mobile 运行时锁定）。
+ARG DART_SDK_VERSION=3.7.2
```

选型理由：
- **3.7.2 = 满足约束的最小升幅**（`>=3.7.0 <4.0.0`），归档 URL 已验证 HTTP 200（`storage.googleapis.com/dart-archive/channels/stable/release/3.7.2/sdk/dartsdk-linux-x64-release.zip`）；
- protoc_plugin 保持 25.1.0 不动（其 22.x 产物需 protobuf ^4.x 运行时，与 mobile 锁定的 6.1.0 冲突，`3b339db8` 已定性"编译必断"）；
- 生成产物由 protoc_plugin + protoc 版本决定，与生成器的 Dart 运行时版本无关——gen/ 产物字节不变，不影响 `check-generated` 一致性守卫；
- mobile `pubspec.yaml` 环境 sdk `>=3.0.0 <4.0.0`，无约束冲突；
- Dockerfile 内注释已写明配对三元组，防再次单边升版复发。

`ci.yml` 本身无需改动：build job 的 `packages: write` 权限、`docker/login-action@v3`（GHCR + GITHUB_TOKEN）、小写 namespace（`${GITHUB_REPOSITORY_OWNER,,}`）、metadata tags（`sha-<long>` / tag / latest-on-main）均正确。全仓 grep 确认无 3.6.1 钉版残留（`mobile/pubspec.yaml` 的 `timeago ^3.6.1` 是 Dart 包版本，无关）。

## 三、静态验证结果（按卡要求，未做全量 docker build）

| 验证 | 命令 | 结果 |
|---|---|---|
| YAML 语法（ci.yml + prod compose） | `ruby -ryaml` YAML.load_file | OK（系统 python3 无 yaml 模块，改用系统 ruby 解析，真实执行并输出） |
| workflow 静态检查 | `/tmp/actionlint-bin/actionlint .github/workflows/ci.yml` | `exit=0`，零告警 |
| 版本约束核实 | `curl pub.dev/api/packages/protoc_plugin` | 25.1.0 requires `sdk ^3.7.0` ✓ |
| 下载源可用性 | `curl -I dart-archive .../3.7.2/...` | HTTP 200 ✓ |
| 钉版残留扫描 | `grep -rn "3.6.1" --include=*.Dockerfile/*.yml/*.sh` | 仅 timeago（无关）✓ |

按内存红线未做：本地 `docker build` 工具链镜像、`make proto-gen` 本地复跑、go vet/ruff/mypy/flutter analyze 全量复验——lint 门后续步骤是否全绿由主会话 push 后 CI 观察确认。

## 四、风险与未解决问题

1. **lint 门后续步骤未知**：本修复只保证 `Generate Go Proto Code` 不再堵死。`go vet / golangci-lint / ruff / mypy / flutter analyze / coverage 门` 是否全绿无本地证据（CI 从未跑过这些步骤的当前代码版）。若 push 后 lint 死在更后面的步骤，那属于「门该过而红」的代码问题，需另行派卡。
2. **compose 大小写隐患（未改，部署侧注意）**：`docker-compose.prod.yml` 的默认镜像引用是 `ghcr.io/${GITHUB_REPOSITORY_OWNER:-local}/...`——若 ECS 部署环境变量把 `GITHUB_REPOSITORY_OWNER` 设为 `BRSAMAyu`（含大写），GHCR pull 会失败。CI 侧已用 `${GITHUB_REPOSITORY_OWNER,,}` 强制小写，云端部署需保证该变量为小写 `brsamayu` 或直接用 `GATEWAY_IMAGE`/`BACKEND_IMAGE` 覆写。
3. **Dart 3.7.2 与 protoc_plugin 未来升版**：若将来升 protoc_plugin 到要求更高 SDK 的版本，需同步动本 ARG（注释已钉三元组）。
4. 本地开发机若工具链镜像是旧缓存（protoc_plugin 22.x 时代构建），重跑 `make proto-tools-build` 后同样走 3.7.2，行为与 CI 对齐。

## 五、主会话触发清单（push 后）

```bash
# 1. push 后盯 run（本修复随下一批合入 push 到 main 自动触发，workflow 触发条件: push→main）
gh run watch $(gh run list --workflow=ci.yml --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status

# 2. 判据 A：lint job 过了 "Generate Go Proto Code"（本次根因修复的直接验证点）
gh run view <run-id> --job $(gh run view <run-id> --json jobs --jq '.jobs[] | select(.name=="Code Quality & Linting") | .databaseId')

# 3. 判据 B："Build Artifacts" job 出现且绿（此前从未执行过，出现即说明 needs 链通）
gh run view <run-id>   # Build Artifacts 应为 ✓，约 30-45min（含 Flutter APK）

# 4. 判据 C：ghcr 包出现（owner 小写）
gh api /users/BRSAMAyu/packages/container/sparkle-gateway/versions --jq '.[0].metadata.container.tags'
gh api /users/BRSAMAyu/packages/container/sparkle-backend/versions --jq '.[0].metadata.container.tags'
# 期望 tags: ["sha-<full-sha>", "latest"]；或浏览 https://github.com/BRSAMAyu?tab=packages

# 5. 判据 D（云端解锁）：ECS 上
#    IMAGE_TAG=sha-<full-sha> GITHUB_REPOSITORY_OWNER=brsamayu docker compose -f docker-compose.prod.yml pull
```

注意：若 run 死在 lint 更后面的步骤（Go Vet 之后），属风险 1 范畴——发布链已通，代码门另行处理。

## 交付物

- `docker/proto-toolchain.Dockerfile`（1 行钉版 + 3 行注释）
- `v3-output/WT280-FIX-CI/REPORT.md`（本报告）
- `v3-output/WT280-FIX-CI/changes.patch`
