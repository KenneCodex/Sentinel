# Sentinel Automation Features

This document describes the automation features implemented for the Sentinel project.

## Overview

Sentinel now includes comprehensive automation capabilities focused on:
1. CI/CD pipelines for shell script debugging
2. AI-driven task prioritization
3. Standardized PR workflows
4. Audit logging for all automation activities
5. Multi-host deployment automation with CLI validation

## Features

### 1. Shell Script CI/CD Pipeline

**Location:** `.github/workflows/shell-script-ci.yml`

Automated CI pipeline that runs on every push or PR affecting shell scripts:

- **ShellCheck Linting**: Validates shell scripts for syntax and best practices
- **Debug Mode Execution**: Runs scripts with enhanced debugging (`bash -x`)
- **Syntax Validation**: Checks all `.sh` files for syntax errors
- **Best Practices Audit**: Validates shebang presence, `set -e` usage, etc.

**Triggers:**
- Push to `main` or `develop` branches (affecting `*.sh` files)
- Pull requests to `main` or `develop` branches (affecting `*.sh` files)
- Manual workflow dispatch

### 2. AI-Driven Task Prioritization

**Location:** `ai-task-prioritization.sh`

Intelligent task prioritization system using a weighted scoring algorithm:

**Factors:**
- **Urgency** (30% weight): How time-sensitive is the task?
- **Impact** (25% weight): Potential impact on system/users
- **Effort** (20% weight): Required effort to complete (inverse scoring)
- **Dependencies** (15% weight): Number of blocking dependencies
- **Risk** (10% weight): Risk if task is delayed

**Priority Levels:**
- **CRITICAL** (0.75-1.00): SLA 4 hours
- **HIGH** (0.60-0.74): SLA 24 hours
- **MEDIUM** (0.40-0.59): SLA 72 hours
- **LOW** (0.00-0.39): SLA 1 week

**Usage:**
```bash
./ai-task-prioritization.sh <task_id> <task_name> <urgency> <impact> <effort> <dependencies> <risk>

# Example:
./ai-task-prioritization.sh TASK-001 "Fix critical bug" 9 10 3 1 9

# Summarize the most recent task prioritization records (default 100)
./ai-task-prioritization.sh --summary 100
```

**GitHub Workflow:** `.github/workflows/ai-task-prioritization.yml`
- Automatically prioritizes issues based on labels
- Manual workflow dispatch for ad-hoc prioritization
- Creates audit logs for all prioritization activities

### 3. Pull Request Template

**Location:** `.github/PULL_REQUEST_TEMPLATE.md`

Standardized PR format includes:
- AI Provenance & Metadata tracking
- Detailed description and motivation
- Type of change classification
- Testing checklist and results
- Security considerations
- Deployment and rollback plans
- AI audit trail references
- Comprehensive reviewer guidelines

### 4. Audit Logging System

**Location:** `.audit-logs/`

Centralized audit trail for all automation activities:

**Log Types:**
- `task-prioritization-*.json`: Task priority scoring records
- `deployment-*.json`: Deployment execution logs
- `shell-validation-*.json`: Script validation results
- `automation-*.json`: General automation activity logs
- `cli-validation-*.json`: CLI validation results

**Features:**
- Standardized JSON schema for all logs
- Timestamp-based naming convention
- Retention policy documentation
- 90-day default retention (1 year for critical logs)

**Configuration:**
- `.gitignore` configured to exclude most logs
- `priority-config.json` preserved in version control
- Documentation in `.audit-logs/README.md`

### 5. Multi-Host Deployment Automation

**Location:** `multi-host-deployment.sh`

Automated deployment to multiple hosts with validation:

**Commands:**
```bash
# Validate prerequisites
./multi-host-deployment.sh validate

# Generate deployment configuration
./multi-host-deployment.sh config

# Deploy to environment
./multi-host-deployment.sh deploy <environment>
```

**Environments:**
- `production`: Multi-host production deployment
- `staging`: Staging environment testing
- `development`: Local development deployment

**Features:**
- Pre-deployment validation
- Parallel deployment capability
- Automatic backup creation
- Post-deployment validation
- Rollback support (keeps 3 versions)
- Comprehensive audit logging

