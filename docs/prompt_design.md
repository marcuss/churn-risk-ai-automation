# Prompt Design

## Objective

The objective of the prompting layer is to generate concise, analyst-style churn
risk summaries for Customer Success teams.

The model is **not responsible for determining whether an account is at risk**.
Risk qualification is handled deterministically upstream using explicit business
heuristics — see [`risk_strategy.md`](risk_strategy.md) for the scoring model and
threshold. The LLM (Claude; configurable via `ANTHROPIC_MODEL`) is used only to
transform structured account signals into human-readable summaries that resemble
what a thoughtful RevOps analyst would write.

Target output requirements:

* 2–3 sentences maximum
* concise and professional
* readable in Slack
* useful to Customer Success without modification
* avoid simply restating metrics
* synthesize likely concerns from available signals

---

## Prompting Strategy

The system intentionally separates deterministic business logic from generative
behavior.

### Responsibilities

**Deterministic Layer**

* determines whether an account is at risk
* calculates risk score
* identifies contributing risk signals

**LLM Layer**

* converts structured signals into a concise analyst narrative
* highlights likely churn concerns
* communicates findings in natural language

This separation was intentional to improve consistency, explainability, cost
predictability, and operational reliability. Using an LLM for churn
classification would introduce nondeterministic behavior into a business-critical
workflow and make debugging significantly harder.

---

## Context Window Decisions

A key design decision was intentionally constraining the context window. Rather
than sending the entire CSV row or large amounts of account metadata, only
risk-relevant information is included.

### Included Context

For each flagged account, the model receives only risk signals — never the account
name (the formatter owns that as a heading):

* `subscription_status` — in plain language (e.g. *"Past Due (active dunning)"*,
  *"Canceled (set to not renew; still active)"*)
* `failed_payment_count_last_30d`
* `days_since_last_login`
* `open_support_tickets`
* **renewal expressed relative to today** — e.g. *"in 11 days"* — not the raw
  `contract_end_date`, because the model should not be doing date arithmetic or
  guessing the current date

Plus the **derived risk signals** computed by the risk layer:

* payment instability
* low product engagement
* elevated support burden
* upcoming renewal (time-sensitive)
* pending non-renewal (for `canceled` accounts)

These derived signals help the model synthesize information rather than simply
repeating raw metrics. Raw metrics are still included so the prose can be
*specific and accurate* ("85 days without a login"), while the system prompt
pushes the model toward synthesis over enumeration.

> `expired` accounts never reach the LLM — they are filtered upstream as already
> churned (see [`risk_strategy.md`](risk_strategy.md)). The prompt layer only ever
> sees savable accounts.

### Excluded Context

The following information is intentionally excluded:

* **`account_name`** — the model never needs it: the Slack formatter renders the
  name as a heading above the summary. Withholding it makes restating the name
  *impossible* (no "Acme Corp is in active dunning…" duplicating the heading) and
  removes `account_name` as a prompt-injection surface. The model refers to "the
  account" generically.
* **`account_id`** — an identifier, not useful for narrative generation.
* **Internal risk score** — implementation detail; the raw number may bias the
  prose. The model receives interpreted risk *signals* instead.
* **`mrr` and `plan_name`** — these are **priority/impact, not risk** (see
  *Risk ≠ Priority* in [`risk_strategy.md`](risk_strategy.md)). Feeding them to
  the model invites "this high-value account…" prose that conflates account size
  with churn likelihood. Business impact is handled by the Slack formatter, which
  shows MRR on each line and orders the briefing — it does not belong in the
  risk narrative.
* **Entire CSV dataset** — the model only needs account-local context. Unrelated
  accounts add noise and tokens without improving quality.

### Why constrained context?

More context does not necessarily improve output quality. Constrained context
improves consistency, cost efficiency, prompt reliability, and hallucination
resistance. The goal is not maximum intelligence, but predictable operational
output.

---

## System Prompt

The system prompt establishes tone, constraints, and audience expectations.

```txt
You are a thoughtful Revenue Operations analyst.

You are preparing churn-risk notes for a Customer Success team.

Write concise, professional summaries that explain why an account may be at risk.

Requirements:
- Write 2–3 sentences maximum
- Be concise and readable
- Sound like a thoughtful analyst, not an automated system
- Synthesize risk signals rather than repeating raw metrics
- Mention likely concerns when supported by the data
- Focus only on churn-risk drivers; do not comment on account size, value, or priority
- When an account has signaled non-renewal (canceled), treat it as a time-sensitive
  save opportunity, not a lost account
- Avoid speculation beyond available evidence
- Refer to the account generically (e.g., "the account", "this customer"); never invent or guess a company name
- Write plain prose only — no headings, titles, or labels
- Do not use bullet points
- Do not sound robotic
```

### Why this prompt?

The system prompt anchors four things:

