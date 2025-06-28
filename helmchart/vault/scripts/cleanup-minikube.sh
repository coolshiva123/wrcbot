#!/bin/bash

# Vault Minikube Cleanup Script
set -e

echo "🧹 Cleaning up Vault deployment from Minikube"

# Remove Helm release
echo "🗑️ Removing Vault Helm release..."
helm uninstall vault -n wrcbot || echo "Vault release not found"

# Clean up PVs (they don't get auto-deleted with storageClass: manual)
echo "🧽 Cleaning up PersistentVolumes..."
kubectl delete pv -l app.kubernetes.io/name=vault || echo "No PVs found"

# Optional: Clean up the data directory in Minikube
read -p "🤔 Do you want to delete the data directory /data/vaultdata in Minikube? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗂️ Removing data directory..."
    minikube ssh "sudo rm -rf /data/vaultdata"
    echo "✅ Data directory removed"
else
    echo "📁 Data directory preserved"
fi

echo "✅ Cleanup completed!"
