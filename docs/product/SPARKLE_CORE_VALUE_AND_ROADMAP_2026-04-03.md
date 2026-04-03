# Sparkle: Vision, Core Value, and Multi-Phase Roadmap

**Date**: 2026-04-03
**Status**: Active / Foundational Consensus
**Audience**: Product, Engineering, Design, AI Agents

---

## Part 1: Product Vision & Core Value Proposition

### 1.1 The Ultimate Vision: Self-Actualization OS
Sparkle is **not merely an AI learning assistant**, nor is it a glorified task manager. Sparkle is a **Self-Actualization Operating System**. Learning is simply the most immediate, measurable domain to prove this capability.

Users suffer from the **"Red Palace" effect**: the painful gap between their expectations (becoming better, mastering a subject, staying fit) and their reality (laziness, external interruptions, lack of time, cognitive blocks). This mismatch leads to frustration, self-doubt, and abandonment.

Sparkle exists to bridge this gap. We provide the emotional scaffolding and the cognitive course-correction necessary to guide the user from their current state to their target state, adjusting dynamically along the way.

### 1.2 The True Moat: From "Summary" to "Evidence Loop"
Why should a user choose Sparkle over ChatGPT, Claude, DeepSeek, or Quizlet? 
- General LLMs are exceptional at answering questions.
- Quizlet is exceptional at lightweight memory reinforcement.

**Sparkle's unique value and technical moat is the "Learning Evidence Loop" (学习证据闭环).** 
- General LLMs wait for the user to ask. Sparkle **discovers the problem before the user knows it**.
- General LLMs offer "summary-level personalization" (e.g., "This user likes encouraging tones"). Sparkle builds **"evidence-level personalization"** (e.g., "This user failed 3 thermodynamics problems because they conflate the First and Second Laws; we must intervene immediately").

Sparkle is an AI Learning OS that **corrects the trajectory**, provides **deep diagnostics**, and **pushes interventions proactively**.

### 1.3 The North Star Metric
Abandon generic metrics like DAU, task completion rate, or chat turns. 
**The New North Star: Concept Block Resolution Rate (概念卡点解决率).**
*Definition: The percentage of high-risk cognitive blocks identified by the system that are verifiably resolved within 7 days.*

**Supporting Metrics:**
1. **Recurring Error Drop Rate**: Decrease in the recurrence of the specific error types.
2. **Pre-Deadline Plan Rescue Rate**: The success rate of salvaging a failing learning path before the deadline.
3. **Time-to-Clarity**: The time it takes for a user to transition from "I don't know what I'm doing" to "I know exactly how to fix this."

---

## Part 2: The Multi-Phase Execution Roadmap

This roadmap is designed linearly. Each phase builds the necessary foundation for the next. Both human developers and AI agents must follow this sequential progression to avoid disjointed feature development.

### Phase 1: The Evidence Loop & Cognitive Deepening (Building the Moat)
**Objective**: Transform the system's understanding of the user from "execution tracking" (what they did) to "cognitive tracking" (what they actually understand).

*   **Step 1.1: Deep Error Classification**
    *   Upgrade the Error Book (`error_book_service.py`).
    *   Every logged error must be classified into strict cognitive failure types: *Computation Error*, *Concept Confusion*, or *Application/Transfer Failure*.
*   **Step 1.2: Knowledge Star Map Refactoring**
    *   Currently, the Knowledge Star Map reflects task completion. It must reflect **verified mastery**.
    *   Connect the categorized errors directly to their corresponding Knowledge Nodes.
    *   Mastery level of a node must strictly correlate with the real-time cognitive state derived from the Error Book, not just checklist ticks.
*   **Step 1.3: Evidence-Based Context Injection**
    *   Upgrade the LLM context pruner/router.
    *   Instead of compressing user data into a generic 100-token summary, inject the precise **Cognitive Block Profile** into the prompt when the user asks a related question. The AI must "remember" the specific concepts the user struggles with during real-time inference.

### Phase 2: Proactive OS & Pre-Cognitive Intervention (The "Push" Paradigm)
**Objective**: Shift Sparkle from a "pull" model (waiting for user input) to a "push" model (anticipating failure and intervening).

*   **Step 2.1: The Active Reach-Out Engine**
    *   Build a lightweight background daemon/scanner.
    *   Monitor real-time task completion velocities and error densities.
    *   If a user's completion rate drops below the threshold needed for their deadline, the AI must initiate a conversation: *"At this pace, we won't hit the deadline. Let's recalibrate the plan right now."*
*   **Step 2.2: Proactive Triggering of "The 3 Systems" (Simulation/Theatre/Report)**
    *   Users currently have to manually navigate to trigger a Simulation or read a Report. This is unrealistic for a stressed student.
    *   **Implementation**: If Step 1.1 detects 3 consecutive *Concept Confusions* on the same node, the chat UI automatically pushes a card: *"I noticed you're stuck on this concept. I've prepared a 5-minute interactive simulation to clear it up. Start now?"*
    *   Weekly reports should be pre-summarized and pushed to the homepage feed, not hidden in a dashboard.

### Phase 3: Adaptive Replanning & Multi-Dimensional Modeling (The Local-to-Global Path)
**Objective**: Acknowledge human weakness. Plans will fail. Sparkle must dynamically recalculate the "local optimum" path to keep the user moving toward the "global optimum."

*   **Step 3.1: Chunked Adaptive Replanning**
    *   Implement dynamic plan restructuring. If a user misses 3 days of tasks, do not just pile them up. The system automatically offers a "Restructured Rescue Plan," recalculating the critical path based on the highest-priority Knowledge Nodes (identified in Phase 1).
*   **Step 3.2: Behavioral Pattern Recognition (The Hidden Traits)**
    *   Analyze metadata: At what time of day does the user usually abandon tasks? After what type of failure do they procrastinate?
    *   Feed these behavioral traits into the User Model. The Orchestrator will use these insights to schedule hard tasks during peak energy times, or inject nudges *before* the predicted procrastination window.

### Phase 4: Emotional Scaffolding & Social Accountability (Sustaining Willpower)
**Objective**: Address the psychological "valley of despair" through multi-sensory emotional value and human connection.

*   **Step 4.1: Multi-Sensory Reinforcement**
    *   Integrate contextual BGM, precise haptic feedback, and visual "surprise" micro-interactions in the frontend UI (`Flutter`).
    *   These are not gimmicks; they are psychological rewards directly tied to overcoming specific cognitive blocks (verified in Phase 1).
*   **Step 4.2: Accountability Partner & Vanity Sharing**
    *   Build the "Responsibility Partner" protocol. Allow users to link their progress.
    *   Design high-aesthetic, data-rich "Insight Cards" (sharing cognitive breakthroughs, not just study hours) that satisfy social vanity and provide external motivation.

---

## Execution Guidelines for AI and Human Agents

1. **Strict Sequencing**: Do not implement Phase 3 or Phase 4 features until the Phase 1 Evidence Loop is completely sealed. A pretty UI for a broken cognitive model is useless.
2. **Context is King**: Any new LLM prompt or LangGraph node created must answer: *"Does this prompt have access to the user's specific cognitive blocks and recent errors?"* If no, the architecture is flawed.
3. **Continuous Verification**: Every PR or feature completion must be tested against the North Star metric: *Does this directly help resolve a concept block faster or more reliably?*