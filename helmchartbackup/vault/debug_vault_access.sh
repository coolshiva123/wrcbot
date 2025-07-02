#!/bin/bash
# Comprehensive Vault access debugging script for wrcbot pod
# Usage: Run this script from inside the wrcbot pod

set -e

echo "🔍 WRCBot Vault Access Debug Script"
echo "===================================="

# Configuration
VAULT_ADDR="http://vault.wrcbot.svc.cluster.local:8200"
VAULT_ROLE="wrcbot"
VAULT_SECRET_PATH="secret/data/wrcbot/config"

echo "📋 Configuration:"
echo "   VAULT_ADDR: $VAULT_ADDR"
echo "   VAULT_ROLE: $VAULT_ROLE"
echo "   SECRET_PATH: $VAULT_SECRET_PATH"
echo ""

# Step 1: Check if we're in a Kubernetes pod
echo "🔍 Step 1: Checking Kubernetes environment..."
if [ -f "/var/run/secrets/kubernetes.io/serviceaccount/token" ]; then
    echo "✅ ServiceAccount token found"
    KUBE_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
    echo "   Token length: ${#KUBE_TOKEN} characters"
    
    NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
    echo "   Namespace: $NAMESPACE"
else
    echo "❌ ServiceAccount token not found - pod may not be using a ServiceAccount"
    exit 1
fi

# Step 2: Check network connectivity to Vault
echo ""
echo "🔍 Step 2: Testing network connectivity to Vault..."
if curl -s --connect-timeout 5 "$VAULT_ADDR/v1/sys/health" >/dev/null; then
    echo "✅ Can reach Vault at $VAULT_ADDR"
else
    echo "❌ Cannot reach Vault at $VAULT_ADDR"
    echo "   Trying alternative addresses..."
    
    # Try different service names
    ALT_ADDRS=(
        "http://vault.wrcbot.svc.cluster.local:8200"
        "http://vault:8200"
        "http://10.105.105.195:8200"
        "http://vault.default.svc.cluster.local:8200"
    )
    
    for addr in "${ALT_ADDRS[@]}"; do
        echo "   Trying $addr..."
        if curl -s --connect-timeout 5 "$addr/v1/sys/health" >/dev/null; then
            echo "✅ Found Vault at $addr"
            VAULT_ADDR="$addr"
            break
        fi
    done
fi

# Step 3: Check Vault health
echo ""
echo "🔍 Step 3: Checking Vault health..."
HEALTH_RESPONSE=$(curl -s "$VAULT_ADDR/v1/sys/health" || echo "")
if [ -n "$HEALTH_RESPONSE" ]; then
    echo "✅ Vault health response received"
    if echo "$HEALTH_RESPONSE" | jq -e '.sealed == false' >/dev/null 2>&1; then
        echo "✅ Vault is unsealed"
    else
        echo "❌ Vault is sealed or unhealthy"
        echo "   Response: $HEALTH_RESPONSE"
    fi
else
    echo "❌ No response from Vault health endpoint"
    exit 1
fi

# Step 4: Attempt authentication
echo ""
echo "🔍 Step 4: Attempting Kubernetes authentication..."
AUTH_RESPONSE=$(curl -s --request POST \
    --data "{\"role\": \"$VAULT_ROLE\", \"jwt\": \"$KUBE_TOKEN\"}" \
    "$VAULT_ADDR/v1/auth/kubernetes/login" || echo "")

