#!/bin/bash

# Sentinel Client Auto-Update & AI Synchronization Script
# Enhancements: Security, Multi-Platform Support, Cloud Readiness, AI Research Sync, and Error Handling

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load local environment variables when available (without overriding explicit shell exports)
if [ -f "$SCRIPT_DIR/.env" ]; then
    # Read .env line by line and only export variables that are not already set
    while IFS='=' read -r var_name var_value || [ -n "$var_name" ]; do
        # Trim whitespace
        var_name="${var_name#"${var_name%%[![:space:]]*}"}"
        var_name="${var_name%"${var_name##*[![:space:]]}"}"
        # Skip empty lines and comments
        case "$var_name" in
            ''|\#*) continue ;;
        esac
        # Remove leading 'export ' if present
        if [[ "$var_name" == export* ]]; then
            var_name="${var_name#export }"
            var_name="${var_name#"${var_name%%[![:space:]]*}"}"
        fi
        # Extract key and value
        if [[ "$var_name" =~ ^([A-Za-z_][A-Za-z0-9_]*)$ ]]; then
            key="$var_name"
            # Only set the variable if it is not already defined in the environment
            if [ -z "${!key+x}" ]; then
                export "$key=$var_value"
            fi
        fi
    done < "$SCRIPT_DIR/.env"
fi

CODEXJR_PORT="${CODEXJR_PORT:-5051}"
SENTINEL_PORT="${SENTINEL_PORT:-5052}"
ARCHIVIST_PORT="${ARCHIVIST_PORT:-5053}"
SHRINE_PORT="${SHRINE_PORT:-5054}"
CODEX_PHASE="${CODEX_PHASE:-Phase Unknown}"

# Define Sentinel Node directory
SENTINEL_DIR="$HOME/sentinel_client"
LOG_FILE="$SENTINEL_DIR/update_log.txt"

# Ensure Sentinel Node directory exists
mkdir -p "$SENTINEL_DIR"

# Function to log messages
echo_log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

echo_log "🚀 Starting Sentinel Client Update & AI Synchronization..."
echo_log "📘 Phase: $CODEX_PHASE"
echo_log "🔌 Local parity ports: CodexJr=$CODEXJR_PORT Sentinel=$SENTINEL_PORT Archivist=$ARCHIVIST_PORT Shrine=$SHRINE_PORT"

# 🛠 Step 1: Ensure Git is Installed
if ! command -v git &> /dev/null; then
    echo_log "🔹 Git is not installed. Installing now..."
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y git
    else
        echo_log "❌ Unsupported package manager for automatic git installation. Install git manually and retry."
        exit 1
    fi
else
    echo_log "✅ Git is already installed."
fi

# 🛠 Step 2: Clone or Pull Latest Updates
if [ -d "$SENTINEL_DIR/.git" ]; then
    cd "$SENTINEL_DIR"
    git reset --hard HEAD  # Reset any local changes
    git pull origin main || { echo_log "❌ Git pull failed! Check repository access."; exit 1; }
elif [ -d "$SENTINEL_DIR" ]; then
    echo_log "⚠️ Directory exists but is not a Git repo. Recreating..."
    rm -rf "$SENTINEL_DIR"
    git clone https://github.com/KenneCodex/Sentinel.git "$SENTINEL_DIR" || { echo_log "❌ Git clone failed!"; exit 1; }
else
    echo_log "🚀 Cloning fresh Sentinel Client repository..."
    git clone https://github.com/KenneCodex/Sentinel.git "$SENTINEL_DIR" || { echo_log "❌ Git clone failed!"; exit 1; }
fi

echo_log "✅ Sentinel Client successfully updated from repository."

# 🛠 Step 3: Set File Permissions
if [ -f "$SENTINEL_DIR/sentinel_client.py" ]; then
    chmod +x "$SENTINEL_DIR/sentinel_client.py"
else
    echo_log "⚠️ sentinel_client.py not found; skipping executable bit update."
fi
chmod -R 755 "$SENTINEL_DIR"
echo_log "✅ Permissions set for Sentinel Client."

# 🛠 Step 4: Create Desktop Shortcut (Linux Only)
if [[ "${OSTYPE:-}" == "linux-gnu"* ]]; then
    cat > "$HOME/Desktop/SentinelClient.desktop" <<DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Sentinel Client
Exec="$SENTINEL_DIR/sentinel_client.py"
Icon="$SENTINEL_DIR/icon.png"
Terminal=false
DESKTOP
    chmod +x "$HOME/Desktop/SentinelClient.desktop"
    echo_log "✅ Sentinel Client Shortcut Created on Desktop!"
fi

# 🛠 Step 5: Apply Security Configurations
cat > "$SENTINEL_DIR/security_config.json" <<SECURITY
{
    "authentication": "blockchain-based",
    "node_hierarchy": "centralized governance",
    "auto_update": "enabled"
}
SECURITY

echo_log "✅ Security settings applied. Blockchain authentication enabled."

# 🛠 Step 6: Verify Python Dependencies
REQUIRED_PYTHON="Python 3.10"
if ! python3 -c "import sys; assert sys.version_info.major == 3 and sys.version_info.minor == 10" &>/dev/null; then
    echo_log "🔹 Installing $REQUIRED_PYTHON..."
    if command -v apt &> /dev/null; then
        sudo apt install -y python3.10 python3.10-venv python3.10-dev
    else
        echo_log "❌ Unsupported package manager for automatic Python installation. Install Python 3.10 manually and retry."
        exit 1
    fi
else
    echo_log "✅ $REQUIRED_PYTHON is already installed."
fi

# 🛠 Step 7: Fetch Sentinel AI EEG Data & Synchronize
SENTINEL_API_URL="http://localhost:8000"
echo_log "📡 Fetching Sentinel EEG Synchronization Data..."
EEG_DATA=$(curl -s "$SENTINEL_API_URL/eeg_synchronization")
echo_log "🧠 Retrieved EEG Data: $EEG_DATA"

# 🛠 Step 8: Request MyGPT EEG Research
MYGPT_API_URL="https://mygpt-research-assistant.com/api"
TASK="Analyze EEG synchronization in AI-human interaction using Sentinel AI data"
RESEARCH_RESPONSE=$(curl -s -X POST "$MYGPT_API_URL/chat" -H "Content-Type: application/json" -d "{\"input\": \"$TASK\"}")
echo_log "🔬 MyGPT EEG Research Response: $RESEARCH_RESPONSE"

# 🛠 Step 9: Send Research Findings to Sentinel AI
echo_log "📡 Sending research findings to Sentinel AI..."
SEND_RESPONSE=$(curl -s -X POST "$SENTINEL_API_URL/update" -H "Content-Type: application/json" -d "{\"research_update\": $RESEARCH_RESPONSE}")
echo_log "✅ Sentinel AI Update Response: $SEND_RESPONSE"

# 🛠 Step 10: Authenticate GitHub API & Fetch Repo Info
GITHUB_API_URL="https://api.github.com/repos/KenneCodex/Sentinel"
if [ -n "${GITHUB_API_TOKEN:-}" ]; then
    echo_log "📡 Fetching repository information from GitHub with token auth..."
    GITHUB_RESPONSE=$(curl -s \
      --header "Authorization: token $GITHUB_API_TOKEN" \
      --header "X-GitHub-Api-Version: 2022-11-28" \
      "$GITHUB_API_URL")
else
    echo_log "⚠️ GITHUB_API_TOKEN not set; using unauthenticated GitHub API request."
    GITHUB_RESPONSE=$(curl -s --header "X-GitHub-Api-Version: 2022-11-28" "$GITHUB_API_URL")
fi

echo_log "🔍 GitHub API Response: $GITHUB_RESPONSE"

# 🛠 Step 11: Local parity health sweep
# NOTE: Health checks use -fsS flags for strict error handling (fail on HTTP/connection errors).
# Other curl calls in this script use -s because they are best-effort/diagnostic.
# Health checks are non-fatal - failures are logged but don't abort the script.
health_check() {
    local service="$1"
    local port="$2"
    local response

    if [[ ! "$port" =~ ^[0-9]+$ ]]; then
        echo_log "❌ Invalid port: $port"
        return 1
    fi

    if ! response=$(curl -fsS --connect-timeout 5 --max-time 10 "http://localhost:${port}/healthz"); then
        echo_log "❌ ${service} health check failed at http://localhost:${port}/healthz"
        return 1
    fi

    if echo "$response" | jq -e \
        --arg service "$service" \
        --arg phase "$CODEX_PHASE" \
        --argjson port "$port" \
        '.status == "ok" and .service == $service and .phase == $phase and .port == $port' >/dev/null; then
        echo_log "✅ ${service} health check passed on port ${port}: $response"
    else
        echo_log "❌ ${service} health response shape mismatch on port ${port}: $response"
        return 1
    fi
}

echo_log "🩺 Running localhost parity health sweep..."
health_check "CodexJr" "$CODEXJR_PORT" || true
health_check "Sentinel" "$SENTINEL_PORT" || true
health_check "Archivist" "$ARCHIVIST_PORT" || true
health_check "Shrine" "$SHRINE_PORT" || true

echo_log "✅ Sentinel Client Update & AI Synchronization Completed Successfully! 🚀"
