# RuleSet Guide

## Location
`backend/rules/ruleset_v1.json`

## Structure
- `version`: ruleset version string
- `effective_from`: date rules are valid from
- `categories`: per-category schedules (STANDARD, SPECIAL_GROUP, HDAT)

Each category defines:
- `baseline`: tests due at start_date
- `weekly`: weekly cadence tests (count + interval_weeks)
- `milestones`: month-based checkpoints
- `annual`: tests repeated yearly after year 1
- Recurring groups (optional):
  - `every_4_6_months` (SPECIAL_GROUP glucose)
  - `every_3_months` (HDAT)
  - `every_6_months` (HDAT ECG)

## Modifying Tests
Example: Add a new test to the 3‑month milestone in STANDARD.

```json
{
  "months": 3,
  "tests": ["Weight/BMI", "Prolactin", "NEW_TEST"]
}
```

## Drug Exceptions
Milestones can specify exceptions for specific drugs:

```json
"exceptions": {
  "chlorpromazine": {"remove_tests": ["Lipids"]}
}
```

## Notes
- `ECG_if_indicated` is resolved by conditional rules.
- Horizon is controlled via `SCHEDULING_HORIZON_YEARS` in config.