1. **Role** — Revenue Operations analyst
2. **Audience** — Customer Success
3. **Communication style** — concise and operational
4. **Failure prevention** — avoid robotic metric repetition; avoid conflating
   size with risk; treat `canceled` as savable

Early prompt experiments produced outputs that resembled dashboards rather than
analyst notes — e.g. *"Customer has 3 failed payments and 42 inactive days."*
While factually correct, this is not operationally useful. The final prompt
emphasizes synthesis over restatement.

---

## User Prompt

The user prompt contains structured account context, built per account by the
prompt layer. It is intentionally structured rather than conversational, which
yields more predictable outputs, easier debugging, lower variance, and
standardized inputs for production monitoring.

### Example A — billing distress (`past_due`)

```txt
Generate a churn-risk assessment for an at-risk account. Refer to it as "the account".

Subscription Status: Past Due (active dunning)
Failed Payments (last 30d): 2
Days Since Last Login: 9
Open Support Tickets: 1
Renewal: in 126 days

Detected Risk Signals:
- payment instability

Write a concise 2–3 sentence churn-risk summary for Customer Success.
```

> The account has slipped into active dunning with two failed payment attempts in
> the past month, a billing-instability pattern that often precedes involuntary
> churn. Engagement is otherwise healthy and renewal is months away, so the
> immediate priority is getting the payment method corrected before the failures
> compound.

### Example B — signaled non-renewal (`canceled`)

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

---

## Prompt Iteration

### Attempt 1 — Minimal prompt

```txt
Generate a churn risk summary for this customer.
```

**Problem:** the model repeated metrics verbatim, sounded robotic, and lacked
actionable language — e.g. *"Customer has 2 failed payments and has not logged in
for 47 days. There are 5 support tickets open. Contract renewal is approaching."*
Accurate, but reads like a dashboard rather than analyst judgment.

### Attempt 2 — Analyst framing

Framed the model explicitly as *"a thoughtful Revenue Operations analyst."*
Outputs became more concise, readable, and useful; the model began synthesizing
signals instead of enumerating them.

### Attempt 3 — Risk-signal enrichment

Instead of only passing raw metrics, the prompt added interpreted risk signals
(payment instability, low engagement, renewal risk, pending non-renewal). This
reduced metric repetition and improved narrative quality; the model became better
at identifying patterns across signals.

### Attempt 4 — Aligning the prompt with *Risk ≠ Priority*

Two fixes, once the deterministic layer was settled:

* **Removed `mrr` and `plan_name`** from the context. The model had started
  editorializing about account value ("this major enterprise account…"), which
  conflates business impact with churn likelihood. Those belong to the formatter,
  not the risk narrative.
* **Switched renewal from a raw date to a relative window** ("in 11 days"). The
  model has no reliable notion of "today" and produced wrong date math; the risk
  layer now computes the window and passes it in.

### Attempt 5 — Stop sending the account name at all

The formatter already renders the account name as a heading above each summary,
but the model kept opening with it ("Vertex Payments is showing…"), duplicating
the heading. Fighting this with prompt rules was a losing battle — a negative rule
was followed inconsistently, and one phrasing even made the model emit a literal
`## Vertex Payments` line.

The fix was to remove the problem at the source: **stop sending the name to the
model entirely.** It was never needed for the *risk narrative* (it's a label the
formatter owns), so withholding it is consistent with the constrained-context
principle above. The model now refers to "the account", the duplication is
*impossible* rather than discouraged, the prompt is simpler (no rule, no example,
no post-processing guard), and `account_name` is no longer a prompt-injection
surface. The right move was less prompt engineering, not more.

---

## Known Limitation

Even when working correctly, the prompt can only reason over visible account
signals. Examples:

* A customer may reduce usage seasonally, making inactivity look risky when it is
  expected.
* A high-value account may have open support tickets because of active
  implementation work rather than dissatisfaction.
* A `canceled` flag captures *that* the customer signaled non-renewal but never
  *why* — the most important thing CS actually needs.

The prompt lacks broader business context such as historical churn outcomes, CS
notes, CRM opportunity data, and product-adoption trends.

### Production improvements

In production I would enrich the context with historical account behavior,
previous churn outcomes, sentiment from support interactions, CRM metadata, and
renewal-stage information — and add a prompt evaluation dataset to measure summary
consistency and quality over time.

---

## Failure Handling

LLM calls are probabilistic and occasionally fail or return garbage. To prevent
workflow disruption, generation is retried; if it still fails (or returns empty /
implausibly long output), the system falls back to a **deterministic summary**
built from the same detected signals. Example fallback:

> Elevated churn risk detected due to failed payments, reduced engagement, and
> multiple open support tickets. Recommend Customer Success review before the
> upcoming renewal.

This ensures the weekly Slack report is always delivered, even when AI generation
partially fails. The goal of the automation is reliability first, elegance second.
See [`adr/0003-graceful-degradation.md`](adr/0003-graceful-degradation.md).
