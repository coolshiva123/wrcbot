#!/bin/bash
# View Vault Secrets Script
# Usage: ./view-vault-secrets.sh [--show-values]

SHOW_VALUES=false
if [[ "$1" == "--show-values" ]]; then
    SHOW_VALUES=true
fi

echo "👀 WRCBot Vault Secret Viewer"
echo "============================="

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

echo "✅ Connected to Vault"
echo ""

# Check if secrets exist
if ! VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/config >/dev/null 2>&1; then
    echo "📭 No secrets found at secret/wrcbot/config"
    echo "💡 Use ./set-vault-secrets.sh to create secrets"
    kill $PORT_FORWARD_PID 2>/dev/null || true
    exit 0
fi

# Display secrets
echo "📋 Current secrets in Vault:"
echo "=============================="

if [ "$SHOW_VALUES" = true ]; then
    echo "⚠️  WARNING: Showing actual secret values!"
    echo ""
    VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/config
else
    echo "🔒 Secret values are masked for security"
    echo "   Use --show-values flag to see actual values"
    echo ""
    
    # Get secrets and mask values
    VAULT_ADDR='http://localhost:8200' VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/config | while IFS= read -r line; do
        if [[ "$line" =~ ^(bot_token|admin_users|bot_signing_secret|bot_app_token)[[:space:]] ]]; then
            key=$(echo "$line" | awk '{print $1}')
            value=$(echo "$line" | awk '{$1=""; print $0}' | sed 's/^ *//')
            
            if [[ "$key" == "admin_users" ]]; then
                # Don't mask admin users as they're not sensitive
                echo "$key    $value"
            else
                # Mask other values
                masked_value=$(echo "$value" | sed 's/./*/g')
                echo "$key    ${masked_value:0:20}..."
            fi
        else
            echo "$line"
        fi
    done
fi

# Clean up port-forward
kill $PORT_FORWARD_PID 2>/dev/null || true

echo ""
echo "💡 Management commands:"
echo "   ./set-vault-secrets.sh       # Update secrets"
echo "   ./view-vault-secrets.sh --show-values  # Show actual values"
echo "   ./get-vault-credentials.sh   # Get UI access token"
