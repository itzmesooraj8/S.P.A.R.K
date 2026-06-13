# SPARK Architecture

## System Overview

SPARK is an event-driven, continuously-observing AI agent with an LLM intent classifier at the entry point, four-type memory, a permission gate on every action, dynamic confidence thresholds, and a 5-second observation loop.

```
User Input → Intent Router → Agent → LLM Bridge → Action → Authority Check → Execution
     ↑                                                                    ↓
     └────────────────────── Response ←──────────────────────────────────┘
```

## Layer Architecture

| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
| **Core** | Infrastructure (Events, State, Config, DI) | `spark/core/` |
| **Cognition** | Thinking only (Goals, Reasoning, Reflection) | `spark/cognition/` |
| **Persona** | Identity only (Name, Style, Tone) | `spark/persona/` |
| **Orchestration** | Execution only (Workflows, Scheduling) | `spark/orchestration/` |
| **Memory** | Persistence (Semantic, Episodic, Procedural, Working) | `spark/memory/` |
| **Awareness** | Perception (Screen, App, Context, User, World Model) | `spark/awareness/` |
| **Agents** | Specialized (Planner, Executor, Observer) | `spark/agents/` |
| **Authority** | Permission gating | `spark/authority/` |
| **Policy** | Security constitution | `spark/policy/` |
| **Planning** | LLM-driven planning | `spark/planning/` |
| **Automation** | Browser, Desktop, IoT | `spark/automation/` |
| **Observability** | Metrics, Tracing, Audit | `spark/observability/` |

## Data Flow

```
1. User sends message
2. Intent Router classifies: goal_creation | action_execution | memory_query | status_check | conversation
3. Routed to appropriate agent
4. Agent uses LLM Bridge for reasoning
5. Action passes through Authority + Policy checks
6. Action executes
7. Result logged to Decision Log
8. Memory updated
9. World Model updated
10. Response returned
```

## Continuous Loop

```
Observe → Understand → Predict → Plan → Act → Reflect → Learn → Observe
Forever. 24/7.
```

The loop runs every 5 seconds:
1. **Observe** — Take snapshot of environment
2. **Understand** — Update World Model
3. **Predict** — What will user likely need
4. **Plan** — Create plan for predicted needs
5. **Act** — Execute if confidence >= 0.7
6. **Reflect** — Analyze what happened
7. **Learn** — Update skills and strategies
