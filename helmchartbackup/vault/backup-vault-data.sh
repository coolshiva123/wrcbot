#!/bin/bash

# Vault Data Backup Script for Minikube
# This script backs up Vault data from minikube VM to the EC2 host

set -e

BACKUP_DIR="/home/ec2-user/vault-persistent-data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/vault-backup-$TIMESTAMP.tar.gz"

echo "🔄 Starting Vault data backup from minikube..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if minikube is running
if ! minikube status &>/dev/null; then
    echo "❌ Minikube is not running. Please start minikube first."
    exit 1
fi

# Method 1: Backup from pod (recommended - gets processed data)
echo "📦 Method 1: Backing up from Vault pod..."
if kubectl get pods -n wrcbot -l app.kubernetes.io/instance=vault | grep -q Running; then
    VAULT_POD=$(kubectl get pods -n wrcbot -l app.kubernetes.io/instance=vault -o jsonpath='{.items[0].metadata.name}')
    echo "   Using pod: $VAULT_POD"
    
    kubectl exec -n wrcbot "$VAULT_POD" -- tar czf - /vault/file 2>/dev/null > "$BACKUP_FILE"
    
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        echo "   ✅ Pod backup completed: $BACKUP_FILE"
    else
        echo "   ❌ Pod backup failed, trying minikube direct access..."
        rm -f "$BACKUP_FILE"
    fi
fi

# Method 2: Backup from minikube node directly (fallback)
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "📦 Method 2: Backing up directly from minikube node..."
    
    # Check if /vaultdata exists in minikube
    if minikube ssh -- "test -d /vaultdata"; then
        echo "   Found /vaultdata in minikube node"
        minikube ssh -- "sudo tar czf - /vaultdata 2>/dev/null" > "$BACKUP_FILE"
        
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            echo "   ✅ Minikube direct backup completed: $BACKUP_FILE"
        else
            echo "   ❌ Direct backup failed or resulted in empty file"
            rm -f "$BACKUP_FILE"
            exit 1
        fi
    else
        echo "   ❌ /vaultdata not found in minikube node"
        exit 1
    fi
fi

# Backup Vault credentials as well
echo "🔑 Backing up Vault credentials..."
if kubectl get secret vault-keys -n wrcbot &>/dev/null; then
    kubectl get secret vault-keys -n wrcbot -o yaml > "$BACKUP_DIR/vault-credentials-$TIMESTAMP.yaml"
    echo "   ✅ Credentials backed up to: $BACKUP_DIR/vault-credentials-$TIMESTAMP.yaml"
else
    echo "   ⚠️  No vault-keys secret found to backup"
fi

# Create symlinks to latest backups
ln -sf "$BACKUP_FILE" "$BACKUP_DIR/vault-backup-latest.tar.gz"
ln -sf "$BACKUP_DIR/vault-credentials-$TIMESTAMP.yaml" "$BACKUP_DIR/vault-credentials-latest.yaml" 2>/dev/null || true

# Show backup summary
echo ""
echo "✅ Backup completed successfully!"
echo "📁 Backup location: $BACKUP_DIR"
echo "📦 Data backup: $(basename "$BACKUP_FILE")"
echo "🔑 Credentials: vault-credentials-$TIMESTAMP.yaml"
echo ""
echo "📋 Available backups:"
ls -lah "$BACKUP_DIR"/vault-backup-*.tar.gz 2>/dev/null || echo "   No data backups found"
ls -lah "$BACKUP_DIR"/vault-credentials-*.yaml 2>/dev/null || echo "   No credential backups found"

echo ""
echo "💡 To restore this backup after minikube restart:"
echo "   1. Start minikube and deploy Vault"
echo "   2. Run: ./restore-vault-data.sh"
