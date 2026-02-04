# API Reference

## Health
- `GET /api/v1/health`

## Auth (v1 stub)
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/change-password`

## Scheduling (Phase 2)
- `POST /api/v1/medications/{med_id}/calculate-schedule`
- `GET /api/v1/patients/{id}/monitoring-timeline`

## Webhooks
- `POST /api/v1/webhooks/medication`
- `POST /api/v1/webhooks/monitoring-event`

## Worklist/Tasks
- `GET /api/v1/worklist`
- `POST /api/v1/tasks/{task_id}/acknowledge`
- `POST /api/v1/tasks/{task_id}/complete`
- `POST /api/v1/tasks/{task_id}/waive`

## Admin
- `GET /api/v1/admin/ruleset`
- `PUT /api/v1/admin/ruleset`
- `GET /api/v1/admin/config`
- `PUT /api/v1/admin/config`

## Audit
- `GET /api/v1/audit`
