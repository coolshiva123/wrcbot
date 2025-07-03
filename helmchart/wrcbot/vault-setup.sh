#!/bin/bash
set -e

echo "Starting Vault configuration..."

# Function to check if Vault is ready
check_vault_status() {
    kubectl -n wrcbot exec vault-0 -- vault status >/dev/null 2>&1
}

# Function to check if auth method is enabled
check_auth_method() {
    local auth_method=$1
    kubectl -n wrcbot exec vault-0 -- vault auth list | grep "^$auth_method/"
}

echo "Waiting for Vault to be ready..."
until check_vault_status; do
    echo "Vault is not ready yet... waiting 5 seconds"
    sleep 5
done

echo "Vault is ready. Proceeding with configuration..."

# Enable Kubernetes auth if not already enabled
if ! check_auth_method "kubernetes"; then
    echo "Enabling Kubernetes auth method..."
    kubectl -n wrcbot exec vault-0 -- vault auth enable kubernetes
else
    echo "Kubernetes auth method already enabled"
fi

echo "Configuring Kubernetes auth method..."
kubectl -n wrcbot exec vault-0 -- sh -c '
# Get the Kubernetes CA certificate
KUBE_CA_CERT=$(cat /var/run/secrets/kubernetes.io/serviceaccount/ca.crt)
KUBE_TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)

# Configure the Kubernetes auth method
vault write auth/kubernetes/config \
    kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
    kubernetes_ca_cert="$KUBE_CA_CERT" \
    token_reviewer_jwt="$KUBE_TOKEN" \
    issuer="https://kubernetes.default.svc.cluster.local"
'

echo "Creating Vault policy for wrcbot..."
kubectl -n wrcbot exec vault-0 -- sh -c '
cat <<EOF | vault policy write wrcbot-policy -
path "secret/data/wrcbot-config" {
  capabilities = ["read"]
}
path "secret/metadata/wrcbot-config" {
  capabilities = ["read"]
}
EOF'

echo "Creating Kubernetes auth role for wrcbot..."
kubectl -n wrcbot exec vault-0 -- vault write auth/kubernetes/role/wrcbot-role \
    bound_service_account_names=wrcbot-sa \
    bound_service_account_namespaces=wrcbot \
    policies=wrcbot-policy \
    ttl=1h

echo "Storing bot configuration in Vault..."
kubectl -n wrcbot exec vault-0 -- vault kv put secret/wrcbot-config \
    config="{
        \"BOT_ADMINS\": [\"admin@example.com\"],
        \"BOT_IDENTITY\": {
            \"token\": \"${BOT_TOKEN:-xoxb-your-token}\",
            \"signing_secret\": \"${SIGNING_SECRET:-your-signing-secret}\",
            \"app_token\": \"${APP_TOKEN:-xapp-your-app-token}\"
        },
        \"BOT_PREFIX\": \"!\"
    }"

echo "Verifying the configuration..."
echo "Checking Vault policy..."
kubectl -n wrcbot exec vault-0 -- vault policy read wrcbot-policy

echo "Checking Kubernetes auth role..."
kubectl -n wrcbot exec vault-0 -- vault read auth/kubernetes/role/wrcbot-role

echo "Checking stored secret (without revealing sensitive data)..."
kubectl -n wrcbot exec vault-0 -- vault kv metadata get secret/wrcbot-config

echo "Configuration completed successfully!"
echo "You can now deploy your application using:"
echo "kubectl apply -f argoapp/wrcbotapp.yaml"
