# 深度审计 #48 — File Handler 文件上传/下载/删除完整链路

> **日期**: 2026-04-24 11:15
> **模块**: Go Gateway FileHandler — Presigned Upload → Complete → Processing Trigger → Download → Thumbnail → Delete 完整链路
> **范围**: `file_handler.go`（622 行）
> **审计员**: Claude Deep Auditor (Round 48)

---

## 审计范围

`FileHandler` 是 Sparkle 文件系统的 Go Gateway 入口，负责文件上传准备、上传完成确认、文件元数据查询、下载 URL 生成、缩略图 URL 生成、文件搜索与删除。采用 Presigned URL 模式：客户端直传 S3/MinIO，Gateway 不经手文件内容。

### 文件清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `gateway/internal/handler/file_handler.go` | 622 | 文件 CRUD + 上传/下载/删除全部端点 |

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Flutter → REST API → FileHandler                                       │
│                                                                         │
│  上传流程:                                                              │
│    1. POST /files/upload/prepare (:146-233)                              │
│       限流: LRU(1000) rate.Limiter 10/min/user ✅                       │
│       校验: FileSize>0, FileSize<=MaxUploadSize ✅                      │
│       校验: MIME ↔ Extension 白名单 ✅                                  │
│       文件名: path.Base() 防路径穿越 ✅                                 │
│       ❌ P0-1: .svg 在白名单但无内容校验 — stored XSS                   │
│       响应: presigned_url + fields + bucket + object_key                │
│       ❌ P1-1: bucket/object_key 泄露内部存储架构                       │
│                                                                         │
│    2. Client → S3/MinIO (presigned POST)                                │
│       Gateway 不经手文件内容                                            │
│                                                                         │
│    3. POST /files/upload/complete (:235-289)                             │
│       ❌ P1-2: 不验证对象是否实际上传 — 幽灵文件                        │
│       更新状态: pending → uploaded (:258)                                │
│       ❌ P1-3: TriggerProcessing goroutine + context.Background()       │
│                  无超时 + 无追踪 + 错误丢弃 (_ = err)                   │
│       Thumbnail key: fileID + "/thumbnail.jpg" (:267)                   │
│       ❌ P2-1: 硬编码 .jpg — 非图片文件缩略图断裂                      │
│                                                                         │
│  查询流程:                                                              │
│    4. GET /files/:file_id (:291-320)                                    │
│       ❌ P1-1: FileResponse 含 Bucket + ObjectKey                       │
│       支持 group_id 查询参数 → GetFileForGroupView ✅                  │
│                                                                         │
│    5. GET /files/:file_id/download (:322-360)                           │
│       PresignGet 生成下载 URL ✅                                        │
│                                                                         │
│    6. GET /files/:file_id/thumbnail (:362-400)                          │
│       ❌ P2-1: thumbnailKey 硬编码 .jpg — 缩略图 404 for non-JPEG     │
│                                                                         │
│    7. GET /me/files (:402-424)                                          │
│       ❌ P1-4: parseIntQuery 无边界检查 — limit=-1/999999999           │
│                                                                         │
│  删除流程:                                                              │
│    8. DELETE /me/files/:file_id (:426-450)                               │
│       SoftDeleteFile → DeleteObject                                     │
│       ❌ P1-5: 非原子 — 软删成功+存储删失败=孤立对象                    │
│                                                                         │
│  全局问题:                                                              │
│    ❌ P2-2: validateFileByMagicBytes (568-621) 定义但从未调用 — 死代码  │
│    ❌ P2-3: isDevelopmentModeForErrors() 每次请求调用 — 未缓存         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 审计发现

### P0 — 严重缺陷

#### P0-1: SVG 上传无内容校验 — Stored XSS 攻击向量
**文件**: `file_handler.go:58-78, 568-621`
**严重性**: P0 — 存储型跨站脚本攻击，影响所有访问该文件的用户

```go
// :77 — .svg 在白名单中
".svg":  {"image/svg+xml": true},

// :568-621 — validateFileByMagicBytes 不检查 .svg
switch strings.ToLower(ext) {
case ".pdf":   // ✅ 有检查
case ".docx":  // ✅ 有检查 (fallthrough)
case ".xlsx":  // ✅ 有检查 (fallthrough)
case ".pptx":  // ✅ 有检查
case ".png":   // ✅ 有检查
case ".jpg", ".jpeg": // ✅ 有检查
case ".gif":   // ✅ 有检查
case ".webp":  // ✅ 有检查
// .svg, .txt, .csv, .json, .md, .zip, .bin — 全部 fallthrough 到 return true, ""
}
```

