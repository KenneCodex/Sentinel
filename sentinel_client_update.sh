#!/bin/bash

# Sentinel Client Auto-Update & AI Synchronization Script
# Enhancements: Security, Multi-Platform Support, Cloud Readiness, AI Research Sync, and Error Handling

set -euo pipefail

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

# 🛠 Step 1: Ensure Git is Installed
if ! command -v git &> /dev/null; then
    echo_log "🔹 Git is not installed. Installing now..."
    sudo apt update && sudo apt install -y git
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
if ! python3 --version | grep -q "3.10"; then
    echo_log "🔹 Installing $REQUIRED_PYTHON..."
    sudo apt install -y python3.10 python3.10-venv python3.10-dev
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

echo_log "✅ Sentinel Client Update & AI Synchronization Completed Successfully! 🚀"
