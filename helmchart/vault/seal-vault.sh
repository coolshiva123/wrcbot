#!/bin/bash
# Vault Sealing Script for ArgoCD Deployment
# Usage: ./helmchart/vault/seal-vault.sh

echo "🔒 Sealing Vault deployed via ArgoCD..."

# Check if vault is running
if ! kubectl get deployment vault -n wrcbot &>/dev/null; then
    echo "❌ Vault deployment not found in wrcbot namespace"
    exit 1
fi

# Check vault status
echo "📊 Checking Vault status..."
VAULT_STATUS=$(kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null || echo "Failed to get status")
echo "$VAULT_STATUS"

# Check if vault is already sealed
if echo "$VAULT_STATUS" | grep -q "Sealed.*true"; then
    echo "✅ Vault is already sealed!"
    exit 0
fi

# Seal vault
echo "🔒 Sealing Vault..."

# Get root token for authentication
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)

if [ -z "$ROOT_TOKEN" ]; then
    echo "❌ Could not retrieve root token from vault-keys secret"
    echo "   Sealing requires authentication. Make sure vault-keys secret exists."
    exit 1
fi

# Seal vault with authentication
if kubectl exec deployment/vault -n wrcbot -- env VAULT_TOKEN="$ROOT_TOKEN" vault operator seal 2>/dev/null; then
    echo "✅ Vault sealed successfully"
else
    echo "❌ Failed to seal Vault"
    exit 1
fi

# Verify final status
echo "📊 Final status:"
kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null || true

echo ""
echo "🔓 To unseal Vault again, run: ./unseal-vault.sh"
