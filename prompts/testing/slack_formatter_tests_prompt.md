Generate pytest tests for Slack report formatting.

Requirements:

Validate:

- report title exists
- account names appear
- summaries appear
- formatting remains readable
- empty state behavior
- multiple account formatting

Avoid brittle string matching.

Prefer behavior-oriented assertions.