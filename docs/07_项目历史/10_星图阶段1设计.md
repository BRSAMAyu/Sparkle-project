# Sparkle Knowledge Galaxy - Phase 1 (MVP) Technical Design

## 1. Database Layer Design (PostgreSQL)

### 1.1. Subjects Table Extension (`subjects`)
Existing table `subjects` will be extended to support the Galaxy visual metaphors.

| Field Name | Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `sector_code` | `VARCHAR(20)` | No | Enumeration: `COSMOS`, `TECH`, `ART`, `CIVILIZATION`, `LIFE`, `WISDOM`, `VOID`. Default `VOID` if undefined. |
| `hex_color` | `VARCHAR(7)` | No | Hex string (e.g., `#FF5733`) representing the sector's nebula color. |

### 1.2. Knowledge Nodes Table (`knowledge_nodes`)
Represents the atomic "stars" in the galaxy.

```sql
CREATE TABLE knowledge_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    parent_id UUID REFERENCES knowledge_nodes(id), -- Self-referencing for hierarchy
    name VARCHAR(255) NOT NULL,
    description TEXT,
    importance_level INTEGER DEFAULT 1 CHECK (importance_level BETWEEN 1 AND 5), -- 1=Dim, 5=Bright Giant
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_nodes_subject ON knowledge_nodes(subject_id);
CREATE INDEX idx_nodes_parent ON knowledge_nodes(parent_id);
```

### 1.3. User Node Status Table (`user_node_status`)
Tracks the user's relationship with each star (Personalization).

```sql
CREATE TABLE user_node_status (
    user_id UUID NOT NULL REFERENCES users(id),
    node_id UUID NOT NULL REFERENCES knowledge_nodes(id),
    
    mastery_score INTEGER DEFAULT 0 CHECK (mastery_score BETWEEN 0 AND 100), -- 0-100% Brightness/Opacity
    total_minutes INTEGER DEFAULT 0, -- Time invested
    is_unlocked BOOLEAN DEFAULT FALSE, -- Has the user "discovered" this node?
    
    last_interacted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, node_id)
);
```

---

## 2. Backend API Design (FastAPI)

### 2.1. Models (Pydantic)
**File**: `app/schemas/galaxy.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class SectorEnum(str, Enum):
    COSMOS = "COSMOS"
    TECH = "TECH"
    ART = "ART"
    CIVILIZATION = "CIVILIZATION"
    LIFE = "LIFE"
    WISDOM = "WISDOM"
    VOID = "VOID"

class GalaxyNodeDTO(BaseModel):
    id: UUID
    parent_id: Optional[UUID]
    name: str
    importance: int
    sector: SectorEnum
    base_color: str
    
    # User Status
    is_unlocked: bool
    mastery_score: int
    
    class Config:
        from_attributes = True

class GalaxyGraphResponse(BaseModel):
    nodes: List[GalaxyNodeDTO]
    # Edges are implicit via parent_id in nodes
    user_flame_intensity: float # Calculated from total study time today
```

### 2.2. Endpoints
**File**: `app/api/v1/galaxy.py`

*   **GET /api/v1/galaxy/graph**
    *   **Logic**: 
        1. Fetch all `subjects` and map to `SectorEnum`.
        2. Fetch all `knowledge_nodes`.
        3. Fetch `user_node_status` for the current user.
        4. Join data: If no status exists for a node, default to `unlocked=False, mastery=0`.
        5. Calculate `user_flame_intensity` based on today's total focus minutes from `Job/Task` history.
    
*   **POST /api/v1/galaxy/node/{id}/spark** (Debug/MVP)
    *   **Logic**: Upsert `user_node_status`. Set `is_unlocked=True`, increment `mastery_score` by fixed amount (e.g., +10), or set directly via body.

---

## 3. Frontend Architecture (Flutter)

### 3.1. State Layer (Riverpod)

**`GalaxyRepository`**:
*   Fetches `GalaxyGraphResponse`.

