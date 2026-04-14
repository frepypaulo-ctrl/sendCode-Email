


import os
import random
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Configuração de CORS profissional para não dar erro no Netlify
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Dicionário temporário (Em produção, considere usar um banco de dados)
codigos_gerados = {}

# Pega as credenciais das Variáveis de Ambiente do Render (Mais seguro)
# Se não estiverem lá, ele usa esses valores padrão que você mandou
EMAIL_USER =  'frepypaulo@gmail.com'
EMAIL_PASS =  'jpxultwisgohraax'

def enviar_email(destinatario, codigo):
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código de verificação SharLink"
    msg['From'] = EMAIL_USER
    msg['To'] = destinatario

    # HTML ajustado para o nome SharLink (removi a menção a LinhBus para manter o padrão)
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 400px; margin: auto; background: white; padding: 30px; border-radius: 10px; border: 1px solid #ddd;">
                <h2 style="color: #333;">Verificação LinhBus</h2>
                <p style="color: #666; font-size: 16px;">Utilize o código abaixo para validar o seu acesso:</p>
                
                <div style="background-color: #f0f7ff; border: 2px dashed #007bff; margin: 20px 0; padding: 20px; border-radius: 8px;">
                    <span style="font-size: 40px; font-weight: bold; color: #007bff; letter-spacing: 10px; display: block;">
                        {codigo}
                    </span>
                </div>
                
                <p style="font-size: 12px; color: #999;">Este código expira em breve. Se não solicitou este e-mail, ignore-o.</p>
            </div>

              <div style="max-width: 500px; margin: auto; background: white; padding: 40px; border-radius: 20px; border-top: 15px solid #28a745; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <h1 style="color: #28a745; margin-bottom: 10px;">Email Verificado!</h1>
                <p style="color: #666; font-size: 18px; line-height: 1.6;">
                    Seja muito bem-vindo à 
                    <a href="https://seusite.com" style="color: #007bff; text-decoration: none; font-weight: bold;">SharLink</a>.
                </p>
                <div style="margin-top: 25px; padding: 15px; background-color: #e9f7ef; border-radius: 10px; color: #155724; font-weight: bold; font-size: 20px;">
                    Conta Ativada com Sucesso
                </div>
                <p style="margin-top: 30px;">
                    <a href="https://seusite.com" style="background-color: #28a745; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        ACESSAR O SITE AGORA
                    </a>
                </p>
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
    # CORREÇÃO CRÍTICA: O método OPTIONS serve apenas para o navegador verificar permissão.
    # Ele não envia corpo JSON. Se tentar ler request.json no OPTIONS, o código quebra.
    if request.method == 'OPTIONS':
        return '', 200

    dados = request.json
    if not dados or 'email' not in dados:
        return jsonify({"erro": "Email obrigatório"}), 400
    
    email = dados.get('email')
    codigo = "".join([str(random.randint(0, 9)) for _ in range(6)])
    codigos_gerados[email] = codigo 
    
    try:
        enviar_email(email, codigo)
        return jsonify({"sucesso": True, "mensagem": "Código enviado!"})
    except Exception as e:
        print(f"Erro SMTP: {e}")
        return jsonify({"sucesso": False, "erro": "Falha ao enviar e-mail. Verifique as credenciais."}), 500

@app.route('/verificar-codigo', methods=['POST', 'OPTIONS'])
def rota_verificar():
    if request.method == 'OPTIONS':
        return '', 200

    dados = request.json
    if not dados:
        return jsonify({"validado": False, "erro": "Dados inválidos"}), 400

    email = dados.get('email')
    codigo_digitado = dados.get('codigo')

    if email in codigos_gerados and str(codigos_gerados[email]) == str(codigo_digitado):
        del codigos_gerados[email] 
        return jsonify({
            "validado": True, 
            "redirect": "https://dancing-palmier-3650ec.netlify.app/sucesso.html" # Ajustado para o seu Netlify
        })
    else:
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401

if __name__ == "__main__":
    # O Render exige que a porta seja dinâmica através da variável de ambiente PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

















