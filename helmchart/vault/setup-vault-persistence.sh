#!/bin/bash

# Vault Persistence Setup Script
# This script sets up Vault with proper data persistence for minikube restarts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/home/ec2-user/vault-persistent-data"

echo "🚀 Setting up Vault with persistent data support..."

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "📋 Current minikube status:"
minikube status || echo "Minikube not running"

echo ""
echo "⚠️  IMPORTANT: Data Persistence Information"
echo "=============================================="
echo "Due to minikube running in Docker mode, true filesystem persistence"
echo "between minikube restarts is not supported. However, this setup provides:"
echo ""
echo "✅ Data persistence as long as minikube is running (stop/start OK)"
echo "✅ Backup/restore mechanism for minikube delete/recreate scenarios"
echo "✅ Easy data migration between minikube clusters"
echo ""
echo "🔄 Available commands:"
echo "  ./backup-vault-data.sh    - Backup current Vault data"
echo "  ./restore-vault-data.sh   - Restore Vault data from backup"
echo "  ./unseal-vault.sh         - Unseal Vault after restart"
echo ""

# Deploy Vault if not already deployed
if ! kubectl get namespace wrcbot &>/dev/null; then
    echo "📦 Deploying Vault using ArgoCD..."
    kubectl apply -f /home/ec2-user/wrcbot/argoproj/wrcbot.yaml
    echo "⏳ Waiting for ArgoCD to deploy Vault..."
    sleep 10
fi

# Wait for Vault to be ready
echo "⏳ Waiting for Vault pod to be ready..."
kubectl wait --for=condition=ready pod -l app=vault -n wrcbot --timeout=300s || {
    echo "❌ Vault pod failed to become ready. Checking status..."
    kubectl get pods -n wrcbot -l app=vault
    kubectl describe pods -n wrcbot -l app=vault
    exit 1
}

echo "✅ Vault is now running!"

# Check if we have a backup to restore
if [ -f "$BACKUP_DIR/vault-backup-latest.tar.gz" ]; then
    echo ""
    read -p "🔄 Found existing Vault backup. Restore it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📥 Restoring Vault data from backup..."
        "$SCRIPT_DIR/restore-vault-data.sh"
    fi
fi

echo ""
echo "🎉 Vault setup complete!"
echo ""
echo "Next steps:"
echo "1. Unseal Vault: ./unseal-vault.sh"
echo "2. Access Vault UI: minikube service vault -n wrcbot"
echo "3. Set up your secrets: ./set-vault-secrets.sh"
echo ""
echo "💡 Remember to backup your data before minikube restarts:"
echo "   ./backup-vault-data.sh"