**但更关键的是**: `validateFileByMagicBytes` 从未被调用。整个上传流程是 Presigned URL 模式，客户端直传 S3，Gateway 不经手文件内容。所以：
1. 客户端声明 `mime_type: "image/svg+xml"`, `filename: "test.svg"` → 通过白名单校验
2. 获取 Presigned URL → 直传 S3
3. 上传含 `<script>alert(document.cookie)</script>` 的 SVG 文件
4. 调用 CompleteUpload → 文件标记 "uploaded"
5. 其他用户通过 GetDownloadURL 获取 Presigned GET URL
6. 浏览器访问 URL → S3 返回 `Content-Type: image/svg+xml` → **浏览器执行 JavaScript**

**攻击影响**:
- 窃取用户 JWT Token（如果存储在 cookie 中）
- 代表用户执行任意操作
- 钓鱼/社工攻击（修改页面内容）

**修复方向**: (1) 从白名单中移除 `.svg`（Sparkle 不需要 SVG 上传）；(2) 如需支持，在 Python Processing Pipeline 中剥离 SVG 中的 `<script>` 和事件属性。

---

### P1 — 重要问题

#### P1-1: FileResponse 泄露内部存储 Bucket 和 ObjectKey — 存储架构信息泄露
**文件**: `file_handler.go:132-144, 478-492, 224-232`
**严重性**: P1 — 防御纵深缺失

```go
// :138-139 — FileResponse 包含内部字段
Bucket:     string    `json:"bucket"`
ObjectKey:  string    `json:"object_key"`

// :224-232 — PrepareUpload 响应也暴露
"bucket":        record.Bucket,
"object_key":    record.ObjectKey,
```

`Bucket` 暴露存储桶名称（如 `sparkle-uploads`），`ObjectKey` 暴露存储路径结构（`{userID}/{fileID}/original.ext`）。客户端不需要这些信息来上传（已提供 presigned URL）或下载（已提供 presigned URL）。

**攻击场景**: 攻击者收集 Bucket 名称 + 路径结构后，如果存储桶策略配置错误（如公开读取），可直接构造 URL 访问其他用户的文件。

**修复方向**: 从 `FileResponse` 和 PrepareUpload 响应中移除 `Bucket` 和 `ObjectKey` 字段。客户端仅需 `upload_id`/`file_id` + `presigned_url` + `fields`。

---

#### P1-2: CompleteUpload 不验证对象是否实际上传到存储 — 幽灵文件记录
**文件**: `file_handler.go:235-289`
**严重性**: P1 — 数据完整性缺失

```go
// :258 — 直接更新状态，不验证对象存在
record, err := h.metadata.UpdateFileStatus(c.Request.Context(), fileID, userID, "uploaded", visibility)
```

CompleteUpload 接受客户端声称"上传完成"的请求，但不做任何验证（无 `HeadObject` 调用）。恶意或错误的客户端可以：
1. 调用 PrepareUpload → 获取 presigned URL
2. 从不上传任何内容
3. 调用 CompleteUpload → 文件标记为 "uploaded"
4. 触发无效的 Processing Pipeline（goroutine 下载不存在的对象 → 静默失败）
5. 其他用户/系统引用此"幽灵文件" → 断裂引用

**影响链路**: RAG 系统、Chat 文件引用、Knowledge Graph 文件关联都可能引用到不存在的文件。

**修复方向**: CompleteUpload 中调用 `h.storage.HeadObject(objectKey)` 验证对象存在后再更新状态。

---

#### P1-3: CompleteUpload TriggerProcessing fire-and-forget — 无超时无追踪无声错误
**文件**: `file_handler.go:264-285`
**严重性**: P1 — 处理管道不可观测

```go
// :280-284 — context.Background() + 错误丢弃
go func() {
    if err := h.processor.TriggerProcessing(context.Background(), payload); err != nil {
        _ = err  // ← 静默丢弃
    }
}()
```

**三重问题**:
1. `context.Background()` — 无超时（处理可永久挂起 → goroutine 泄漏）、无取消（服务器关闭时不中断）、无 OpenTelemetry 追踪
2. `_ = err` — 处理失败完全不可见。无日志、无指标、无重试
3. 在 PresignGet 失败时（:266 `err == nil` 才进入处理），整个处理被静默跳过

**修复方向**: 使用 `context.WithTimeout(c.Request.Context(), 5*time.Minute)` 传递 context；至少 log 处理错误；添加 Prometheus counter 跟踪处理成功/失败率。

---

#### P1-4: parseIntQuery 无边界检查 — 恶意 limit/offset 参数
**文件**: `file_handler.go:542-552`
**严重性**: P1 — 资源滥用

```go
func parseIntQuery(c *gin.Context, key string, fallback int) int {
    parsed, err := strconv.Atoi(value)
    if err != nil {
        return fallback
    }
    return parsed  // ← 无边界检查
}
```

