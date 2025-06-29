#!/bin/bash

# Vault Management Script for WRCBot
# This script helps manage Vault secrets and operations

set -e

NAMESPACE=${NAMESPACE:-wrcbot}
VAULT_SERVICE=${VAULT_SERVICE:-vault}
VAULT_PORT=${VAULT_PORT:-8200}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
}

# Get Vault credentials
get_vault_credentials() {
    log_info "Retrieving Vault credentials..."
    
    if ! kubectl get secret vault-keys -n $NAMESPACE &> /dev/null; then
        log_error "vault-keys secret not found. Has Vault been initialized?"
        exit 1
    fi
    
    export VAULT_TOKEN=$(kubectl get secret vault-keys -n $NAMESPACE -o jsonpath='{.data.root-token}' | base64 -d)
    export VAULT_UNSEAL_KEY=$(kubectl get secret vault-keys -n $NAMESPACE -o jsonpath='{.data.unseal-key}' | base64 -d)
    export VAULT_ADDR="http://localhost:8200"
    
    log_success "Vault credentials retrieved"
}

# Start port forward to Vault
start_port_forward() {
    log_info "Starting port forward to Vault..."
    
    # Kill any existing port forward
    pkill -f "kubectl.*port-forward.*$VAULT_SERVICE.*8200" 2>/dev/null || true
    
    # Start new port forward in background
    kubectl port-forward svc/$VAULT_SERVICE $VAULT_PORT:$VAULT_PORT -n $NAMESPACE > /dev/null 2>&1 &
    PORT_FORWARD_PID=$!
    
    # Wait for port forward to be ready
    sleep 3
    
    if ps -p $PORT_FORWARD_PID > /dev/null; then
        log_success "Port forward started (PID: $PORT_FORWARD_PID)"
        echo $PORT_FORWARD_PID > /tmp/vault-port-forward.pid
    else
        log_error "Failed to start port forward"
        exit 1
    fi
}

# Stop port forward
stop_port_forward() {
    if [ -f /tmp/vault-port-forward.pid ]; then
        PID=$(cat /tmp/vault-port-forward.pid)
        if ps -p $PID > /dev/null; then
            kill $PID
            log_success "Port forward stopped"
        fi
        rm -f /tmp/vault-port-forward.pid
    fi
}

# Check Vault status
check_vault_status() {
    log_info "Checking Vault status..."
    
    if ! command -v vault &> /dev/null; then
        log_warning "Vault CLI not found, using kubectl exec..."
        kubectl exec deployment/$VAULT_SERVICE -n $NAMESPACE -- vault status
    else
        vault status
    fi
}

# Unseal Vault manually
unseal_vault() {
    log_info "Unsealing Vault..."
    
    if ! command -v vault &> /dev/null; then
        kubectl exec deployment/$VAULT_SERVICE -n $NAMESPACE -- vault operator unseal $VAULT_UNSEAL_KEY
    else
        vault operator unseal $VAULT_UNSEAL_KEY
    fi
    
    log_success "Vault unsealed"
}

# Set bot secrets
set_bot_secrets() {
    log_info "Setting bot secrets..."
    
    echo "Please provide the following bot secrets:"
    read -p "Bot Token (xoxb-...): " BOT_TOKEN
    read -p "Admin Users (comma-separated): " ADMIN_USERS
    read -p "Bot Signing Secret: " BOT_SIGNING_SECRET
    read -p "Bot App Token (xapp-...): " BOT_APP_TOKEN
    
    if ! command -v vault &> /dev/null; then
        kubectl exec deployment/$VAULT_SERVICE -n $NAMESPACE -- sh -c "
            export VAULT_TOKEN=$VAULT_TOKEN
            vault kv put secret/wrcbot/config \
              bot_token='$BOT_TOKEN' \
              admin_users='$ADMIN_USERS' \
              bot_signing_secret='$BOT_SIGNING_SECRET' \
              bot_app_token='$BOT_APP_TOKEN'
        "
    else
        vault kv put secret/wrcbot/config \
          bot_token="$BOT_TOKEN" \
          admin_users="$ADMIN_USERS" \
          bot_signing_secret="$BOT_SIGNING_SECRET" \
          bot_app_token="$BOT_APP_TOKEN"
    fi
    
    log_success "Bot secrets set successfully"
}

