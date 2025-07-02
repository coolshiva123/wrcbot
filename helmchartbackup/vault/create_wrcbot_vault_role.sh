#!/bin/bash
# Script to create a Vault policy and Kubernetes Auth role for wrcbot to access /v1/secret/data/wrcbot/config
# Usage: ./create_wrcbot_vault_role.sh

set -e

# Set these variables as needed
VAULT_ADDR="http://127.0.0.1:8200"
VAULT_NAMESPACE="wrcbot"
VAULT_ROLE="wrcbot"
K8S_SA="wrcbot-sa"
K8S_NAMESPACE="wrcbot"
VAULT_POLICY="wrcbot-policy"

# Step 0: Prompt for Vault token
read -s -p "Enter your Vault root/admin token: " VAULT_TOKEN
export VAULT_TOKEN

echo
# Step 1: Port-forward Vault service to localhost
if lsof -i:8200 | grep LISTEN; then
  echo "Port 8200 is already in use. Assuming an existing port-forward is running."
  PF_PID=""
else
  echo "Starting kubectl port-forward for Vault..."
  kubectl port-forward svc/vault -n $VAULT_NAMESPACE 8200:8200 &
  PF_PID=$!
  sleep 3
fi

# Step 2: Export VAULT_ADDR for the local Vault CLI
export VAULT_ADDR="http://127.0.0.1:8200"

# Step 2.5: Enable Kubernetes Auth method if not already enabled
echo "Enabling Kubernetes Auth method (if not already enabled)..."
if vault auth list | grep -q '^kubernetes/'; then
  echo "Kubernetes Auth method already enabled."
else
  vault auth enable kubernetes
fi

# Step 3: Create the policy for the correct secret path
cat <<EOF > /tmp/${VAULT_POLICY}.hcl
path "secret/data/wrcbot/config" {
  capabilities = ["read"]
}
EOF
vault policy write $VAULT_POLICY /tmp/${VAULT_POLICY}.hcl

# Step 4: Create the Kubernetes Auth role
echo "Creating Vault Kubernetes Auth role..."
vault write auth/kubernetes/role/${VAULT_ROLE} \
  bound_service_account_names=${K8S_SA} \
  bound_service_account_namespaces=${K8S_NAMESPACE} \
  policies=${VAULT_POLICY} \
  ttl=1h

# Step 5: Cleanup port-forward
if [ -n "$PF_PID" ]; then
  kill $PF_PID
  wait $PF_PID 2>/dev/null || true
fi

echo "Vault policy and role created for /v1/secret/data/wrcbot/config."
