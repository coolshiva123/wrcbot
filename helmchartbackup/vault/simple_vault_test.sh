#!/bin/bash
# Simple Vault access test for wrcbot pod
# Copy and paste this into your pod terminal

echo "🔍 Simple Vault Access Test"
echo "==========================="

# Set variables
VAULT_ADDR="http://vault.vault.svc.cluster.local:8200"
VAULT_ROLE="wrcbot"
VAULT_SECRET_PATH="secret/data/wrcbot/config"

# Get the ServiceAccount token
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    KUBE_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    echo "✅ ServiceAccount token found (${#KUBE_TOKEN} chars)"
else
    echo "❌ No ServiceAccount token found"
    exit 1
fi

# Test Vault connectivity
echo "🔍 Testing Vault connectivity..."
if curl -s --connect-timeout 5 "$VAULT_ADDR/v1/sys/health" | jq -e '.sealed == false' >/dev/null 2>&1; then
    echo "✅ Vault is reachable and unsealed"
else
    echo "❌ Vault is not reachable or sealed"
    echo "Trying alternative addresses..."
    for addr in "http://vault.wrcbot.svc.cluster.local:8200" "http://vault:8200"; do
        if curl -s --connect-timeout 5 "$addr/v1/sys/health" >/dev/null; then
            VAULT_ADDR="$addr"
            echo "✅ Found Vault at $addr"
            break
        fi
    done
fi

# Authenticate to Vault
echo "🔍 Authenticating to Vault..."
VAULT_LOGIN=$(curl -s --request POST \
    --data "{\"role\": \"$VAULT_ROLE\", \"jwt\": \"$KUBE_TOKEN\"}" \
    "$VAULT_ADDR/v1/auth/kubernetes/login")

if echo "$VAULT_LOGIN" | jq -e '.auth.client_token' >/dev/null 2>&1; then
    VAULT_TOKEN=$(echo "$VAULT_LOGIN" | jq -r '.auth.client_token')
    echo "✅ Authentication successful"
    
    # Try to read the secret
    echo "🔍 Reading secret..."
    SECRET_RESPONSE=$(curl -s \
        --header "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/$VAULT_SECRET_PATH")
    
    if echo "$SECRET_RESPONSE" | jq -e '.data.data' >/dev/null 2>&1; then
        echo "✅ Secret retrieved successfully!"
        echo "Secret keys:"
        echo "$SECRET_RESPONSE" | jq -r '.data.data | keys[]'
    else
        echo "❌ Failed to read secret"
        echo "Response: $SECRET_RESPONSE"
    fi
else
    echo "❌ Authentication failed"
    echo "Response: $VAULT_LOGIN"
fi
