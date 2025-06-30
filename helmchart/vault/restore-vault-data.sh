#!/bin/bash

# Vault Data Restore Script
# This script restores Vault data from backup after minikube restart

set -e

BACKUP_DIR="/home/ec2-user/vault-persistent-data"
BACKUP_FILE="$BACKUP_DIR/vault-backup-latest.tar.gz"

echo "🔄 Starting Vault data restore..."

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ No backup file found at: $BACKUP_FILE"
    echo "Available backups:"
    ls -la "$BACKUP_DIR"/vault-backup-*.tar.gz 2>/dev/null || echo "No backups found"
    echo ""
    echo "Usage: $0 [backup-file]"
    echo "  If no backup-file is specified, uses the latest backup"
    exit 1
fi

# Allow specifying a specific backup file
if [ -n "$1" ]; then
    if [ -f "$1" ]; then
        BACKUP_FILE="$1"
    elif [ -f "$BACKUP_DIR/$1" ]; then
        BACKUP_FILE="$BACKUP_DIR/$1"
    else
        echo "❌ Backup file not found: $1"
        exit 1
    fi
fi

echo "📦 Using backup file: $BACKUP_FILE"

# Check if Vault pod is running
if ! kubectl get pods -n wrcbot -l app=vault | grep -q Running; then
    echo "❌ Vault pod is not running. Please ensure Vault is deployed and running."
    echo "You can deploy with: kubectl apply -f /home/ec2-user/wrcbot/argoproj/wrcbot.yaml"
    exit 1
fi

# Get the Vault pod name
VAULT_POD=$(kubectl get pods -n wrcbot -l app=vault -o jsonpath='{.items[0].metadata.name}')

echo "📥 Restoring data to pod: $VAULT_POD"

# Wait for Vault pod to be fully ready
echo "⏳ Waiting for Vault pod to be ready..."
kubectl wait --for=condition=ready pod -l app=vault -n wrcbot --timeout=60s

# Restore backup to Vault data directory
kubectl exec -n wrcbot "$VAULT_POD" -- sh -c 'rm -rf /vault/file/* 2>/dev/null || true'
cat "$BACKUP_FILE" | kubectl exec -i -n wrcbot "$VAULT_POD" -- tar xzf - -C /

echo "✅ Restore completed successfully!"
echo "🔓 You may need to unseal Vault. Run: ./unseal-vault.sh"
