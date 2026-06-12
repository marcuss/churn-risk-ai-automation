# System Card — Churn Risk Briefing

A short responsible-AI summary of what this system is, what it should and should
not be trusted for, and how it is kept safe and observable.

## Intended use

Automate RevOps's weekly churn-risk briefing: turn a billing CSV into a
Slack-delivered list of at-risk accounts with short, analyst-style summaries, so
Customer Success can prioritize **proactive outreach**. The output is a
**decision-support aid for humans**, not an automated action.

## Out of scope / do not use for

- Automated account actions (no auto-emails, discounts, downgrades, or
  cancellations triggered by this system).
- A system of record for churn — it reflects one weekly CSV snapshot.
- Predicting churn *probability* — the score is an explainable risk *heuristic*,
  not a calibrated probability.
- Any decision about already-churned (`expired`) accounts — they are excluded.

## How it works (and why that's safer)

Risk qualification is **deterministic and explainable**
([0001](adr/0001-deterministic-risk-scoring.md)); the LLM only writes prose and
**never decides risk** ([0002](adr/0002-llm-only-for-summarization.md)). This
split means the business-critical decision is auditable and testable, and the
LLM's nondeterminism is confined to wording.

## Data handling

- **Sensitivity:** the only free-text/PII-ish field is `account_name`. No payment
  card data, personal contact info, or message content is processed.
- **Sent to the LLM:** interpreted risk signals + coarse metrics only.
  **Not sent:** the account name, `account_id`, the raw risk score, `mrr`,
  `plan_name`.
- **Secrets:** the Anthropic API key and Slack webhook URL are read from the
  environment, never committed (`.env` is git-ignored).
- **Prompt-injection:** the model receives only structured risk signals and
  numbers — no free-text account fields — so there is no `account_name` injection
  surface in the prompt path.

## Known failure modes

- Inactivity can look risky when it is seasonal/expected.
- Open tickets may reflect active implementation, not dissatisfaction.
- A `canceled` flag captures *that* a customer is leaving, never *why*.
- The LLM can write a plausible-but-imperfect summary even on a correct flag
  (mitigated by output validation, deterministic fallback, and the eval).

## Human oversight & monitoring

- A Customer Success human reviews every briefing and decides any action.
- Each run logs inputs, the flag decision, and whether each summary fell back to
  the deterministic path; the per-run **fallback rate** is the key health metric.
  A fallback also posts an alert to a separate Slack ops webhook
  (`SLACK_ALERT_WEBHOOK_URL`), so an LLM outage is noticed, not buried.
- Summary quality is governed by `evals/` (deterministic checks + LLM-as-judge);
  prompt changes must clear the eval gate before merge.
