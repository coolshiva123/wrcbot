#!/bin/bash
# Vault Unsealing Script for ArgoCD Deployment
# Usage: ./unseal-vault.sh

echo "🔓 Unsealing Vault deployed via ArgoCD..."

# Check if vault is running
if ! kubectl get deployment vault -n wrcbot &>/dev/null; then
    echo "❌ Vault deployment not found in wrcbot namespace"
    exit 1
fi

# Check vault status
echo "📊 Checking Vault status..."
if kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Sealed.*false"; then
    echo "✅ Vault is already unsealed!"
    exit 0
fi

# Get unseal key from secret
echo "🔑 Retrieving unseal key..."
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' 2>/dev/null | base64 -d)

if [ -z "$UNSEAL_KEY" ]; then
    echo "❌ Could not retrieve unseal key from vault-keys secret"
    exit 1
fi

# Unseal vault
echo "🔓 Unsealing Vault..."
if kubectl exec deployment/vault -n wrcbot -- vault operator unseal "$UNSEAL_KEY" 2>/dev/null; then
    echo "✅ Vault successfully unsealed!"
    
    # Verify status
    echo "📊 Final status:"
    kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null || true
else
    echo "❌ Failed to unseal Vault"
    exit 1
fi
