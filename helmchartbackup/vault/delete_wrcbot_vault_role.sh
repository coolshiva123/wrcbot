#!/bin/bash
# Script to clean up all Vault policies and Kubernetes Auth roles related to wrcbot
# Usage: ./cleanup_wrcbot_vault.sh

set -e

# Set these variables as needed
VAULT_ADDR="http://127.0.0.1:8200"
VAULT_NAMESPACE="wrcbot"

# Step 0: Prompt for Vault token
read -s -p "Enter your Vault root/admin token: " VAULT_TOKEN
export VAULT_TOKEN

echo
# Step 1: Port-forward Vault service to localhost
# Check if port 8200 is already in use
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

# Step 3: Delete all wrcbot-related policies and k8s auth roles
echo "Deleting all Vault Kubernetes Auth roles related to wrcbot..."
for role in $(vault list -format=json auth/kubernetes/role | jq -r '.[]' | grep wrcbot); do
  echo "Deleting Vault Kubernetes Auth role: $role"
  vault delete auth/kubernetes/role/$role || true
  sleep 1
done
echo "Deleting all Vault policies related to wrcbot..."
for policy in $(vault policy list | grep wrcbot); do
  echo "Deleting Vault policy: $policy"
  vault policy delete $policy || true
  sleep 1
done

# Step 4: Cleanup port-forward
if [ -n "$PF_PID" ]; then
  kill $PF_PID
  wait $PF_PID 2>/dev/null || true
fi

echo "All wrcbot Vault policies and Kubernetes Auth roles have been deleted."
