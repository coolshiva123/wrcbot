#!/bin/bash
# Script to set WRCBot secrets in Vault using JSON method
# Usage: ./set_secrets_json.sh

set -e

echo "🔐 WRCBot Vault Secret Setup (JSON Method)"
echo "=========================================="

# Configuration
VAULT_NAMESPACE="wrcbot"
VAULT_SECRET_PATH="secret/data/wrcbot/config"

# Step 1: Port-forward Vault service
echo "🔌 Setting up Vault connection..."
if lsof -i:8200 | grep LISTEN; then
  echo "Port 8200 is already in use. Assuming an existing port-forward is running."
  PF_PID=""
else
  echo "Starting kubectl port-forward for Vault..."
  kubectl port-forward svc/vault -n $VAULT_NAMESPACE 8200:8200 &
  PF_PID=$!
  sleep 3
fi

export VAULT_ADDR="http://127.0.0.1:8200"

# Step 2: Get root token
echo "🔑 Retrieving Vault root token..."
ROOT_TOKEN=$(kubectl get secret vault-keys -n $VAULT_NAMESPACE -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)

if [ -z "$ROOT_TOKEN" ]; then
    echo "❌ Could not retrieve root token from vault-keys secret"
    exit 1
fi

echo "✅ Root token retrieved"

# Step 3: Create JSON payload with bot secrets
echo "📝 Creating JSON payload with bot secrets..."

# Interactive input for secrets
read -p "Enter Slack Bot Token (xoxb-...): " BOT_TOKEN
read -p "Enter Slack Signing Secret: " SIGNING_SECRET  
read -p "Enter Slack App Token (xapp-...): " APP_TOKEN
read -p "Enter Admin Users (comma-separated, e.g., @user1,@user2): " ADMIN_USERS
read -p "Enter Log Level (default: DEBUG): " LOG_LEVEL
LOG_LEVEL=${LOG_LEVEL:-DEBUG}

# Create JSON file
cat > /tmp/wrcbot_secrets.json << EOF
{
  "data": {
    "bot_token": "$BOT_TOKEN",
    "signing_secret": "$SIGNING_SECRET",
    "app_token": "$APP_TOKEN", 
    "admin_users": "$ADMIN_USERS",
    "log_level": "$LOG_LEVEL"
  }
}
EOF

echo "✅ JSON payload created"

# Step 4: Write secrets to Vault
echo "💾 Writing secrets to Vault..."
WRITE_RESPONSE=$(curl -s \
    --header "X-Vault-Token: $ROOT_TOKEN" \
    --header "Content-Type: application/json" \
    --request POST \
    --data @/tmp/wrcbot_secrets.json \
    "$VAULT_ADDR/v1/$VAULT_SECRET_PATH")

if echo "$WRITE_RESPONSE" | jq -e '.errors' >/dev/null 2>&1; then
    echo "❌ Error writing secrets:"
    echo "$WRITE_RESPONSE" | jq -r '.errors[]'
    exit 1
else
    echo "✅ Secrets written successfully"
fi

# Step 5: Verify secrets were written
echo "🔍 Verifying secrets..."
READ_RESPONSE=$(curl -s \
    --header "X-Vault-Token: $ROOT_TOKEN" \
    "$VAULT_ADDR/v1/$VAULT_SECRET_PATH")

if echo "$READ_RESPONSE" | jq -e '.data.data' >/dev/null 2>&1; then
    echo "✅ Secrets verified. Available keys:"
    echo "$READ_RESPONSE" | jq -r '.data.data | keys[]' | sed 's/^/  - /'
else
    echo "❌ Could not verify secrets"
    echo "Response: $READ_RESPONSE"
fi

# Step 6: Show example of how to read secrets
echo ""
echo "📖 Example JSON payload to read these secrets:"
cat << 'EOF'
{
  "role": "wrcbot",
  "jwt": "$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
}
EOF

echo ""
echo "📖 Example curl command to read secrets from pod:"
cat << 'EOF'
# 1. Authenticate and get token
VAULT_LOGIN=$(curl -s --request POST \
    --data '{"role": "wrcbot", "jwt": "'"$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"'"}' \
    http://vault.vault.svc.cluster.local:8200/v1/auth/kubernetes/login)

VAULT_TOKEN=$(echo $VAULT_LOGIN | jq -r .auth.client_token)

# 2. Read secrets
curl -s \
    --header "X-Vault-Token: $VAULT_TOKEN" \
    http://vault.vault.svc.cluster.local:8200/v1/secret/data/wrcbot/config | jq
EOF

# Cleanup
rm -f /tmp/wrcbot_secrets.json

# Kill port-forward if we started it
if [ -n "$PF_PID" ]; then
    echo "🧹 Cleaning up port-forward..."
    kill $PF_PID
    wait $PF_PID 2>/dev/null || true
fi

echo ""
echo "✅ WRCBot secrets setup completed!"
echo "   You can now test secret retrieval from your wrcbot pod"
