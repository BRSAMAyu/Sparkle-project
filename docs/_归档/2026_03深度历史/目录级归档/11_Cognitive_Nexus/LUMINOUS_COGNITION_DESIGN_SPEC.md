# Sparkle Design Evolution: Luminous Cognition
> Engineering Specification for "Artistic Level" UI Upgrade

**Version:** 1.1.0
**Date:** 2026-01-07
**Status:** Approved for Implementation

---

## 1. Vision & Philosophy

The goal is to elevate Sparkle from a "functional tool" to a "cognitive artifact." We are moving beyond simple Dark/Light modes to a physics-based lighting model:

*   **Daylight Flow (Light Mode):** Simulates natural light diffusion. Materials resemble **Matte Ceramic** or **High-Density Paper**. Shadows are soft and directional.
*   **Deep Space Resonance (Dark Mode):** Simulates self-luminous objects in a void. Materials resemble **Obsidian** and **Holographic Glass**. Emphasis on **Glow**, **Reflection (Rim Light)**, and **Depth**, rather than simple grey backgrounds.

**Core Engineering Principle:**
> "Decouple Art from Architecture."
> Visual richness is achieved through a **Material Recipe System**, not by hardcoding styles into widgets.

---

## 2. Unified Visual Model (Non-Negotiable Rules)

### 2.1 Lighting Rules
*   **Primary light source:** Top-left at 35 degrees.
*   **Rim Light:** Top edge only. No multi-direction highlights.
*   **Shadows:** Cast only to bottom-right. No conflicting shadow directions.

### 2.2 Layering Rules
*   **Layer 0:** Environment (surface ambient + global gradients).
*   **Layer 1:** Material (ceramic/neo-glass/obsidian).
*   **Layer 2:** Information (text/icons).
*   **Layer 3:** Emphasis (glow/halo/active states).

### 2.3 Visual Budget
*   **Max hero materials per screen:** 2.
*   **Max accent material per screen:** 1.
*   **No noise overlay on text containers.**

---

## 3. Architecture: The Material Layer

We introduce a new layer between **Design Tokens (v2.0)** and **Components**.

### 3.1 The Layer Model

| Layer | Responsibility | Example |
| :--- | :--- | :--- |
| **1. Tokens (v2.1)** | Raw atomic values (Colors, Numbers). **No logic.** | `rimLightColor`, `surfaceAmbient`, `blurSigmaLg` |
| **2. Recipes (`SparkleMaterial`)** | **Pure Data** describing physical properties. Platform agnostic. | `neoGlass = { blur: 15, noise: 0.05, rim: white05 }` |
| **3. Presets (`AppMaterials`)** | The catalog of standard materials used in the app. | `AppMaterials.neoGlass`, `AppMaterials.obsidian` |
| **4. Styler (`MaterialStyler`)** | The **Renderer**. Converts Recipes + Shape into `BoxDecoration`/`CustomPaint`. | `MaterialStyler.apply(recipe, shape)` |
| **5. Components** | Functional widgets that consume Styles. | `FocusCard`, `ChatBubble` |

### 3.2 The Recipe Definition (`SparkleMaterial`)

Located in: `mobile/lib/core/design/materials.dart`

```dart
/// Pure data class defining a material's physical properties.
/// Does NOT contain Flutter rendering logic (like BoxDecoration).
class SparkleMaterial {
  const SparkleMaterial({
    this.backgroundGradient,
    this.backgroundColor,
    this.opacity = 1.0,
    this.blendMode,
    this.noiseOpacity = 0.0,
    this.noiseBlendMode,
    this.blurSigma = 0.0,
    this.rimLightColor,
    this.glowColor,
    this.shadows,
    this.borderWidth = 0.0,
    this.borderColor,
    this.borderGradient,
  });

  final Gradient? backgroundGradient;
  final Color? backgroundColor;
  final double opacity;
  final BlendMode? blendMode;

  final double noiseOpacity; // 0.0 - 1.0
  final BlendMode? noiseBlendMode;

  final double blurSigma; // Backdrop filter sigma
  final Color? rimLightColor; // Top edge highlight
  final Color? glowColor; // Inner ambient glow
  final List<BoxShadow>? shadows; // Shadow parameters only

  final double borderWidth;
  final Color? borderColor;
  final Gradient? borderGradient;
}
```

