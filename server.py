# ============================================================
#  server.py — Painel Admin DNL (FastAPI + Visual Moderno)
# ============================================================
from fastapi import FastAPI, Form, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import json, os, uuid, secrets
from datetime import datetime, timedelta

app = FastAPI()

DB_FILE      = "licenses_db.json"
LOG_FILE     = "login_logs.json"
ADMIN_USER   = "admin"
ADMIN_PASS   = "1234"
SESSIONS     = {}  # token -> True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ── DB helpers ───────────────────────────────────────────────
def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f: json.dump({}, f)
    with open(DB_FILE) as f: return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

def load_logs():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f: json.dump([], f)
    with open(LOG_FILE) as f: return json.load(f)

def save_logs(logs):
    with open(LOG_FILE, "w") as f: json.dump(logs[-500:], f, indent=4)

def add_log(key, hwid, status, msg, ip=""):
    logs = load_logs()
    logs.append({
        "time":   datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S"),
        "key":    key,
        "hwid":   (hwid or "")[:16] + "…" if hwid and len(hwid) > 16 else (hwid or ""),
        "status": status,
        "msg":    msg,
        "ip":     ip,
    })
    save_logs(logs)

def check_auth(session_token: str = None):
    if not session_token or session_token not in SESSIONS:
        return False
    return True

def get_notice():
    db = load_db()
    return db.get("__notice__", "Nenhum aviso no momento.")

# ── HTML base ────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>DNL Admin Panel</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#080808;--bg2:#0f0f0f;--card:#141414;--border:#1e1e1e;
  --neon:#00ff88;--neon2:#00cc6a;--red:#ff3b3b;--yellow:#f5c518;
  --blue:#3b82f6;--muted:#444;--text:#e8e8e8;--soft:#888;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;min-height:100vh;}
a{color:var(--neon);text-decoration:none;}
a:hover{text-decoration:underline;}

/* LAYOUT */
.sidebar{position:fixed;top:0;left:0;width:220px;height:100vh;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:24px 0;z-index:100;}
.sidebar-logo{padding:0 24px 24px;border-bottom:1px solid var(--border);}
.sidebar-logo h1{font-family:'Syne',sans-serif;font-size:20px;color:var(--neon);letter-spacing:1px;}
.sidebar-logo span{font-size:10px;color:var(--muted);}
.nav{padding:16px 0;flex:1;}
.nav a{display:flex;align-items:center;gap:10px;padding:10px 24px;color:var(--soft);font-size:12px;font-weight:600;transition:.2s;}
.nav a:hover,.nav a.active{color:var(--neon);background:rgba(0,255,136,.05);text-decoration:none;border-left:2px solid var(--neon);}
.sidebar-footer{padding:16px 24px;border-top:1px solid var(--border);font-size:10px;color:var(--muted);}
.main{margin-left:220px;padding:32px;}

/* CARDS */
.page-title{font-family:'Syne',sans-serif;font-size:26px;color:var(--neon);margin-bottom:24px;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:28px;}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;position:relative;overflow:hidden;}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.stat-card.green::before{background:var(--neon);}
.stat-card.red::before{background:var(--red);}
.stat-card.yellow::before{background:var(--yellow);}
.stat-card.blue::before{background:var(--blue);}
.stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
.stat-value{font-family:'Syne',sans-serif;font-size:32px;font-weight:800;}
.stat-card.green .stat-value{color:var(--neon);}
.stat-card.red .stat-value{color:var(--red);}
.stat-card.yellow .stat-value{color:var(--yellow);}
.stat-card.blue .stat-value{color:var(--blue);}

