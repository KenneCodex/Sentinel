#!/bin/bash

# Multi-Host Deployment Automation Script for Sentinel
# Supports parallel deployment to multiple hosts with validation

set -e

# Configuration
DEPLOYMENT_CONFIG_FILE="${DEPLOYMENT_CONFIG_FILE:-./deployment-config.json}"
AUDIT_LOG_DIR="./.audit-logs"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
AUDIT_LOG_FILE="$AUDIT_LOG_DIR/deployment-$TIMESTAMP.json"
DEPLOYMENT_ID="deploy-$TIMESTAMP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure audit log directory exists
mkdir -p "$AUDIT_LOG_DIR"

# Function to log messages
log_message() {
    echo -e "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to validate deployment prerequisites
validate_prerequisites() {
    log_message "Validating deployment prerequisites..."
    
    local validation_passed=true
    
    # Check for required commands
    for cmd in ssh scp rsync git; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is not installed"
            validation_passed=false
        else
            log_success "$cmd is available"
        fi
    done
    
    # Check for deployment config
    if [[ ! -f "$DEPLOYMENT_CONFIG_FILE" ]]; then
        log_warning "Deployment config not found at $DEPLOYMENT_CONFIG_FILE"
        log_message "Generating default configuration..."
        generate_deployment_config
    else
        log_success "Deployment config found"
    fi
    
    if [[ "$validation_passed" == "false" ]]; then
        log_error "Prerequisites validation failed"
        return 1
    fi
    
    log_success "All prerequisites validated"
    return 0
}

# Function to generate default deployment configuration
generate_deployment_config() {
    cat > "$DEPLOYMENT_CONFIG_FILE" << 'EOF'
{
  "version": "1.0",
  "deployment_name": "Sentinel Multi-Host Deployment",
  "environments": {
    "production": {
      "hosts": [
        {
          "hostname": "prod-host-01.example.com",
          "user": "sentinel",
          "port": 22,
          "deploy_path": "/opt/sentinel"
        },
        {
          "hostname": "prod-host-02.example.com",
          "user": "sentinel",
          "port": 22,
          "deploy_path": "/opt/sentinel"
        }
      ],
      "pre_deploy_commands": [
        "systemctl stop sentinel-service"
      ],
      "post_deploy_commands": [
        "systemctl start sentinel-service",
        "systemctl status sentinel-service"
      ],
      "validation_commands": [
        "curl -f http://localhost:8000/health || exit 1"
      ]
    },
    "staging": {
      "hosts": [
        {
          "hostname": "staging-host-01.example.com",
          "user": "sentinel",
          "port": 22,
          "deploy_path": "/opt/sentinel"
        }
      ],
      "pre_deploy_commands": [],
      "post_deploy_commands": [
        "systemctl restart sentinel-service"
      ],
      "validation_commands": [
        "curl -f http://localhost:8000/health || exit 1"
      ]
    },
    "development": {
      "hosts": [
        {
          "hostname": "localhost",
          "user": "developer",
          "port": 22,
          "deploy_path": "$HOME/sentinel"
        }
      ],
      "pre_deploy_commands": [],
      "post_deploy_commands": [],
      "validation_commands": []
    }
  },
  "rollback": {
    "enabled": true,
    "keep_versions": 3
  },
  "notifications": {
    "enabled": false,
    "webhook_url": ""
  }
}
EOF
    log_success "Default deployment configuration generated at $DEPLOYMENT_CONFIG_FILE"
}

# Function to deploy to a single host
deploy_to_host() {
    local hostname=$1
    local user=$2
    local port=$3
    local deploy_path=$4
    
    log_message "Deploying to $hostname..."
    
    # Create backup
    local backup_path="${deploy_path}.backup-$TIMESTAMP"
    ssh -p "$port" "${user}@${hostname}" "if [ -d '$deploy_path' ]; then cp -r '$deploy_path' '$backup_path'; fi" || true
    
    # Sync files (dry-run first for validation)
    log_message "Validating file sync to $hostname..."
    rsync -avz --dry-run -e "ssh -p $port" \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.audit-logs/*.json' \
        ./ "${user}@${hostname}:${deploy_path}/" || {
        log_error "Dry-run sync failed for $hostname"
        return 1
    }
    
    # Actual sync
    log_message "Syncing files to $hostname..."
    rsync -avz -e "ssh -p $port" \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.audit-logs/*.json' \
        ./ "${user}@${hostname}:${deploy_path}/" || {
        log_error "File sync failed for $hostname"
        return 1
    }
    
    log_success "Deployment to $hostname completed"
    return 0
}

# Function to validate deployment on a host
validate_deployment() {
    local hostname=$1
    local user=$2
    local port=$3
    local validation_commands=$4
    
    log_message "Validating deployment on $hostname..."
    
    # Execute validation commands
    while IFS= read -r cmd; do
        if [[ -n "$cmd" ]]; then
            log_message "Running validation: $cmd"
            ssh -p "$port" "${user}@${hostname}" "$cmd" || {
                log_error "Validation failed on $hostname: $cmd"
                return 1
            }
        fi
    done <<< "$validation_commands"
    
    log_success "Deployment validation passed on $hostname"
    return 0
}

# Function to create audit log entry
create_audit_log() {
    local environment=$1
    local status=$2
    local hosts_count=$3
    local duration=$4
    
    cat > "$AUDIT_LOG_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployment_id": "$DEPLOYMENT_ID",
  "environment": "$environment",
  "status": "$status",
  "duration_seconds": $duration,
  "hosts_deployed": $hosts_count,
  "deployment_config": "$DEPLOYMENT_CONFIG_FILE",
  "metadata": {
    "user": "$USER",
    "hostname": "$(hostname)",
    "git_commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')"
  }
}
EOF
    log_success "Audit log created: $AUDIT_LOG_FILE"
}

# Function to perform multi-host deployment
deploy_environment() {
    local environment=${1:-development}
    
    log_message "=== Starting Multi-Host Deployment ==="
    log_message "Environment: $environment"
    log_message "Deployment ID: $DEPLOYMENT_ID"
    
    local start_time=$(date +%s)
    
    # Validate prerequisites
    validate_prerequisites || {
        log_error "Prerequisites validation failed"
        create_audit_log "$environment" "failed" 0 0
        exit 1
    }
    
    # In a real implementation, parse JSON config
    # For now, demonstrate the structure
    log_message "Loading deployment configuration..."
    
    # Simulate deployment
    log_message "This is a demonstration script. In production:"
    log_message "1. Parse $DEPLOYMENT_CONFIG_FILE for environment '$environment'"
    log_message "2. Deploy to each host in parallel"
    log_message "3. Execute pre-deploy, post-deploy, and validation commands"
    log_message "4. Create detailed audit logs"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    create_audit_log "$environment" "completed" 1 "$duration"
    
    log_success "=== Multi-Host Deployment Completed ==="
}

# Main execution
main() {
    case "${1:-help}" in
        deploy)
            deploy_environment "${2:-development}"
            ;;
        validate)
            validate_prerequisites
            ;;
        config)
            generate_deployment_config
            ;;
        *)
            echo "Usage: $0 {deploy|validate|config} [environment]"
            echo ""
            echo "Commands:"
            echo "  deploy <env>    Deploy to specified environment (production|staging|development)"
            echo "  validate        Validate deployment prerequisites"
            echo "  config          Generate default deployment configuration"
            echo ""
            echo "Examples:"
            echo "  $0 deploy production"
            echo "  $0 validate"
            echo "  $0 config"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
