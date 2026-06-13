# SPARK Security Model

## Threat Model

SPARK has:
- Filesystem access
- Browser control
- Code execution
- Voice input
- LLM reasoning
- Automation capabilities

This makes it effectively an operating system assistant.

## Threats

### 1. Prompt Injection

**Risk:** User visits malicious website that contains "Ignore all previous instructions."

**Mitigation:**
- Instruction Hierarchy (system prompt > user prompt > web content)
- Prompt Provenance (track where content came from)
- Tool Permission Layer (every tool call verifies source)

### 2. Tool Escalation

**Risk:** "Read file" becomes "Delete file" through agent reasoning.

**Mitigation:**
- Authority Layer enforces separate permissions: READ, WRITE, DELETE, EXECUTE, NETWORK
- Never trust agent decisions alone
- Policy Engine evaluates every action

### 3. Secret Leakage

**Risk:** .env files, tokens, API keys entering LLM context.

**Mitigation:**
- SecretsManager never stores in code
- Policy Engine blocks secrets from LLM context
- `.env` is gitignored

### 4. Autonomous Loop Abuse

**Risk:** Infinite observe → plan → act cycles.

**Mitigation:**
- Every autonomous action requires: Goal, Reason, Confidence, Budget, Permission
- Rate limiting (10 autonomous actions per hour)
- Confidence threshold (0.7 minimum)

## Policy Engine

Every action passes `policy.evaluate()` before execution:

```python
result = policy.evaluate({
    "action": "open_browser",
    "source": "autonomous",
    "confidence": 0.8,
    "input": "user request",
})

if not result.allowed:
    return "Blocked by policy"
if result.requires_confirmation:
    return "Requires user confirmation"
```

## Authority Layers

```
User Request
  ↓
Intent Router
  ↓
Agent Decision
  ↓
Policy Engine (constitution)
  ↓
Authority Validator (permissions)
  ↓
Risk Engine (risk assessment)
  ↓
Action Execution
```