客户端可传入 `limit=-1`（某些 ORM 解释为无限制）、`limit=999999999`（加载海量数据导致 OOM）、`offset=-999`。调用点：
- `ListMyFiles` (:409-410): `limit`, `offset`
- `SearchMyFiles` (:463): `limit`

**修复方向**: `if parsed < 0 { return 0 }; if parsed > 100 { return 100 }`。

---

#### P1-5: DeleteMyFile 非原子删除 — 软删成功后存储删失败导致孤立对象
**文件**: `file_handler.go:426-450`
**严重性**: P1 — 存储泄漏

```go
// :438 — 步骤1: 软删除 metadata（已提交）
record, err := h.metadata.SoftDeleteFile(c.Request.Context(), fileID, userID)

// :444 — 步骤2: 硬删除存储对象（可能失败）
if err := h.storage.DeleteObject(c.Request.Context(), record.Bucket, record.ObjectKey); err != nil {
    c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to delete object"})
    return  // ← metadata 已删除但存储对象仍在
}
```

**失败场景**: metadata 软删成功 → 存储删除失败（MinIO 暂时不可用）→ 客户端收到 500 → 存储对象成为孤儿（metadata 已删，无法再触发删除）。

**修复方向**: (1) 先删存储再删 metadata（失败时不暴露已删状态）；(2) 或添加异步清理任务定期扫描孤儿对象。

---

### P2 — 改进建议

#### P2-1: Thumbnail key 硬编码为 `.jpg` — 非图片文件缩略图断裂

```go
// :267 — 所有文件类型都生成 .jpg 缩略图 key
thumbnailKey := fileID.String() + "/thumbnail.jpg"
```

对于 `.pdf`、`.docx`、`.png` 等文件，Python processing pipeline 可能生成不同格式的缩略图。硬编码 `.jpg` 会导致：
- 非图片文件的缩略图 404
- PNG 文件的缩略图格式不匹配

**修复方向**: 使用通用 key `fileID.String() + "/thumbnail"`，或在 CompleteUpload 时根据文件类型确定缩略图格式。

---

#### P2-2: `validateFileByMagicBytes` 是死代码 — 定义但从未在上传流程中调用

`validateFileByMagicBytes`（:568-621）覆盖了 8 种文件类型的魔数校验，但 Presigned URL 模式下 Gateway 不经手文件内容，此函数永远不会被调用。仅覆盖 8/17 白名单扩展名，缺少 `.svg`/`.txt`/`.csv`/`.json`/`.md`/`.zip`/`.bin`/`.svg` 的验证。

**修复方向**: (1) 如果 Presigned 模式确定不变，移除此死代码减少认知负担；(2) 或在 Python Processing Pipeline 中实现等价验证。

---

#### P2-3: `isDevelopmentModeForErrors()` 每次错误调用 — 应缓存

```go
// :27-29 — 每次调用 os.Getenv
func isDevelopmentModeForErrors() bool {
    env := strings.ToLower(os.Getenv("ENVIRONMENT"))
    ...
}
```

在 `sanitizeError` 和 `sanitizeErrorWithDetail` 中被调用。环境变量运行时不变，应 `init()` 时读取并缓存。

---

## 合规项

| 检查项 | 状态 |
|--------|------|
| 上传限流 | ✅ LRU(1000) + rate.Limiter 10/min/user (:94, :154-158) |
| MIME ↔ Extension 交叉验证 | ✅ allowedMimeTypesByExt 白名单 + isAllowedMimeType 校验 (:58-78, 534-539) |
| 文件名路径穿越防护 | ✅ path.Base() 剥离目录组件 (:506-512) |
| 文件大小校验 | ✅ FileSize > 0 且 <= MaxUploadSize (:165-172) |
| UUID 参数解析 | ✅ 所有 file_id/group_id 参数经 uuid.Parse 校验 |
| 认证中间件 | ✅ 所有路由挂载在 authMiddleware 下 (:103, 112) |
| Group 访问控制 | ✅ GetFileForGroupView/GetFileForGroupDownload 检查组成员 (:310, 342) |
| 生产错误隐藏 | ✅ sanitizeError/sanitizeErrorWithDetail 在生产环境隐藏内部错误 |
| Presigned URL 时效 | ✅ 返回 expires_in 供客户端感知 (:229, 358, 398) |

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 1 |
| P1 | 5 |
| P2 | 3 |
| **总计** | **9** |

---

## 修复优先级建议

