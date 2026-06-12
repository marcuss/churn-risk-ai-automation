# Recurly Churn Risk Automation

Turns the weekly billing CSV into a Slack-ready churn-risk briefing for Customer
Success — automatically, with no manual review.

## TL;DR

- **What it does:** ingest the Monday account CSV → flag at-risk accounts with
  **deterministic rules** → have an LLM write a 2–3 sentence analyst note per
  flagged account → POST a priority-sorted briefing to Slack.
- **The LLM never decides risk.** Qualification is 100% deterministic and
  explainable (`src/risk/`); the model only writes prose. The business-critical
  decision stays debuggable and consistent.
- **Risk ≠ Priority.** MRR and plan do **not** raise an account's risk score —
  they only order the report. In the sample, a healthy \$9.8k account is absent
  while an at-risk \$1.9k account is included.
- **`canceled` ≠ churned.** Modeled on Recurly's real lifecycle: `canceled` =
  set to not renew but still active → the *top* save target. `expired` accounts
  have already churned and are **excluded** — a risk report is about accounts you
  can still save.
- **Flag rule:** score **≥ 6** (table below).
- **Always delivers:** LLM failures retry, then fall back to a deterministic
  summary; one bad account never breaks the batch.
- **Run:** `pip install -r requirements.txt` → set 2 env vars → `python -m app.main`.

## Quick start

```bash
pip install -r requirements.txt          # anthropic, requests, python-dotenv, pytest
```

Set two secrets (e.g. in a local `.env`, which is git-ignored):

```env
ANTHROPIC_API_KEY=sk-ant-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
ANTHROPIC_MODEL=claude-sonnet-4-6        # optional; this is the default
```

Run against the bundled sample (13 accounts):

```bash
python -m app.main --csv sample_data/sample_accounts.csv
# or pipe a CSV on stdin:
cat sample_data/sample_accounts.csv | python -m app.main
```

## At-risk threshold — how accounts are flagged

Risk is the **sum of deterministic signal points**. An account is flagged when
the total is **≥ 6**.

| Signal | Condition | Points |
|---|---|---|
| Subscription status | `canceled` (signaled non-renewal) | **+10** |
| | `past_due` (active dunning) | +5 |
| | `active` | 0 |
| | `expired` | *excluded from the report* |
| Failed payments (30d) | ≥ 2 / 1 | +4 / +2 |
| Inactivity (days since login) | >60 / 31–60 / 15–30 | +5 / +3 / +1 |
| Support tickets (open) | >5 / 3–5 | +3 / +2 |
| Renewal proximity | <14 days / 14–29 days | +3 / +2 |

**Why ≥ 6:** roughly *"two real problems, or one severe one."* A single moderate
signal (2 failed payments = 4, or 45 idle days = 3) does **not** flag — dunning
often self-resolves and lone signals create alert fatigue. The threshold catches
*compounding* risk, while `canceled` (+10) auto-flags because signaled
non-renewal is risk by definition.

**Risk vs. priority:** the score decides *whether* to flag; the briefing is then
ordered by **risk severity first, MRR as the tiebreak**, with MRR on every line
so CS sees business impact without it distorting the risk call.

Full reasoning: [`docs/risk_strategy.md`](docs/risk_strategy.md) · status
modeling: [`docs/adr/0005-subscription-status-modeling.md`](docs/adr/0005-subscription-status-modeling.md)

## Architecture

```text
CSV ─▶ Risk scoring (deterministic) ─▶ flag (≥6) ─▶ LLM summary ─┐
        src/risk/                                    src/ai/      ├─▶ Slack briefing
                                     deterministic fallback if LLM fails        src/messaging/
```

| Module | Responsibility |
|---|---|
| `src/ingestion/` | CSV / stdin loading + parsing |
| `src/risk/` | deterministic scoring, threshold, derived signals (**authoritative**) |
| `src/ai/` | prompt construction + LLM call + deterministic fallback |
| `src/messaging/` | Slack formatting (priority-sorted) + webhook delivery |
| `src/resilience/` | retry + per-account error isolation |

The deterministic/LLM split is the core design choice — see
[`docs/adr/0001`](docs/adr/0001-deterministic-risk-scoring.md) and
[`0002`](docs/adr/0002-llm-only-for-summarization.md).

## Failure handling

LLM calls fail or return garbage. Per account: **retry transient errors →
validate the output (non-empty, sane length) → fall back to a deterministic
summary built from the detected signals → continue the batch.** The weekly report
always completes. See [`docs/adr/0003`](docs/adr/0003-graceful-degradation.md).

## Example briefing (Slack)

```text
🚨 Weekly Churn Risk — 6 accounts flagged

1. Vertex Payments · $6.1k MRR · risk 20
   Vertex is in active dunning with repeated payment failures and has gone 85
   days without a login, all while its renewal lands in under two weeks. The
   combination points to serious involuntary-churn risk — CS should reach out
   ahead of the contract date.

2. Lumen Retail · $4.5k MRR · risk 14
   Lumen has signaled non-renewal and its contract ends in 11 days, yet the
   account is still active and lightly engaged. This is a time-boxed save
   opportunity; a renewal conversation this week is warranted.
```

(Summaries shown are illustrative; the real ones are LLM-generated at run time.)

## Testing

```bash
pytest
```

Tests assert **business behavior** — flag/no-flag by archetype, threshold
boundaries, fallback content, Slack formatting — not internal scoring math, so
they survive refactors. Specs live in [`prompts/testing/`](prompts/testing/).

**Evaluation.** Because risk qualification is deterministic and unit-tested, LLM
evaluation only has to grade the *prose*, never the risk decision — a system that
let the model decide risk would force the eval to check correctness too, which is
far harder and noisier. That split keeps the summary-quality eval small and
trustworthy: deterministic output checks plus an LLM-as-judge rubric at
temperature 0, gated separately in CI (`evals.yml`) because judge calls cost money.

## What I'd change for production

- **Calibrate, don't guess.** Replace hand-picked weights and the threshold with
  values fit against historical churn outcomes (precision/recall), backed by a
  labeled eval set to catch regressions.
- **Richer, evaluated LLM context.** Add CRM notes, product-adoption trends, and
  support sentiment; add output evals + drift monitoring so prose quality is
  measured, not assumed.
- **Secrets & trust boundary.** Move the API key and webhook into a secret
  manager, verify/sign the inbound webhook trigger, and minimize PII sent to the
  LLM.
- **Observability.** Structured per-account logs (inputs, score, decision, LLM
  status, fallback used) plus an alert on fallback rate; make re-runs idempotent.

## Docs

- [`docs/risk_strategy.md`](docs/risk_strategy.md) — scoring, threshold, risk vs. priority
- [`docs/prompt_design.md`](docs/prompt_design.md) — prompts, context-window decisions, limitations
- [`docs/data_contract.md`](docs/data_contract.md) — the 9-field CSV input schema
- [`docs/system_card.md`](docs/system_card.md) — intended use, data handling, failure modes
- [`docs/sample_output.md`](docs/sample_output.md) — expected briefing format + examples
- [`evals/rubric.md`](evals/rubric.md) — summary-quality spec (checks + judge rubric)
- [`docs/adr/`](docs/adr/) — architecture decision records (0001–0005)
- [`CLAUDE.md`](CLAUDE.md) — spec-driven rule, conventions & module boundaries
