# gRPC 协议定义 (Protocol Buffers)

> **版本**: v1.0
> **日期**: 2026-01-10
> **文件**: `proto/*.proto`

## 1. 概述

Sparkle 使用 gRPC 作为 Go Gateway 与 Python Engine 之间的内部通信协议。定义文件位于 `proto/` 目录。

## 2. AgentService (AI 代理服务)

定义在 `proto/agent_service_v2.proto`。

### 2.1 接口定义

```protobuf
service AgentServiceV2 {
  // 双向流式聊天接口
  rpc StreamChat(ChatRequestV2) returns (stream ChatResponseV2);
  
  // 获取用户画像
  rpc GetUserProfile(ProfileRequestV2) returns (ProfileResponseV2);
}
```

### 2.2 消息结构

#### `ChatRequestV2`
```protobuf
message ChatRequestV2 {
  string user_id = 1;
  string message = 2;
  string session_id = 3;
  repeated string active_tools = 4; // 当前启用的工具列表
}
```

#### `ChatResponseV2`
```protobuf
message ChatResponseV2 {
  string content = 1;      // 文本增量 (Delta)
  string type = 2;         // 消息类型: "delta", "tool_start", "tool_result", "error"
  int64 timestamp = 3;
  string tool_name = 4;    // (可选) 工具名称
  string tool_payload = 5; // (可选) 工具数据 JSON
}
```

## 3. GalaxyService (星图服务)

定义在 `proto/galaxy_service.proto`。

### 3.1 接口定义

```protobuf
service GalaxyService {
  // 更新节点掌握度
  rpc UpdateNodeMastery(UpdateNodeMasteryRequest) returns (UpdateNodeMasteryResponse);
  
  // 同步协作星图 (CRDT)
  rpc SyncCollaborativeGalaxy(SyncCollaborativeGalaxyRequest) returns (SyncCollaborativeGalaxyResponse);
}
```

### 3.2 消息结构

#### `UpdateNodeMasteryRequest`
```protobuf
message UpdateNodeMasteryRequest {
  string user_id = 1;
  string node_id = 2;
  int32 mastery = 3;       // 新的掌握度 (0-100)
  int64 revision = 4;      // 逻辑时钟，用于冲突解决
}
```

## 4. 最佳实践

1.  **流式处理**: `StreamChat` 是核心接口，网关应在一个循环中读取流，直到收到 `EOF`。
2.  **错误处理**: 服务端应使用标准的 gRPC Status Code (如 `UNAUTHENTICATED`, `RESOURCE_EXHAUSTED`)，网关需将其转换为适当的 HTTP 响应或 WebSocket 错误帧。
3.  **超时控制**: 网关调用 gRPC 时应始终设置 `context.WithTimeout` (建议 30-60秒)。
4.  **生成代码**: 修改 `.proto` 文件后，必须运行 `make proto-gen` 重新生成 Go 和 Python 代码。
