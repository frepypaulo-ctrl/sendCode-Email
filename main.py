import os
import time
import secrets
import smtplib
import logging
from email.message import EmailMessage
from flask import Flask, request, jsonify
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Configuração básica
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Habilita CORS globalmente para todas as rotas, origens, métodos e cabeçalhos
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dimako-api")

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

if not EMAIL_USER or not EMAIL_PASS:
    raise RuntimeError(
        "EMAIL_USER e EMAIL_PASS precisam estar configurados como variáveis "
        "de ambiente (no dashboard do Render, em Environment)."
    )

CODIGO_VALIDADE_SEGUNDOS = 10 * 60
LIMITE_PEDIDOS = 3
JANELA_LIMITE_SEGUNDOS = 15 * 60

# ---------------------------------------------------------------------------
# Armazenamento em memória
# ---------------------------------------------------------------------------
codigos_gerados = {}   # email -> {"codigo": str, "expira_em": float}
pedidos_por_email = {} # email -> [timestamps]


def limpar_expirados():
    agora = time.time()
    for email in list(codigos_gerados.keys()):
        if codigos_gerados[email]["expira_em"] < agora:
            del codigos_gerados[email]


def excedeu_limite(email):
    agora = time.time()
    historico = pedidos_por_email.get(email, [])
    historico = [t for t in historico if agora - t < JANELA_LIMITE_SEGUNDOS]
    pedidos_por_email[email] = historico
    return len(historico) >= LIMITE_PEDIDOS


def registar_pedido(email):
    pedidos_por_email.setdefault(email, []).append(time.time())


# ---------------------------------------------------------------------------
# Middleware CORS Adicional (Para garantir suporte total em file:// e Apps)
# ---------------------------------------------------------------------------
@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    return response


# ---------------------------------------------------------------------------
# Envio de e-mail
# ---------------------------------------------------------------------------
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
        <p style="font-size:12px; color:#B0A69F; margin-top:24px;">Se não solicitou este código, ignore este e-mail.</p>
    </div>
    """
    msg.add_alternative(html, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)


def gerar_codigo():
    return "".join(secrets.choice("0123456789") for _ in range(6))


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.route('/enviar-codigo', methods=['POST', 'OPTIONS'])
def rota_enviar():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    limpar_expirados()

    dados = request.get_json(silent=True) or {}
    email = str(dados.get('email', '')).strip().lower()

    if not email or '@' not in email or '.' not in email:
        return jsonify({"sucesso": False, "erro": "Email inválido"}), 400

    if excedeu_limite(email):
        return jsonify({
            "sucesso": False,
            "erro": "Muitos pedidos para este e-mail. Tente novamente mais tarde."
        }), 429

    codigo = gerar_codigo()
    codigos_gerados[email] = {
        "codigo": codigo,
        "expira_em": time.time() + CODIGO_VALIDADE_SEGUNDOS,
    }
    registar_pedido(email)

    try:
        enviar_email(email, codigo)
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s", email)
        if email in codigos_gerados:
            del codigos_gerados[email]
        return jsonify({"sucesso": False, "erro": "Não foi possível enviar o e-mail. Tente novamente."}), 500

    return jsonify({"sucesso": True})


@app.route('/verificar-codigo', methods=['POST', 'OPTIONS'])
def rota_verificar():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200

    limpar_expirados()

    dados = request.get_json(silent=True) or {}
    email = str(dados.get('email', '')).strip().lower()
    codigo_digitado = str(dados.get('codigo', '')).strip()

    if not email or not codigo_digitado:
        return jsonify({"validado": False, "erro": "Email ou código não fornecido"}), 400

    registo = codigos_gerados.get(email)

    if not registo:
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401

    if registo["expira_em"] < time.time():
        del codigos_gerados[email]
        return jsonify({"validado": False, "erro": "Código expirado. Solicite um novo."}), 401

    if not secrets.compare_digest(registo["codigo"], codigo_digitado):
        return jsonify({"validado": False, "erro": "Código incorreto ou expirado"}), 401

    del codigos_gerados[email]
    return jsonify({"validado": True})


@app.route('/', methods=['GET', 'OPTIONS'])
def health():
    return jsonify({"api": "Dimako", "status": "running", "cors": "enabled_all"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
