# Eval Rubric — Churn Summary Quality

The spec for what a "good" summary is. The harness (`evals/run.py`) executes this;
the rubric is the source of truth, not the code.

## What this grades — and why it can stay small

Only the LLM **prose** is graded. The risk *decision* is deterministic and covered
by unit tests ([ADR 0001](../docs/adr/0001-deterministic-risk-scoring.md)), so the
eval never checks whether flagging is correct — only whether the summary is good.
Reference date is fixed at **2026-06-11** so renewal phrasing is deterministic.
Inputs come from [`golden_set.jsonl`](golden_set.jsonl).

## Layer 1 — deterministic checks (pass/fail, no model call)

- non-empty and within length bounds (~20–800 chars)
- ≤ 3 sentences
- no bullet points / list markers
- mentions the account name
- does **not** leak the internal risk score (no "score", no bare risk integer)
- not a raw metric dump (heuristic: limited runs of digits)
- for `canceled` accounts: mentions renewal / non-renewal / save language

Every Layer-1 check must pass; a failure is a hard fail for that case.

## Layer 2 — LLM-as-judge (1–5 per dimension, temperature 0)

| Dimension | 1 (bad) | 5 (good) |
|---|---|---|
| `synthesis` | lists raw metrics | synthesizes signals into a concern |
| `tone` | robotic / dashboard | reads like a thoughtful analyst |
| `actionability` | vague | clear what CS should do next |
| `faithfulness` | invents facts beyond signals | grounded only in given signals |
| `canceled_framing` | treats as lost (N/A → 3) | treats as a time-boxed save |

The judge returns structured JSON (per-dimension score + one-line rationale). See
[`../prompts/eval_judge_prompt.txt`](../prompts/eval_judge_prompt.txt).

## Aggregation & gate

- **Per case:** all Layer-1 checks pass **and** Layer-2 mean ≥ 4.0.
- **Suite:** ≥ 90% of cases pass Layer 1, and the overall mean judge score ≥ 4.0.
- `python -m evals.run --check` exits non-zero when the suite is below bar — the
  gate `evals.yml` runs on prompt changes.

The judge runs at temperature 0 for repeatability. A ~10-case set catches
regressions ("the new prompt now data-dumps"), not fine-grained ranking.
