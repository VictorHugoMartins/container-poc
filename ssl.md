Para ter uma conexão segura (HTTPS) usando o Let's Encrypt no seu cluster AKS com o Ingress, o processo envolve a instalação e configuração de uma ferramenta chamada Cert-Manager.

Você já tem o primeiro passo no seu manifesto: a definição de um ClusterIssuer. Agora, precisamos garantir que o Cert-Manager e o Ingress Controller estejam instalados e que o seu Ingress seja atualizado para solicitar o certificado.

Aqui está o passo a passo completo, presumindo que você está usando o Ingress Controller NGINX (que é o padrão para a maioria dos manifestos com a anotação nginx.ingress.kubernetes.io/rewrite-target).

⚠️ Pré-requisitos Cruciais
Domínio Válido: Você deve ter um nome de domínio registrado (ex: minhaapp.com) e o registro A desse domínio deve apontar para o IP Externo do seu LoadBalancer NGINX. O Let's Encrypt só emite certificados para nomes de domínio válidos, não para IPs brutos.

Ingress Controller Instalado: Um NGINX Ingress Controller (ou similar) deve estar instalado e funcionando no seu AKS.

Helm Instalado: O helm é a maneira mais fácil de instalar o Cert-Manager.

1. Instalar o kubect no WSL
```
# Baixar a versão mais recente do kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Tornar o binário executável
chmod +x ./kubectl

# Mover para o diretório de executáveis
sudo mv ./kubectl /usr/local/bin/kubectl

# Verificar a instalação
kubectl version --client
```

2. Verificar a conexão
