#!/bin/bash
# Non-interactive script to create a Vault policy and Kubernetes Auth role for wrcbot
# Usage: ./create_wrcbot_vault_role_auto.sh

set -e

# Set these variables as needed
VAULT_ADDR="http://127.0.0.1:8200"
VAULT_NAMESPACE="wrcbot"
VAULT_ROLE="wrcbot"
K8S_SA="wrcbot-sa"
K8S_NAMESPACE="wrcbot"
VAULT_POLICY="wrcbot-policy"

# Get root token from Kubernetes secret
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)
export VAULT_TOKEN="$ROOT_TOKEN"

echo "Using root token: ${ROOT_TOKEN:0:10}..."

# Step 1: Port-forward Vault service to localhost
if lsof -i:8200 | grep LISTEN; then
  echo "Port 8200 is already in use. Killing existing port-forwards..."
  pkill -f "kubectl port-forward svc/vault" || true
  sleep 2
fi

echo "Starting kubectl port-forward for Vault..."
kubectl port-forward svc/vault -n $VAULT_NAMESPACE 8200:8200 &
PF_PID=$!
sleep 5

# Step 2: Export VAULT_ADDR for the local Vault CLI
export VAULT_ADDR="http://127.0.0.1:8200"

# Step 2.5: Enable Kubernetes Auth method if not already enabled
echo "Enabling Kubernetes Auth method (if not already enabled)..."
if vault auth list | grep -q '^kubernetes/'; then
  echo "Kubernetes Auth method already enabled."
else
  vault auth enable kubernetes
fi

# Step 3: Configure Kubernetes Auth
echo "Configuring Kubernetes Auth..."
K8S_HOST="https://kubernetes.default.svc"
K8S_CA_CERT=$(kubectl config view --raw --minify --flatten -o jsonpath='{.clusters[].cluster.certificate-authority-data}' | base64 -d)

vault write auth/kubernetes/config \
  token_reviewer_jwt="$(kubectl create token vault-auth -n $VAULT_NAMESPACE --duration=24h)" \
  kubernetes_host="$K8S_HOST" \
  kubernetes_ca_cert="$K8S_CA_CERT"

# Step 4: Create the policy for the correct secret path
echo "Creating Vault policy..."
cat <<EOF > /tmp/${VAULT_POLICY}.hcl
path "secret/data/wrcbot/config" {
  capabilities = ["read"]
}
EOF
vault policy write $VAULT_POLICY /tmp/${VAULT_POLICY}.hcl

# Step 5: Create the Kubernetes Auth role
echo "Creating Vault Kubernetes Auth role..."
vault write auth/kubernetes/role/${VAULT_ROLE} \
  bound_service_account_names=${K8S_SA} \
  bound_service_account_namespaces=${K8S_NAMESPACE} \
  policies=${VAULT_POLICY} \
  ttl=1h

# Step 6: Cleanup port-forward
if [ -n "$PF_PID" ]; then
  kill $PF_PID
  wait $PF_PID 2>/dev/null || true
fi

echo "✅ Vault policy and role created successfully for /v1/secret/data/wrcbot/config."
echo "   Policy: $VAULT_POLICY"
echo "   Role: $VAULT_ROLE"
echo "   ServiceAccount: $K8S_SA"
echo "   Namespace: $K8S_NAMESPACE"
