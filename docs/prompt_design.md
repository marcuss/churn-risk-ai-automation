# Prompt Design

How the LLM layer turns risk signals into analyst-style summaries. The model
**never decides risk** — qualification is deterministic (see
[`risk_strategy.md`](risk_strategy.md) and ADRs [0001](adr/0001-deterministic-risk-scoring.md)/[0002](adr/0002-llm-only-for-summarization.md)).
The LLM (Claude, configurable via `ANTHROPIC_MODEL`) only writes the 2–3 sentence
prose: concise, readable in Slack, usable by Customer Success without edits, and
**synthesizing** signals rather than restating metrics.

## Context window — what goes in, and why

Deliberately constrained to account-local, risk-relevant fields — never the whole
CSV (more context adds noise, cost, and hallucination risk without improving
quality).

**Sent** (per flagged account):

- `subscription_status` in plain language (e.g. *"Past Due (active dunning)"*)
- `failed_payment_count_last_30d`, `days_since_last_login`, `open_support_tickets`
- **renewal as a relative window** ("in 11 days") — not the raw date; the model has
  no reliable notion of "today" and gets date math wrong, so the risk layer computes it
- the **derived signals** (payment instability, low engagement, support burden,
  upcoming renewal, pending non-renewal) — these push synthesis over enumeration,
  while the raw metrics keep the prose specific ("85 days without a login")

**Deliberately withheld:**

- **`account_name`** — the formatter owns it as a heading; withholding it makes
  restating the name impossible *and* removes a prompt-injection surface (see
  Attempt 5). The model refers to "the account".
- **the internal risk score** — an implementation detail that would bias the prose
- **`mrr` / `plan_name`** — these are *priority, not risk*; sending them invites
  "this high-value account…" prose that conflates size with churn likelihood
- **`account_id`** and **other accounts** — useless for a single-account narrative
- **`expired` accounts** never reach the LLM at all (filtered upstream as churned)

## System prompt

The versioned source is [`../prompts/system_prompt.txt`](../prompts/system_prompt.txt)
(code loads it; no copy here to drift). It anchors role (RevOps analyst), audience
(Customer Success), style (concise, operational), and the failure modes to avoid:
metric-dumping, conflating size with risk, and treating `canceled` as lost.

## User prompt

Built per account from
[`../prompts/risk_summary_prompt.txt`](../prompts/risk_summary_prompt.txt) —
structured (not conversational) for predictable, monitorable output. A filled
`canceled` save case and its output:

```txt
Generate a churn-risk assessment for an at-risk account. Refer to it as "the account".

Subscription Status: Canceled (set to not renew; still active)
Failed Payments (last 30d): 0
Days Since Last Login: 16
Open Support Tickets: 2
Renewal: in 11 days

Detected Risk Signals:
- pending non-renewal
- upcoming renewal (time-sensitive)

Write a concise 2–3 sentence churn-risk summary for Customer Success.
```

> The account has signaled it will not renew, and the contract ends in just 11
> days — but it is still active, leaving a narrow window to intervene. Engagement
> has been light rather than absent, so a save is still realistic if Customer
> Success reaches out this week to understand the cancellation reason.

## Iteration — what broke, what changed

1. **Minimal prompt** ("summarize this customer") → metric-dumping and robotic:
   *"Customer has 2 failed payments and 47 inactive days…"*. Reads like a dashboard.
2. **Analyst framing** ("a thoughtful RevOps analyst") → more concise; began
   synthesizing instead of enumerating.
3. **Derived signals** added (payment instability, etc.) → less metric repetition,
   better pattern-spotting.
4. **Risk ≠ Priority alignment** → removed `mrr`/`plan_name` (the model was
   editorializing about account value) and switched renewal to a relative window
   (the model got date math wrong).
5. **Stopped sending the account name** → the model kept opening with it,
   duplicating the heading; a negative rule was followed inconsistently (one phrasing
   even produced a literal `## Vertex Payments`). Removing the name from context
   killed the problem at the source — simpler prompt, no post-processing guard, no
   injection surface. *The right move was less prompt engineering, not more.*

## One thing it gets wrong (even when it works)

The model only sees the visible signals, never the *why*. A `canceled` flag shows
*that* a customer is leaving but not the reason CS most needs; a seasonal lull looks
like risky inactivity; support tickets may reflect active implementation, not
dissatisfaction. **Production fix:** enrich context with historical churn outcomes,
CS notes, CRM/renewal-stage data, and support sentiment — and gate prompt changes on
the eval ([`../evals/rubric.md`](../evals/rubric.md)) so quality is measured, not
assumed.

## Failure handling

On unusable output (empty / overlong) the prompt falls back to a **deterministic
summary** from the same signals — full retry/fallback flow in
[ADR 0003](adr/0003-graceful-degradation.md).
