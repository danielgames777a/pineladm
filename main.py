from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os

app = FastAPI()

DB_FILE = "licenses_db.json"
NOTICE_FILE = "notice.txt"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

class ValidateReq(BaseModel):
    key: str
    hwid: str

@app.get("/")
def home():
    return {"status": "ok", "service": "pineladm"}

@app.get("/api/notice")
def get_notice():
    if os.path.exists(NOTICE_FILE):
        with open(NOTICE_FILE, "r") as f:
            return {"notice": f.read()}
    return {"notice": ""}

@app.post("/api/validar")
def validar(req: ValidateReq):
    db = load_db()
    key = req.key

    if key not in db:
        return {"ok": False, "msg": "Key inválida", "notice": ""}

    lic = db[key]

    # verifica expiração
    if lic["expires_at"]:
        exp = datetime.fromisoformat(lic["expires_at"])
        if datetime.utcnow() > exp:
            return {"ok": False, "msg": "Key expirada", "notice": ""}

    # verifica HWID (primeiro uso grava)
    if lic.get("hwid") is None:
        lic["hwid"] = req.hwid
        db[key] = lic
        save_db(db)
    elif lic["hwid"] != req.hwid:
        return {"ok": False, "msg": "HWID não autorizado", "notice": ""}

    return {"ok": True, "msg": "Acesso liberado", "notice": ""}

