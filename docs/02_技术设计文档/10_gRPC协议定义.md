# gRPC 协议定义 (Protocol Buffers)

> **版本**: v1.0
> **日期**: 2026-01-10
> **文件**: `proto/*.proto`

## 1. 概述

Sparkle 使用 gRPC 作为 Go Gateway 与 Python Engine 之间的内部通信协议。定义文件位于 `proto/` 目录。

## 2. AgentService (AI 代理服务)

定义在 `proto/agent_service.proto`。

### 2.1 接口定义

```protobuf
service AgentService {
  // 双向流式聊天接口
  rpc StreamChat(ChatRequest) returns (stream ChatResponse);
  
  // 获取用户画像
  rpc GetUserProfile(ProfileRequest) returns (UserProfile);
}
```

### 2.2 消息结构

#### `ChatRequest`
```protobuf
message ChatRequest {
  string user_id = 1;
  string session_id = 2;
  // input: user message or tool result
  oneof input {
    string message = 3;
    ToolResult tool_result = 7;
  }
  UserProfile user_profile = 4;
  google.protobuf.Struct extra_context = 5;
  repeated ChatMessage history = 6;
  ChatConfig config = 8;
  string request_id = 9;
  repeated string file_ids = 10;
  bool include_references = 11;
  repeated string active_tools = 12; // 当前启用的工具列表
  string chat_mode = 13;
}
```

#### `ChatResponse`
```protobuf
message ChatResponse {
  string response_id = 1;
  int64 created_at = 2;
  string request_id = 10;
  string trace_id = 15;
  string workflow_id = 16;
  string prompt_version = 17;
  map<string, string> metadata = 18;
  oneof content {
    string delta = 3;
    ToolCall tool_call = 4;
    AgentStatus status_update = 5;
    string full_text = 6;
    Error error = 7;
    Usage usage = 8;
    CitationBlock citations = 11;
    ToolResultPayload tool_result = 12;
    InterventionPayload intervention = 14;
  }
  FinishReason finish_reason = 9;
  int64 timestamp = 13;
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
