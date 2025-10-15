# container-poc

POC AKS Autoscaled

## Executando e verificando logs no termminal da Azure

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

## Para configurar NGINX

Passo 1: Limpar o LoadBalancer (Opcional, mas Recomendado)
Como o Ingress Controller assumirá a função de balanceamento de carga de entrada, você pode remover o Service do tipo LoadBalancer que você postou, substituindo-o por um Service do tipo ClusterIP (interno).

Siga os próximos passos pelo terminal da Azure.
Passo 2: Instalar o NGINX Ingress Controller
O Ingress Controller é o componente que recebe o tráfego na porta 443 (HTTPS) e o descriptografa antes de enviá-lo para os seus Pods (na porta 8080).

Adicionar o repositório Helm do NGINX:
```
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```
Instalar o Ingress Controller:

```
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-basic \
  --create-namespace \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-resource-group"=<SEU_GRUPO_DE_RECURSOS>
```
Isto cria um novo LoadBalancer com um IP público dedicado ao NGINX.

Adicionar o Repositório jetstack (O passo que faltou)
Este comando diz ao Helm onde encontrar os gráficos (charts) de instalação do Cert-Manager:

```
helm repo add jetstack https://charts.jetstack.io
```

Passo 2: Atualizar os Repositórios
Este comando garante que o Helm baixe as informações mais recentes sobre os gráficos disponíveis:
```
helm repo update
```

Passo 3: Tentar a Instalação Novamente
Agora que o repositório jetstack foi adicionado e está atualizado, você pode executar o comando de instalação do Cert-Manager com sucesso:

```
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.0 \
  --set installCRDs=true
```
Se tudo ocorrer bem, o Helm deverá retornar uma mensagem de sucesso, indicando que o Cert-Manager foi instalado no seu cluster AKS. O próximo passo seria configurar o ClusterIssuer.

Configurar um ClusterIssuer:
Crie um arquivo YAML (ex: cluster-issuer.yaml) para configurar o Let's Encrypt. Substitua <SUA_CONTA_EMAIL>:

```
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: <SUA_CONTA_EMAIL> # SEU EMAIL AQUI
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
    - http01:
        ingress:
          class: nginx
```