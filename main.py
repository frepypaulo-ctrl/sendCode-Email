from flask import Flask, request, jsonify
from flask_cors import CORS
import smtplib
import random
from email.message import EmailMessage

app = Flask(__name__)
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# Dicionário temporário para guardar os códigos: { "email@teste.com": "123456" }
codigos_gerados = {}

def enviar_email(destinatario, codigo):
    seu_email = "frepypaulo@gmail.com"
    sua_senha = "jpxultwisgohraax" # A sua senha de app segura
    
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código de verificação SharLink"
    msg['From'] = seu_email
    msg['To'] = destinatario

    # Criamos uma versão em HTML para o e-mail ficar bonito e grande
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
    
    # Adicionamos o conteúdo HTML à mensagem
    msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(seu_email, sua_senha)
        smtp.send_message(msg)

# ROTA 1: Envia o código e salva no dicionário
@app.route('/enviar-codigo', methods=['POST'])
def rota_enviar():
    dados = request.json
    email = dados.get('email')
    
    if not email:
        return jsonify({"erro": "Email obrigatório"}), 400
    
    codigo = "".join([str(random.randint(0, 9)) for _ in range(6)])
    codigos_gerados[email] = codigo # Salva o código associado ao email
    
    try:
        enviar_email(email, codigo)
        return jsonify({"sucesso": True, "mensagem": "Código enviado!"})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 500

# ROTA 2: Verifica se o código que o usuário digitou está correto
@app.route('/verificar-codigo', methods=['POST'])
def rota_verificar():
    dados = request.json
    email = dados.get('email')
    codigo_digitado = dados.get('codigo')

    # Verifica se o código existe no dicionário e se coincide
    if email in codigos_gerados and codigos_gerados[email] == codigo_digitado:
        # Opcional: deletar o código após usar para segurança
        del codigos_gerados[email] 
        return jsonify({"validado": True, "redirect": "https://seusite.com/pagina-sucesso.html"})
    else:
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