---

## 4. Token Expansion (Design Tokens v2.1)

We will expand `SparkleColors` in `theme_manager.dart` to support lighting semantics.

### 4.1 New Semantic Tokens

| Token Name | Light Mode Value (Daylight) | Dark Mode Value (Deep Space) | Usage |
| :--- | :--- | :--- | :--- |
| **`surfaceAmbient`** | `#FAFAF8` (Warm Alabaster) | `#050510` (Deep Void) | Screen background base |
| **`rimLightColor`** | `Colors.white` (opacity 0.6) | `Colors.white` (opacity 0.2) | Top edge reflection |
| **`glowPrimaryColor`** | `brandPrimary` (opacity 0.15) | `brandPrimary` (opacity 0.4) | Inner glow / Active state |
| **`shadowSoftColor`** | Neutral grey | Black (low opacity) | Standard elevation |
| **`shadowDeepColor`** | Dark grey | Black (0.5 opacity) | Floating elements |
| **`noiseColorLight`** | Black (low opacity) | - | Light-mode noise |
| **`noiseColorDark`** | - | White (low opacity) | Dark-mode noise |

### 4.2 Numeric Tokens

| Token Name | Value | Usage |
| :--- | :--- | :--- |
| **`blurSigmaSm`** | 6.0 | Light glass |
| **`blurSigmaMd`** | 10.0 | Standard glass |
| **`blurSigmaLg`** | 15.0 | Hero glass |
| **`shadowSoftBlur`** | 10.0 | Standard elevation |
| **`shadowSoftOffset`** | (0, 4) | Standard elevation |
| **`shadowDeepBlur`** | 20.0 | Floating elevation |
| **`shadowDeepOffset`** | (0, 8) | Floating elevation |
| **`noiseOpacityLight`** | 0.05 | Light mode noise |
| **`noiseOpacityDark`** | 0.03 | Dark mode noise |

### 4.3 Visual Budget (Performance & Aesthetics)

*   **Max Hero Materials:** Limit of **2** "Hero" materials (NeoGlass/Obsidian) per screen.
*   **No Noise on Text:** Text containers (e.g., Chat Bubbles) must use `noiseOpacity: 0.0` to ensure readability.
*   **Unified Light Source:** Top-Left is the primary light source.
    *   **Rim Light:** Top edge.
    *   **Shadow:** Bottom/Right edge.

---

## 5. Material Catalog (`AppMaterials`)

We will implement these standard presets.

### 5.1 **NeoGlass** (The Hero)
*   **Usage:** `CuriosityCapsule`, `FocusCard`, `OmniBar`.
*   **Description:** Frosted glass with subtle grain.
*   **Recipe:**
    *   `blurSigma`: `blurSigmaLg`
    *   `noiseOpacity`: `noiseOpacityLight` / `noiseOpacityDark`
    *   `rimLightColor`: `tokens.rimLightColor`
    *   `background`: Linear Gradient (White 0.05 -> White 0.15)

### 5.2 **Obsidian** (Dark Accent Only)
*   **Usage:** Primary CTA in Dark Mode, key active states.
*   **Description:** Deep, glossy, volcanic glass.
*   **Recipe:**
    *   `blurSigma`: 0.0
    *   `noiseOpacity`: 0.0
    *   `backgroundColor`: Black (0.8 opacity)
    *   `rimLightColor`: `brandPrimary` (0.3 opacity)
    *   `glowColor`: `brandPrimary` (0.1 opacity)

### 5.3 **Ceramic** (Light Mode Standard)
*   **Usage:** Bento Grid Cards (Standard).
*   **Description:** Matte, opaque, tactile.
*   **Recipe:**
    *   `blurSigma`: 0.0
    *   `backgroundColor`: `surfaceSecondary`
    *   `shadows`: `shadowSoftColor` + `shadowSoftBlur`
    *   `noiseOpacity`: 0.0

