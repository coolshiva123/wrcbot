#!/bin/bash

# Minikube Vault Backup/Restore Commands
# Quick reference for common operations

echo "🔧 Minikube Vault Backup/Restore Commands"
echo "=========================================="

case "$1" in
    "backup"|"b")
        echo "📦 Creating backup..."
        cd /home/ec2-user/wrcbot/helmchart/vault
        ./backup-vault-data.sh
        ;;
    
    "restore"|"r")
        echo "📥 Restoring from backup..."
        cd /home/ec2-user/wrcbot/helmchart/vault
        if [ -n "$2" ]; then
            ./restore-vault-data.sh "$2"
        else
            ./restore-vault-data.sh
        fi
        ;;
    
    "list"|"l")
        echo "📋 Available backups:"
        ls -lah /home/ec2-user/vault-persistent-data/vault-backup-*.tar.gz 2>/dev/null || echo "No backups found"
        echo ""
        echo "🔑 Available credentials:"
        ls -lah /home/ec2-user/vault-persistent-data/vault-credentials-*.yaml 2>/dev/null || echo "No credentials found"
        ;;
    
    "status"|"s")
        echo "🔍 Minikube status:"
        minikube status
        echo ""
        echo "🏢 Vault deployment:"
        kubectl get deployment vault -n wrcbot 2>/dev/null || echo "Vault not deployed"
        echo ""
        echo "🏃 Vault pod:"
        kubectl get pods -n wrcbot -l app.kubernetes.io/instance=vault 2>/dev/null || echo "No vault pods found"
        ;;
    
    "clean"|"c")
        echo "🗑️  Cleaning old backups (keeping last 5)..."
        cd /home/ec2-user/vault-persistent-data
        ls -t vault-backup-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
        ls -t vault-credentials-*.yaml 2>/dev/null | tail -n +6 | xargs -r rm -f
        echo "✅ Cleanup completed"
        ;;
    
    "help"|"h"|*)
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  backup|b              - Create backup of current Vault data"
        echo "  restore|r [file]      - Restore from backup (latest if no file specified)"
        echo "  list|l                - List available backups"
        echo "  status|s              - Show minikube and Vault status"
        echo "  clean|c               - Clean old backups (keep last 5)"
        echo "  help|h                - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 backup"
        echo "  $0 restore"
        echo "  $0 restore vault-backup-20250630_190441.tar.gz"
        echo "  $0 list"
        echo "  $0 status"
        echo ""
        echo "Backup location: /home/ec2-user/vault-persistent-data/"
        echo ""
        echo "💡 Before minikube restart: $0 backup"
        echo "💡 After minikube restart:  $0 restore"
        ;;
esac