/* TABELAS */
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:24px;}
.table-header{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.table-header h3{font-size:13px;color:var(--text);font-weight:600;}
table{width:100%;border-collapse:collapse;}
th{padding:10px 16px;text-align:left;font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);}
td{padding:11px 16px;font-size:11px;border-bottom:1px solid #1a1a1a;vertical-align:middle;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(255,255,255,.02);}
.badge{display:inline-block;padding:3px 8px;border-radius:4px;font-size:10px;font-weight:700;}
.badge.ok{background:rgba(0,255,136,.1);color:var(--neon);}
.badge.exp{background:rgba(245,197,24,.1);color:var(--yellow);}
.badge.ban{background:rgba(255,59,59,.1);color:var(--red);}
.badge.err{background:rgba(255,59,59,.1);color:var(--red);}

/* BOTÕES */
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:6px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace;cursor:pointer;border:none;transition:.2s;}
.btn-neon{background:var(--neon);color:#000;}
.btn-neon:hover{background:var(--neon2);}
.btn-red{background:rgba(255,59,59,.15);color:var(--red);border:1px solid rgba(255,59,59,.3);}
.btn-red:hover{background:rgba(255,59,59,.25);}
.btn-gray{background:rgba(255,255,255,.06);color:var(--soft);border:1px solid var(--border);}
.btn-gray:hover{color:var(--text);}
.btn-yellow{background:rgba(245,197,24,.1);color:var(--yellow);border:1px solid rgba(245,197,24,.3);}

/* FORMS */
.form-row{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;}
input,select{background:#0d0d0d;border:1px solid var(--border);color:var(--text);padding:9px 12px;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:12px;outline:none;transition:.2s;}
input:focus,select:focus{border-color:var(--neon);box-shadow:0 0 0 2px rgba(0,255,136,.1);}
input::placeholder{color:var(--muted);}
.search-bar{width:260px;}

/* COPY KEY */
.key-cell{display:flex;align-items:center;gap:8px;}
.copy-btn{background:none;border:none;color:var(--muted);cursor:pointer;padding:2px 4px;border-radius:4px;font-size:13px;transition:.2s;}
.copy-btn:hover{color:var(--neon);}
.copied{color:var(--neon) !important;}

/* LOGIN PAGE */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;}
.login-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:40px;width:360px;}
.login-card h1{font-family:'Syne',sans-serif;color:var(--neon);font-size:24px;margin-bottom:4px;}
.login-card p{color:var(--muted);font-size:11px;margin-bottom:28px;}
.field{margin-bottom:16px;}
.field label{display:block;font-size:10px;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;}
.field input{width:100%;}
.neon-bar{height:2px;background:var(--neon);border-radius:0 0 16px 16px;margin:-1px -1px 0;}

/* SECTION */
.section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:20px;}
.section h3{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px;}

