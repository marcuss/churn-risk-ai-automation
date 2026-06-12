# System Flow

End-to-end flow of the weekly churn-risk briefing. Deterministic steps are the
spine; the LLM only writes prose, and any failure degrades to a deterministic
fallback (with an ops alert).

```mermaid
flowchart TD
    CSV["CSV export — path or stdin"] --> ING["Ingestion · csv_loader"]
    ING -->|drop expired| RISK["Deterministic risk scoring · src/risk"]
    RISK -->|below threshold| SKIP["Not flagged — omitted"]
    RISK -->|score 6 or more| LLM["LLM summary · src/ai/llm_client"]
    LLM -->|success| FMT["Slack formatter · tier + name + MRR + prose"]
    LLM -->|retry then still failing| FB["Deterministic fallback · src/ai/fallback_summary"]
    FB --> FMT
    FMT --> SLACK["Slack webhook · Customer Success channel"]
    FB -.->|fallback used| ALERT["Ops alert webhook · SLACK_ALERT_WEBHOOK_URL"]
```
