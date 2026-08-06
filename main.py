import os
import time
import secrets
import smtplib
import logging
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Libera CORS globalmente para qualquer origem (HTML local, sites ou Apps)
CORS(app, resources={r"/*": {"origins": "*"}})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dimako-api")

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# Cada código individual é válido por 10 minutos (600 segundos)
CODIGO_VALIDADE_SEGUNDOS = 10 * 60

# Armazenamento em memória: email -> list de dicts [{"codigo": str, "expira_em": float}]
codigos_gerados = {}


def limpar_expirados():
    """Remove apenas os códigos que já passaram de 10 minutos."""
    agora = time.time()
    for email in list(codigos_gerados.keys()):
        validos = [c for c in codigos_gerados[email] if c["expira_em"] > agora]
        if validos:
            codigos_gerados[email] = validos
        else:
            del codigos_gerados[email]


@app.after_request
def after_request(response):
    """Garante cabeçalhos CORS em TODAS as respostas (mesmo em erros 400 ou 500)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    return response


def enviar_email(destinatario, codigo):
    msg = EmailMessage()
    msg['Subject'] = f"{codigo} é o seu código Dimako"
    msg['From'] = f"Dimako <{EMAIL_USER}>"
    msg['To'] = destinatario

    html = f"""
    <div style="font-family:sans-serif; text-align:center; padding:32px 20px; background:#FFF8F3; border:1px solid #FFD9B3; border-radius:14px;">
        <h2 style="color:#FF6B1A; margin:0 0 4px; letter-spacing:0.02em;">DIMAKO</h2>
        <p style="color:#7A6F68; margin:0 0 20px;">O seu código de verificação é:</p>
        <div style="display:inline-block; background:#FF6B1A; color:#ffffff; font-size:28px; font-weight:700; letter-spacing:8px; padding:14px 24px; border-radius:10px;">
            {codigo}
        </div>
        <p style="font-size:12px; color:#B0A69F; margin-top:24px;">Este código expira em 10 minutos.</p>
    </div>
    """
    msg.add_alternative(html, subtype='html')

    # Conexão direta com timeout seguro de 12s
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=12) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)


def gerar_codigo():
    return "".join(secrets.choice("0123456789") for _ in range(6))


# ---------------------------------------------------------------------------
# ROTAS
# ---------------------------------------------------------------------------

@app.route('/enviar-codigo', methods=['POST', 'OPTIONS'])
def rota_enviar():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    limpar_expirados()

    dados = request.get_json(silent=True) or {}
    email = str(dados.get('email', '')).strip().lower()

    if not email or '@' not in email or '.' not in email:
        return jsonify({"sucesso": False, "erro": "E-mail inválido"}), 400

    if not EMAIL_USER or not EMAIL_PASS:
        return jsonify({"sucesso": False, "erro": "Variáveis EMAIL_USER/EMAIL_PASS não configuradas no Render"}), 500

    codigo = gerar_codigo()
    novo_registro = {
        "codigo": codigo,
        "expira_em": time.time() + CODIGO_VALIDADE_SEGUNDOS
    }

    try:
        # Envia o e-mail primeiro
        enviar_email(email, codigo)
        
        # Guarda o código associado ao e-mail
        codigos_gerados.setdefault(email, []).append(novo_registro)
        
        return jsonify({"sucesso": True, "mensagem": "Código enviado com sucesso!"}), 200

    except smtplib.SMTPAuthenticationError:
        logger.error("Erro de autenticação no SMTP do Gmail.")
        return jsonify({
            "sucesso": False, 
            "erro": "Falha de login no servidor de e-mail (Verifique a Senha de Aplicação)."
        }), 500

    except Exception as e:
        logger.exception("Erro ao enviar e-mail: %s", str(e))
        return jsonify({
            "sucesso": False, 
            "erro": f"Erro ao enviar e-mail: {str(e)}"
        }), 500


@app.route('/verificar-codigo', methods=['POST', 'OPTIONS'])
def rota_verificar():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    limpar_expirados()

    dados = request.get_json(silent=True) or {}
    email = str(dados.get('email', '')).strip().lower()
    codigo_digitado = str(dados.get('codigo', '')).strip()

    if not email or not codigo_digitado:
        return jsonify({"validado": False, "erro": "E-mail ou código não fornecido"}), 400

    lista_codigos = codigos_gerados.get(email, [])
    agora = time.time()

    codigo_encontrado = None
    for item in lista_codigos:
        # Compara com qualquer código válido não expirado
        if item["expira_em"] > agora and secrets.compare_digest(item["codigo"], codigo_digitado):
            codigo_encontrado = item
            break

    if codigo_encontrado:
        # Consome o código validado para não ser reutilizado
        lista_codigos.remove(codigo_encontrado)
        return jsonify({"validado": True}), 200
    else:
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado."}), 401


@app.route('/', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({"api": "Dimako", "status": "running"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
