# Input Data Contract

The weekly CSV export is the system's only input. This is the authoritative
schema; `src/ingestion/csv_loader.py` enforces it (required-column check +
per-row parsing), and the sample lives in
[`../sample_data/sample_accounts.csv`](../sample_data/sample_accounts.csv).

## Schema (9 fields, all required)

| Field | Type | Allowed / range | Role | Notes |
|---|---|---|---|---|
| `account_id` | string | non-empty | identifier | not sent to the LLM |
| `account_name` | string | non-empty | display + narrative | sanitized before prompting (injection surface) |
| `mrr` | number | ≥ 0 (USD/month) | **priority**, not risk | shown in Slack; never scored |
| `plan_name` | string | e.g. Starter / Growth / Enterprise | context | not scored |
| `subscription_status` | enum | `active` \| `past_due` \| `canceled` \| `expired` | risk signal | see lifecycle note |
| `failed_payment_count_last_30d` | integer | ≥ 0 | risk signal | billing distress severity |
| `days_since_last_login` | integer | ≥ 0 | risk signal | engagement |
| `open_support_tickets` | integer | ≥ 0 | risk signal | support burden |
| `contract_end_date` | date | ISO `YYYY-MM-DD` | risk signal | renewal proximity vs. today |

## `subscription_status` lifecycle (Recurly semantics)

Modeled on Recurly's real states — see
[`adr/0005-subscription-status-modeling.md`](adr/0005-subscription-status-modeling.md):

- `active` — baseline.
- `past_due` — in active dunning.
- `canceled` — set to not renew but **still active** → the top save target.
- `expired` — already churned → **filtered out before scoring**; never appears in
  the briefing.

## Validation & failure behavior

- **Missing a required column** → the load fails fast with a clear `ValueError`
  (a structural problem with the whole file).
- **A malformed row** (bad type, unknown status) → that row is **logged and
  skipped**; the batch continues (CLAUDE.md §4).
- **`expired` rows** → excluded as already-churned, logged at info.

## Out of scope (deliberately not in the contract)

No historical churn outcomes, CRM data, CS notes, product-adoption telemetry, or
sentiment. These would materially improve risk and prose quality and are the first
enrichment targets for production (see [`system_card.md`](system_card.md)).
