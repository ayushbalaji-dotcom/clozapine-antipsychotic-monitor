# NHS Antipsychotic Monitoring Active Tracker (v1)

## Purpose
A secure, auditable tracker that identifies patients on antipsychotics and flags overdue monitoring tests. This is a safety net for missed monitoring, **not** clinical decision support.

## Scope
**In scope**
- Due/overdue monitoring tracking for antipsychotic therapies
- Auditable task workflow (acknowledge/complete/waive)
- Pseudonymised operational data

**Out of scope**
- Clinical interpretation of results
- Prescribing or medication changes
- Decision support or alerts based on result values

## Deployment Model (v1)
- Local/offline execution on a laptop or Trust VM
- No outbound network connections required
- Cloud-neutral architecture (on‑prem VM or Trust private cloud)
- HSCN/N3 and cloud mapping deferred to CITO pathway

## Retention (v1 default)
- **Default retention**: 90 days (configurable)
- Longer retention (e.g., 7 years) requires formal IG decision + DPIA

## Integration
- Webhook ingestion for Medication/Monitoring events
- FHIR R4 adapter interface stubbed (MedicationRequest/MedicationStatement/Observation/Patient)
- No EPR-specific hardcoding (Epic/Cerner/Lorenzo‑agnostic)

## Auth (v1)
- Local dev-only login: `admin / ChangeMe_123!`
- Forced password change on first login
- OIDC config placeholders for Azure AD (Entra ID)

## Quick Start (local dev)
1. Create `.env` from `.env.example` and set secrets
2. Start Postgres via Docker Compose
3. Run the API: `uvicorn backend.main:app --reload`
4. Run the UI: `streamlit run frontend_streamlit/app.py`

## Directory Layout
Core code is under `backend/`. Streamlit UI lives in `frontend_streamlit/`.

## Clinical Rules
Monitoring schedules are defined in `backend/rules/ruleset_v1.json` based on the Psychotropic Monitoring Guide.

## Notes
- No patient-identifiable data in logs
- Field-level encryption for NHS number/MRN
- Audit trail for all sensitive actions

## Phase 2 Status
- Scheduling engine implemented (ruleset-driven)
- Conditional logic: ECG indication, clozapine FBC, HDAT hydration vigilance
- Task generator and lifecycle updates
- Core scheduling tests added
- Daily status job available: `python -m backend.jobs.task_updater` (schedule via cron)
