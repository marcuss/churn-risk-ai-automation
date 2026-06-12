Generate pytest tests for edge cases in a deterministic churn risk system.

Focus on unusual but possible account states.

Examples:

- cancelled but recently active
- high engagement but multiple failed payments
- inactive but high-value enterprise account
- renewal approaching with otherwise healthy signals
- support-heavy but active customer

Requirements:

- prioritize realistic SaaS scenarios
- avoid impossible states
- validate deterministic behavior
- include rationale comments in tests