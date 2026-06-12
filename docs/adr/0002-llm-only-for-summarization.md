# 0002 — LLM only for summarization

- **Status:** Accepted
- **Date:** 2026-06-11

## Context

Given deterministic risk scoring ([0001](0001-deterministic-risk-scoring.md)),
where should the LLM be used? It could classify risk, rank accounts, decide
thresholds, or simply write the prose. Letting a probabilistic model touch the
business decision would reintroduce exactly the nondeterminism 0001 removed.

## Decision

The LLM is restricted to **narrative generation** for already-flagged accounts.
It receives the account's *interpreted* signals (e.g. "payment instability") and
writes a 2–3 sentence analyst-style summary. It never sees the raw risk score,
never decides whether an account is at risk, and never orders the report.

## Tradeoffs

- **(+)** Nondeterminism is contained to prose, where it is harmless and even
  desirable (natural phrasing).
- **(+)** The authoritative business logic stays deterministic and testable.
- **(+)** Smaller, cheaper prompts (account-local context only).
- **(−)** Two subsystems to maintain (rules + prompt).
- **(−)** Prose quality is itself unverified by unit tests — it needs a separate
  evaluation harness (rubric + judge).
- **(−)** The model can still write a poor or subtly wrong summary even on a
  correct flag; mitigated by output validation, the deterministic fallback
  ([0003](0003-graceful-degradation.md)), and the eval.

## Consequences

- Prompts are versioned specs in `prompts/` and documented in
  [`../prompt_design.md`](../prompt_design.md); code loads them rather than
  duplicating prompt text.
- The internal risk score and `mrr`/`plan_name` are deliberately excluded from the
  model's context to avoid biasing the prose.
- Summary quality is governed by `evals/` (deterministic checks + LLM-as-judge).
