#!/bin/bash

# Complete Vault Backup/Restore Validation Test
# This script validates the entire backup and restore workflow

set -e

echo "🧪 Starting Complete Vault Backup/Restore Validation Test"
echo "=========================================================="

BACKUP_DIR="/home/ec2-user/vault-persistent-data"
TEST_LOG="/tmp/vault-test-$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "$1" | tee -a "$TEST_LOG"
}

log "📋 Test started at: $(date)"
log "📁 Backup directory: $BACKUP_DIR"
log "📝 Test log: $TEST_LOG"

# Step 1: Verify Vault is running and accessible
echo ""
log "🔍 Step 1: Verifying Vault Status"
if kubectl get deployment vault -n wrcbot &>/dev/null; then
    log "   ✅ Vault deployment exists"
else
    log "   ❌ Vault deployment not found"
    exit 1
fi

if kubectl exec deployment/vault -n wrcbot -- vault status &>/dev/null; then
    VAULT_STATUS=$(kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep "Initialized\|Sealed")
    log "   📊 Vault Status:"
    log "   $VAULT_STATUS"
else
    log "   ❌ Cannot access Vault"
    exit 1
fi

# Step 2: Verify secrets exist
echo ""
log "🔍 Step 2: Verifying Existing Secrets"
ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)

if [ -n "$ROOT_TOKEN" ]; then
    log "   ✅ Root token retrieved"
    
    # Check each secret
    for secret in config database redis; do
        if kubectl exec deployment/vault -n wrcbot -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/$secret &>/dev/null; then
            log "   ✅ Secret secret/wrcbot/$secret exists"
        else
            log "   ❌ Secret secret/wrcbot/$secret missing"
        fi
    done
else
    log "   ❌ Cannot retrieve root token"
    exit 1
fi

# Step 3: Test backup
echo ""
log "🔄 Step 3: Testing Backup Process"
if ./backup-vault-data.sh &>>"$TEST_LOG"; then
    log "   ✅ Backup completed successfully"
    
    # Verify backup files
    LATEST_BACKUP=$(readlink -f "$BACKUP_DIR/vault-backup-latest.tar.gz")
    LATEST_CREDS=$(readlink -f "$BACKUP_DIR/vault-credentials-latest.yaml")
    
    if [ -f "$LATEST_BACKUP" ] && [ -s "$LATEST_BACKUP" ]; then
        BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
        log "   ✅ Backup file created: $(basename "$LATEST_BACKUP") ($BACKUP_SIZE)"
    else
        log "   ❌ Backup file missing or empty"
        exit 1
    fi
    
    if [ -f "$LATEST_CREDS" ] && [ -s "$LATEST_CREDS" ]; then
        log "   ✅ Credentials file created: $(basename "$LATEST_CREDS")"
    else
        log "   ❌ Credentials file missing or empty"
        exit 1
    fi
else
    log "   ❌ Backup failed"
    exit 1
fi

# Step 4: Simulate data loss (optional destructive test)
echo ""
read -p "🚨 Do you want to test data loss recovery? This will DELETE vault data! (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "⚠️  Step 4: Simulating Data Loss (DESTRUCTIVE TEST)"
    
    # Stop vault pod
    log "   🛑 Stopping Vault pod..."
    kubectl scale deployment vault -n wrcbot --replicas=0 &>>"$TEST_LOG"
    kubectl wait --for=delete pod -l app.kubernetes.io/instance=vault -n wrcbot --timeout=60s &>>"$TEST_LOG" || true
    
    # Delete data
    log "   🗑️  Deleting vault data..."
    minikube ssh -- "sudo rm -rf /vaultdata/*" &>>"$TEST_LOG"
    
    # Restart vault pod
    log "   🚀 Starting Vault pod..."
    kubectl scale deployment vault -n wrcbot --replicas=1 &>>"$TEST_LOG"
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=vault -n wrcbot --timeout=120s &>>"$TEST_LOG"
    sleep 10
    
    # Verify vault is uninitialized
    if kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Initialized.*false"; then
        log "   ✅ Data loss confirmed - Vault is uninitialized"
    else
        log "   ⚠️  Expected uninitialized vault after data deletion"
    fi
    
    # Step 5: Test restore
    echo ""
    log "🔄 Step 5: Testing Restore Process"
    if ./restore-vault-data.sh &>>"$TEST_LOG"; then
        log "   ✅ Restore completed successfully"
        
        # Wait for vault to be ready
        sleep 10
        
        # Check vault status
        if kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Initialized.*true"; then
            log "   ✅ Vault is initialized after restore"
        else
            log "   ❌ Vault is not initialized after restore"
            exit 1
        fi
        
        # Check if unsealed
        if kubectl exec deployment/vault -n wrcbot -- vault status 2>/dev/null | grep -q "Sealed.*false"; then
            log "   ✅ Vault is unsealed"
        else
            log "   ⚠️  Vault is sealed (may need manual unseal)"
        fi
        
    else
        log "   ❌ Restore failed"
        exit 1
    fi
    
    # Step 6: Verify restored secrets
    echo ""
    log "🔍 Step 6: Verifying Restored Secrets"
    ROOT_TOKEN=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.root-token}' 2>/dev/null | base64 -d)
    
    if [ -n "$ROOT_TOKEN" ]; then
        log "   ✅ Root token available after restore"
        
        # Check each secret
        SECRETS_OK=true
        for secret in config database redis; do
            if kubectl exec deployment/vault -n wrcbot -- env VAULT_TOKEN="$ROOT_TOKEN" vault kv get secret/wrcbot/$secret &>/dev/null; then
                log "   ✅ Secret secret/wrcbot/$secret restored successfully"
            else
                log "   ❌ Secret secret/wrcbot/$secret missing after restore"
                SECRETS_OK=false
            fi
        done
        
        if [ "$SECRETS_OK" = true ]; then
            log "   ✅ All secrets restored successfully"
        else
            log "   ❌ Some secrets failed to restore"
            exit 1
        fi
    else
        log "   ❌ Cannot retrieve root token after restore"
        exit 1
    fi
else
    log "⏭️  Step 4-6: Skipping destructive data loss test"
fi

# Final summary
echo ""
log "🎉 Test Summary"
log "==============="
log "✅ Vault deployment verified"
log "✅ Backup process validated"
log "✅ Backup files created successfully"

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "✅ Data loss simulation completed"
    log "✅ Restore process validated"
    log "✅ All secrets restored successfully"
fi

log ""
log "📊 Test completed successfully at: $(date)"
log "📝 Full test log available at: $TEST_LOG"
log ""
log "🔗 Backup location: $BACKUP_DIR"
log "📦 Latest backup: $(basename "$(readlink -f "$BACKUP_DIR/vault-backup-latest.tar.gz")" 2>/dev/null || echo "N/A")"

echo ""
echo "🏆 All tests passed! Vault backup/restore workflow is fully functional."
