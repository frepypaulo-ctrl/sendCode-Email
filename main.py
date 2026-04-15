import os
import random
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Permite que qualquer site chame esta API (CORS)
CORS(app)

codigos_gerados = {}

# Recomendo preencher estas variáveis no painel do Render
EMAIL_USER = os.environ.get("EMAIL_USER", "frepypaulo@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "jpxultwisgohraax")

def enviar_email(destinatario, codigo):
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código SharLink"
    msg['From'] = EMAIL_USER
    msg['To'] = destinatario
    
    html = f"""
    <div style="font-family:sans-serif; text-align:center; padding:20px; border:1px solid #eee; border-radius:10px;">
        <h2 style="color:#00A3A3;">SharLink</h2>
        <p>O seu código de verificação é:</p>
        <h1 style="letter-spacing:5px; color:#333;">{codigo}</h1>
        <p style="font-size:12px; color:#999;">Válido por 10 minutos.</p>
    </div>
    """
    msg.add_alternative(html, subtype='html')
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

@app.route('/enviar-codigo', methods=['POST'])
def rota_enviar():
    dados = request.json
    email = dados.get('email')
    if not email: return jsonify({"sucesso": False}), 400
    
    codigo = "".join([str(random.randint(0, 9)) for _ in range(6)])
    codigos_gerados[email] = codigo
    
    try:
        enviar_email(email, codigo)
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

@app.route('/verificar-codigo', methods=['POST'])
def rota_verificar():
    dados = request.json
    email = dados.get('email')
    codigo_digitado = dados.get('codigo')
    
    if email in codigos_gerados and str(codigos_gerados[email]) == str(codigo_digitado):
        del codigos_gerados[email]
        return jsonify({"validado": True})
    return jsonify({"validado": False, "erro": "Código inválido"}), 401

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
