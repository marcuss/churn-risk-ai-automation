# CLAUDE.md

Operating guidelines for AI-assisted development. Rules are ordered by priority.

---

## 0. Spec-driven — highest priority

**Everything in this repo must trace to a versioned spec. No ad-hoc artifacts.**

Code, tests, prompts, and generated summaries each implement a spec that lives in
version control. Before writing code, point to the spec it implements — or write
that spec first. To change behavior, **change the spec, then the code.**

Where specs live:

```text
docs/risk_strategy.md        → scoring weights, threshold, risk≠priority
docs/prompt_design.md        → prompt + context-window decisions
docs/data_contract.md        → the 9-field CSV input schema
docs/system_card.md          → intended use, data handling, failure modes
docs/adr/                    → architecture decision records (context→decision→tradeoffs→consequences)
prompts/*.txt                → LLM behavior specs (code loads these; never duplicate prompt text)
prompts/testing/*.md         → test-generation specs
evals/rubric.md + golden_set.jsonl + prompts/eval_judge_prompt.txt → summary-quality spec
```

---

## 1. Deterministic risk is authoritative

Churn qualification is deterministic and lives **only** in `src/risk/`. The LLM
generates prose and **never decides whether an account is at risk**. This
preserves explainability, consistency, and debuggability.
See `docs/adr/0001` and `0002`.

## 2. Simple and explicit over clever

Prefer small focused modules and explicit business logic. Avoid, unless there's a
clear operational benefit: orchestration frameworks, multi-agent systems, vector
DBs / RAG, persistence layers, excessive indirection. When in doubt, choose the
simpler implementation. Small duplication beats premature abstraction.

## 3. Fail gracefully

One account's failure must not stop the batch: retry transient failures →
validate output → deterministic fallback → continue. The weekly report always
completes. Reliability over elegance. See `docs/adr/0003`.

## 4. Test behavior, not implementation

Test risk qualification, thresholds, fallback, and Slack formatting — by observable
outcome, not internal math. Good: `test_past_due_customer_is_flagged`. Avoid:
`test_adds_two_risk_points`. Tests should survive refactoring.

## 5. Respect module boundaries

```text
ingestion/  → CSV loading and parsing
risk/       → deterministic churn qualification (authoritative)
ai/         → prompt construction and LLM interaction
messaging/  → Slack formatting and delivery
resilience/ → retry and fallback logic
```

No business logic leaks across boundaries: the Slack formatter doesn't score risk,
the LLM client doesn't decide thresholds, the CSV loader doesn't transform rules.

## 6. Git discipline

Small, focused, incrementally-committed changes; one concern per commit.
Conventional messages: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`,
`ci:`.

## 7. Observability over assumptions

Explicit logging, meaningful errors, structured failure handling — no silent
failures. Error messages carry enough context to debug.

## 8. Operational usefulness first

The goal is actionable churn reporting: concise summaries, readable output,
reliable execution — over novelty or unnecessary intelligence. Output should be
usable by Customer Success without modification.

---

## Change protocol (consequences of Rule 0)

- Change risk behavior → update `docs/risk_strategy.md` (and an ADR if it's a
  decision) before the code.
- Change a prompt → update `docs/prompt_design.md`; edit the `prompts/*.txt` spec,
  not inline strings.
- Change summary-quality expectations → update `evals/rubric.md`.
- Make a non-trivial architectural decision → add an ADR under `docs/adr/`.
