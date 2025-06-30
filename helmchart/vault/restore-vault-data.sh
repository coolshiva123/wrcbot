#!/bin/bash

# Vault Data Restore Script for Minikube (Fixed Version)
# This script restores Vault data from backup after minikube restart

set -e

BACKUP_DIR="/home/ec2-user/vault-persistent-data"
BACKUP_FILE="$BACKUP_DIR/vault-backup-latest.tar.gz"
CREDENTIALS_FILE="$BACKUP_DIR/vault-credentials-latest.yaml"

echo "🔄 Starting Vault data restore for minikube..."

# Check if minikube is running
if ! minikube status &>/dev/null; then
    echo "❌ Minikube is not running. Please start minikube first."
    exit 1
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ No backup file found at: $BACKUP_FILE"
    echo "📋 Available backups:"
    ls -la "$BACKUP_DIR"/vault-backup-*.tar.gz 2>/dev/null || echo "   No backups found"
    echo ""
    echo "Usage: $0 [backup-file]"
    echo "  If no backup-file is specified, uses the latest backup"
    exit 1
fi

# Allow specifying a specific backup file
if [ -n "$1" ]; then
    if [ -f "$1" ]; then
        BACKUP_FILE="$1"
        # Try to find matching credentials file
        BACKUP_BASE=$(basename "$1" .tar.gz)
        TIMESTAMP=${BACKUP_BASE#vault-backup-}
        CREDENTIALS_FILE="$BACKUP_DIR/vault-credentials-$TIMESTAMP.yaml"
    elif [ -f "$BACKUP_DIR/$1" ]; then
        BACKUP_FILE="$BACKUP_DIR/$1"
        BACKUP_BASE=$(basename "$1" .tar.gz)
        TIMESTAMP=${BACKUP_BASE#vault-backup-}
        CREDENTIALS_FILE="$BACKUP_DIR/vault-credentials-$TIMESTAMP.yaml"
    else
        echo "❌ Backup file not found: $1"
        exit 1
    fi
fi

echo "📦 Using backup file: $(basename "$BACKUP_FILE")"

# Check if Vault is deployed
VAULT_DEPLOYED=false
if kubectl get deployment vault -n wrcbot &>/dev/null; then
    VAULT_DEPLOYED=true
    echo "   ✅ Vault deployment found"
else
    echo "   ⚠️  Vault deployment not found"
fi

# Check if Vault pod is running
VAULT_RUNNING=false
if kubectl get pods -n wrcbot -l app.kubernetes.io/instance=vault 2>/dev/null | grep -q Running; then
    VAULT_RUNNING=true
    echo "   ✅ Vault pod is running"
else
    echo "   ⚠️  Vault pod is not running"
fi

if [ "$VAULT_DEPLOYED" = false ]; then
    echo ""
    echo "🚀 Vault not deployed. Deploying first..."
    echo "   Please deploy Vault with: kubectl apply -f /home/ec2-user/wrcbot/argoproj/wrcbot.yaml"
    echo "   Then run this restore script again."
    exit 1
fi

# Stop Vault pod to restore data safely
if [ "$VAULT_RUNNING" = true ]; then
    echo ""
    echo "🛑 Stopping Vault pod for safe restore..."
    kubectl scale deployment vault -n wrcbot --replicas=0
    echo "   ⏳ Waiting for pod to terminate..."
    kubectl wait --for=delete pod -l app.kubernetes.io/instance=vault -n wrcbot --timeout=60s 2>/dev/null || true
    sleep 5
fi

# Restore data to minikube node
echo ""
echo "📥 Restoring data to minikube node..."
echo "   Target path: /vaultdata"

# Clear existing data
echo "   🗑️  Clearing existing data..."
minikube ssh -- "sudo rm -rf /vaultdata/* 2>/dev/null || true"

# Restore from backup using improved method
echo "   📦 Extracting backup..."

# Create unique temporary directory
TMP_DIR="/tmp/vault-restore-$(date +%s)-$$"
echo "   🗂️  Creating temporary directory: $TMP_DIR"
minikube ssh -- "sudo mkdir -p $TMP_DIR"

# Extract backup to temporary directory
echo "   📂 Extracting backup to temporary directory..."

# First, copy the backup file to minikube
echo "   📋 Copying backup file to minikube..."
minikube cp "$BACKUP_FILE" /tmp/vault-backup.tar.gz

# Then extract it inside minikube
if minikube ssh -- "sudo tar xzf /tmp/vault-backup.tar.gz -C $TMP_DIR"; then
    echo "   ✅ Backup extracted successfully"
    
    # Clean up the temporary backup file
    minikube ssh -- "sudo rm -f /tmp/vault-backup.tar.gz"
    
    # List the structure to understand what we have
    echo "   🔍 Analyzing extracted structure..."
    minikube ssh -- "sudo find $TMP_DIR -type d | head -10"
    
    # Look for vault/file structure (pod-based backup)
    if minikube ssh -- "sudo test -d $TMP_DIR/vault/file"; then
        echo "   📁 Detected pod-based backup format (vault/file structure)"
        VAULT_FILE_DIR="$TMP_DIR/vault/file"
        echo "   📋 Copying from: $VAULT_FILE_DIR to /vaultdata"
        
        # Copy the contents of vault/file to /vaultdata
        minikube ssh -- "sudo cp -r $VAULT_FILE_DIR/* /vaultdata/"
        if [ $? -eq 0 ]; then
            echo "   ✅ Data copied successfully"
        else
            echo "   ❌ Failed to copy data"
            exit 1
        fi
        
    # Look for direct vaultdata structure (node-based backup)
    elif minikube ssh -- "sudo test -d $TMP_DIR/vaultdata"; then
        echo "   📁 Detected node-based backup format (vaultdata structure)"
        VAULTDATA_DIR="$TMP_DIR/vaultdata"
        echo "   📋 Copying from: $VAULTDATA_DIR to /vaultdata"
        
        minikube ssh -- "sudo cp -r $VAULTDATA_DIR/* /vaultdata/"
        if [ $? -eq 0 ]; then
            echo "   ✅ Data copied successfully"
        else
            echo "   ❌ Failed to copy data"
            exit 1
        fi
    else
        echo "   ❌ Could not identify backup structure. Available directories:"
        minikube ssh -- "sudo find $TMP_DIR -type d"
        echo "   ⚠️  Attempting to copy all contents to /vaultdata..."
        minikube ssh -- "sudo cp -r $TMP_DIR/* /vaultdata/ 2>/dev/null || true"
    fi
else
    echo "   ❌ Failed to extract backup"
    minikube ssh -- "sudo rm -rf $TMP_DIR"
    exit 1
fi

# Clean up temporary directory
echo "   🧹 Cleaning up temporary directory..."
minikube ssh -- "sudo rm -rf $TMP_DIR"

# Set proper permissions
echo "   🔐 Setting permissions..."
minikube ssh -- "sudo chown -R 100:1000 /vaultdata 2>/dev/null || sudo chown -R root:root /vaultdata"
minikube ssh -- "sudo chmod -R 755 /vaultdata"

# Verify restore
echo "   🔍 Verifying restore..."
DATA_SIZE=$(minikube ssh -- "sudo du -s /vaultdata 2>/dev/null | cut -f1" || echo "0")
FILE_COUNT=$(minikube ssh -- "sudo find /vaultdata -type f | wc -l" 2>/dev/null || echo "0")

if [ "$DATA_SIZE" -gt 0 ] && [ "$FILE_COUNT" -gt 0 ]; then
    echo "   ✅ Data restored successfully ($DATA_SIZE KB, $FILE_COUNT files)"
    echo "   📋 Sample files:"
    minikube ssh -- "sudo find /vaultdata -type f | head -5"
else
    echo "   ❌ Data restore may have failed (size: $DATA_SIZE KB, files: $FILE_COUNT)"
    echo "   📋 Directory contents:"
    minikube ssh -- "sudo ls -la /vaultdata/"
fi

# Restart Vault pod
echo ""
echo "🚀 Starting Vault pod..."
kubectl scale deployment vault -n wrcbot --replicas=1
echo "   ⏳ Waiting for pod to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=vault -n wrcbot --timeout=120s

# Give Vault a moment to initialize
echo "   ⏳ Waiting for Vault to initialize..."
sleep 10

# Check Vault status
echo "   🔍 Checking Vault status..."
kubectl exec deployment/vault -n wrcbot -- vault status || echo "   ⚠️  Vault status check failed (this may be normal if sealed)"

# Restore credentials if available
if [ -f "$CREDENTIALS_FILE" ]; then
    echo ""
    echo "🔑 Restoring Vault credentials..."
    if kubectl get secret vault-keys -n wrcbot &>/dev/null; then
        echo "   ⚠️  vault-keys secret already exists, backing it up first..."
        kubectl get secret vault-keys -n wrcbot -o yaml > "$BACKUP_DIR/vault-keys-backup-$(date +%Y%m%d_%H%M%S).yaml"
        kubectl delete secret vault-keys -n wrcbot
    fi
    kubectl apply -f "$CREDENTIALS_FILE"
    echo "   ✅ Credentials restored"
else
    echo ""
    echo "⚠️  No credentials file found at: $(basename "$CREDENTIALS_FILE")"
    echo "   You may need to reinitialize Vault or manually restore credentials"
fi

echo ""
echo "✅ Restore completed!"
echo ""
echo "🔧 Next steps:"
echo "   1. Check Vault status: kubectl exec deployment/vault -n wrcbot -- vault status"
echo "   2. If sealed, unseal with: ./unseal-vault.sh"
echo "   3. Verify your data: ./get-vault-credentials.sh"
echo ""
echo "💡 If Vault shows as uninitialized, the restore may not have worked correctly."
echo "   In that case, you may need to run: ./initialize-vault.sh"