# Get bot secrets
get_bot_secrets() {
    log_info "Retrieving bot secrets..."
    
    if ! command -v vault &> /dev/null; then
        kubectl exec deployment/$VAULT_SERVICE -n $NAMESPACE -- sh -c "
            export VAULT_TOKEN=$VAULT_TOKEN
            vault kv get secret/wrcbot/config
        "
    else
        vault kv get secret/wrcbot/config
    fi
}

# Refresh Kubernetes secrets
refresh_k8s_secrets() {
    log_info "Refreshing Kubernetes secrets from Vault..."
    
    # Create a one-time job from the CronJob
    JOB_NAME="manual-refresh-$(date +%s)"
    kubectl create job --from=cronjob/wrcbot-secret-refresh $JOB_NAME -n $NAMESPACE
    
    log_info "Waiting for job to complete..."
    kubectl wait --for=condition=complete --timeout=300s job/$JOB_NAME -n $NAMESPACE
    
    # Show job logs
    kubectl logs job/$JOB_NAME -n $NAMESPACE
    
    # Clean up job
    kubectl delete job $JOB_NAME -n $NAMESPACE
    
    log_success "Kubernetes secrets refreshed"
}

# Restart bot deployment
restart_bot() {
    log_info "Restarting bot deployment..."
    kubectl rollout restart deployment/wrcbot -n $NAMESPACE
    kubectl rollout status deployment/wrcbot -n $NAMESPACE
    log_success "Bot deployment restarted"
}

# Show help
show_help() {
    cat << EOF
Vault Management Script for WRCBot

Usage: $0 [COMMAND]

Commands:
    status          Check Vault status
    unseal          Manually unseal Vault
    set-secrets     Set bot secrets in Vault
    get-secrets     Retrieve bot secrets from Vault
    refresh-secrets Refresh Kubernetes secrets from Vault
    restart-bot     Restart the bot deployment
    port-forward    Start port forward to Vault UI
    stop-forward    Stop port forward
    help            Show this help message

Environment Variables:
    NAMESPACE       Kubernetes namespace (default: wrcbot)
    VAULT_SERVICE   Vault service name (default: vault)
    VAULT_PORT      Vault port for port forwarding (default: 8200)

Examples:
    $0 status                    # Check Vault status
    $0 set-secrets              # Interactively set bot secrets
    $0 refresh-secrets          # Update Kubernetes secrets from Vault
    $0 port-forward             # Access Vault UI at http://localhost:8200
    
    NAMESPACE=prod $0 status    # Check Vault status in 'prod' namespace
EOF
}

# Cleanup function
cleanup() {
    stop_port_forward
}

# Set trap for cleanup
trap cleanup EXIT

# Main script logic
main() {
    check_kubectl
    
    case "${1:-help}" in
        status)
            get_vault_credentials
            start_port_forward
            check_vault_status
            ;;
        unseal)
            get_vault_credentials
            start_port_forward
            unseal_vault
            ;;
        set-secrets)
            get_vault_credentials
            start_port_forward
            set_bot_secrets
            ;;
        get-secrets)
            get_vault_credentials
            start_port_forward
            get_bot_secrets
            ;;
        refresh-secrets)
            refresh_k8s_secrets
            ;;
        restart-bot)
            restart_bot
            ;;
        port-forward)
            start_port_forward
            log_success "Vault UI available at: http://localhost:$VAULT_PORT"
            log_info "Press Ctrl+C to stop port forwarding"
            wait
            ;;
        stop-forward)
            stop_port_forward
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
