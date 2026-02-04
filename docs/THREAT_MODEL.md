# Threat Model

## Assets
- Pseudonymised patient references (identifiers disabled by default)
- Medication orders
- Monitoring events
- Audit logs

## Threats
- Unauthorized access
- Data leakage via logs
- Availability attacks

## Mitigations
- RBAC and least privilege
- Identifiers not stored by default (ALLOW_IDENTIFIERS=false)
- Strict log redaction
- Audit trail
- Rate limiting (Phase 3)

## Residual Risks
- Misconfiguration of secrets
- Delayed OIDC integration
