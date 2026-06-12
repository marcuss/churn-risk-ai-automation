You are a senior Python engineer designing behavior-oriented tests for a deterministic churn risk system.

Context:

The system evaluates churn risk using deterministic business rules.

Risk inputs:

1. subscription_status
    - active
    - past_due
    - cancelled

2. failed_payment_count_last_30d
    - 0
    - 1
    - >=2

3. days_since_last_login
    - <=14
    - 15–30
    - 31–60
    - >60

4. open_support_tickets
    - 0–2
    - 3–5
    - >5

5. contract_end_date
    - >30 days
    - 14–30 days
    - <14 days

Constraints:

- Risk qualification is deterministic.
- Tests must validate business behavior.
- Avoid implementation-coupled assertions.
- Avoid testing internal scoring math directly.
- Prefer realistic SaaS account scenarios.
- Use pytest.
- Use readable test names.

Generate tests for these archetypes:

1. healthy account
2. billing instability
3. engagement decline
4. elevated support burden
5. renewal urgency
6. compound moderate signals crossing threshold
7. severe risk account
8. borderline non-risk account

Requirements:

- Return complete pytest test code.
- Use realistic account names.
- Keep tests concise.
- Assert behavioral outcomes only.

Good example:

test_past_due_customer_is_flagged()

Bad example:

test_adds_three_points_for_inactivity()