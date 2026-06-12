Generate pytest tests for threshold boundary behavior in a deterministic churn risk system.

Focus only on boundary conditions.

Important thresholds:

- inactivity: 14, 30, 60 days
- failed payments: 0, 1, 2+
- support tickets: 2, 3, 5+
- renewal windows: 14 and 30 days
- risk threshold for flagging

Requirements:

- test both sides of thresholds
- avoid duplicate scenarios
- assert expected classification behavior
- prefer minimal account fixtures

Example:

30 days inactivity should behave differently than 31 days if thresholds differ.