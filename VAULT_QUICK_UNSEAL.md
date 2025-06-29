# 🔓 Quick Vault Unsealing Reference

## When Vault Needs Unsealing
- ✅ After pod restarts
- ✅ After cluster maintenance  
- ✅ After Helm upgrades
- ✅ When manually sealed

## 🚀 Quick Unseal (One Command)
```bash
cd /home/ec2-user/wrcbot
./helmchart/vault/unseal-vault.sh
```

## 🔍 Check Status First
```bash
kubectl exec deployment/vault -n wrcbot -- vault status
```

**Look for:**
- `Sealed: true` → **Needs unsealing**
- `Sealed: false` → **Ready to use**

## 🔑 Manual Unseal (Alternative)
```bash
# Get the unseal key
UNSEAL_KEY=$(kubectl get secret vault-keys -n wrcbot -o jsonpath='{.data.unseal-key}' | base64 -d)

# Unseal Vault
kubectl exec deployment/vault -n wrcbot -- vault operator unseal $UNSEAL_KEY
```

## 🎯 After Unsealing
- ✅ Secrets are automatically available
- ✅ Bot can access configuration
- ✅ All data persists from before restart

## 📖 Full Documentation
See: `helmchart/vault/VAULT_SECRETS_GUIDE.md`

---
*Your vault secrets persist across restarts - you just need to unseal after pod restarts for security.*
