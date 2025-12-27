# Knowledge Galaxy Improvement Roadmap

This roadmap outlines the plan to implement the comprehensive improvements requested for the Sparkle Knowledge Galaxy module.

## Phase 1: Foundation & Performance (LOD - Level of Detail)
**Goal:** Prevent performance degradation as the number of nodes scales to thousands.

### Backend (`GalaxyService` & API)
- [ ] **API Update**: Modify `GET /api/v1/galaxy/graph` to accept optional `zoom_level` (float) and `viewport` (min_x, min_y, max_x, max_y) parameters.
- [ ] **LOD Logic Implementation**:
    - **Zoom Level < 0.3**: Return only Sector Root nodes (top-level nodes).
    - **Zoom Level 0.3 - 0.6**: Return Sector Roots + their immediate children (2nd layer).
    - **Zoom Level > 0.6**: Return all nodes within the `viewport` bounding box + Global "Landmark" nodes (Importance >= 4).
- [ ] **Response Optimization**: Ensure `GalaxyGraphResponse` can handle partial updates without breaking the frontend state.

### Frontend (`GalaxyProvider` & Layout)
- [ ] **Repository Update**: Update `GalaxyRepository.getGraph` to pass `zoomLevel` and `viewport` to the backend.
- [ ] **State Management**: Modify `GalaxyProvider` to merge fetched nodes into the existing state instead of replacing it entirely, effectively implementing an "infinite canvas" caching strategy.
- [ ] **Optimization**: Ensure `GalaxyLayoutEngine` re-runs only for newly added nodes or uses cached positions for stable nodes.

## Phase 2: UX & Navigation
**Goal:** Solve the "lost in space" problem and provide better context.

### Frontend (Widgets)
- [ ] **Mini-map Widget**: Create `GalaxyMiniMap` that renders a simplified view of the 7 sectors and a rectangle indicating the current viewport.
- [ ] **Learning Path Tracing**:
    - Fetch recent `StudyRecord`s.
    - Draw a distinct visual path (e.g., a glowing spline line) connecting the last 5-10 visited nodes in temporal order.
- [ ] **Smooth Transitions**:
    - Listen for `nodes_expanded` SSE events.
    - Instead of full reload, add new nodes to the `nodes` list and trigger a "spawn" animation (scale from 0 to 1 with a glow burst).

## Phase 3: AI & Functional Deepening (Predictive Path)
**Goal:** Transform the galaxy from a static map to an active guide.

### Backend (AI Service)
- [ ] **New Endpoint**: `POST /api/v1/galaxy/predict-next`.
- [ ] **Logic**:
    - Input: User's recent study history + Current high-mastery nodes.
    - Process: Use LLM/Heuristic to find a node that is:
        1. Unlocked but not mastered.
        2. Connected to a recently mastered node.
        3. High importance.
    - Output: `node_id` and `reason`.

### Frontend (Visuals)
- [ ] **Path Visualization**: Render a pulsing "guide line" or "spirit wisp" leading from the current view center to the predicted node.
- [ ] **Suggestion UI**: A small toast or floating button "Next Recommended: [Node Name]".

## Phase 4: Visualization Enhancements (2.5D & Shaders)
**Goal:** Improve visual immersion.

- [ ] **Parallax Effect**: In `StarMapPainter`, apply a slight positional offset to nodes based on their `importance` (Z-depth) and the camera's pan position.
- [ ] **Corona Shader**: Apply a specific shader (similar to the central flame but subtler) to nodes with Mastery > 90 to make them look like burning stars.
- [ ] **Dynamic Edges**: Adjust edge drawing to vary tension/curve based on `relation_type`.

## Phase 5: Functional Extensions (Time Machine & Social)
**Goal:** Add temporal and social dimensions.

- [ ] **Time Machine UI**: A slider at the bottom of the screen to filter visible nodes by their `unlock_date`.
- [ ] **Shared Constellations**: (Requires Backend User Graph) Mockup a "Social Mode" where nodes popular among friends glow with a different color.

---

**Next Steps:**
We will proceed with **Phase 1 (LOD)** and **Phase 2 (Mini-map)** immediately as per priority.