1. **P0-1** (SVG XSS) — 从白名单移除 `.svg` 或在 Python 端添加 SVG 净化 — ~5 行
2. **P1-1** (信息泄露) — FileResponse 移除 Bucket/ObjectKey — ~10 行
3. **P1-2** (幽灵文件) — CompleteUpload 添加 HeadObject 验证 — ~10 行
4. **P1-3** (fire-and-forget) — 使用有超时 context + log error — ~5 行
5. **P1-4** (parseIntQuery) — 添加边界检查 — ~3 行
6. **P1-5** (非原子删除) — 先删存储再删 metadata — ~5 行
7. P2-1/P2-2/P2-3 — 随后续迭代修复

---

## 跨轮次因果链

| 本轮发现 | 关联轮次 | 关联模式 |
|----------|---------|---------|
| P0-1 (SVG XSS) | Round #14 (输入校验/XSS防御) | 输入校验在 Gateway 层不完整 — Presigned URL 绕过 Gateway 内容检查 |
| P1-1 (Bucket泄露) | Round #47 P1-2 (FileIds未验证) | Go Gateway 响应过度暴露内部实现细节 |
| P1-2 (幽灵文件) | Round #47 P0-1 (配额不退还) | 资源声明与实际状态不一致 — 缺乏验证 |
| P1-3 (fire-and-forget) | Round #2 (WebSocket 消息流) | 异步操作错误处理不充分 |

---

## 复核笔记

> **复核日期**: 2026-04-25 05:30
> **复核轮次**: 第九次唤醒 (Round #55 并行复核)
> **复核方式**: 代码验证

### 复核结果: 0/9 已修

| 原始编号 | 描述 | 状态 | 备注 |
|----------|------|------|------|
| P0-1 | SVG 上传无内容校验 — 存储型 XSS | ❌ 未修 | `.svg` 仍在白名单 (file_handler.go:77)，无 SVG 净化。CSP `script-src 'self'` 不覆盖 MinIO 预签名 URL (不同源)，攻击向量完整可用 |
| P1-1 | FileResponse 泄露 Bucket/ObjectKey | ❌ 未修 | FileResponse 结构体仍含字段 (:138-139)，PrepareUpload 仍暴露 (:230-231)，fileToResponse 仍填充 (:485-486) |
| P1-2 | CompleteUpload 不验证对象存在 — 幽灵文件 | ❌ 未修 | 仍直接 UpdateFileStatus (:258)，无 HeadObject。**部分缓解**: FileGCService 定期清理 uploading/failed 状态过期记录 |
| P1-3 | TriggerProcessing fire-and-forget | ❌ 未修 | 仍 context.Background() (:281) + `_ = err` 静默丢弃 (:282)。无超时/日志/追踪 |
| P1-4 | parseIntQuery 无边界检查 | ❌ 未修(部分缓解) | 下游 FileMetadataService 钳制 limit<=0 和 offset<0，但 limit=999999999 仍可通过 |
| P1-5 | DeleteMyFile 非原子删除 | ❌ 未修(部分缓解) | FileGCService 在 grace period 后清理孤立对象，最坏 24h 内清理 |
| P2-1 | Thumbnail key 硬编码 .jpg | ❌ 未修 | CompleteUpload (:267) 和 GetThumbnailURL (:390) 仍硬编码。Python thumbnail 仅处理 PDF |
| P2-2 | validateFileByMagicBytes 死代码 | ❌ 未修 | 函数仍存于 :568-621，无调用点 |
| P2-3 | isDevelopmentModeForErrors 不缓存 | ❌ 未修 | :26-29 每次调用 os.Getenv |

### 复核附加发现

**AF-1: FileGCService 提供最终一致性缓解**
P1-2 和 P1-5 的爆炸半径被 FileGCService 缩小: GC 扫描 uploading/failed 超过 grace period 的文件，以及已软删超 grace period 的文件。这不是根本修复但降低了影响。

**AF-2: Thumbnail 404 for non-PDF files**
thumbnail_service.py 仅对 PDF 生成缩略图 (`if ext != ".pdf": return None`)。对 .png/.jpg 等图片文件，Go 侧的 `/thumbnail.jpg` key 永远无对应对象，Flutter thumbnail 请求始终 404。

### 跨轮次因果链更新

| 本轮复核 | 关联 | 说明 |
|----------|------|------|
| P0-1 (SVG XSS 未修) | Round #51 P1-2 (CSP connect-src) | 完整攻击链仍有效: SVG XSS → connect-src 允许外发数据 |
| P0-1 (SVG XSS 未修) | Round #14 P2-3 (Bluemonday 过于宽松) | SVG 攻击面从 HTML 延伸到文件上传，两处均未剥离 |
| AF-2 (Thumbnail 404) | Round #35 (文件处理管线) | 非文件类型 thumbnail 管线断裂 |
