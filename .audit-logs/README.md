# AI Automation Audit Logs

This directory contains audit trails for all AI automation activities in the Sentinel project.

## Directory Structure

```
.audit-logs/
├── README.md                           # This file
├── .gitkeep                            # Ensures directory is preserved in git
├── priority-config.json                # AI task prioritization configuration
├── task-prioritization-*.json          # Task prioritization audit logs
├── deployment-*.json                   # Deployment automation audit logs
├── shell-validation-*.json             # Shell script validation logs
└── automation-*.json                   # General automation audit logs
```

## Log File Naming Convention

All audit log files follow this naming convention:
```
<log-type>-<YYYYMMDD>-<HHMMSS>.json
```

Examples:
- `task-prioritization-20260123-141530.json`
- `deployment-20260123-142000.json`
- `shell-validation-20260123-143000.json`

## Audit Log Schema

### General Automation Log
```json
{
  "timestamp": "ISO 8601 timestamp",
  "workflow": "workflow name or identifier",
  "action": "action performed",
  "status": "completed|failed|in-progress",
  "details": {
    "key": "value"
  },
  "metadata": {
    "runner": "runner OS",
    "trigger": "manual|scheduled|webhook",
    "initiator": "user or system"
  }
}
```

### Task Prioritization Log
```json
{
  "task_id": "unique task identifier",
  "task_name": "task description",
  "timestamp": "ISO 8601 timestamp",
  "priority_score": 0.75,
  "priority_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "factors": {
    "urgency": 9,
    "impact": 10,
    "effort": 3,
    "dependencies": 1,
    "risk": 9
  },
  "weights": {
    "urgency": 0.30,
    "impact": 0.25,
    "effort": 0.20,
    "dependencies": 0.15,
    "risk": 0.10
  }
}
```

### Deployment Log
```json
{
  "timestamp": "ISO 8601 timestamp",
  "deployment_id": "unique deployment identifier",
  "environment": "production|staging|development",
  "hosts": ["host1", "host2"],
  "status": "success|failed|partial",
  "duration_seconds": 120,
  "changes_deployed": 15,
  "validations_passed": true,
  "rollback_available": true
}
```

## Retention Policy

- Audit logs are retained for 90 days by default
- Critical logs (failures, security events) are retained for 1 year
- Logs can be archived to external storage for long-term retention

## Access and Security

- Audit logs should be treated as sensitive information
- Access should be limited to authorized personnel
- Logs may contain operational details and should not be publicly shared
- When sharing logs externally, ensure sensitive information is redacted

## Compliance

These audit logs support:
- Traceability of all automation activities
- Debugging and troubleshooting
- Performance analysis and optimization
- Security auditing and compliance
- Change management and accountability
