#!/bin/bash

# Vault Data Backup Script
# This script backs up Vault data to the EC2 host for persistence across minikube restarts

set -e

BACKUP_DIR="/home/ec2-user/vault-persistent-data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/vault-backup-$TIMESTAMP.tar.gz"

echo "🔄 Starting Vault data backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if Vault pod is running
if ! kubectl get pods -n wrcbot -l app=vault | grep -q Running; then
    echo "❌ Vault pod is not running. Cannot backup data."
    exit 1
fi

# Get the Vault pod name
VAULT_POD=$(kubectl get pods -n wrcbot -l app=vault -o jsonpath='{.items[0].metadata.name}')

echo "📦 Backing up data from pod: $VAULT_POD"

# Create backup of Vault data
kubectl exec -n wrcbot "$VAULT_POD" -- tar czf - /vault/file 2>/dev/null | cat > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "✅ Backup completed successfully: $BACKUP_FILE"
    
    # Create a symlink to the latest backup
    ln -sf "$BACKUP_FILE" "$BACKUP_DIR/vault-backup-latest.tar.gz"
    
    # List all backups
    echo "📋 Available backups:"
    ls -lah "$BACKUP_DIR"/vault-backup-*.tar.gz
else
    echo "❌ Backup failed or resulted in empty file"
    rm -f "$BACKUP_FILE"
    exit 1
fi

echo "💡 To restore this backup after minikube restart, run: ./restore-vault-data.sh"
