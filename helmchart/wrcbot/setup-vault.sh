#!/bin/bash
# Script to verify and configure Vault auth

# Wait for Vault to be ready
until kubectl exec -n wrcbot vault-0 -- vault status; do
    echo "Waiting for Vault to be ready..."
    sleep 5
done

# Enable kubernetes auth method if not already enabled
kubectl exec -n wrcbot vault-0 -- vault auth enable kubernetes || true

# Configure kubernetes auth
kubectl exec -n wrcbot vault-0 -- sh -c 'vault write auth/kubernetes/config \
    kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
    token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    issuer="https://kubernetes.default.svc.cluster.local"'

# Create policy for wrcbot
kubectl exec -n wrcbot vault-0 -- sh -c 'cat << EOF | vault policy write wrcbot-policy -
path "secret/wrcbot-config" {
  capabilities = ["read"]
}
EOF'

# Create role for wrcbot
kubectl exec -n wrcbot vault-0 -- vault write auth/kubernetes/role/wrcbot-role \
    bound_service_account_names=wrcbot-sa \
    bound_service_account_namespaces=wrcbot \
    policies=wrcbot-policy \
    ttl=1h

# Store test config in Vault
kubectl exec -n wrcbot vault-0 -- vault kv put secret/wrcbot-config \
    config='{"BOT_ADMINS": ["admin@example.com"], "BOT_IDENTITY": {"token": "test-token", "signing_secret": "test-secret", "app_token": "test-app-token"}, "BOT_PREFIX": "!"}'

echo "Vault configuration completed!"
