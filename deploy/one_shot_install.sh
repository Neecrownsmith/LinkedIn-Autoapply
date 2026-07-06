#!/usr/bin/env bash
# ==============================================================================
# LINKEDIN AUTO-APPLY BOT ONE-SHOT INTERACTIVE INSTALLER
# ==============================================================================
# Run as root: sudo ./deploy/one_shot_install.sh
# ==============================================================================
set -euo pipefail

# Ensure running as root
if [[ $EUID -ne 0 ]]; then
  echo "Error: This script must be run as root: sudo $0"
  exit 1
fi

# Detect project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Normalize line endings on script directory before continuing
sed -i -e 's/\r$//' "$PROJECT_ROOT"/deploy/*.sh || true

# Helper function to ask if the user wants to skip a step
should_skip_step() {
  local step_name="$1"
  local skip=""
  read -r -p "Skip step: '$step_name'? (y/N): " skip
  if [[ "$skip" =~ ^[Yy] ]]; then
    return 0 # True (skip)
  fi
  return 1 # False (run)
}

echo "=========================================================="
echo "    LINKEDIN AUTO-APPLY BOT ONE-SHOT VPS INSTALLER"
echo "=========================================================="

# 1. Setup User and Password
echo ""
echo "--- STEP 1: CONFIGURE USER ACCOUNT ---"
if should_skip_step "Configure User Account (botuser Setup)"; then
  echo "Skipped Step 1."
else
  read -r -p "Enter a password for the secure 'botuser' account: " BOT_PASSWORD
  while [[ -z "$BOT_PASSWORD" ]]; do
    read -r -p "Password cannot be empty. Please enter a password: " BOT_PASSWORD
  done

  if ! id "botuser" &>/dev/null; then
    echo "Creating 'botuser' account..."
    adduser --disabled-password --gecos "" botuser
  fi

  echo "botuser:$BOT_PASSWORD" | chpasswd
  usermod -aG sudo botuser
  usermod -aG systemd-journal botuser
  echo "Secure 'botuser' configured successfully."
fi

# 2. Setup Swap file
echo ""
echo "--- STEP 2: CONFIGURE SWAP SPACE ---"
if should_skip_step "Configure Swap Space (4GB Virtual Memory)"; then
  echo "Skipped Step 2."
else
  read -r -p "Create a 4GB Swap file for memory stability? (y/N): " DO_SWAP
  if [[ "$DO_SWAP" =~ ^[Yy] ]]; then
    if [[ ! -f /swapfile ]]; then
      echo "Allocating 4GB swapfile (this may take a few seconds)..."
      fallocate -l 4G /swapfile
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
      echo "Swap space configured."
    else
      echo "Swap file already exists. Skipping."
    fi
  else
    echo "Skipping swap space setup."
  fi
fi

# 3. Configure Timezone
echo ""
echo "--- STEP 3: CONFIGURE SERVER TIMEZONE (WAT) ---"
if should_skip_step "Configure Server Timezone (Africa/Lagos for WAT)"; then
  echo "Skipped Step 3."
else
  echo "Setting server timezone to Africa/Lagos..."
  timedatectl set-timezone Africa/Lagos || echo "Warning: timedatectl not available or failed."
  echo "Current server time: $(date)"
fi

# 4. Install dependencies
echo ""
echo "--- STEP 4: INSTALLING SYSTEM DEPENDENCIES ---"
if should_skip_step "Installing System Dependencies (python3-venv, pip)"; then
  echo "Skipped Step 4."
else
  echo "Updating package index and installing base dependencies..."
  apt-get update
  apt-get install -y python3-venv python3-pip python3-dev wget curl unzip git nano
  echo "Installing system shared libraries required for headless Chrome..."
  apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 || true
fi

# 5. Set permissions
echo ""
echo "--- STEP 5: SETTING WORKSPACE PERMISSIONS ---"
if should_skip_step "Setting Workspace Permissions"; then
  echo "Skipped Step 5."
else
  chown -R botuser:botuser "$PROJECT_ROOT"
  chmod +x "$PROJECT_ROOT"/deploy/*.sh
  # Prevent future chmod calls from blocking git pull on this server
  git -C "$PROJECT_ROOT" config core.fileMode false || true
  echo "Workspace permissions secured."
fi

# 6. Build Python Virtual Environment
echo ""
echo "--- STEP 6: CREATING PYTHON VIRTUAL ENVIRONMENT ---"
if should_skip_step "Creating Python Virtual Environment (.venv)"; then
  echo "Skipped Step 6."
else
  su - botuser -c "
    cd '$PROJECT_ROOT'
    if [[ ! -f venv_ok ]]; then
      echo 'Creating virtualenv in .venv...'
      python3 -m venv .venv
      . .venv/bin/activate
      pip install --upgrade pip
      if [[ -f requirements.txt ]]; then
        echo 'Installing requirements.txt dependencies...'
        pip install -r requirements.txt
      fi
      touch venv_ok
    else
      echo 'Virtualenv (.venv) already exists. Upgrading dependencies...'
      . .venv/bin/activate
      pip install --upgrade pip -r requirements.txt
    fi
  "
fi

# 7. Configure Environment Variables
echo ""
echo "--- STEP 7: CONFIGURE ENVIRONMENT VARIABLES (.env) ---"
if should_skip_step "Configure Environment Variables (.env File)"; then
  echo "Skipped Step 7."
else
  ENV_PATH="$PROJECT_ROOT/.env"
  if [[ ! -f "$ENV_PATH" ]]; then
    # Create empty env file if template is not found
    touch "$ENV_PATH"
    chown botuser:botuser "$ENV_PATH"
  fi

  echo "The script will now open your .env configuration in the 'nano' editor."
  echo "Configure your PREFERRED_LLM (gemini or groq), API keys, and target GOOGLE_SHEET_ID."
  echo "Save with [Ctrl+O, then Enter], and exit with [Ctrl+X]."
  echo ""
  read -r -p "Press Enter to open the .env editor..."
  nano "$ENV_PATH"
fi

# 8. Configure background systemd service and timer
echo ""
echo "--- STEP 8: CONFIGURING BACKGROUND PRODUCTION SERVICE & TIMER ---"
if should_skip_step "Configuring Background Production Service & Timer"; then
  echo "Skipped Step 8."
else
  cp "$PROJECT_ROOT/deploy/linkedin_bot.service" /etc/systemd/system/linkedin_bot.service
  cp "$PROJECT_ROOT/deploy/linkedin_bot.timer" /etc/systemd/system/linkedin_bot.timer
  systemctl daemon-reload

  # Disable the service to prevent accidental boot-time runs, enable only the timer.
  systemctl disable linkedin_bot.service 2>/dev/null || true
  systemctl enable --now linkedin_bot.timer

  # Trigger a first run immediately via the launcher wrapper so the user
  # can verify logs right away without waiting for the next timer slot.
  echo "Triggering first test run via launcher..."
  su - botuser -c "bash '$PROJECT_ROOT/deploy/launch_bot.sh'"
  echo "Background service and 30-minute timer configured and started successfully."
fi

# 9. Configure GitHub SSH Key
echo ""
echo "--- STEP 9: CONFIGURE GITHUB SSH KEY & ACCESS ---"
if should_skip_step "Configure GitHub SSH Key (for passwordless git pull)"; then
  echo "Skipped Step 9."
else
  SSH_DIR="/home/botuser/.ssh"
  KEY_PATH="$SSH_DIR/id_ed25519"
  
  # Run this inside botuser context to ensure the key is owned by botuser
  su - botuser -c "
    mkdir -p '$SSH_DIR'
    chmod 700 '$SSH_DIR'
    
    if [[ ! -f '$KEY_PATH' ]]; then
      echo 'Generating new ED25519 SSH key...'
      ssh-keygen -t ed25519 -N '' -f '$KEY_PATH' -C 'adeniyifajemisin@gmail.com'
    else
      echo 'SSH key already exists at $KEY_PATH.'
    fi
    
    # Start ssh-agent and add the key
    eval \"\$(ssh-agent -s)\" >/dev/null
    ssh-add '$KEY_PATH'
    
    echo ''
    echo '=========================================================='
    echo 'YOUR GITHUB SSH DEPLOY KEY:'
    echo '=========================================================='
    cat '${KEY_PATH}.pub'
    echo '=========================================================='
    echo 'Copy the public key above and add it as a Deploy Key'
    echo 'in your GitHub repository settings (Allow write access).'
    echo 'This enables passwordless git pull / git fetch.'
    echo '=========================================================='
  "
  read -r -p "Press Enter once you have added the key to GitHub..."
fi

# 10. Finished!
echo ""
echo "=========================================================="
echo "                INSTALLATION COMPLETE!"
echo "=========================================================="
echo "Your LinkedIn Auto-Apply Bot is configured with a 30-minute systemd timer."
echo "You can check status or view logs in real-time:"
echo ""
echo "  * View Logs:       journalctl -u linkedin_bot.service -f"
echo "  * Timer Status:    systemctl status linkedin_bot.timer"
echo "  * Active Timers:   systemctl list-timers"
echo "=========================================================="
echo ""
read -r -p "Press Enter to start viewing real-time logs..."
journalctl -u linkedin_bot.service -f
