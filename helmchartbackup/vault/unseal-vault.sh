#!/bin/bash
# Vault Unsealing Script for ArgoCD Deployment
# Usage: ./helmchart/vault/unseal-vault.sh [--show-token]

SHOW_TOKEN=false
if [[ "$1" == "--show-token" ]]; then
    SHOW_TOKEN=true
fi

echo "🔓 Unsealing Vault deployed via ArgoCD..."

# Check if vault is running
if ! kubectl get deployment vault -n wrcbot &>/dev/null; then
    echo "❌ Vault deployment not found in wrcbot namespace"
    exit 1
fi

# Wait for vault pod to be ready
echo "⌛ Waiting for Vault pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=vault -n wrcbot --timeout=60s || {
    echo "❌ Timeout waiting for Vault pod to be ready"
    exit 1
}

# Check vault status
echo "📊 Checking Vault status..."
if kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Sealed.*false"; then
    echo "✅ Vault is already unsealed!"
    
    # Show UI access info if token requested, even when already unsealed
    if [ "$SHOW_TOKEN" = true ]; then
        echo "🔑 Retrieving root token..."
        ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)
        if [ -n "$ROOT_TOKEN" ]; then
            echo ""
            echo "🌐 Vault UI Access:"
            echo "   URL: http://localhost:8200"
            echo "   Root Token: $ROOT_TOKEN"
            echo ""
            echo "💡 Start port-forward with:"
            echo "   kubectl port-forward svc/vault 8200:8200 -n wrcbot"
        fi
    fi
    
    exit 0
fi

# Function to check vault-init logs
check_init_status() {
    echo "📋 Checking vault-init container status..."
    INIT_LOGS=$(kubectl logs -n wrcbot -l app.kubernetes.io/name=vault -c vault-init --tail=50)
    if echo "$INIT_LOGS" | grep -q "Vault configuration completed successfully"; then
        echo "✅ Vault initialization completed successfully"
        return 0
    else
        echo "⏳ Vault initialization still in progress..."
        echo "Recent logs from vault-init container:"
        echo "$INIT_LOGS"
        return 1
    fi
}

# Get unseal key from secret
echo "🔑 Retrieving unseal key..."
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' 2>/dev/null | base64 -d)

if [ -z "$UNSEAL_KEY" ]; then
    echo "❌ Could not retrieve unseal key from vault-keys secret"
    exit 1
fi

# Get root token if requested
if [ "$SHOW_TOKEN" = true ]; then
    echo "🔑 Retrieving root token..."
    ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)
    if [ -z "$ROOT_TOKEN" ]; then
        echo "❌ Could not retrieve root token from vault-keys secret"
        exit 1
    fi
fi

# Unseal vault
echo "🔓 Unsealing Vault..."
if ! kubectl exec deployment/vault -n wrcbot -- vault operator unseal "$UNSEAL_KEY" 2>/dev/null; then
    echo "❌ Failed to unseal Vault"
    exit 1
fi
echo "✅ Vault successfully unsealed!"

# Wait for vault-init to complete
echo "⌛ Waiting for vault-init to complete..."
RETRIES=0
while ! check_init_status && [ $RETRIES -lt 12 ]; do
    echo "⏳ Waiting 5 seconds before checking again..."
    sleep 5
    RETRIES=$((RETRIES + 1))
done

if [ $RETRIES -eq 12 ]; then
    echo "❌ Timeout waiting for vault-init to complete"
    exit 1
fi

# Verify status
echo "📊 Final status:"
kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null || true
    
    # Show UI access info if token requested
    if [ "$SHOW_TOKEN" = true ]; then
        echo ""
        echo "🌐 Vault UI Access:"
        echo "   URL: http://localhost:8200"
        echo "   Root Token: $ROOT_TOKEN"
        echo ""
        echo "💡 Start port-forward with:"
        echo "   kubectl port-forward svc/vault 8200:8200 -n wrcbot"
    fi
else
    echo "❌ Failed to unseal Vault"
    exit 1
fi
