from flask import Flask, request, jsonify
import time

app = Flask(__name__)

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

@app.route('/')
def hello_world():
    # Rota simples para verificar que o serviço está no ar
    return "Hello World Python Escalavel! V2"

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

if __name__ == '__main__':
    # O container do AKS precisa ouvir em 0.0.0.0
    app.run(host='0.0.0.0', port=8080)