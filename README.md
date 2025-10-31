# container-poc

POC AKS Autoscaled

## Como verificar logs no termminal da Azure

1. Abra um terminal da Azure.


1. Faça login no terminal. Use o az aks get-credentials para que o Azure CLI baixe o arquivo de configuração do cluster e o mescle com o seu arquivo kubeconfig local.
```
az aks get-credentials --resource-group k8scluster_group --name clusterk8s --overwrite-existing
```

2. Liste os Pods do container.
```
kubectl get pods -n azure-store-1758905293727
```

3. Identificar o IP **externo** do Pod
```
kubectl logs hello-python-deployment-86c54bb7c7-bfgh5 --namespace azure-store-1758905293727
```

3.1 Identificar o IP **interno** do Pod
```
kubectl get svc
```

4. Liste os logs do seu Pod.
```
kubectl logs hello-python-deployment-86c54bb7c7-bfgh5 --namespace azure-store-1758905293727
```

## Obter variáveis de configuração
I. Configuração Inicial e Variáveis
Dadas as variáveis de configuração:

```
$NOME_CLUSTER="clusterk8s" # nome do cluster do AKS
$RG_PRINCIPAL="k8scluster_group"
$NSG_RG="MC_k8scluster_group_clusterk8s_eastus"
NSG_NAME=$(az network nsg list \
    --resource-group $NSG_RG \
    --query "[?contains(name, 'aks-agentpool')].name" -o tsv) # $NSG_NAME="aks-agentpool-30022306-nsg"
SEU_EMAIL="<SEU_EMAIL_PARA_LETS_ENCRYPT>"
SEU_DOMINIO="<SEU_DOMINIO_REAL_EX_app.minhaempresa.com>"
NS_APP="azure-store-1758905293727" # Namespace da sua aplicação
$RG_NO=$(az aks show --resource-group $RG_CLUSTER --name $NOME_CLUSTER --query nodeResourceGroup -o tsv)
# Retornará algo como MC_k8scluster_group_clusterk8s_eastus
echo "RG de Infraestrutura: $RG_NO"
```

## Interromper o container temporariamente
```
kubectl get deployment -n azure-store-1758905293727
kubectl scale deployment/hello-python-deployment --replicas=0 -n azure-store-1758905293727 
```
Para reiniciar:
```
kubectl scale deployment/hello-python-deployment --replicas=1 -n azure-store-1758905293727 
```

## Liberar as portas 80 e 443
Passo 1: Descubra o nome do Grupo de Recursos do Nó e confira-o.
```
echo "Grupo de Recursos do Nó: $AKS_NODE_RG"
```
Passo 2: Liste o NSG. Com a variável agora preenchida corretamente, você pode listar os NSGs (Network Security Groups) no Grupo de Recursos do Nó. O NSG deve ter um nome que começa com `aks-agentpool` ou similar.
```
az network nsg list --resource-group $AKS_NODE_RG --query '[].name' -o tsv
```

* Passo 2: Execute o Comando para Liberar a Porta 443
Após identificar o nome do NSG ($NSG_NAME), você pode executar o comando de permissão da porta 443 (o mesmo da resposta anterior).

PowerShell
```
# ⚠️ SUBSTITUA PELO NOME DO NSG ENCONTRADO ⚠️
$NSG_NAME="<O_NOME_DO_SEU_NSG>"

az network nsg rule create `
    --resource-group $AKS_NODE_RG `
    --nsg-name $NSG_NAME `
    --name Allow-HTTP-HTTPS-Inbound `
    --priority 100 `
    --direction Inbound `
    --source-address-prefixes Internet `
    --source-port-ranges "*" `
    --destination-address-prefixes "*" `
    --destination-port-ranges 80 443 `
    --protocol Tcp `
    --access Allow `
    --description "Allow HTTP and HTTPS inbound from the Internet"
```

## Configurar NGINX
* Onde os Load Balancers são criados.
```
# 2. Instale o addon de Ingress Controller (AKS)
# Isso instalará o Ingress Controller no namespace 'ingress-basic' e criará um LoadBalancer
az aks addon enable --resource-group $RG_PRINCIPAL --name $NOME_CLUSTER --addon ingress-nginx

# 3. Obtenha o novo IP do Ingress Controller
# Aguarde alguns minutos após o comando acima.
# O IP do NGINX Ingress Controller agora é o IP que o seu domínio DuckDNS DEVE apontar.
$INGRESS_IP = az network public-ip list --resource-group $RG_PRINCIPAL --query "[?name=='ingress-nginx-controller-ip'].ipAddress" -o tsv

echo "NOVO IP DO INGRESS CONTROLLER: $INGRESS_IP"
```
II. Instalação e Configuração dos Controladores
Estes passos instalam os componentes que gerenciam o roteamento (NGINX) e o certificado (Cert-Manager).

1. NGINX Ingress Controller

```
helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --create-namespace \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-protocol"="http" \
    --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-port"="80" \
    --set controller.service.loadBalancerIP=""
```

Obter o NOVO IP: Aguarde 2-3 minutos e obtenha o IP do novo Load Balancer (o IP que você deve usar no DuckDNS):


kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
Atualizar o DNS: Atualize o hello-python-aks.duckdns.org com o IP obtido.

Aplicar as Mudanças no YAML: Prossiga com o Passo 2 do meu roteiro anterior (mudar o seu Service para ClusterIP e criar o Ingress).

Forçar Nova Emissão do Certificado: Depois de aplicar tudo, o cert-manager finalmente deverá conseguir validar e emitir o certificado.


### Configurar um nome de domínio personalizado e um certificado SSL com o complemento de roteamento de aplicativo
Baseado no (Microsoft Learn)[https://learn.microsoft.com/pt-br/azure/aks/app-routing-dns-ssl]


```
az provider register --namespace Microsoft.KeyVault
```

```
az keyvault create --resource-group <ResourceGroupName> --location <Location> --name <KeyVaultName> --enable-rbac-authorization true 
# az keyvault create --resource-group RG-Vaults --location eastus --name k8sgroupvault --enable-rbac-authorization true
```

```
openssl req -new -x509 -nodes -out aks-ingress-tls.crt -keyout aks-ingress-tls.key -subj "/CN=hello-python-aks.duckdns.org" -addext "subjectAltName=DNS:hello-python-aks.duckdns.org"
```


```
az keyvault certificate import --vault-name k8sgroupvault --name <KeyVaultCertificateName> --file aks-ingress-tls.pfx [--password <certificate password if specified>]
```
Em caso de erro de permissão:
```
az role assignment create  --role "Key Vault Reader"  --assignee-object-id "990a38bb-3a55-4f81-b4fe-884832be0ee3"  --scope "/subscriptions/670bc431-d5b3-4586-afcc-5b920f8c7e5e/resourcegroups/k8scluster_group/providers/Microsoft.KeyVault/vaults/k8sgroupvault"  --assignee-principal-type User
```