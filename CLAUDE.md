# CLAUDE.md

Repository operating guidelines for AI-assisted development.

This document defines implementation rules, architectural boundaries, and development conventions to maintain consistency and reliability as the system evolves.

---

# Core Principles

## 1. Prefer simple, explicit solutions

This project intentionally favors clarity over abstraction.

Prefer:

* small focused modules
* explicit business logic
* readable implementations
* deterministic behavior

Avoid introducing complexity without a clear operational benefit.

Examples of intentionally avoided scope:

* workflow orchestration frameworks
* multi-agent systems
* vector databases / RAG
* unnecessary persistence layers
* excessive indirection

When in doubt:

> choose the simpler implementation.

---

## 2. Deterministic business logic is authoritative

Churn qualification must remain deterministic.

Risk scoring belongs exclusively to:

```text
src/risk/
```

The LLM is restricted to:

* summary generation
* natural language synthesis

The LLM must **never determine whether an account is at risk**.

This separation exists to preserve:

* explainability
* consistency
* debuggability
* operational reliability

---

## 3. Prefer readability over cleverness

Code should optimize for maintainability.

Prefer explicit logic:

```python
if account.days_since_last_login > 30:
```

Over unnecessary indirection:

```python
risk += inactivity_penalty(account)
```

unless abstraction materially improves clarity.

Small duplication is acceptable if it improves readability.

Avoid premature abstractions.

---

## 4. Fail gracefully

The system should degrade gracefully.

Failures affecting one account must not interrupt processing for others.

Expected failure behavior:

1. retry transient failures
2. fallback to deterministic summary generation
3. continue batch execution
4. log failures with context

The weekly report should always complete.

Reliability is preferred over elegance.

---

## 5. Test business behavior

Tests should validate behavior, not implementation details.

Focus testing on:

* risk qualification
* threshold behavior
* fallback generation
* Slack formatting

Avoid low-value tests tied to implementation internals.

Good:

```text
test_past_due_customer_is_flagged
```

Avoid:

```text
test_adds_two_risk_points
```

Tests should remain resilient to refactoring.

---

## 6. Maintain git discipline

All meaningful changes should be committed incrementally.

Prefer:

* small commits
* focused scope
* descriptive messages

Recommended commit style:

```text
feat: implement deterministic risk scoring
test: add threshold behavior coverage
docs: document prompt iteration
fix: add llm timeout fallback
refactor: simplify slack formatter
```

Avoid mixing unrelated concerns in the same commit.

---

## 7. Document architectural decisions

Non-trivial architectural decisions should be documented under:

```text
docs/adr/
```

ADRs should include:

* context
* decision
* tradeoffs
* consequences

Document reasoning, not just outcomes.

---

## 8. Prompt changes require documentation

Prompt changes should be intentional and traceable.

When modifying prompts:

Update:

```text
prompt_design.md
```

Include:

* what changed
* why it changed
* expected outcome
* observed tradeoffs

Avoid undocumented prompt experimentation.

---

## 9. Respect module boundaries

Module responsibilities:

```text
ingestion/  → CSV loading and parsing
risk/       → deterministic churn qualification
ai/         → prompt construction and LLM interaction
messaging/  → Slack formatting and delivery
resilience/ → retry and fallback logic
```

Avoid business logic leaking into unrelated modules.

Examples:

* Slack formatter should not calculate risk
* LLM client should not decide thresholds
* CSV loader should not transform business rules

---

## 10. Prefer observability over assumptions

Unexpected behavior should be diagnosable.

Prefer:

* explicit logging
* meaningful errors
* structured failure handling

Avoid silent failures.

Error messages should include enough context to support debugging.

---

## 11. Optimize for operational usefulness

The primary goal of the system is actionable churn reporting.

Favor:

* concise summaries
* operational readability
* reliable execution

Over:

* novelty
* excessive intelligence
* unnecessary complexity

The system should produce outputs that are immediately usable by downstream teams.
