export VAULT_ADDR=http://localhost:8200 && export VAULT_TOKEN=<>

/ # vault policy list
default
wrcbot-policy
root
/ # 
/ # 
/ # 
/ # vault policy read wrcbot-policy
path "secret/data/wrcbot/config" {
  capabilities = ["read"]
}
/ # 
/ # 
/ # 
/ # 
/ # vault auth list
Path           Type          Accessor                    Description                Version
----           ----          --------                    -----------                -------
kubernetes/    kubernetes    auth_kubernetes_e94a0505    n/a                        n/a
token/         token         auth_token_8a245316         token based credentials    n/a
/ # 
/ # 
/ # 
/ # 
/ # vault read auth/kubernetes/config
Key                       Value
---                       -----
disable_iss_validation    true
disable_local_ca_jwt      false
issuer                    n/a
kubernetes_ca_cert        n/a
kubernetes_host           https://kubernetes.default.svc.cluster.local
pem_keys                  []
/ # 
/ # 
/ # 
/ # 
/ # vault list auth/kubernetes/role
Keys
----
wrcbot
wrcbot-role
/ # 
/ # 
/ # 
/ # vault list auth/kubernetes/role
Keys
----
wrcbot
wrcbot-role
/ # vault read auth/kubernetes/role/wrcbot-role
Key                                 Value
---                                 -----
alias_name_source                   serviceaccount_uid
bound_service_account_names         [wrcbot-sa]
bound_service_account_namespaces    [wrcbot]
policies                            [wrcbot-policy]
token_bound_cidrs                   []
token_explicit_max_ttl              0s
token_max_ttl                       0s
token_no_default_policy             false
token_num_uses                      0
token_period                        0s
token_policies                      [wrcbot-policy]
token_ttl                           1h
token_type                          default
ttl                                 1h


kubectl get serviceaccount wrcbot-sa -n wrcbot -o yaml
kubectl get secret -n wrcbot | grep wrcbot-sa
kubectl describe secret <secret-name> -n wrcbot

kubectl get serviceaccount wrcbot-sa -n wrcbot -o yaml
kubectl get secret -n wrcbot | grep wrcbot-sa empty output




