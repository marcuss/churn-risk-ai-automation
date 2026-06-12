# Risk Strategy

How the system decides which accounts are "at risk." Risk qualification is
**deterministic** — the LLM plays no part in it (it only writes the summary
prose). This document explains the model and, more importantly, *why* it is
shaped this way.

## Goal

Reproduce the judgment of a thoughtful RevOps analyst scanning the Monday CSV:
surface accounts Customer Success can still **save**, ranked so the most urgent
and impactful land first — and stay quiet on noise.

## Modeling `subscription_status` (the decision that matters most)

The CSV names a `subscription_status` field but never defines its values, so I
modeled it on **Recurly's actual subscription lifecycle** rather than inventing
a generic `active / past_due / cancelled` enum. The non-obvious consequence:

- **`canceled` is not "already churned."** In Recurly it means *set to not renew
  at period end, but still active and paying through `contract_end_date`*. That
  makes it the **single most actionable** state for CS — the customer has
  signaled intent to leave and there is a hard deadline. I weight it highest
  (+10, auto-flags) and the summary frames it as a time-boxed save, not a lost
  cause.
- **`expired` accounts are excluded before scoring.** They have already churned;
  a churn-*risk* briefing is about accounts you can still influence. Including
  them would pad the report with un-actionable rows. (The sample CSV contains one
  `expired` account specifically to demonstrate it is filtered out.)
- **`past_due` is kept distinct from `failed_payment_count_last_30d`.** I
  considered collapsing the two, but they answer different questions: status =
  *are they currently in dunning?*, the count = *how severe is the failure
  history?* State and severity are complementary, so both contribute.

## Scoring model

Risk score = sum of signal points. **Flag when score ≥ 6.**

| Signal | Condition | Points |
|---|---|---|
| Subscription status | `canceled` | **+10** |
| | `past_due` | +5 |
| Failed payments (30d) | ≥ 2 / 1 | +4 / +2 |
| Inactivity (days since login) | >60 / 31–60 / 15–30 | +5 / +3 / +1 |
| Support tickets (open) | >5 / 3–5 | +3 / +2 |
| Renewal proximity | <14d / 14–29d | +3 / +2 |

`active` = 0 from status; `expired` = excluded; anything below a listed band = 0.

## Why threshold 6, and the "compounding" philosophy

Six is roughly *two real problems, or one severe one*. A lone moderate signal —
2 failed payments (4) or 45 idle days (3) — deliberately does **not** flag:
dunning frequently self-resolves on card re-auth, and single-signal alerts train
CS to ignore the channel. The system flags when risk **compounds** across
billing, engagement, support, and renewal. The exception is `canceled`, which
auto-flags because signaled non-renewal *is* risk.

The threshold is the main tuning knob. In production I would calibrate it against
historical churn outcomes rather than intuition (see README → production notes).

## Risk ≠ Priority

MRR and plan do **not** enter the risk score — risk is *churn likelihood*, and a
small account can be just as likely to churn as a large one. Business impact
enters only at **ordering**: the Slack briefing sorts by **risk severity first,
MRR as the tiebreak**, and shows MRR on every line. So the report can rank a
severely-at-risk \$1.9k account above a moderately-at-risk \$5.2k one, while still
letting CS see size at a glance. Conflating the two — "big account = high risk" —
is the failure mode this split exists to prevent.

## Risk tiers (Slack display)

The briefing prefixes each account with a deterministic triage color, mapped
straight from the score so the tier is always consistent with qualification — the
LLM never sets it (that would let a probabilistic model convey risk *level*, which
this whole design forbids):

| Tier | Score | Meaning |
|---|---|---|
| 🔴 High | ≥ 12 | multiple strong signals, or signaled non-renewal |
| 🟠 Medium | 8–11 | a serious signal, or several moderate ones |
| 🟡 Elevated | 6–7 | just over the flag threshold |

The tiers are a display aid only: they don't change who is flagged (still score
≥ 6), and like the threshold they're tunable.

## State space & testing

Five risk-driving fields with 3·3·4·3·3 = **324** combinations, but they collapse
into ~8–12 behavioral archetypes (healthy, billing, engagement, support, renewal,
compound, severe, canceled-save, borderline). Tests target the archetypes and the
threshold boundaries — not the 324 states or the internal arithmetic. The state
space is small enough to govern explicitly, which is the whole argument for
staying deterministic. Test specs live in [`prompts/testing/`](../prompts/testing/).
