#!/bin/bash

# Vault Initialization Script
# This script initializes a fresh Vault instance and stores the credentials securely

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/home/ec2-user/vault-persistent-data"

echo "🚀 Vault Initialization Script"
echo "================================"

# Function to check if Vault is accessible
check_vault_connection() {
    echo "🔍 Checking Vault connection..."
    if ! curl -s http://localhost:8200/v1/sys/health > /dev/null; then
        echo "❌ Cannot connect to Vault. Please ensure port-forward is running:"
        echo "   kubectl port-forward svc/vault 8200:8200 -n wrcbot"
        exit 1
    fi
    echo "✅ Vault connection confirmed"
}

# Function to check if Vault is initialized
check_vault_status() {
    local status=$(curl -s http://localhost:8200/v1/sys/health | jq -r '.initialized')
    echo "📊 Vault initialization status: $status"
    return 0
}

# Function to initialize Vault
initialize_vault() {
    echo "🔧 Initializing Vault with single key share..."
    
    # Initialize Vault and capture output
    local init_output=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"secret_shares": 1, "secret_threshold": 1}' \
        http://localhost:8200/v1/sys/init)
    
    if [ $? -ne 0 ] || [ -z "$init_output" ]; then
        echo "❌ Failed to initialize Vault"
        exit 1
    fi
    
    # Extract credentials
    local root_token=$(echo "$init_output" | jq -r '.root_token')
    local unseal_key=$(echo "$init_output" | jq -r '.keys[0]')
    
    if [ "$root_token" = "null" ] || [ "$unseal_key" = "null" ]; then
        echo "❌ Failed to extract credentials from initialization"
        echo "Response: $init_output"
        exit 1
    fi
    
    echo "✅ Vault initialized successfully!"
    echo "🔑 Root Token: $root_token"
    echo "🔐 Unseal Key: $unseal_key"
    
    # Store credentials in variables for later use
    VAULT_ROOT_TOKEN="$root_token"
    VAULT_UNSEAL_KEY="$unseal_key"
    
    # Store in Kubernetes secret
    echo "💾 Storing credentials in Kubernetes secret..."
    kubectl create secret generic vault-keys -n wrcbot \
        --from-literal=root-token="$root_token" \
        --from-literal=unseal-key="$unseal_key" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    echo "✅ Credentials stored in vault-keys secret"
    
    # Backup credentials to file
    mkdir -p "$BACKUP_DIR"
    cat > "$BACKUP_DIR/vault-credentials.json" << EOF
{
  "root_token": "$root_token",
  "unseal_key": "$unseal_key",
  "initialized_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "vault_version": "$(curl -s http://localhost:8200/v1/sys/health | jq -r '.version')"
}
EOF
    chmod 600 "$BACKUP_DIR/vault-credentials.json"
    echo "💾 Credentials backed up to $BACKUP_DIR/vault-credentials.json"
}

# Function to unseal Vault
unseal_vault() {
    echo "🔓 Unsealing Vault..."
    
    if [ -z "$VAULT_UNSEAL_KEY" ]; then
        echo "❌ Unseal key not available"
        exit 1
    fi
    
    local unseal_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"$VAULT_UNSEAL_KEY\"}" \
        http://localhost:8200/v1/sys/unseal)
    
    local sealed=$(echo "$unseal_response" | jq -r '.sealed')
    
    if [ "$sealed" = "false" ]; then
        echo "✅ Vault unsealed successfully!"
    else
        echo "❌ Failed to unseal Vault"
        echo "Response: $unseal_response"
        exit 1
    fi
}

# Function to verify Vault is ready
verify_vault_ready() {
    echo "🔍 Verifying Vault is ready..."
    
    local health=$(curl -s http://localhost:8200/v1/sys/health)
    local initialized=$(echo "$health" | jq -r '.initialized')
    local sealed=$(echo "$health" | jq -r '.sealed')
    
    if [ "$initialized" = "true" ] && [ "$sealed" = "false" ]; then
        echo "✅ Vault is initialized and unsealed"
        echo "🌐 Vault UI: http://localhost:8200"
        echo "🔑 Root Token: $VAULT_ROOT_TOKEN"
        return 0
    else
        echo "❌ Vault is not ready (initialized: $initialized, sealed: $sealed)"
        return 1
    fi
}

# Function to setup basic secret engine
setup_secret_engine() {
    echo "🔧 Setting up KV secret engine..."
    
    # Enable KV v2 secret engine at secret/
    curl -s -X POST \
        -H "X-Vault-Token: $VAULT_ROOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"type": "kv", "options": {"version": "2"}}' \
        http://localhost:8200/v1/sys/mounts/secret
    
    echo "✅ KV secret engine enabled at secret/"
}

# Main execution
main() {
    echo "📋 Prerequisites Check:"
    echo "  - Vault pod must be running"
    echo "  - Port forward must be active (kubectl port-forward svc/vault 8200:8200 -n wrcbot)"
    echo ""
    
    # Check if port forward is running
    if ! ss -tulpn | grep -q ":8200.*kubectl" 2>/dev/null; then
        echo "⚠️  Port forward may not be running. Starting it now..."
        kubectl port-forward svc/vault 8200:8200 -n wrcbot &
        sleep 5
    fi
    
    check_vault_connection
    
    local vault_initialized=$(curl -s http://localhost:8200/v1/sys/health | jq -r '.initialized')
    check_vault_status
    
    if [ "$vault_initialized" = "true" ]; then
        echo "⚠️  Vault is already initialized!"
        echo ""
        echo "Options:"
        echo "1. Use existing credentials (if available)"
        echo "2. Reinitialize (will destroy existing data)"
        echo ""
        read -p "Choose option (1/2): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[2]$ ]]; then
            echo "🚨 Reinitializing will destroy all existing data!"
            read -p "Are you sure? (type 'yes' to confirm): " confirm
            if [ "$confirm" != "yes" ]; then
                echo "❌ Initialization cancelled"
                exit 1
            fi
            
            # Stop Vault, clear data, restart
            echo "🔄 Clearing Vault data..."
            kubectl delete pod -l app=vault -n wrcbot
            kubectl exec -n wrcbot $(kubectl get pod -l app=vault -n wrcbot -o jsonpath='{.items[0].metadata.name}' --wait=true) -- sh -c "rm -rf /vault/file/*" || true
            kubectl delete pod -l app=vault -n wrcbot
            
            echo "⏳ Waiting for Vault to restart..."
            kubectl wait --for=condition=ready pod -l app=vault -n wrcbot --timeout=300s
            sleep 10
            
            check_vault_connection
            vault_initialized=$(curl -s http://localhost:8200/v1/sys/health | jq -r '.initialized')
        else
            echo "🔍 Checking for existing credentials..."
            if kubectl get secret vault-keys -n wrcbot &>/dev/null; then
                VAULT_ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' | base64 -d)
                VAULT_UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)
                echo "✅ Found existing credentials"
                
                # Check if Vault is sealed and unseal if needed
                local health=$(curl -s http://localhost:8200/v1/sys/health)
                local sealed=$(echo "$health" | jq -r '.sealed')
                if [ "$sealed" = "true" ]; then
                    unseal_vault
                fi
                
                verify_vault_ready
                echo ""
                echo "🎉 Vault is ready to use!"
                echo "💡 Use './get-vault-credentials.sh' to view credentials"
                exit 0
            else
                echo "❌ No existing credentials found. Cannot proceed with initialized Vault."
                echo "💡 Either reinitialize (option 2) or restore from backup"
                exit 1
            fi
        fi
    fi
    
    if [ "$vault_initialized" = "false" ]; then
        initialize_vault
        unseal_vault
        verify_vault_ready
        setup_secret_engine
        
        echo ""
        echo "🎉 Vault initialization complete!"
        echo "================================"
        echo ""
        echo "📊 Summary:"
        echo "  ✅ Vault initialized and unsealed"
        echo "  ✅ Credentials stored in Kubernetes secret"
        echo "  ✅ Credentials backed up to $BACKUP_DIR/"
        echo "  ✅ KV secret engine enabled"
        echo ""
        echo "🔗 Next steps:"
        echo "  1. Access UI: http://localhost:8200"
        echo "  2. Login with root token: $VAULT_ROOT_TOKEN"
        echo "  3. Set up secrets: ./set-vault-secrets.sh"
        echo "  4. View credentials: ./get-vault-credentials.sh"
        echo ""
        echo "💾 Backup your data before minikube restarts:"
        echo "   ./backup-vault-data.sh"
        echo ""
    else
        echo "❌ Unknown vault status: $vault_initialized"
        exit 1
    fi
}

# Trap to cleanup background processes
trap 'jobs -p | xargs -r kill' EXIT

# Run main function
main "$@"
