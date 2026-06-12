Generate pytest tests for fallback summary generation behavior.

Context:

The system uses an LLM to generate churn summaries.

If LLM generation fails:

1. retry occurs
2. fallback summary is generated
3. processing continues

Requirements:

- test timeout handling
- test exception handling
- test non-empty fallback output
- test key signals appear in fallback summary
- avoid over-mocking
- use pytest