if [ -n "$AUTH_RESPONSE" ]; then
    echo "✅ Authentication response received"
    
    # Check if authentication was successful
    if echo "$AUTH_RESPONSE" | jq -e '.auth.client_token' >/dev/null 2>&1; then
        echo "✅ Authentication successful"
        VAULT_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.auth.client_token')
        echo "   Token length: ${#VAULT_TOKEN} characters"
        
        # Step 5: Attempt to read secret
        echo ""
        echo "🔍 Step 5: Attempting to read secret..."
        SECRET_RESPONSE=$(curl -s \
            --header "X-Vault-Token: $VAULT_TOKEN" \
            "$VAULT_ADDR/v1/$VAULT_SECRET_PATH" || echo "")
        
        if [ -n "$SECRET_RESPONSE" ]; then
            echo "✅ Secret response received"
            if echo "$SECRET_RESPONSE" | jq -e '.data' >/dev/null 2>&1; then
                echo "✅ Secret data found"
                echo "   Secret keys:"
                echo "$SECRET_RESPONSE" | jq -r '.data.data | keys[]' | sed 's/^/     - /'
            else
                echo "❌ No secret data found"
                echo "   Response: $SECRET_RESPONSE"
            fi
        else
            echo "❌ No response when reading secret"
        fi
        
    else
        echo "❌ Authentication failed"
        echo "   Response: $AUTH_RESPONSE"
        
        # Check for common error patterns
        if echo "$AUTH_RESPONSE" | grep -q "permission denied"; then
            echo ""
            echo "💡 Troubleshooting suggestions:"
            echo "   1. Check if the Vault role '$VAULT_ROLE' exists"
            echo "   2. Verify the ServiceAccount name matches the role configuration"
            echo "   3. Ensure the namespace matches the role configuration"
        elif echo "$AUTH_RESPONSE" | grep -q "invalid role name"; then
            echo ""
            echo "💡 The Vault role '$VAULT_ROLE' does not exist"
            echo "   Run the create_wrcbot_vault_role.sh script to create it"
        fi
    fi
else
    echo "❌ No response from Vault authentication endpoint"
fi

echo ""
echo "🔍 Debug Summary:"
echo "   ServiceAccount Token: ${KUBE_TOKEN:0:20}..."
echo "   Vault Address: $VAULT_ADDR"
echo "   Vault Role: $VAULT_ROLE"
echo "   Secret Path: $VAULT_SECRET_PATH"

# Additional debugging info
echo ""
echo "🔍 Additional Debug Information:"
echo "   Hostname: $(hostname)"
echo "   Pod IP: $(hostname -i)"
echo "   Environment variables:"
env | grep -E '^(KUBERNETES|VAULT)' | sed 's/^/     /'

echo ""
echo "🔧 Step 6: Creating test secrets using JSON method..."

# Function to create test secrets in Vault
create_test_secrets() {
    local vault_token="$1"
    
    # Create JSON payload with test bot configuration
    cat > /tmp/wrcbot_secrets.json << 'EOF'
{
  "data": {
    "bot_token": "xoxb-test-slack-bot-token-12345",
    "signing_secret": "test-signing-secret-abcdef",
    "app_token": "xapp-test-app-token-67890",
    "admin_users": "@admin1,@admin2",
    "log_level": "DEBUG"
  }
}
EOF

    echo "   Created JSON payload for secrets"
    
    # Put secrets into Vault using JSON
    WRITE_RESPONSE=$(curl -s \
        --header "X-Vault-Token: $vault_token" \
        --header "Content-Type: application/json" \
        --request POST \
        --data @/tmp/wrcbot_secrets.json \
        "$VAULT_ADDR/v1/$VAULT_SECRET_PATH" || echo "")
    
    if [ -n "$WRITE_RESPONSE" ]; then
        if echo "$WRITE_RESPONSE" | jq -e '.errors' >/dev/null 2>&1; then
            echo "❌ Error writing secrets:"
            echo "$WRITE_RESPONSE" | jq -r '.errors[]' | sed 's/^/     /'
        else
            echo "✅ Test secrets written successfully"
            
            # Verify by reading them back
            echo "   Verifying secrets..."
            READ_RESPONSE=$(curl -s \
                --header "X-Vault-Token: $vault_token" \
                "$VAULT_ADDR/v1/$VAULT_SECRET_PATH" || echo "")
            
            if echo "$READ_RESPONSE" | jq -e '.data.data' >/dev/null 2>&1; then
                echo "✅ Secrets verified - available keys:"
                echo "$READ_RESPONSE" | jq -r '.data.data | keys[]' | sed 's/^/     - /'
            fi
        fi
    else
        echo "❌ No response when writing secrets"
    fi
    
    # Clean up temp file
    rm -f /tmp/wrcbot_secrets.json
}

# If we have a valid token, try to create test secrets
if [ -n "$VAULT_TOKEN" ] && [ "$VAULT_TOKEN" != "null" ]; then
    create_test_secrets "$VAULT_TOKEN"
else
    echo "⚠️  No valid Vault token available - cannot create test secrets"
    echo "   Please ensure authentication is working first"
fi

echo ""
echo "✅ Debug script completed"
