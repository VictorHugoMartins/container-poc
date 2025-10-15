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

3. Liste os logs do seu Pod.
```
kubectl logs hello-python-deployment-86c54bb7c7-bfgh5 --namespace azure-store-1758905293727
```

## Configurar HTTPS no AKS
I. Configuração Inicial e Variáveis
Dadas as variáveis de configuração:

```
NOME_CLUSTER="<SEU_NOME_DO_CLUSTER_AKS>"
RG_CLUSTER="<NOME_DO_RESOURCE_GROUP_DO_CLUSTER>"
SEU_EMAIL="<SEU_EMAIL_PARA_LETS_ENCRYPT>"
SEU_DOMINIO="<SEU_DOMINIO_REAL_EX_app.minhaempresa.com>"
NS_APP="azure-store-1758905293727" # Namespace da sua aplicação
```


# 2. Obter o Grupo de Recursos de Infraestrutura (RG do Nó)
* Onde os Load Balancers são criados.
RG_NO=$(az aks show --resource-group $RG_CLUSTER --name $NOME_CLUSTER --query nodeResourceGroup -o tsv)
echo "RG de Infraestrutura: $RG_NO"

II. Instalação e Configuração dos Controladores
Estes passos instalam os componentes que gerenciam o roteamento (NGINX) e o certificado (Cert-Manager).

1. NGINX Ingress Controller

```
# Adiciona o repositório Helm do NGINX
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

## Instalar NGINX Ingress Controller
* Nota: Usamos --upgrade --install para ser robusto
```
helm upgrade --install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-basic \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"=$RG_CLUSTER
```

2. Cert-Manager
```
# Adiciona o repositório Helm do Cert-Manager
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Instala o Cert-Manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true
```

III. Correção de Permissão (Erro: IP <pending>)
Este bloco corrige a permissão do Azure que impede o provisionamento do IP público.
```
# 1. Obter a Managed Identity do Cluster
ID_IDENTIDADE=$(az aks show --resource-group $RG_CLUSTER --name $NOME_CLUSTER --query identity.principalId -o tsv)
echo "ID da Identidade Gerenciada: $ID_IDENTIDADE"

# 2. Atribuir a função Contributor ao RG de Infraestrutura do Nó
# Este comando corrige a falha de provisionamento do IP
az role assignment create \
    --assignee $ID_IDENTIDADE \
    --scope /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RG_NO \
    --role "Contributor"
```
IV. Obter IP Público e Configurar DNS
Aguarde 3-5 minutos para a propagação da permissão. Em seguida, reinicie o Service para forçar o provisionamento do IP.

```
# 1. Deleta o Serviço NGINX antigo (necessário após a correção de permissão)
kubectl delete service nginx-ingress-ingress-nginx-controller --namespace ingress-basic

# 2. Recria/Atualiza o Ingress Controller (Força o provisionamento com a permissão correta)
helm upgrade --install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-basic \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"=$RG_CLUSTER

# 3. Aguarde e obtenha o IP Público
echo "Aguarde 3-5 minutos para o IP aparecer..."
kubectl get service nginx-ingress-ingress-nginx-controller --namespace ingress-basic -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
# Repita o comando acima até que um IP real (ex: 40.x.x.x) seja retornado.
AÇÃO MANUAL: Use o IP retornado para configurar um Registro A no painel de DNS do seu provedor de domínio, apontando <SEU_DOMINIO_REAL> para este IP.

```

V. Configuração do HTTPS (Cert-Manager e Ingress)
1. Aplicar o ClusterIssuer
Crie o arquivo cluster-issuer.yaml (substituindo o email) e aplique:

```
# cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: $SEU_EMAIL
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - http01:
        ingress:
          class: nginx
```
Aplique via comando:
```
kubectl apply -f cluster-issuer.yaml
```
2. Criar e Aplicar o Recurso Ingress
Crie o arquivo ingress.yaml (substituindo o domínio) e aplique:

```
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: hello-python-ingress
  namespace: azure-store-1758905293727
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    kubernetes.io/ingress.class: "nginx"
spec:
  tls:
  - hosts:
    - $SEU_DOMINIO # Seu domínio real aqui
    secretName: hello-python-tls
  rules:
  - host: $SEU_DOMINIO # Seu domínio real aqui
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: hello-python-service
            port:
              number: 80 # A porta do Service (que encaminha para 8080 no Pod)
```

kubectl apply -f ingress.yaml -n $NS_APP
3. Verificação Final
Verifique se o certificado foi emitido com sucesso.

```
kubectl get certificate hello-python-tls -n $NS_APP
# O status deve mudar para 'Ready' (Pronto)
```

Passo 3: Aguardar e Monitorar o Log do Controller
O NGINX Ingress Controller deve estar emitindo logs agora, indicando que ele está ativamente tentando solicitar o Load Balancer ao Azure.

Obtenha o IP com o Monitoramento (Aguarde 5 minutos):

Execute o comando a seguir e aguarde. A opção -w fará com que o terminal fique observando o serviço. Assim que o IP for atribuído, ele aparecerá na tela.

```
kubectl get service nginx-ingress-ingress-nginx-controller --namespace ingress-basic -w
```
Verifique os Logs do Controlador (Se o IP não aparecer):

Se o IP ainda não aparecer após 5 minutos, verifique os logs para ver se o NGINX Ingress está relatando algum novo erro relacionado ao Azure:

```
kubectl logs $(kubectl get pods -n ingress-basic -l app.kubernetes.io/name=ingress-nginx -o jsonpath='{.items[0].metadata.name}') -n ingress-basic | tail
```


1. Adicionar Regras de Entrada ao NSG (HTTP e HTTPS)
Execute estes dois comandos sequenciais para abrir as portas 80 e 443 para o tráfego da Internet:

Regra 1: Permitir HTTP (Porta 80)

```
az network nsg rule create \
    --resource-group MC_k8scluster_group_clusterk8s_eastus \
    --nsg-name aks-agentpool-30022306-nsg \
    --name AllowHttp80Inbound \
    --priority 300 \
    --protocol Tcp \
    --direction Inbound \
    --access Allow \
    --source-address-prefixes Internet \
    --destination-port-ranges 80
```
Regra 2: Permitir HTTPS (Porta 443)

```
az network nsg rule create \
    --resource-group MC_k8scluster_group_clusterk8s_eastus \
    --nsg-name aks-agentpool-30022306-nsg \
    --name AllowHttps443Inbound \
    --priority 310 \
    --protocol Tcp \
    --direction Inbound \
    --access Allow \
    --source-address-prefixes Internet \
    --destination-port-ranges 443
```

## Interromper o container temporariamente
```
kubectl get deployment -n azure-store-1758905293727
kubectl scale deployment/hello-python-deployment --replicas=0 -n azure-store-1758905293727 
```