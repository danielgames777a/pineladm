from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import os
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "licenses_db.json"
NOTICE_FILE = "notice.txt"

ADMIN_USER = "admin"
ADMIN_PASS = "123456"  # MUDA ESSA SENHA

sessions = {}

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_notice():
    if not os.path.exists(NOTICE_FILE):
        return ""
    return open(NOTICE_FILE).read()

def save_notice(txt):
    with open(NOTICE_FILE, "w") as f:
        f.write(txt)

def now():
    return int(time.time())

def auth(token: str = ""):
    return token in sessions

# ---------------- API PRO BOT ----------------

@app.post("/api/validate")
async def api_validate(data: dict):
    key = data.get("key")
    hwid = data.get("hwid")

    db = load_db()
    notice = load_notice()

    if key not in db:
        return {"success": False, "message": "Key inválida", "notice": notice}

    lic = db[key]

    if lic.get("banned"):
        return {"success": False, "message": "Key banida", "notice": notice}

    if lic["expires_at"] < now():
        return {"success": False, "message": "Key expirada", "notice": notice}

    if lic["hwid"] is None:
        lic["hwid"] = hwid
        db[key] = lic
        save_db(db)

    elif lic["hwid"] != hwid:
        return {"success": False, "message": "Key já em uso em outro PC", "notice": notice}

    return {"success": True, "message": "Licença válida. Bem-vindo!", "notice": notice}

@app.get("/api/notice")
async def api_notice():
    return {"notice": load_notice()}

# ---------------- PAINEL WEB ----------------

@app.get("/", response_class=HTMLResponse)
async def login():
    return """
    <h2>Login Admin</h2>
    <form method="post" action="/login">
      <input name="user" placeholder="Usuário"/><br><br>
      <input name="pass" placeholder="Senha" type="password"/><br><br>
      <button>Entrar</button>
    </form>
    """

@app.post("/login")
async def do_login(user: str = Form(...), passw: str = Form(...)):
    if user == ADMIN_USER and passw == ADMIN_PASS:
        token = str(uuid.uuid4())
        sessions[token] = True
        return RedirectResponse(url=f"/panel?token={token}", status_code=302)
    return HTMLResponse("Login inválido", status_code=401)

@app.get("/panel", response_class=HTMLResponse)
async def panel(token: str):
    if token not in sessions:
        return HTMLResponse("Não autorizado", status_code=401)

    db = load_db()
    notice = load_notice()

    rows = ""
    for k, v in db.items():
        rows += f"""
        <tr>
            <td>{k}</td>
            <td>{v.get('hwid')}</td>
            <td>{time.ctime(v['expires_at'])}</td>
            <td>{'BANIDA' if v.get('banned') else 'OK'}</td>
            <td>
              <a href="/reset?key={k}&token={token}">Reset HWID</a> |
              <a href="/ban?key={k}&token={token}">Banir</a>
            </td>
        </tr>
        """

    return f"""
    <h1>Painel ADM</h1>

    <h3>Aviso Global</h3>
    <form method="post" action="/notice">
      <input type="hidden" name="token" value="{token}"/>
      <textarea name="text" rows="3" cols="40">{notice}</textarea><br>
      <button>Salvar Aviso</button>
    </form>

    <h3>Gerar Key</h3>
    <form method="post" action="/create">
      <input type="hidden" name="token" value="{token}"/>
      <input name="amount" placeholder="Quantidade" value="1"/>
      <input name="hours" placeholder="Horas" value="0"/>
      <input name="days" placeholder="Dias" value="1"/>
      <input name="months" placeholder="Meses" value="0"/>
      <button>Criar</button>
    </form>

    <h3>Licenças</h3>
    <table border="1" cellpadding="5">
      <tr><th>KEY</th><th>HWID</th><th>EXPIRA</th><th>Status</th><th>Ações</th></tr>
      {rows}
    </table>
    """

@app.post("/create")
async def create(token: str = Form(...), amount: int = Form(1), hours: int = Form(0), days: int = Form(0), months: int = Form(0)):
    if token not in sessions:
        return HTMLResponse("Não autorizado", status_code=401)

    db = load_db()
    total_seconds = hours*3600 + days*86400 + months*2592000

    for _ in range(amount):
        key = str(uuid.uuid4()).split("-")[0].upper()
        db[key] = {
            "hwid": None,
            "expires_at": now() + total_seconds,
            "banned": False
        }

    save_db(db)
    return RedirectResponse(url=f"/panel?token={token}", status_code=302)

@app.get("/reset")
async def reset_hwid(key: str, token: str):
    if token not in sessions:
        return HTMLResponse("Não autorizado", status_code=401)

    db = load_db()
    if key in db:
        db[key]["hwid"] = None
        save_db(db)

    return RedirectResponse(url=f"/panel?token={token}", status_code=302)

@app.get("/ban")
async def ban_key(key: str, token: str):
    if token not in sessions:
        return HTMLResponse("Não autorizado", status_code=401)

    db = load_db()
    if key in db:
        db[key]["banned"] = True
        save_db(db)

    return RedirectResponse(url=f"/panel?token={token}", status_code=302)

@app.post("/notice")
async def set_notice(token: str = Form(...), text: str = Form(...)):
    if token not in sessions:
        return HTMLResponse("Não autorizado", status_code=401)

    save_notice(text)
    return RedirectResponse(url=f"/panel?token={token}", status_code=302)
