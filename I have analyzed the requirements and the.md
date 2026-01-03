I have analyzed the requirements and the codebase. Here is the plan to implement the Sparkle Chaos Engineering and FinOps Dashboard.

### Overview
The goal is to enhance the Sparkle Gateway with FinOps capabilities (calculating savings from semantic cache hits) and Chaos Engineering features (dynamic circuit breaker for database persistence). We will also update the Flutter frontend to visualize these metrics, providing a "Mission Control" experience for the system's anti-fragility and commercial value.

The implementation will focus on:
1.  **FinOps**: Adding a `CostCalculator` to the Gateway to estimate savings when semantic cache hits occur.
2.  **Chaos Engineering**: Modifying the `ChatHistoryService` to use a dynamic threshold for its circuit breaker and adding an admin API to control this threshold.
3.  **Real-time Feedback**: Updating the WebSocket communication to include metadata about cost savings and system status.
4.  **Frontend Visualization**: Enhancing the chat UI with "geek-style" badges for cache hits and cost savings.

### Key Changes
- **Backend (Go Gateway)**:
    - `internal/service/billing.go`: New service for token cost estimation and savings calculation.
    - `internal/service/chat_history.go`: Update to support dynamic circuit breaker thresholds.
    - `internal/handler/chaos.go`: New handler for the Chaos Control API.
    - `internal/handler/chat_orchestrator.go`: Update to integrate billing logic and send metadata to the frontend.
    - `cmd/server/main.go`: Register new routes and services.
- **Frontend (Flutter)**:
    - `lib/data/models/chat_message_model.dart`: Add metadata fields (`costSaved`, `isCacheHit`, `isBreakerTripped`).
    - `lib/presentation/widgets/chat/chat_bubble.dart`: Implement the "FinOps Badge" UI overlay.

### Implementation Steps

#### Phase 1: Backend (Go Gateway) Implementation
1.  **Create Billing Service**: Implement `internal/service/billing.go` with `CostCalculator` to estimate tokens and calculate savings based on model pricing.
2.  **Enhance Chat History Service**: 
    - Add a `SetThreshold` method to `ChatHistoryService`.
    - Make `CircuitBreakerThreshold` an atomic or protected variable.
    - Add a `GetQueueLength` method for monitoring.
3.  **Implement Chaos Handler**: Create `internal/handler/chaos.go` to provide an endpoint for dynamically adjusting the circuit breaker threshold.
4.  **Update Chat Orchestrator**:
    - Modify the WebSocket loop to check the semantic cache.
    - If a cache hit occurs, use `CostCalculator` to determine savings.
    - Include `cost_saved`, `is_cache_hit`, and `breaker_status` in the JSON response sent to the Flutter app.
5.  **Wire Everything Up**: Update `cmd/server/main.go` to initialize the billing service and register the chaos admin routes.

#### Phase 2: Frontend (Flutter) Implementation
6.  **Update Models**: Add the new metadata fields to `ChatMessageModel` and update the JSON serialization.
7.  **Implement FinOps Badge**: Create or modify a widget in `lib/presentation/widgets/chat/` to display the "🚀 Semantic Cache Hit | 💰 Saved $X.XX" status.
8.  **Integrate with Chat Bubble**: Update `ChatBubble` to conditionally render the FinOps badge based on the message metadata.

### Technical Considerations
- **Token Estimation**: Using a simple 1.5 token/char heuristic as requested, which is sufficient for demo purposes.
- **Concurrency**: The circuit breaker threshold will be updated via API, so it must be handled safely (e.g., using `atomic` package in Go).
- **Graceful Degradation**: The core logic ensures that even if the DB persistence queue is blocked (chaos mode), the user still receives AI responses from the cache or LLM.

### Success Criteria
- Sending a repeated query triggers a "Semantic Cache Hit" with a calculated cost saving.
- Reducing the circuit breaker threshold via API causes subsequent messages to trigger "Breaker Tripped" logs/status while maintaining chat functionality.
- The Flutter UI correctly displays the savings badge for cached responses.

Please **toggle to Act mode** to start the implementation.