**`GalaxyNotifier` (StateNotifier<AsyncValue<GalaxyState>>)**:
*   **State**: Holds list of `GalaxyNode` entities which include computed `Offset position`.
*   **Polar Layout Algorithm**:
    1.  **Sector Assignment**: Divide 360° into 6 sectors (60° each) + Void (Center/Background).
    2.  **Root Nodes**: Place subject root nodes at `R_min` (e.g., 200px) within their designated sector angle.
    3.  **Child Nodes**: Place children relative to parents using a "Gravitational Cluster" approach:
        *   `Angle = Parent_Angle + random_noise(-15°, +15°)`
        *   `Radius = Parent_Radius + Node_Importance * spacing_factor`
    4.  **Collision Avoidance**: Simple iteration to push overlapping nodes apart if necessary (MVP might skip complex force-directed layout for performance).

### 3.2. Core UI Components

**Widget Tree**:
```
GalaxyScreen
 └── GalaxyViewport (Stack)
      ├── DeepSpaceBackground (CustomPainter - Stars/Nebula static)
      ├── InteractiveViewer (handles pan/zoom)
      │    └── StarMapLayer (CustomPaint)
      │         └── Painter: Draws lines (connections) and circles (nodes)
      └── Center
           └── FlameCore (ShaderWidget)
```

#### A. GalaxyViewport
*   Wraps the galaxy in `InteractiveViewer`.
*   **Constraint**: `constrained: false` to allow infinite scroll sensation (or large finite size).
*   **Coordinate System**: Center of the layout is `(0,0)`.

#### B. StarMapLayer (CustomPainter)
*   **Performance**: Use `drawAtlas` if node count > 500 for batch rendering sprites. For MVP (<100 nodes), `canvas.drawCircle` is fine.
*   **Visuals**:
    *   **Locked Node**: Small grey dot, low opacity.
    *   **Unlocked Node**: Colored glow (based on `hex_color`), size based on `importance`.
    *   **Connections**: Thin lines with gradient opacity fading towards children.

#### C. FlameCore (Shader)
*   **Tech**: `FragmentProgram` from a `.frag` file.
*   **Uniforms**:
    *   `u_time`: Drives animation loop.
    *   `u_intensity`: Controls the "wildness" / radius of the flame (mapped from study time).
    *   `u_color`: Dominant color (white/blue for high intensity, orange/red for low).

### 3.3. Shader Logic (GLSL Draft)
**`mobile/shaders/core_flame.frag`**

```glsl
#include <flutter/runtime_effect.glsl>

uniform float u_time;
uniform float u_intensity; // 0.0 to 1.0
uniform vec2 u_resolution;

// Simplex noise function (simplified for brevity)
float noise(vec2 st) { ... } 

vec4 main(vec2 coords) {
    vec2 uv = coords / u_resolution;
    uv = uv * 2.0 - 1.0; // Center at 0,0
    
    // Distance from center
    float d = length(uv);
    
    // Deform radius with noise based on time and angle
    float angle = atan(uv.y, uv.x);
    float n = noise(vec2(angle * 3.0, u_time * 2.0 + d * 2.0));
    
    // Core shape
    float radius = 0.3 + (u_intensity * 0.2); // Grow with intensity
    float flame_edge = radius + n * 0.1;
    
    // Soft glow
    float glow = 1.0 - smoothstep(0.0, flame_edge, d);
    
    // Color mixing
    vec3 coreColor = vec3(1.0, 0.9, 0.5); // Hot center
    vec3 outerColor = vec3(1.0, 0.4, 0.1); // Red/Orange edge
    vec3 finalColor = mix(outerColor, coreColor, glow * 2.0);
    
    return vec4(finalColor * glow, glow);
}
```

## 4. Interaction Flow
1.  **Init**: `GalaxyNotifier` calls API. On success, runs `layoutNodes()` to assign `(x,y)` to each node. State updates.
2.  **Render**: `StarMapLayer` reads the positioned nodes and paints. `FlameCore` starts ticking (via `TickerProvider`).
3.  **Gestures**: `InteractiveViewer` handles the matrix transformations for the stars. `FlameCore` ignores the translation (stays centered) but respects the scale (grows/shrinks) if desired, OR stays fixed UI overlay. *Design Decision: Flame should probably stay fixed screen center ("You are here"), while stars move around you.*
