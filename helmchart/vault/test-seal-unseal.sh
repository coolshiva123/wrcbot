#!/bin/bash

# Vault Seal/Unseal Test Script
# This script tests the seal and unseal functionality of Vault

set -e

echo "🔐 Vault Seal/Unseal Test"
echo "========================="

# Check if vault-keys secret exists
if ! kubectl get secret vault-keys -n wrcbot &>/dev/null; then
    echo "❌ vault-keys secret not found. Run ./initialize-vault.sh first"
    exit 1
fi

# Get credentials
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)

echo "🔍 Initial Vault status:"
curl -s http://localhost:8200/v1/sys/health | jq '{initialized, sealed, version}'

echo ""
echo "🔒 Testing SEAL operation..."
seal_response=$(curl -s -X POST \
    -H "X-Vault-Token: $ROOT_TOKEN" \
    http://localhost:8200/v1/sys/seal)

echo "✅ Vault sealed successfully"

echo ""
echo "🔍 Vault status after sealing:"
curl -s http://localhost:8200/v1/sys/health | jq '{initialized, sealed, version}'

echo ""
echo "🔓 Testing UNSEAL operation..."
unseal_response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "{\"key\": \"$UNSEAL_KEY\"}" \
    http://localhost:8200/v1/sys/unseal)

sealed=$(echo "$unseal_response" | jq -r '.sealed')

if [ "$sealed" = "false" ]; then
    echo "✅ Vault unsealed successfully"
else
    echo "❌ Failed to unseal Vault"
    echo "$unseal_response"
    exit 1
fi

echo ""
echo "🔍 Final Vault status:"
curl -s http://localhost:8200/v1/sys/health | jq '{initialized, sealed, version}'

echo ""
echo "🎉 Seal/Unseal test completed successfully!"
echo ""
echo "🔑 Credentials for reference:"
echo "   Root Token: $ROOT_TOKEN"
echo "   Unseal Key: $UNSEAL_KEY"