---

## 6. MaterialStyler (Rendering Rules)

**Render order is mandatory to ensure visual consistency:**
1. Background Color / Gradient
2. Backdrop Blur
3. Noise Overlay
4. Rim Light
5. Inner Glow
6. Border / Gradient Border
7. Shadow

**Any deviation requires explicit documentation in the component.**

---

## 7. Key Component Upgrades

### 7.1 The Galaxy (Performance Optimized)
*   **Nodes:**
    *   **Core:** Solid circle.
    *   **Halo:** Use `MaskFilter.blur` (efficient) instead of complex shaders.
    *   **LOD:** Halo alpha follows `alpha = clamp(scale * 2.0 - 0.4)` to avoid hard transitions.
*   **Beams:**
    *   Use `Paint.shader` (LinearGradient).
    *   Animate the `GradientTransform` to simulate flowing energy particles (zero allocation).
*   **Background:**
    *   Multi-layered `RadialGradient` with slow rotation. No real-time fluid simulation.

### 7.2 Chat Interface (Fluid Thought)
*   **Bubbles:**
    *   Shape: Super-ellipse (`ContinuousRectangleBorder`, radius ~24).
    *   Material: `surfaceSecondary` + `glowColor` (Agent specific).
    *   Noise: Always disabled.
*   **Reasoning:**
    *   Collapsed by default into a "Pulse Line".
    *   **Shimmer Effect:** Active for first 3 seconds of "Thinking", then fades to static glow.

### 7.3 Bento Grid (Unified Lighting)
*   **Curiosity Capsule:** The flagship implementation of **NeoGlass**.
*   **Lighting:** Ensure all cards share the same "Rim Light" direction (Top).

---

## 8. Motion & Micro-Interaction Rules

*   **Breathing:** 4s cycle, scale range 0.97–1.03 for hero elements only.
*   **Transitions:** Prefer morphing/expansion + background blur over slide transitions.
*   **Shimmer:** Limited to short thinking states to reduce eye fatigue.

---

## 9. Performance & Graceful Degradation

*   **Tier Ultra:** Noise + Blur + Halo + Full motion.
*   **Tier High:** No noise. Keep blur + halo.
*   **Tier Medium:** No blur. Keep gradients + soft shadows.
*   **Tier Low:** Solid colors only, no glow/halo/blur.

---

## 10. Accessibility & Readability

*   Minimum contrast for body text: **4.5:1**.
*   Glow must never reduce text contrast.
*   Light mode base must use Warm Alabaster (`#FAFAF8`), not pure white.

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Current Sprint)
1.  **System Setup:**
    *   Create `SparkleMaterial` class (The Recipe).
    *   Create `MaterialStyler` helper (The Renderer).
    *   Update `ThemeManager` with new tokens (`rimLightColor`, `surfaceAmbient`).
2.  **Asset:** Add `noise_texture.png` (tiled 64x64 or 128x128).
3.  **Prototype:** Apply `AppMaterials.neoGlass` to **Curiosity Capsule** and **Focus Card**.

### Phase 2: Material Rollout
1.  **Refactor Components:** Update `BentoGrid` cards to consume `AppMaterials` presets.
2.  **Light Source Unification:** Ensure global light direction consistency.
3.  **Performance Tuning:** Implement `PerformanceService` hooks to downgrade materials (e.g., disable Blur/Noise) on low-end devices.

### Phase 3: Artistic Polish
1.  **Galaxy Upgrade:** Implement the Core+Halo node rendering and Gradient Beams.
2.  **Chat Upgrade:** Implement Super-ellipse bubbles and Shimmering Reasoning bar.
3.  **Motion:** Add subtle "Breathing" animations to Hero elements.

---

## 12. Migration Guide (Legacy to Luminous)

*   **Avoid:** `BoxDecoration(color: Colors.white.withOpacity(0.2))`
*   **Use:** `MaterialStyler.apply(AppMaterials.neoGlass, shape)`
*   **Avoid:** Hardcoded `BoxShadow`
*   **Use:** `SparkleMaterial(shadows: context.sparkleShadows.soft)`

