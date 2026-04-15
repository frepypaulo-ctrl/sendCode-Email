import os
import random
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Configuração de CORS para permitir que qualquer site acesse a API
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Dicionário em memória para códigos (em produção, recomenda-se Redis ou BD)
codigos_gerados = {}

# Credenciais de E-mail
# Recomendo configurar estas variáveis no Dashboard do Render (Environment Variables)
EMAIL_USER = os.environ.get("EMAIL_USER", "frepypaulo@gmail.com")
EMAIL_PASS = os.environ.get("EMAIL_PASS", "jpxultwisgohraax")

def enviar_email(destinatario, codigo):
    """Lógica de envio de e-mail via SMTP SSL do Gmail"""
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código de verificação"
    msg['From'] = EMAIL_USER
    msg['To'] = destinatario

    # Layout HTML Profissional
    html_content = f"""
    <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; text-align: center; background-color: #f4f7f6; padding: 40px;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                <h2 style="color: #00A3A3;">Verificação de Conta</h2>
                <p style="color: #666;">Use o código abaixo para completar o seu acesso:</p>
                <div style="background: #f1f1f1; padding: 20px; border-radius: 15px; margin: 25px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #333;">{codigo}</span>
                </div>
                <p style="font-size: 12px; color: #999;">Se não solicitou este código, por favor ignore este e-mail.</p>
            </div>
        </body>
    </html>
    """
    msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

@app.route('/enviar-codigo', methods=['POST', 'OPTIONS'])
def rota_enviar():
    if request.method == 'OPTIONS':
        return '', 200
        
    dados = request.json
    if not dados or 'email' not in dados:
        return jsonify({"sucesso": False, "erro": "E-mail é obrigatório"}), 400

    email = dados.get('email')
    codigo = "".join([str(random.randint(0, 9)) for _ in range(6)])
    codigos_gerados[email] = str(codigo)

    try:
        enviar_email(email, codigo)
        return jsonify({"sucesso": True, "mensagem": "Código enviado com sucesso!"})
    except Exception as e:
        print(f"Erro ao enviar: {e}")
        return jsonify({"sucesso": False, "erro": "Erro interno ao enviar e-mail"}), 500

@app.route('/verificar-codigo', methods=['POST', 'OPTIONS'])
def rota_verificar():
    if request.method == 'OPTIONS':
        return '', 200

    dados = request.json
    if not dados:
        return jsonify({"validado": False, "erro": "Dados ausentes"}), 400

    email = dados.get('email')
    codigo_digitado = dados.get('codigo')

    if email in codigos_gerados and str(codigos_gerados[email]) == str(codigo_digitado):
        del codigos_gerados[email]  # Limpa o código após sucesso
        return jsonify({
            "validado": True,
            "redirect": "https://dancing-palmier-3650ec.netlify.app/sucesso.html"
        })
    
    return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401

@app.route('/')
def health_check():
    return "API Online", 200

if __name__ == "__main__":
    # O Render usa a porta da variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
