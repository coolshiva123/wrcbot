#!/bin/bash
# Get Vault credentials for UI access
# Usage: ./get-vault-credentials.sh

echo "🔑 Vault Credentials"
echo "===================="

# Check if vault-keys secret exists
if ! kubectl get secret vault-keys -n wrcbot &>/dev/null; then
    echo "❌ vault-keys secret not found in wrcbot namespace"
    exit 1
fi

# Get root token
echo "🔐 Root Token:"
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)
echo "   $ROOT_TOKEN"

# Get unseal key
echo ""
echo "🔑 Unseal Key:"
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)
echo "   $UNSEAL_KEY"

echo ""
echo "🌐 Vault UI Access:"
echo "   1. Start port-forward: kubectl port-forward svc/vault 8200:8200 -n wrcbot"
echo "   2. Open browser: http://localhost:8200"
echo "   3. Login with root token: $ROOT_TOKEN"

echo ""
echo "🚀 CLI Access:"
echo "   export VAULT_ADDR='http://localhost:8200'"
echo "   export VAULT_TOKEN='$ROOT_TOKEN'"
echo "   vault status"
