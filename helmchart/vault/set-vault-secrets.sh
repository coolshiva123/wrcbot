#!/bin/bash
# Interactive Vault Secret Management Script
# Usage: ./set-vault-secrets.sh

set -e

echo "🔐 WRCBot Vault Secret Management"
echo "=================================="

# Check if vault is running
if ! kubectl get deployment vault -n wrcbot &>/dev/null; then
    echo "❌ Vault deployment not found in wrcbot namespace"
    exit 1
fi

# Check if vault is unsealed
echo "📊 Checking Vault status..."
if ! kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Sealed.*false"; then
    echo "🔒 Vault is sealed. Please unseal it first:"
    echo "   ./unseal-vault.sh"
    exit 1
fi

# Get root token
echo "🔑 Retrieving root token..."
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)

if [ -z "$ROOT_TOKEN" ]; then
    echo "❌ Could not retrieve root token from vault-keys secret"
    exit 1
fi

echo "✅ Vault is ready for secret management"
echo ""

# Interactive secret collection
echo "📝 Please provide the following bot secrets:"
echo "   (Press Enter to keep existing value, if any)"
echo ""

# Function to read secret with optional masking
read_secret() {
    local prompt="$1"
    local var_name="$2"
    local mask_input="$3"
    
    if [ "$mask_input" = "true" ]; then
        read -s -p "$prompt: " value
        echo ""  # New line after hidden input
    else
        read -p "$prompt: " value
    fi
    
    # Set the variable dynamically
    eval "$var_name='$value'"
}

# Collect secrets interactively
read_secret "Bot Token (xoxb-...)" "BOT_TOKEN" "true"
read_secret "Admin Users (comma-separated, e.g., @user1,@user2)" "ADMIN_USERS" "false"
read_secret "Bot Signing Secret" "BOT_SIGNING_SECRET" "true"
read_secret "Bot App Token (xapp-...)" "BOT_APP_TOKEN" "true"

echo ""
echo "📋 Collected secrets summary:"
echo "   Bot Token: ${BOT_TOKEN:0:10}..." 
echo "   Admin Users: $ADMIN_USERS"
echo "   Bot Signing Secret: ${BOT_SIGNING_SECRET:0:8}..."
echo "   Bot App Token: ${BOT_APP_TOKEN:0:10}..."
echo ""

# Confirm before proceeding
read -p "🤔 Do you want to store these secrets in Vault? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Operation cancelled"
    exit 0
fi

# Create JSON payload
echo "📦 Creating JSON payload..."
JSON_PAYLOAD=$(cat <<EOF
{
  "bot_token": "$BOT_TOKEN",
  "admin_users": "$ADMIN_USERS", 
  "bot_signing_secret": "$BOT_SIGNING_SECRET",
  "bot_app_token": "$BOT_APP_TOKEN"
}
EOF
)

# Store secrets using JSON method via port-forward
echo "🚀 Storing secrets in Vault..."

# Start port-forward in background
echo "📡 Starting port-forward to Vault..."
kubectl port-forward svc/vault 8200:8200 -n wrcbot >/dev/null 2>&1 &
PORT_FORWARD_PID=$!

# Wait for port-forward to be ready
sleep 3

# Verify port-forward is working
if ! curl -s http://localhost:8200/v1/sys/health >/dev/null; then
    echo "❌ Failed to establish port-forward to Vault"
    kill $PORT_FORWARD_PID 2>/dev/null || true
    exit 1
fi

# Store secrets using the JSON method
echo "💾 Storing secrets via JSON method..."
if echo "$JSON_PAYLOAD" | VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv put secret/wrcbot/config -; then
    echo "✅ Secrets successfully stored in Vault!"
else
    echo "❌ Failed to store secrets in Vault"
    kill $PORT_FORWARD_PID 2>/dev/null || true
    exit 1
fi

# Verify secrets were stored
echo "🔍 Verifying stored secrets..."
if VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/config >/dev/null 2>&1; then
    echo "✅ Secrets verification successful!"
    echo ""
    echo "📋 Stored secrets (values masked for security):"
    VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/config | grep -E "^(bot_token|admin_users|bot_signing_secret|bot_app_token)" | sed 's/\(.*\s\)\(.*\)$/\1[MASKED]/' || true
else
    echo "⚠️  Warning: Could not verify secrets, but they may have been stored"
fi

# Clean up port-forward
kill $PORT_FORWARD_PID 2>/dev/null || true
echo ""
echo "🎉 Secret management complete!"
echo ""
echo "💡 Next steps:"
echo "   1. Deploy your wrcbot application if not already deployed"
echo "   2. Restart wrcbot deployment to pick up new secrets:"
echo "      kubectl rollout restart deployment/wrcbot -n wrcbot"
echo ""
echo "🔧 To view secrets later:"
echo "   ./get-vault-credentials.sh  # Get UI token"
echo "   kubectl port-forward svc/vault 8200:8200 -n wrcbot  # Start port-forward"
echo "   # Then visit http://localhost:8200"