/* TOAST */
#toast{position:fixed;bottom:24px;right:24px;background:var(--neon);color:#000;padding:10px 18px;border-radius:8px;font-size:12px;font-weight:700;opacity:0;transition:opacity .3s;pointer-events:none;z-index:9999;}
</style>
</head>
<body>
{BODY}
<div id="toast">✓ Copiado!</div>
<script>
function copyKey(key){
  navigator.clipboard.writeText(key);
  var t=document.getElementById('toast');
  t.style.opacity=1;
  setTimeout(()=>t.style.opacity=0,1800);
}
function filterTable(){
  var q=document.getElementById('search').value.toLowerCase();
  document.querySelectorAll('#keys-table tr').forEach(function(r){
    r.style.display=r.innerText.toLowerCase().includes(q)?'':'none';
  });
}
</script>
</body></html>"""

def page(body, active="keys"):
    nav = f"""
    <div class="sidebar">
      <div class="sidebar-logo">
        <h1>⬡ DNL</h1>
        <span>ADMIN PANEL</span>
      </div>
      <nav class="nav">
        <a href="/dashboard" class="{'active' if active=='keys' else ''}">🔑 Keys</a>
        <a href="/logs" class="{'active' if active=='logs' else ''}">📋 Logs de Acesso</a>
      </nav>
      <div class="sidebar-footer">v2.0 · DNL AutoBot</div>
    </div>
    <div class="main">{body}</div>"""
    return HTML.replace("{BODY}", nav)

# ── Login ────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def login_page():
    body = """
    <div class="login-wrap">
      <div>
        <div class="login-card">
          <h1>⬡ DNL Admin</h1>
          <p>Acesso restrito ao painel de controle</p>
          <form method="post" action="/login">
            <div class="field"><label>Usuário</label><input name="user" placeholder="admin" autocomplete="off"/></div>
            <div class="field"><label>Senha</label><input name="passw" type="password" placeholder="••••••"/></div>
            <button class="btn btn-neon" style="width:100%;justify-content:center;padding:11px;">Entrar →</button>
          </form>
        </div>
        <div class="neon-bar"></div>
      </div>
    </div>"""
    return HTML.replace("{BODY}", body)

@app.post("/login")
async def do_login(user: str = Form(...), passw: str = Form(...)):
    if user == ADMIN_USER and passw == ADMIN_PASS:
        token = secrets.token_hex(32)
        SESSIONS[token] = True
        r = RedirectResponse("/dashboard", status_code=302)
        r.set_cookie("session_token", token, httponly=True, max_age=86400)
        return r
    return HTMLResponse(HTML.replace("{BODY}", '<div class="login-wrap"><div class="login-card"><h1 style="color:var(--red)">❌ Login inválido</h1><br><a href="/" class="btn btn-gray">← Voltar</a></div></div>'))

# ── Dashboard ────────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(session_token: str = Cookie(None)):
    if not check_auth(session_token):
        return RedirectResponse("/")
    db = load_db()
    keys = {k: v for k, v in db.items() if not k.startswith("__")}
    now  = datetime.utcnow()

    total   = len(keys)
    ativas  = sum(1 for v in keys.values() if not v.get("banned") and datetime.fromisoformat(v["expires_at"]) > now)
    expiras = sum(1 for v in keys.values() if not v.get("banned") and datetime.fromisoformat(v["expires_at"]) <= now)
    banidas = sum(1 for v in keys.values() if v.get("banned"))

    rows = ""
    for k, v in sorted(keys.items(), key=lambda x: x[1]["expires_at"], reverse=True):
        exp   = datetime.fromisoformat(v["expires_at"])
        venc  = exp <= now
        ban   = v.get("banned", False)
        hwid  = v.get("hwid") or "—"
        hwid_short = hwid[:20] + "…" if len(hwid) > 20 else hwid

        if ban:   badge = '<span class="badge ban">BANIDA</span>'
        elif venc: badge = '<span class="badge exp">EXPIRADA</span>'
        else:      badge = '<span class="badge ok">ATIVA</span>'

        acoes = f'<a href="/reset_hwid/{k}" class="btn btn-gray" style="margin-right:4px">↺ HWID</a>'
        if ban:
            acoes += f'<a href="/unban/{k}" class="btn btn-yellow" style="margin-right:4px">✓ Unban</a>'
        else:
            acoes += f'<a href="/ban/{k}" class="btn btn-red" style="margin-right:4px">✕ Ban</a>'
        acoes += f'<a href="/delete/{k}" class="btn btn-red" onclick="return confirm(\'Deletar key {k}?\')">🗑</a>'

        rows += f"""<tr>
          <td><div class="key-cell">
            <span style="color:var(--neon);font-weight:700">{k}</span>
            <button class="copy-btn" onclick="copyKey('{k}')" title="Copiar key">⎘</button>
          </div></td>
          <td>{exp.strftime('%d/%m/%Y %H:%M')}</td>
          <td title="{hwid}" style="color:var(--soft)">{hwid_short}</td>
          <td>{badge}</td>
          <td>{acoes}</td>
        </tr>"""

    notice = get_notice()
    body = f"""
    <div class="page-title">Painel de Controle</div>

    <div class="stats">
      <div class="stat-card blue"><div class="stat-label">Total de Keys</div><div class="stat-value">{total}</div></div>
      <div class="stat-card green"><div class="stat-label">Keys Ativas</div><div class="stat-value">{ativas}</div></div>
      <div class="stat-card yellow"><div class="stat-label">Expiradas</div><div class="stat-value">{expiras}</div></div>
      <div class="stat-card red"><div class="stat-label">Banidas</div><div class="stat-value">{banidas}</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;">
      <div class="section">
        <h3>🔑 Gerar Nova Key</h3>
        <form method="post" action="/generate">
          <div class="form-row">
            <input name="value" placeholder="Quantidade" type="number" min="1" style="width:110px"/>
            <select name="unit">
              <option value="hours">Horas</option>
              <option value="days">Dias</option>
              <option value="months">Meses</option>
            </select>
            <button class="btn btn-neon" type="submit">+ Gerar</button>
          </div>
        </form>
      </div>
      <div class="section">
        <h3>📢 Aviso Global</h3>
        <form method="post" action="/set_notice">
          <div class="form-row">
            <input name="message" placeholder="Mensagem para os usuários..." value="{notice}" style="flex:1"/>
            <button class="btn btn-neon" type="submit">Salvar</button>
          </div>
        </form>
      </div>
    </div>

    <div class="table-wrap">
      <div class="table-header">
        <h3>🗝 Licenças ({total})</h3>
        <input id="search" class="search-bar" placeholder="🔍 Buscar key, HWID..." oninput="filterTable()"/>
      </div>
      <table>
        <thead><tr>
          <th>Key</th><th>Expira em</th><th>HWID</th><th>Status</th><th>Ações</th>
        </tr></thead>
        <tbody id="keys-table">{rows if rows else '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:30px">Nenhuma key cadastrada</td></tr>'}</tbody>
      </table>
    </div>"""
    return HTMLResponse(page(body, "keys"))

# ── Logs ─────────────────────────────────────────────────────
@app.get("/logs", response_class=HTMLResponse)
def logs_page(session_token: str = Cookie(None)):
    if not check_auth(session_token):
        return RedirectResponse("/")
    logs = list(reversed(load_logs()))
    rows = ""
    for l in logs:
        ok = l["status"] == "ok"
        badge = f'<span class="badge {"ok" if ok else "err"}">{"✓ OK" if ok else "✕ ERRO"}</span>'
        rows += f"""<tr>
          <td style="color:var(--soft)">{l['time']}</td>
          <td><span style="color:var(--neon);font-weight:700">{l['key']}</span></td>
          <td style="color:var(--soft);font-size:10px">{l['hwid']}</td>
          <td>{badge}</td>
          <td style="color:var(--soft)">{l['msg']}</td>
          <td style="color:var(--soft)">{l.get('ip','')}</td>
        </tr>"""

    body = f"""
    <div class="page-title">Logs de Acesso</div>
    <div class="table-wrap">
      <div class="table-header">
        <h3>📋 Histórico ({len(logs)} registros)</h3>
        <a href="/clear_logs" class="btn btn-red" onclick="return confirm('Limpar todos os logs?')">🗑 Limpar logs</a>
      </div>
      <table>
        <thead><tr><th>Hora</th><th>Key</th><th>HWID</th><th>Status</th><th>Mensagem</th><th>IP</th></tr></thead>
        <tbody>{rows if rows else '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:30px">Nenhum log ainda</td></tr>'}</tbody>
      </table>
    </div>"""
    return HTMLResponse(page(body, "logs"))

# ── Ações ────────────────────────────────────────────────────
@app.post("/generate")
async def generate_key(session_token: str = Cookie(None),
                       value: int = Form(...), unit: str = Form(...)):
    if not check_auth(session_token): return RedirectResponse("/")
    db  = load_db()
    key = str(uuid.uuid4()).split("-")[0].upper()
    now = datetime.utcnow()
    if unit == "hours":   expires = now + timedelta(hours=value)
    elif unit == "days":  expires = now + timedelta(days=value)
    else:                 expires = now + timedelta(days=value * 30)
    db[key] = {"expires_at": expires.isoformat(), "hwid": None, "banned": False}
    save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/reset_hwid/{key}")
def reset_hwid(key: str, session_token: str = Cookie(None)):
    if not check_auth(session_token): return RedirectResponse("/")
    db = load_db()
    if key in db: db[key]["hwid"] = None; save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/ban/{key}")
def ban_key(key: str, session_token: str = Cookie(None)):
    if not check_auth(session_token): return RedirectResponse("/")
    db = load_db()
    if key in db: db[key]["banned"] = True; save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/unban/{key}")
def unban_key(key: str, session_token: str = Cookie(None)):
    if not check_auth(session_token): return RedirectResponse("/")
    db = load_db()
    if key in db: db[key]["banned"] = False; save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/delete/{key}")
def delete_key(key: str, session_token: str = Cookie(None)):
    if not check_auth(session_token): return RedirectResponse("/")
    db = load_db()
    if key in db: del db[key]; save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.post("/set_notice")
async def set_notice(session_token: str = Cookie(None), message: str = Form(...)):
    if not check_auth(session_token): return RedirectResponse("/")
    db = load_db()
    db["__notice__"] = message
    save_db(db)
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/clear_logs")
def clear_logs(session_token: str = Cookie(None)):
    if not check_auth(session_token): return RedirectResponse("/")
    save_logs([])
    return RedirectResponse("/logs", status_code=302)

# ── API para o Bot ───────────────────────────────────────────
@app.post("/api/validate")
async def validate_license(request: Request, data: dict):
    key  = data.get("key", "")
    hwid = data.get("hwid", "")
    ip   = request.client.host if request.client else ""
    db   = load_db()

    if key not in db:
        add_log(key, hwid, "error", "Key inválida", ip)
        return JSONResponse({"status": "error", "message": "Key inválida"})

    lic = db[key]

    if lic.get("banned"):
        add_log(key, hwid, "error", "Key banida", ip)
        return JSONResponse({"status": "error", "message": "Key banida"})

    expires_at = datetime.fromisoformat(lic["expires_at"])
    if datetime.utcnow() > expires_at:
        add_log(key, hwid, "error", "Key expirada", ip)
        return JSONResponse({"status": "error", "message": "Key expirada"})

    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_db(db)
    elif lic["hwid"] != hwid:
        add_log(key, hwid, "error", "HWID não autorizado", ip)
        return JSONResponse({"status": "error", "message": "HWID não autorizado"})

    add_log(key, hwid, "ok", "Login liberado", ip)
    return JSONResponse({
        "status":     "ok",
        "message":    "Login liberado",
        "expires_at": lic["expires_at"],
        "notice":     db.get("__notice__", "")
    })

@app.get("/api/notice")
def get_notice_api():
    db = load_db()
    return {"message": db.get("__notice__", "Nenhum aviso no momento.")}
