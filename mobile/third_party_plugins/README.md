# mobile/third_party_plugins/ — Vendored 插件 Fork

本目录存放 7 个 Flutter 插件的本地 fork，全部通过 `mobile/pubspec.yaml` 的 `dependency_overrides`（`path:` 指向）接入。fork 的主要动机是**本地构建可控性**（Apple Silicon / ARM64 兼容、本地补丁不必等上游发版）。

## Fork 清单

| 插件 | 用途 | 备注 |
|---|---|---|
| `file_picker` | 文件选择 | 上传材料/文档 |
| `flutter_local_notifications` | 本地通知 | |
| `flutter_secure_storage` | 安全存储 | token 存储 |
| `fluwx` | 微信 SDK（分享/登录） | |
| `isar_flutter_libs` | Isar 本地数据库原生库 | 离线优先架构的关键依赖 |
| `jpush_flutter` | 极光推送 | |
| `sentry_flutter` (v8.14.2) | 崩溃监控 | |

## 维护注意

1. **升级前必须 diff 上游**：各 fork 基于的上游 commit 未登记（待补）；升级时应拉取上游对应版本 diff 本地改动，确认无本地补丁丢失。
2. 各 fork 的 `example/` 目录已于 2026-09 仓库重置时删除（约 19MB 上游残留，不参与本仓构建）；升级 fork 时如需示例可从上游取回。
3. 修改 fork 内代码属于高风险操作：先确认该改动无法通过 wrapper/配置在上游版本实现。

## 待办

- [ ] 为每个 fork 登记所基于的上游仓库与 commit（`git log` 各 fork 目录可追溯拉入时间）
