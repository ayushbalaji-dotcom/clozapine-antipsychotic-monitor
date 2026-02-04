# Scheduling Engine Logic

## Flow
1. Determine category: HDAT flag → HDAT, special group drugs → SPECIAL_GROUP, else STANDARD
2. Load rules from `backend/rules/ruleset_v1.json`
3. Build milestones: baseline, weekly, month-based, and recurring schedules
4. Generate MonitoringTask objects
5. Apply conditional rules:
- ECG indication
- Clozapine FBC overlay
- HDAT hydration vigilance flag
6. Remove tasks after stop_date

## ECG Indication
ECG required at baseline and annually if any of:
- Drug in SPC list (haloperidol, pimozide, sertindole)
- CV risk present
- Family history of CVD/sudden collapse
- Inpatient admission
- Manual ECG-indicated flag

## Clozapine FBC
Overrides base FBC schedule:
- Weekly x 18 weeks
- 2-weekly x 34 weeks
- 4-weekly thereafter (to scheduling horizon)

## Task Windows
Events match tasks within ±`TASK_WINDOW_DAYS` (default 14 days).

## Horizon
Schedules project out to `SCHEDULING_HORIZON_YEARS` (default 5 years).

## Special Group Glucose (4–6 Months)
Implemented as a 5‑month interval starting 16 months after start_date (configurable in code).

## Stop Date
Tasks with due_date after `stop_date` are excluded.
