import os
import random
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# 1. Configuração Global de CORS para permitir QUALQUER origem (*)
CORS(app, resources={r"/*": {"origins": "*"}})

codigos_gerados = {}

# Variáveis de e-mail (Configure no Render dashboard)
EMAIL_USER = os.environ.get("EMAIL_USER", "frepypaulo@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "jpxultwisgohraax")

# 2. Middleware que força os cabeçalhos de permissão em TODAS as respostas
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def enviar_email(destinatario, codigo):
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código SharLink"
    msg['From'] = f"SharLink <{EMAIL_USER}>"
    msg['To'] = destinatario
    
    html = f"""
    <div style="font-family:sans-serif; text-align:center; padding:20px; border:1px solid #eee; border-radius:10px;">
        <h2 style="color:#00A3A3;">SharLink</h2>
        <p>O seu código de verificação é:</p>
        <h1 style="letter-spacing:5px; color:#333;">{codigo}</h1>
        <p style="font-size:12px; color:#999;">Se não solicitou este código, ignore este e-mail.</p>
    </div>
    """
    msg.add_alternative(html, subtype='html')
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

@app.route('/enviar-codigo', methods=['POST', 'OPTIONS'])
def rota_enviar():
    # 3. Resposta imediata para pre-flight (pedido de verificação do navegador)
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    try:
        dados = request.get_json()
        if not dados or 'email' not in dados:
            return jsonify({"sucesso": False, "erro": "Email não fornecido"}), 400
            
        email = dados.get('email')
        codigo = "".join([str(random.randint(0, 9)) for _ in range(6)])
        codigos_gerados[email] = codigo
        
        enviar_email(email, codigo)
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/verificar-codigo', methods=['POST', 'OPTIONS'])
def rota_verificar():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    try:
        dados = request.get_json()
        email = dados.get('email')
        codigo_digitado = dados.get('codigo')
        
        if email in codigos_gerados and str(codigos_gerados[email]) == str(codigo_digitado):
            del codigos_gerados[email]
            return jsonify({"validado": True})
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401
    except Exception as e:
        return jsonify({"validado": False, "erro": str(e)}), 500

@app.route('/')
def health():
    return jsonify({"api": "SharLink", "status": "running", "cors": "enabled_all"}), 200

if __name__ == "__main__":
    # Render exige que a porta seja dinâmica
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
