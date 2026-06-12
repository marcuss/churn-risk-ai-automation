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
   - `*Account Name* · $X.Xk MRR` (MRR shown for impact; it does **not** affect risk)
   - the 2–3 sentence summary
4. Empty state (no flags): `✅ No accounts flagged for churn risk this week.`

The payload carries Block Kit `blocks` plus a plain-text `text` fallback.

## Reference — deterministic fallback (no API key)

Verbatim from `python -m app.main --csv sample_data/sample_accounts.csv` with no
`ANTHROPIC_API_KEY` set (12 accounts loaded, `expired` excluded, 6 flagged):

```text
🚨 Weekly Churn Risk Report

6 account(s) flagged for review.

*Vertex Payments* · $6.1k MRR
Elevated churn risk for Vertex Payments driven by payment instability, low product engagement, elevated support burden, and upcoming renewal (time-sensitive). Recommend Customer Success review ahead of the upcoming renewal.

*Lumen Retail* · $4.5k MRR
Elevated churn risk for Lumen Retail driven by pending non-renewal, and upcoming renewal (time-sensitive). Recommend Customer Success review ahead of the upcoming renewal.

*Cobalt Robotics* · $4.8k MRR
Elevated churn risk for Cobalt Robotics driven by payment instability. Recommend Customer Success review ahead of the upcoming renewal.
```

## Reference — LLM summaries (illustrative)

What the same flags read like once Claude writes them (richer synthesis; this is
what the eval grades):

```text
*Vertex Payments* · $6.1k MRR
Vertex is in active dunning with repeated payment failures and has gone roughly
85 days without a login, just as its renewal lands inside two weeks. That
combination points to serious involuntary-churn risk — Customer Success should
reach out ahead of the contract date.

*Lumen Retail* · $4.5k MRR
Lumen has signaled it won't renew and its contract ends in about 11 days, yet the
account is still active and lightly engaged. This is a narrow, time-boxed save
opportunity; a renewal conversation this week is warranted.
```

The difference — synthesis and actionable framing vs. a templated signal list — is
exactly what the rubric in [`../evals/rubric.md`](../evals/rubric.md) measures.
