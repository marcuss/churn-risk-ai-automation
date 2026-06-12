# 0007 — Evaluating LLM output quality (LLM-as-judge)

- **Status:** Accepted
- **Date:** 2026-06-12

## Context

The deterministic layers are unit-tested, but the **LLM prose is the product's
voice and was unverified.** A prompt edit could silently degrade quality
(data-dumping, robotic tone, hallucination) and nothing would catch it — ordinary
`pytest` can't grade subjective writing. We need to *measure* "is the summary good"
and **gate prompt changes** on it, or we're shipping prompt edits on vibes.

## Decision

Add a two-layer evaluation harness (`evals/`), executed by `evals/run.py` against a
fixed golden set:

- **Layer 1 — deterministic checks** (cheap, pass/fail, no model call): length,
  ≤ 4 sentences, no bullets/headings, omits the account name, no leaked score,
  `canceled` mentions renewal.
- **Layer 2 — LLM-as-judge** at **temperature 0**: scores a rubric (synthesis,
  tone, actionability, faithfulness, canceled-framing) and returns structured JSON.

`python -m evals.run --check` aggregates and **exits non-zero on regression**. The
rubric ([`../../evals/rubric.md`](../../evals/rubric.md)) is the source of truth;
`run.py` executes it. It runs in a **separate** CI workflow (`evals.yml`) because it
makes paid, non-deterministic API calls — never on every commit.

**Why it can stay small:** because risk qualification is deterministic and
unit-tested ([0001](0001-deterministic-risk-scoring.md)), the eval only grades the
*prose*, never the decision. A system that let the LLM decide risk would force the
eval to check correctness too — far harder and noisier. The deterministic/LLM split
is what keeps this trustworthy.

## Tradeoffs

- **(+)** Prose quality becomes a number, so prompt changes produce a measurable
  delta and a regression gate — not a vibe.
- **(+)** Small and cheap: only prose is graded, against ~8 archetype accounts.
- **(−)** The judge is itself an LLM — non-deterministic and potentially sycophantic;
  mitigated by temperature 0, a concrete rubric, and forced structured output.
- **(−)** A small golden set catches regressions ("now it data-dumps"), not
  fine-grained ranking.
- **(−)** Costs real API calls → gated to prompt/eval changes + manual dispatch.

## Consequences

- `evals/` holds the rubric, golden set, and harness; `prompts/eval_judge_prompt.txt`
  is the (versioned) judge prompt.
- `evals.yml` is the gate and needs an `ANTHROPIC_API_KEY` repo secret; the Layer-1
  check functions are pure and unit-tested in the no-network `ci.yml`.
- Production would grow the golden set, add multiple judges / pairwise scoring to
  reduce judge bias, and track scores over time.
