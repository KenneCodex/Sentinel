#!/bin/bash

# CLI Validation Script for Sentinel
# Validates CLI tools, configurations, and runtime environment

set -e

# Configuration
AUDIT_LOG_DIR="./.audit-logs"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
AUDIT_LOG_FILE="$AUDIT_LOG_DIR/cli-validation-$TIMESTAMP.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure audit log directory exists
mkdir -p "$AUDIT_LOG_DIR"

# Validation results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Function to log messages
log_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_CHECKS++))
    ((TOTAL_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++))
}

# Function to check command availability
check_command() {
    local cmd=$1
    local required=${2:-false}
    
    if command -v "$cmd" &> /dev/null; then
        local version=$(${cmd} --version 2>&1 | head -n1 || echo "unknown")
        log_success "$cmd is installed (${version})"
        return 0
    else
        if [[ "$required" == "true" ]]; then
            log_error "$cmd is not installed (REQUIRED)"
            return 1
        else
            log_warning "$cmd is not installed (optional)"
            return 0
        fi
    fi
}

# Function to validate shell environment
validate_shell_environment() {
    log_message "=== Validating Shell Environment ==="
    
    # Check shell type
    log_message "Current shell: $SHELL"
    
    # Check shell version
    if [[ -n "$BASH_VERSION" ]]; then
        log_success "Bash version: $BASH_VERSION"
    fi
    
    # Check important environment variables
    local env_vars=("HOME" "PATH" "USER" "SHELL")
    for var in "${env_vars[@]}"; do
        if [[ -n "${!var}" ]]; then
            log_success "Environment variable $var is set"
        else
            log_error "Environment variable $var is not set"
        fi
    done
    
    echo ""
}

# Function to validate required CLI tools
validate_required_tools() {
    log_message "=== Validating Required CLI Tools ==="
    
    # Core system tools
    check_command "bash" true
    check_command "sh" true
    check_command "cat" true
    check_command "grep" true
    check_command "sed" true
    check_command "awk" true
    
    # Version control
    check_command "git" true
    
    # Network tools
    check_command "curl" true
    check_command "wget" false
    
    # Text processing
    check_command "jq" false
    
    echo ""
}

# Function to validate optional development tools
validate_optional_tools() {
    log_message "=== Validating Optional Development Tools ==="
    
    # Development tools
    check_command "python3" false
    check_command "pip3" false
    check_command "node" false
    check_command "npm" false
    check_command "docker" false
    check_command "docker-compose" false
    
    # Shell script tools
    check_command "shellcheck" false
    check_command "shfmt" false
    
    # Monitoring and debugging
    check_command "htop" false
    check_command "nc" false
    check_command "netstat" false
    
    echo ""
}

# Function to validate file permissions
validate_file_permissions() {
    log_message "=== Validating File Permissions ==="
    
    # Check shell scripts are executable
    local scripts=(
        "sentinel_client_update.sh"
        "ai-task-prioritization.sh"
        "multi-host-deployment.sh"
        "cli-validation.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ -x "$script" ]]; then
                log_success "$script is executable"
            else
                log_error "$script is not executable"
            fi
        else
            log_warning "$script not found"
        fi
    done
    
    echo ""
}

# Function to validate directory structure
validate_directory_structure() {
    log_message "=== Validating Directory Structure ==="
    
    local required_dirs=(
        ".github/workflows"
        ".audit-logs"
    )
    
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_success "Directory exists: $dir"
        else
            log_error "Directory missing: $dir"
        fi
    done
    
    echo ""
}

# Function to validate configuration files
validate_configuration_files() {
    log_message "=== Validating Configuration Files ==="
    
    local config_files=(
        ".github/PULL_REQUEST_TEMPLATE.md"
        ".github/workflows/shell-script-ci.yml"
        ".audit-logs/README.md"
    )
    
    for config in "${config_files[@]}"; do
        if [[ -f "$config" ]]; then
            log_success "Configuration file exists: $config"
            
            # Check if file is not empty
            if [[ -s "$config" ]]; then
                log_success "  └─ File has content"
            else
                log_warning "  └─ File is empty"
            fi
        else
            log_error "Configuration file missing: $config"
        fi
    done
    
    echo ""
}

# Function to validate Git configuration
validate_git_configuration() {
    log_message "=== Validating Git Configuration ==="
    
    if command -v git &> /dev/null; then
        # Check if we're in a git repository
        if git rev-parse --git-dir > /dev/null 2>&1; then
            log_success "Inside a Git repository"
            
            # Get git info
            local branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
            local commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
            
            log_message "  └─ Branch: $branch"
            log_message "  └─ Commit: $commit"
            
            # Check git config
            local user_name=$(git config user.name 2>/dev/null || echo "")
            local user_email=$(git config user.email 2>/dev/null || echo "")
            
            if [[ -n "$user_name" ]]; then
                log_success "Git user.name is configured: $user_name"
            else
                log_warning "Git user.name is not configured"
            fi
            
            if [[ -n "$user_email" ]]; then
                log_success "Git user.email is configured: $user_email"
            else
                log_warning "Git user.email is not configured"
            fi
        else
            log_error "Not inside a Git repository"
        fi
    fi
    
    echo ""
}

# Function to validate shell scripts syntax
validate_shell_scripts_syntax() {
    log_message "=== Validating Shell Scripts Syntax ==="
    
    local scripts=$(find . -name "*.sh" -type f 2>/dev/null)
    
    if [[ -z "$scripts" ]]; then
        log_warning "No shell scripts found"
        return
    fi
    
    while IFS= read -r script; do
        if bash -n "$script" 2>/dev/null; then
            log_success "Syntax OK: $script"
        else
            log_error "Syntax error in: $script"
        fi
    done <<< "$scripts"
    
    echo ""
}

# Function to create audit log
create_validation_audit_log() {
    cat > "$AUDIT_LOG_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "validation_type": "cli_validation",
  "status": "$([ $FAILED_CHECKS -eq 0 ] && echo 'passed' || echo 'failed')",
  "summary": {
    "total_checks": $TOTAL_CHECKS,
    "passed": $PASSED_CHECKS,
    "failed": $FAILED_CHECKS,
    "warnings": $WARNINGS
  },
  "environment": {
    "shell": "$SHELL",
    "bash_version": "${BASH_VERSION:-unknown}",
    "user": "$USER",
    "hostname": "$(hostname)",
    "os": "$(uname -s)",
    "kernel": "$(uname -r)"
  },
  "git_info": {
    "branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'N/A')",
    "commit": "$(git rev-parse --short HEAD 2>/dev/null || echo 'N/A')"
  }
}
EOF
    
    log_success "Audit log created: $AUDIT_LOG_FILE"
}

# Function to print summary
print_summary() {
    echo ""
    echo "=== Validation Summary ==="
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✓ All validations passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some validations failed. Please review the errors above.${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo "=== Sentinel CLI Validation Tool ==="
    echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    
    validate_shell_environment
    validate_required_tools
    validate_optional_tools
    validate_file_permissions
    validate_directory_structure
    validate_configuration_files
    validate_git_configuration
    
    # Only validate syntax if shellcheck is available or bash -n works
    if command -v shellcheck &> /dev/null || command -v bash &> /dev/null; then
        validate_shell_scripts_syntax
    fi
    
    create_validation_audit_log
    print_summary
}

# Run main function
main "$@"
