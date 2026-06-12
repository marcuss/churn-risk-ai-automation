# Expected Output

The format contract for the weekly Slack briefing, plus reference examples. This
doubles as the human-readable spec the eval scores against, and the reference for
the submitted Slack screenshot.

## Format contract

A briefing is one Slack message with:

1. A header: `🚨 Weekly Churn Risk Report`.
2. A count: `N account(s) flagged for review.`
3. One block per flagged account, **ordered by priority** (risk severity, then MRR
   as tiebreak), each with:
   - `{tier} *Account Name* · $X.Xk MRR` — a deterministic triage color
     (🔴/🟠/🟡 from the score) + name + MRR. MRR is shown for impact; it does
     **not** affect risk.
   - the 2–3 sentence analyst summary (which refers to "the account", never the
     name — the name is the heading)
4. Empty state (no flags): `✅ No accounts flagged for churn risk this week.`

The payload carries Block Kit `blocks` plus a plain-text `text` fallback. The
entry is deliberately minimal — the brief warns against a "data dump", so nothing
competes with the summary.

## Reference — deterministic fallback (no API key)

Verbatim from `python -m app.main --csv sample_data/sample_accounts.csv` with no
`ANTHROPIC_API_KEY` set (12 accounts loaded, `expired` excluded, 6 flagged):

```text
🚨 Weekly Churn Risk Report

6 account(s) flagged for review.

🔴 *Vertex Payments* · $6.1k MRR
Elevated churn risk driven by payment instability, low product engagement, elevated support burden, and upcoming renewal (time-sensitive). Recommend Customer Success review ahead of the upcoming renewal.

🔴 *Lumen Retail* · $4.5k MRR
Elevated churn risk driven by pending non-renewal, and upcoming renewal (time-sensitive). Recommend Customer Success review ahead of the upcoming renewal.

🟠 *Cobalt Robotics* · $4.8k MRR
Elevated churn risk driven by payment instability. Recommend Customer Success review ahead of the upcoming renewal.
```

## Reference — LLM summaries (Claude)

The same flags once Claude writes them — richer synthesis, "the account" phrasing,
no restated name. This is what the eval grades:

```text
🔴 *Vertex Payments* · $6.1k MRR
Three consecutive failed payments have placed this account in active dunning, and with renewal just eight days out, the billing situation requires immediate attention. Compounding the concern, the account hasn't logged in for nearly three months, suggesting the product may no longer be in active use — which could be driving both the payment hesitation and six unresolved support tickets. CS should prioritize outreach now to address the billing blockers and understand what's behind the disengagement.

🔴 *Lumen Retail* · $4.5k MRR
This account has formally signaled non-renewal with only 11 days until the renewal date, making re-engagement highly time-sensitive. Two open support tickets may point to unresolved friction that influenced the cancellation decision, and a 16-day login gap suggests the customer may have already begun disengaging. A prompt outreach to address the open issues and understand the cancellation rationale could still create a path to recovery.
```

The difference — synthesis and actionable framing vs. a templated signal list — is
exactly what the rubric in [`../evals/rubric.md`](../evals/rubric.md) measures.
