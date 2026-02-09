from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import json, os, uuid
from datetime import datetime, timedelta

app = FastAPI()

DB_FILE = "licenses_db.json"

ADMIN_USER = "admin"
ADMIN_PASS = "1234"  # MUDA ISSO DEPOIS

AVISO_GLOBAL = {"message": "Nenhum aviso no momento."}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ DB ------------------

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ------------------ LOGIN ADMIN ------------------

@app.get("/", response_class=HTMLResponse)
def login_page():
    return """
    <h2>Login Admin</h2>
    <form method="post" action="/login">
        <input name="user" placeholder="Usuário"/><br><br>
        <input name="passw" type="password" placeholder="Senha"/><br><br>
        <button>Entrar</button>
    </form>
    """

@app.post("/login")
async def do_login(user: str = Form(...), passw: str = Form(...)):
    if user == ADMIN_USER and passw == ADMIN_PASS:
        return RedirectResponse("/dashboard", status_code=302)
    return HTMLResponse("<h3>Login inválido</h3><a href='/'>Voltar</a>")

# ------------------ DASHBOARD ------------------

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    db = load_db()
    keys_html = ""
    for k, v in db.items():
        keys_html += f"""
        <tr>
            <td>{k}</td>
            <td>{v.get('expires_at')}</td>
            <td>{v.get('hwid')}</td>
            <td>{v.get('banned')}</td>
            <td>
                <a href="/reset_hwid/{k}">Reset HWID</a> |
                <a href="/ban/{k}">Ban</a>
            </td>
        </tr>
        """

    return f"""
    <h2>Painel Admin</h2>

    <h3>Aviso Global</h3>
    <form method="post" action="/set_notice">
        <input name="message" placeholder="Aviso global"/>
        <button>Atualizar</button>
    </form>

    <h3>Gerar Key</h3>
    <form method="post" action="/generate">
        <input name="value" placeholder="Quantidade (ex: 1)"/>
        <select name="unit">
            <option value="hours">Horas</option>
            <option value="days">Dias</option>
            <option value="months">Meses</option>
        </select>
        <button>Gerar</button>
    </form>

    <h3>Licenças</h3>
    <table border="1">
        <tr>
            <th>Key</th>
            <th>Expira</th>
            <th>HWID</th>
            <th>Banido</th>
            <th>Ações</th>
        </tr>
        {keys_html}
    </table>
    """

# ------------------ AÇÕES ADMIN ------------------

@app.post("/generate")
async def generate_key(value: int = Form(...), unit: str = Form(...)):
    db = load_db()

    key = str(uuid.uuid4()).split("-")[0].upper()
    now = datetime.utcnow()

    if unit == "hours":
        expires = now + timedelta(hours=value)
    elif unit == "days":
        expires = now + timedelta(days=value)
    else:
        expires = now + timedelta(days=value * 30)

    db[key] = {
        "expires_at": expires.isoformat(),
        "hwid": None,
        "banned": False
    }

    save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/reset_hwid/{key}")
def reset_hwid(key: str):
    db = load_db()
    if key in db:
        db[key]["hwid"] = None
        save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/ban/{key}")
def ban_key(key: str):
    db = load_db()
    if key in db:
        db[key]["banned"] = True
        save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.post("/set_notice")
async def set_notice(message: str = Form(...)):
    AVISO_GLOBAL["message"] = message
    return RedirectResponse("/dashboard", status_code=302)

# ------------------ API PARA O BOT ------------------

@app.post("/api/validate")
async def validate_license(data: dict):
    key = data.get("key")
    hwid = data.get("hwid")

    db = load_db()

    if key not in db:
        return JSONResponse({"status": "error", "message": "Key inválida"})

    lic = db[key]

    if lic.get("banned"):
        return JSONResponse({"status": "error", "message": "Key banida"})

    expires_at = datetime.fromisoformat(lic["expires_at"])
    if datetime.utcnow() > expires_at:
        return JSONResponse({"status": "error", "message": "Key expirada"})

    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_db(db)
    elif lic["hwid"] != hwid:
        return JSONResponse({"status": "error", "message": "HWID não autorizado"})

    return JSONResponse({
        "status": "ok",
        "message": "Login liberado",
        "expires_at": lic["expires_at"],
        "notice": AVISO_GLOBAL["message"]
    })

@app.get("/api/notice")
def get_notice():
    return AVISO_GLOBAL
