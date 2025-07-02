#!/bin/bash
# Fallback script to access Vault secrets directly with root token
# Use this if Kubernetes Auth continues to fail

echo "🔐 Direct Vault Access (Fallback Method)"
echo "========================================"

VAULT_ADDR="http://10.105.105.195:8200"
SECRET_PATH="secret/data/wrcbot/config"

echo "📋 Configuration:"
echo "   VAULT_ADDR: $VAULT_ADDR"
echo "   SECRET_PATH: $SECRET_PATH"
echo ""

# This would need to be set with the root token
# For security, you'd want to create a limited-scope token instead
echo "⚠️  This method requires a Vault token with read access to secrets"
echo "   Set VAULT_TOKEN environment variable with a valid token"
echo ""

if [ -n "$VAULT_TOKEN" ]; then
    echo "🔍 Testing direct secret access..."
    SECRET_RESPONSE=$(curl -s \
        --header "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/$SECRET_PATH")
    
    echo "Secret response:"
    echo "$SECRET_RESPONSE" | jq '.'
    
    if echo "$SECRET_RESPONSE" | jq -e '.data.data' >/dev/null 2>&1; then
        echo ""
        echo "✅ Secret data found!"
        echo "Available keys:"
        echo "$SECRET_RESPONSE" | jq -r '.data.data | keys[]' | sed 's/^/  - /'
        
        echo ""
        echo "Example: Get bot_token"
        BOT_TOKEN=$(echo "$SECRET_RESPONSE" | jq -r '.data.data.bot_token')
        echo "bot_token: ${BOT_TOKEN:0:20}..."
    else
        echo "❌ No secret data found"
    fi
else
    echo "❌ No VAULT_TOKEN provided"
    echo ""
    echo "To use this method:"
    echo "1. Get root token: kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d"
    echo "2. Set token: export VAULT_TOKEN=your-token-here"
    echo "3. Run this script again"
fi
