from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import os
import uuid

app = FastAPI()

# Libera CORS (pra não dar erro no bot)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "licenses_db.json"
ADMIN_USER = "admin"
ADMIN_PASS = "123456"  # TROCA ESSA SENHA

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def now():
    return int(time.time())

# ------------------- API PRO BOT -------------------

@app.post("/api/validate")
async def validate_license(data: dict):
    key = data.get("key")
    hwid = data.get("hwid")

    db = load_db()

    if key not in db:
        return {"success": False, "message": "Key inválida", "notice": ""}

    lic = db[key]

    if lic["expires_at"] < now():
        return {"success": False, "message": "Key expirada", "notice": ""}

    if lic["hwid"] is None:
        lic["hwid"] = hwid
        db[key] = lic
        save_db(db)

    elif lic["hwid"] != hwid:
        return {"success": False, "message": "Key já está em uso em outro PC", "notice": ""}

    return {"success": True, "message": "Licença válida. Bem-vindo!", "notice": ""}

@app.get("/api/notice")
async def get_notice():
    return {"notice": ""}

# ------------------- PAINEL WEB SIMPLES -------------------

@app.get("/", response_class=HTMLResponse)
async def panel():
    return """
    <html>
    <head>
        <title>Painel ADM</title>
    </head>
    <body style="background:#111;color:white;font-family:Arial;padding:40px">
        <h1>Painel Admin - JOTTEX AUTO</h1>
        <form method="post" action="/create">
            <p>Dias de validade:</p>
            <input type="number" name="days" value="1"/>
            <br><br>
            <button type="submit">Gerar KEY</button>
        </form>
        <br>
        <a href="/list">Ver KEYS</a>
    </body>
    </html>
    """

@app.post("/create", response_class=HTMLResponse)
async def create_key(request: Request):
    form = await request.form()
    days = int(form.get("days", 1))

    db = load_db()
    key = str(uuid.uuid4()).split("-")[0].upper()
    expires_at = now() + (days * 86400)

    db[key] = {
        "hwid": None,
        "expires_at": expires_at
    }

    save_db(db)

    return f"""
    <html><body style="background:#111;color:white;font-family:Arial;padding:40px">
    <h2>Key criada com sucesso:</h2>
    <h1>{key}</h1>
    <a href="/">Voltar</a>
    </body></html>
    """

@app.get("/list", response_class=HTMLResponse)
async def list_keys():
    db = load_db()
    rows = ""
    for k, v in db.items():
        rows += f"<tr><td>{k}</td><td>{v['hwid']}</td><td>{time.ctime(v['expires_at'])}</td></tr>"

    return f"""
    <html><body style="background:#111;color:white;font-family:Arial;padding:40px">
    <h2>Licenças</h2>
    <table border="1" cellpadding="10">
        <tr><th>KEY</th><th>HWID</th><th>EXPIRA EM</th></tr>
        {rows}
    </table>
    <br>
    <a href="/">Voltar</a>
    </body></html>
    """
