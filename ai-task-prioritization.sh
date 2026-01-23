#!/bin/bash

# AI-Driven Task Prioritization Model for Sentinel
# This script analyzes tasks and assigns priority scores using AI-driven criteria

set -e

# Configuration
PRIORITY_CONFIG_FILE="${PRIORITY_CONFIG_FILE:-./.audit-logs/priority-config.json}"
AUDIT_LOG_DIR="./.audit-logs"
TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
AUDIT_LOG_FILE="$AUDIT_LOG_DIR/task-prioritization-$TIMESTAMP.json"

# Ensure audit log directory exists
mkdir -p "$AUDIT_LOG_DIR"

# Priority scoring weights (can be adjusted based on AI model recommendations)
WEIGHT_URGENCY=0.30
WEIGHT_IMPACT=0.25
WEIGHT_EFFORT=0.20
WEIGHT_DEPENDENCIES=0.15
WEIGHT_RISK=0.10

# Function to log messages
log_message() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1"
}

# Function to calculate priority score
# Parameters: urgency(1-10), impact(1-10), effort(1-10), dependencies(0-5), risk(1-10)
calculate_priority_score() {
    local urgency=$1
    local impact=$2
    local effort=$3
    local dependencies=$4
    local risk=$5
    
    # Normalize effort (lower effort = higher score)
    local normalized_effort=$(echo "scale=2; (10 - $effort) / 10" | bc)
    
    # Calculate weighted score
    local score=$(echo "scale=2; \
        ($urgency / 10) * $WEIGHT_URGENCY + \
        ($impact / 10) * $WEIGHT_IMPACT + \
        $normalized_effort * $WEIGHT_EFFORT + \
        (1 - $dependencies / 5) * $WEIGHT_DEPENDENCIES + \
        ($risk / 10) * $WEIGHT_RISK" | bc)
    
    echo "$score"
}

# Function to determine priority level
get_priority_level() {
    local score=$1
    
    if (( $(echo "$score >= 0.75" | bc -l) )); then
        echo "CRITICAL"
    elif (( $(echo "$score >= 0.60" | bc -l) )); then
        echo "HIGH"
    elif (( $(echo "$score >= 0.40" | bc -l) )); then
        echo "MEDIUM"
    else
        echo "LOW"
    fi
}

# Function to prioritize task
prioritize_task() {
    local task_id=$1
    local task_name=$2
    local urgency=$3
    local impact=$4
    local effort=$5
    local dependencies=$6
    local risk=$7
    
    log_message "Analyzing task: $task_name (ID: $task_id)"
    
    # Calculate priority score
    local score=$(calculate_priority_score "$urgency" "$impact" "$effort" "$dependencies" "$risk")
    local priority_level=$(get_priority_level "$score")
    
    # Create audit log entry
    cat >> "$AUDIT_LOG_FILE" << EOF
{
    "task_id": "$task_id",
    "task_name": "$task_name",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "priority_score": $score,
    "priority_level": "$priority_level",
    "factors": {
        "urgency": $urgency,
        "impact": $impact,
        "effort": $effort,
        "dependencies": $dependencies,
        "risk": $risk
    },
    "weights": {
        "urgency": $WEIGHT_URGENCY,
        "impact": $WEIGHT_IMPACT,
        "effort": $WEIGHT_EFFORT,
        "dependencies": $WEIGHT_DEPENDENCIES,
        "risk": $WEIGHT_RISK
    }
}
EOF
    
    log_message "Priority Score: $score | Level: $priority_level"
    echo "$priority_level:$score"
}

# Function to analyze and prioritize multiple tasks from JSON input
analyze_tasks_from_json() {
    local json_file=$1
    
    if [[ ! -f "$json_file" ]]; then
        log_message "ERROR: JSON file not found: $json_file"
        return 1
    fi
    
    log_message "Analyzing tasks from: $json_file"
    
    # Initialize audit log
    echo "[" > "$AUDIT_LOG_FILE"
    
    # Parse JSON and prioritize each task
    # This is a simplified version - in production, use jq for JSON parsing
    local first_task=true
    
    # Note: This would typically use jq to parse JSON
    # For now, this is a placeholder for the structure
    
    echo "]" >> "$AUDIT_LOG_FILE"
    
    log_message "Task prioritization completed. Audit log: $AUDIT_LOG_FILE"
}

# Function to generate priority configuration
generate_priority_config() {
    log_message "Generating priority configuration..."
    
    mkdir -p "$(dirname "$PRIORITY_CONFIG_FILE")"
    
    cat > "$PRIORITY_CONFIG_FILE" << 'EOF'
{
  "version": "1.0",
  "model": "AI-Driven Task Prioritization",
  "weights": {
    "urgency": 0.30,
    "impact": 0.25,
    "effort": 0.20,
    "dependencies": 0.15,
    "risk": 0.10
  },
  "priority_levels": {
    "CRITICAL": {
      "min_score": 0.75,
      "max_score": 1.00,
      "sla_hours": 4,
      "description": "Critical tasks requiring immediate attention"
    },
    "HIGH": {
      "min_score": 0.60,
      "max_score": 0.74,
      "sla_hours": 24,
      "description": "High priority tasks to be addressed within 1 day"
    },
    "MEDIUM": {
      "min_score": 0.40,
      "max_score": 0.59,
      "sla_hours": 72,
      "description": "Medium priority tasks to be addressed within 3 days"
    },
    "LOW": {
      "min_score": 0.00,
      "max_score": 0.39,
      "sla_hours": 168,
      "description": "Low priority tasks to be addressed within 1 week"
    }
  },
  "factors": {
    "urgency": {
      "description": "How time-sensitive is the task?",
      "scale": "1-10 (1=not urgent, 10=extremely urgent)"
    },
    "impact": {
      "description": "What is the potential impact on the system/users?",
      "scale": "1-10 (1=minimal impact, 10=critical impact)"
    },
    "effort": {
      "description": "How much effort is required to complete?",
      "scale": "1-10 (1=minimal effort, 10=significant effort)"
    },
    "dependencies": {
      "description": "How many dependencies does this task have?",
      "scale": "0-5 (0=no dependencies, 5=many dependencies)"
    },
    "risk": {
      "description": "What is the risk if this task is delayed?",
      "scale": "1-10 (1=low risk, 10=high risk)"
    }
  }
}
EOF
    
    log_message "Configuration saved to: $PRIORITY_CONFIG_FILE"
}

# Main execution
main() {
    log_message "=== AI-Driven Task Prioritization Model ==="
    
    # Check if config exists, if not create it
    if [[ ! -f "$PRIORITY_CONFIG_FILE" ]]; then
        generate_priority_config
    fi
    
    # Example usage: prioritize a single task
    if [[ $# -eq 7 ]]; then
        prioritize_task "$@"
    elif [[ $# -eq 1 ]]; then
        analyze_tasks_from_json "$1"
    else
        echo "Usage:"
        echo "  Single task: $0 <task_id> <task_name> <urgency> <impact> <effort> <dependencies> <risk>"
        echo "  Multiple tasks: $0 <json_file>"
        echo ""
        echo "Example:"
        echo "  $0 TASK-001 'Fix critical bug' 9 10 3 1 9"
        echo ""
        echo "Parameters:"
        echo "  urgency: 1-10 (how time-sensitive)"
        echo "  impact: 1-10 (potential impact on system/users)"
        echo "  effort: 1-10 (effort required to complete)"
        echo "  dependencies: 0-5 (number of blocking dependencies)"
        echo "  risk: 1-10 (risk if delayed)"
        exit 1
    fi
}

# Run main function
main "$@"
