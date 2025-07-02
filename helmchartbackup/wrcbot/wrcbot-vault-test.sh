#!/bin/bash
# Script to debug and test Vault authentication from wrcbot pod
# Run this from the wrcbot pod

echo "======== Service Account Information ========"
echo "Pod is using service account: $(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)"
ls -la /var/run/secrets/kubernetes.io/serviceaccount/

echo "======== Token Information ========"
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
echo "Token exists: $(if [[ -n $TOKEN ]]; then echo YES; else echo NO; fi)"
echo "Token length: $(echo $TOKEN | wc -c)"
echo "First 20 characters: $(echo $TOKEN | head -c 20)..."

echo "======== Attempting Vault Authentication ========"
VAULT_RESPONSE=$(curl -s --request POST \
  --data "{\"role\": \"wrcbot-role\", \"jwt\": \"$TOKEN\"}" \
  http://vault.wrcbot.svc.cluster.local:8200/v1/auth/kubernetes/login)

echo "Response:"
echo "$VAULT_RESPONSE"

# Check if authentication succeeded
if echo "$VAULT_RESPONSE" | grep -q "client_token"; then
    echo "Authentication successful!"
    
    # Extract the client token
    CLIENT_TOKEN=$(echo "$VAULT_RESPONSE" | grep -o '"client_token":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    
    echo "======== Fetching Secret with Token ========"
    SECRET_RESPONSE=$(curl -s -H "X-Vault-Token: $CLIENT_TOKEN" \
      http://vault.wrcbot.svc.cluster.local:8200/v1/secret/data/wrcbot/config)
    
    echo "Secret Response:"
    echo "$SECRET_RESPONSE"
else
    echo "Authentication failed. Detailed debugging:"
    
    echo "======== Network Connectivity Test ========"
    curl -v http://vault.wrcbot.svc.cluster.local:8200/v1/sys/health
    
    echo "======== DNS Resolution Test ========"
    nslookup vault.wrcbot.svc.cluster.local || echo "nslookup not available"
    
    echo "======== Testing with a different role ========"
    curl -s --request POST \
      --data "{\"role\": \"wrcbot\", \"jwt\": \"$TOKEN\"}" \
      http://vault.wrcbot.svc.cluster.local:8200/v1/auth/kubernetes/login
fi
