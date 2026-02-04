# Data Flow

## Sources
- EPR via CSV export (medications and monitoring events)
- Manual task actions in UI

## Transformations
- Identifiers stripped/blocked in anonymised mode
- Pseudonymised display identifiers (not fully anonymised)

## Destinations
- PostgreSQL (tasks, events, audit)
- Optional audit export sink (JSON lines)

## DPIA Starter Notes
- Lawful basis: healthcare delivery (GDPR Art 9(2)(h))
- Purpose: prevent missed monitoring
- Retention: default 90 days (configurable)
