from flask import Flask, request, jsonify
import time
import os 

import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pymysql
from typing import List

app = Flask(__name__)

# --- Variáveis de Configuração ---
INSTANCE_CONNECTION_NAME = "telemetria-rumo-9ccc4:us-central1:grafana-server-db"
DB_USER = "Harpia_Admin"
DB_PASS = os.environ.get("DB_USER")
DB_NAME = "grafana"

IP_TYPE = IPTypes.PUBLIC

USER_TABLE = "user" 
EMAIL_COLUMN = "email"

# --- Função de Conexão ---
def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """Inicializa um pool de conexões para a instância do Cloud SQL."""
    
    connector = Connector(ip_type=IP_TYPE, refresh_strategy="LAZY")

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pymysql",
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
        )
        return conn

    # 3. Cria o engine do SQLAlchemy com o método de conexão seguro
    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30, # segundos
    )
    return pool

# --- Inicialização do Banco de Dados ---
# ⚠️ CRIE O POOL DE CONEXÕES APENAS UMA VEZ
try:
    db_engine = connect_with_connector()
    print("Pool de Conexões do Cloud SQL inicializado com sucesso.")
except Exception as e:
    # Se falhar aqui, a aplicação não deve subir (comportamento desejado)
    print(f"ERRO CRÍTICO AO INICIALIZAR O POOL DE CONEXÕES: {e}")
    db_engine = None # Deixe como None ou levante o erro (raise)

def get_user_emails() -> List[str]:
    """Conecta ao banco de dados e retorna a lista de e-mails."""
    
    # 1. Estabelece a conexão (pool)
    emails = []
    
    query = f"SELECT {EMAIL_COLUMN} FROM {USER_TABLE};" 

    try:
        print("Conectando e executando a consulta...")
        with db_engine.connect() as db_conn:
            result = db_conn.execute(sqlalchemy.text(query))
            for row in result:
                print(row[0])
                emails.append(row[0]) 
            print("Consulta concluída com sucesso!")

    except Exception as e:
        print(f"Ocorreu um erro ao conectar ou consultar o banco de dados: {e}")
        
    return emails

# --- Execução do Script ---
@app.route('/lista-emails')
def lista_emails():
    lista_emails = get_user_emails()
    
    if lista_emails:
        return jsonify(lista_emails)
    else:
        return jsonify("Nenhum e-mail encontrado ou erro de conexão/consulta.")

# Função que simula o consumo de CPU
def cpu_intensive_task(duration_seconds):
    """Executa um loop para consumir CPU."""
    start_time = time.time()
    count = 0
    while (time.time() - start_time) < duration_seconds:
        # A operação de elevação ao quadrado é intencionalmente intensiva em CPU
        count += 1
        _ = 2 ** 1000
    return count

@app.route('/stress')
def stress_cpu():
    # Define a duração do stress em segundos (0.5s por padrão)
    try:
        duration = float(request.args.get('duration', 0.5))
    except ValueError:
        duration = 0.5
        
    count = cpu_intensive_task(duration)
    
    return jsonify({
        "message": f"Stress de CPU executado por {duration} segundos.",
        "iterations": count
    })

@app.route('/')
def index():
    return jsonify({"message": "API Flask OK. Tente /lista-emails ou /stress"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)