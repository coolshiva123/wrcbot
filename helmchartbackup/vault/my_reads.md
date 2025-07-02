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
kubectl get secret -n wrcbot | grep wrcbot-sa

The Helm chart for `wrcbot` currently defines only the `wrcbot-sa` service account in serviceaccount.yaml. There is no `wrcbot-sa-token.yaml` or equivalent secret manifest present.

In Kubernetes v1.24+, service account tokens are not created as secrets by default. To ensure your pod gets a token for Vault authentication, you should add a secret of type `kubernetes.io/service-account-token` and bind it to `wrcbot-sa`.

Would you like me to provide a Helm template for this secret so you can add it to your chart?

apiVersion: v1
kind: Secret
metadata:
  name: wrcbot-sa-token
  namespace: wrcbot
  annotations:
    kubernetes.io/service-account.name: wrcbot-sa
type: kubernetes.io/service-account-token

kubectl apply 

kubectl get secret -n wrcbot | grep wrcbot-sa
kubectl describe secret wrcbot-sa-token -n wrcbot


Verify Secrets fetch from vault

kubectl get pod wrcbot-7b9674c8bf-vm24z -n wrcbot -o jsonpath="{.spec.serviceAccountName}"
kubectl get pod wrcbot-7b9674c8bf-vm24z -n wrcbot -o json | jq -r '.spec.serviceAccountName'
kubectl get secret wrcbot-sa-token -n wrcbot -o jsonpath="{.data.token}" | base64 -d
curl --request POST \
  --data '{"role": "wrcbot-role", "jwt": "<JWT_TOKEN>"}' \
  http://vault.wrcbot.svc.cluster.local:8200/v1/auth/kubernetes/login

curl -H "X-Vault-Token: <VAULT_CLIENT_TOKEN>" \
     https://vault.wrcbot.svc.cluster.local:8200/v1/secret/data/wrcbot/config


Vault check to k8s 

kubectl exec -it vault-5dc49c799-mqbmj -n wrcbot -- curl -k https://kubernetes.default.svc.cluster.local:443
