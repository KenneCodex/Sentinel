# Sentinel

SentinelAi - Advanced AI automation and monitoring platform

## Features

- 🤖 AI-driven task prioritization
- 🚀 Multi-host deployment automation
- 🔍 Comprehensive shell script debugging and validation
- 📊 Automated audit logging and compliance tracking
- ✅ CLI validation and environment checking
- 📝 Standardized pull request workflows
- 🔔 Scheduled routine source checks and notification receipts

## Quick Start

### Running Automated Validations

```bash
# Validate your CLI environment
./cli-validation.sh

# Prioritize a task
./ai-task-prioritization.sh TASK-001 "Task description" 9 10 3 1 9

# Summarize the last 100 prioritized tasks
./ai-task-prioritization.sh --summary 100

# Validate deployment prerequisites
./multi-host-deployment.sh validate
```

### Running the Python Test Suite

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests -q
```

The same suite runs in CI as part of the `bughunt` routine in the **Sentinel Scheduled Routines** workflow.

### Running Scheduled Routine Checks

Dispatch the **Sentinel Scheduled Routines** workflow from GitHub Actions and select `all`, `system-health`, `issue-triage`, or `bughunt`. Every run writes a job-summary receipt. Configure the optional `SENTINEL_NOTIFICATION_WEBHOOK` Actions secret for Slack-compatible delivery.

## Documentation

- [**Automation Features**](AUTOMATION.md) - Comprehensive guide to all automation capabilities
- [**Automation Routines**](docs/automation-routines.md) - Canonical source, health-state, and notification contract
- [**Bug Finder and Fixer Playbook**](docs/bughunt-routine-playbook.md) - Step-by-step method for the bug-hunt routine, with a worked example
- [**Copilot Recommendations**](COPILOT_RECOMMENDATIONS.md) - AI integration strategies
- [**Pull Request Template**](.github/PULL_REQUEST_TEMPLATE.md) - Standardized PR format
- [**Audit Logs**](.audit-logs/README.md) - Audit logging documentation
- [**Game Starter Mapping**](docs/game_starter_mapping.md) - Inventory of reusable repo assets and a minimal game-project rollout plan
- [**Dormant Components Audit**](docs/dormant-components-audit.md) - Inventory of unreached components and their disposition

## CI/CD Workflows

This project includes GitHub Actions workflows for:
- Shell script CI/CD with debugging
- AI-driven task prioritization
- Multi-host deployment automation
- Scheduled source preflight, issue triage, system health, bughunt validation, and notification receipts

See `.github/workflows/` for workflow definitions.

## Contributing

Please use the pull request template when submitting changes. All automation activities are logged to `.audit-logs/` for traceability.

## License

See LICENSE file for details.
