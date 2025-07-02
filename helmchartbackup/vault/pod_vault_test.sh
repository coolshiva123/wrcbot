#!/bin/bash
# Simple JSON-based Vault access test for wrcbot pod
# Copy and run this directly inside your wrcbot pod

echo "🔍 Simple Vault JSON Test"
echo "========================="

# Configuration
VAULT_ADDR="http://vault.vault.svc.cluster.local:8200"
VAULT_ROLE="wrcbot"
SECRET_PATH="secret/data/wrcbot/config"

# Get Kubernetes token
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    KUBE_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    echo "✅ ServiceAccount token found"
else
    echo "❌ No ServiceAccount token found"
    exit 1
fi

# Test 1: Vault health
echo "🏥 Testing Vault health..."
curl -s "$VAULT_ADDR/v1/sys/health" | jq '.'

# Test 2: Authenticate using JSON
echo ""
echo "🔐 Authenticating with Vault..."
AUTH_JSON=$(cat << EOF
{
  "role": "$VAULT_ROLE",
  "jwt": "$KUBE_TOKEN"
}
EOF
)

AUTH_RESPONSE=$(curl -s \
    --header "Content-Type: application/json" \
    --request POST \
    --data "$AUTH_JSON" \
    "$VAULT_ADDR/v1/auth/kubernetes/login")

echo "Auth response:"
echo "$AUTH_RESPONSE" | jq '.'

# Extract token
VAULT_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.auth.client_token // empty')

if [ -n "$VAULT_TOKEN" ] && [ "$VAULT_TOKEN" != "null" ]; then
    echo "✅ Got Vault token: ${VAULT_TOKEN:0:20}..."
    
    # Test 3: Read secret
    echo ""
    echo "📖 Reading secret..."
    SECRET_RESPONSE=$(curl -s \
        --header "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/$SECRET_PATH")
    
    echo "Secret response:"
    echo "$SECRET_RESPONSE" | jq '.'
    
    # Extract specific values
    if echo "$SECRET_RESPONSE" | jq -e '.data.data' >/dev/null 2>&1; then
        echo ""
        echo "🎉 Successfully retrieved secrets!"
        echo "Available keys:"
        echo "$SECRET_RESPONSE" | jq -r '.data.data | keys[]' | sed 's/^/  - /'
        
        # Show sample values (first 20 chars for security)
        echo ""
        echo "Sample values:"
        echo "$SECRET_RESPONSE" | jq -r '.data.data | to_entries[] | "  \(.key): \(.value[:20])..."'
    else
        echo "❌ No secret data found"
    fi
else
    echo "❌ Failed to get Vault token"
fi
