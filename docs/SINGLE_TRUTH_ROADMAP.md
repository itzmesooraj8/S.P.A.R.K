# S.P.A.R.K. Single Truth Roadmap

This repository is organized around one rule: every surface should feed the same local-first core, not its own private behavior tree.

## Phase 1: Stabilization

Goal: make the brain reliable before expanding.

Implemented hooks:
- Conversational intent routing lives in [intent_router.py](../intent_router.py).
- Intent sanitization lives in [security/intent_validator.py](../security/intent_validator.py).
- Structured payload validation now lives in [security/schema_validator.py](../security/schema_validator.py).
- Tool-call arguments are coerced before execution in [core/spark_brain.py](../core/spark_brain.py).

## Phase 2: Secure Satellite Access

Goal: keep heavy execution on the home machine while thin clients only package requests.

Design contract:
- Thin clients send signed JSON envelopes.
- The home machine validates the envelope before it reaches the commander or brain.
- Cloudflare Tunnel remains the transport, not the authority.

## Phase 3: Agentic Workspace

Goal: let task-specific agents operate inside a bounded workspace.

Design contract:
- Generated tools and forged tools stay in sandboxed paths.
- Workspace mutations should prefer [sandbox/temp_build](../sandbox/temp_build) and [sandbox/tool_forge](../sandbox/tool_forge).
- Tool creation should remain reviewable through the existing forge workflow.