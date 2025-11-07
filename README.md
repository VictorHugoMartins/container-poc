# container-poc

POC AKS Autoscaled

## Como verificar logs no terminal da Azure

1. Abra um terminal da Azure.

1. Faça login no terminal. Use o az aks get-credentials para que o Azure CLI baixe o arquivo de configuração do cluster e o mescle com o seu arquivo kubeconfig local.
```
az aks get-credentials --resource-group k8scluster_group --name clusterk8s --overwrite-existing
```

2. Liste os Pods do container.
```
kubectl get pods -n azure-store-1758905293727
```

3. Identificar os IPs **público** e  **externo** do Pod

![alt text](image.png)

A distinção entre IP Externo e IP Interno é crucial para entender o fluxo de tráfego no seu cluster Azure Kubernetes Service (AKS).

| Recurso/Componente | Tipo de IP | Finalidade |
| :--- | :--- | :--- |
| **Load Balancer (`EXTERNAL-IP`)** | **IP Externo** | É o endereço público. Recebe o tráfego do usuário vindo da Internet. |
| **Service (`CLUSTER-IP`)** | **IP Interno** | É o endereço de rede interno do cluster. Roteia o tráfego do Load Balancer para um conjunto de Pods. |
| **Pods** | **IP Interno** | É o endereço de rede para o container. Onde sua aplicação está rodando e se comunicando internamente. |

Assim, o **IP Externo** atua como o **porteiro** que recebe visitantes da web, e o **IP Interno** atua como o **sistema de endereçamento** dentro da rede do cluster para que os componentes internos (Pods e Services) possam se encontrar e se comunicar com segurança.

Para obter os IPs:
```
kubectl get service -n azure-store-1758905293727 hello-python-service
```

O IP Externo do nosso App é: `http://52.255.214.130/`.

5. Liste os logs do seu Pod.
```
kubectl logs hello-python-deployment-86c54bb7c7-bfgh5 --namespace azure-store-1758905293727
```

## Variáveis de configuração
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

Para descobrir o nome de algumas variáveis:
```
# Nome do NSG
az network nsg list --resource-group MC_k8scluster_group_clusterk8s_eastus -o table 
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

## Configurar um nome de domínio personalizado e um certificado SSL com o complemento de roteamento de aplicativo

Baseado no [Microsoft Learn](https://learn.microsoft.com/pt-br/azure/aks/app-routing-dns-ssl)


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

Agora, libere a porta 80 para expor a aplicação publicamente.
```
az network nsg rule create  --resource-group MC_k8scluster_group_clusterk8s_eastus --nsg-name aks-agentpool-30022306-nsg --name AllowHTTP --priority 100 --direction Inbound  --access Allow --protocol Tcp --destination-port-range 80 --source-address-prefixes '*' --destination-address-prefixes '*'
```


Para ver os certificados:
```
kubectl get certificates -n azure-store-1758905293727 # listar certificados
kubectl describe certificate hello-python-tls-secret -n azure-store-1758905293727 # ver mais detalhes
```

SUBNET_NAME=$(az network vnet subnet list  --resource-group MC_k8scluster_group_clusterk8s_eastus  --vnet-name aks-vnet-30022306   --query '[0].name'  -o tsv) # aks-subnet

NSG_ID=$(az network vnet subnet show --resource-group MC_k8scluster_group_clusterk8s_eastus  --vnet-name aks-vnet-30022306 --name aks-subnet --query networkSecurityGroup.id -o tsv) # /subscriptions/670bc431-d5b3-4586-afcc-5b920f8c7e5e/resourceGroups/MC_k8scluster_group_clusterk8s_eastus/providers/Microsoft.Network/networkSecurityGroups/aks-agentpool-30022306-nsg



# Exemplo: NODEPOOL_NAME="agentpool"