**Deployment Configuration:** `deployment-config.json`
- Environment-specific host definitions
- Pre/post deployment commands
- Validation commands
- Rollback settings
- Notification webhooks (optional)

**GitHub Workflow:** `.github/workflows/deployment-automation.yml`
- Manual workflow dispatch with environment selection
- Dry-run mode for validation
- Artifact upload for deployment logs

### 6. CLI Validation

**Location:** `cli-validation.sh`

Comprehensive validation of CLI environment and tools:

**Validation Categories:**
- Shell environment (bash version, environment variables)
- Required CLI tools (git, curl, bash, etc.)
- Optional development tools (python, node, docker, etc.)
- File permissions (script executability)
- Directory structure
- Configuration files
- Git configuration
- Shell script syntax

**Usage:**
```bash
./cli-validation.sh
```

**Output:**
- Color-coded validation results
- Detailed summary with pass/fail counts
- Audit log generation
- Exit code 0 for success, 1 for failures

## Integration with Existing Systems

### Git Workflow
All scripts integrate with Git:
- Automatic commit SHA and branch detection
- Git user configuration validation
- Repository status checking

### GitHub Actions
Workflows integrate seamlessly:
- Artifact upload for all logs and results
- Environment-based deployments
- Manual and automated triggers

### Security
Security considerations:
- Audit logs for traceability
- Validation of credentials handling
- Pre-deployment security checks
- Input validation in all scripts

## Configuration Files

### Priority Configuration
**File:** `.audit-logs/priority-config.json`

Defines the AI task prioritization model parameters:
- Weight distribution across factors
- Priority level thresholds
- SLA definitions
- Factor descriptions and scales

### Deployment Configuration
**File:** `deployment-config.json` (generated)

Environment-specific deployment settings:
- Host definitions (hostname, user, port, path)
- Pre/post deployment commands
- Validation commands
- Rollback configuration
- Notification settings

### .gitignore
**File:** `.gitignore`

Configured to exclude:
- Generated configuration files (deployment-config.json)
- Most audit logs (preserves priority-config.json)
- Temporary files
- OS and IDE files
- Build artifacts

## Best Practices

### Script Development
1. Always include shebang (`#!/bin/bash`)
2. Use `set -e` for error handling
3. Make scripts executable (`chmod +x`)
4. Test with `bash -n` for syntax
5. Run through shellcheck for linting

### Task Prioritization
1. Be objective when scoring factors
2. Review priority-config.json periodically
3. Adjust weights based on team needs
4. Document priority decisions in audit logs

### Deployment
1. Always run validation before deployment
2. Use dry-run mode first
3. Test in development/staging before production
4. Keep deployment configurations in sync
5. Review audit logs after each deployment

### Audit Logs
1. Review logs regularly
2. Archive logs older than retention period
3. Redact sensitive information before sharing
4. Use logs for troubleshooting and optimization

## Troubleshooting

### Common Issues

**Script not executable:**
```bash
chmod +x script-name.sh
```

**ShellCheck not installed:**
```bash
sudo apt-get install shellcheck
# or
brew install shellcheck
```

**Deployment prerequisites failed:**
```bash
./multi-host-deployment.sh validate
# Install missing tools as indicated
```

**Priority calculation errors:**
Ensure all parameters are numeric and within valid ranges:
- urgency, impact, effort, risk: 1-10
- dependencies: 0-5

## Future Enhancements

Potential improvements:
- Integration with issue tracking systems (Jira, GitHub Issues)
- ML-based priority prediction
- Automated rollback on deployment failures
- Real-time monitoring and alerting
- Enhanced security scanning
- Performance metrics collection
- Multi-cloud deployment support

## Contributing

When contributing automation features:
1. Follow the PR template
2. Add audit logging for new automation
3. Update this documentation
4. Include tests/validation
5. Document configuration options
6. Consider security implications

## License

See repository LICENSE file.

## Support

For issues or questions about automation features:
1. Check troubleshooting section
2. Review audit logs for errors
3. Consult workflow run logs in GitHub Actions
4. Create an issue with relevant logs and context
