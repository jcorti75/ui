# deploy_vercel.py
# ------------------------------------------------------------
# Despliegue + dominios para Vercel en Windows.
# - Crea/usa proyecto
# - Agrega dominios (apex y www)
# - Despliega --prod con CLI (usando vercel.cmd)
# - Asigna alias
# ------------------------------------------------------------

import os
import re
import json
import shlex
import subprocess
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv, find_dotenv

# Cargar .env
load_dotenv(find_dotenv(), override=True)

# ======= CONFIG =======
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
TEAM_ID = os.getenv("VERCEL_TEAM_ID", "jose-cortis-projects")
PROJECT_NAME = os.getenv("VERCEL_PROJECT_NAME", "aitrustyou")
FRAMEWORK = os.getenv("VERCEL_FRAMEWORK", "vite")

FRONTEND_DIR = os.getenv("FRONTEND_DIR", str(Path(__file__).parent.resolve()))

APEX_DOMAIN = os.getenv("APEX_DOMAIN", "aitrustyou.com")
WWW_DOMAIN = os.getenv("WWW_DOMAIN", "www.aitrustyou.com")

APEX_A_RECORD = "76.76.21.21"
WWW_CNAME = "cname.vercel-dns.com"

API_HEADERS = {"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"}

print("TEAM_ID:", TEAM_ID)
print("TOKEN:", (VERCEL_TOKEN[:4] + "..." + VERCEL_TOKEN[-4:]) if VERCEL_TOKEN else None)
print("FRONTEND_DIR:", FRONTEND_DIR)

# ======= UTIL =======
def assert_prereqs():
    if not VERCEL_TOKEN:
        raise SystemExit("❌ Falta VERCEL_TOKEN en .env")

def resolve_vercel_cli() -> str:
    """
    Devuelve la ruta al ejecutable de Vercel CLI en Windows.
    Forzamos .cmd para evitar WinError 193.
    """
    try:
        proc = subprocess.run(["where", "vercel"], text=True, capture_output=True, check=False)
        if proc.returncode == 0:
            first = proc.stdout.strip().splitlines()[0].strip().strip('"')
            if first.lower().endswith("vercel.cmd"):
                return first
            if first.lower().endswith("vercel"):
                candidate = first + ".cmd"
                if os.path.exists(candidate):
                    return candidate
    except Exception:
        pass

    fallback = os.path.expanduser(r"~\AppData\Roaming\npm\vercel.cmd")
    if os.path.exists(fallback):
        return fallback

    raise SystemExit("❌ No se encontró la CLI de Vercel. Instálala con: npm install -g vercel")

VERCEL_BIN = resolve_vercel_cli()

def run(cmd: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Ejecuta comandos de shell usando vercel.cmd y shell=True.
    Inyecta --token si no está presente.
    """
    cmd_str = cmd.strip()
    if cmd_str.startswith("vercel "):
        cmd_str = cmd_str.replace("vercel", f"\"{VERCEL_BIN}\"", 1)
        if VERCEL_TOKEN and "--token" not in cmd_str:
            cmd_str += f" --token {VERCEL_TOKEN}"
    elif cmd_str == "vercel":
        cmd_str = f"\"{VERCEL_BIN}\""
        if VERCEL_TOKEN:
            cmd_str += f" --token {VERCEL_TOKEN}"

    print(f"\n$ {cmd_str}")
    proc = subprocess.run(
        cmd_str,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        shell=True,
        env={**os.environ, "VERCEL_TOKEN": VERCEL_TOKEN}
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr)
        raise RuntimeError(f"Command failed: {cmd}\n{proc.stderr}")
    return proc

# ======= API PROJECTS =======
def get_project(name: str):
    url = f"https://api.vercel.com/v9/projects?teamId={TEAM_ID}"
    r = requests.get(url, headers=API_HEADERS, timeout=60)
    r.raise_for_status()
    for p in r.json().get("projects", []):
        if p["name"] == name:
            return p
    return None

def create_project_if_needed():
    p = get_project(PROJECT_NAME)
    if p:
        print(f"✅ Proyecto existe: {p['id']} ({PROJECT_NAME})")
        return p
    print("📦 Creando proyecto…")
    url = f"https://api.vercel.com/v9/projects?teamId={TEAM_ID}"
    payload = {"name": PROJECT_NAME, "framework": FRAMEWORK}
    r = requests.post(url, headers=API_HEADERS, data=json.dumps(payload), timeout=60)
    if r.status_code not in (200, 201):
        raise SystemExit(f"❌ Error al crear proyecto: {r.status_code} {r.text}")
    p = r.json()
    print("✅ Proyecto creado:", p.get("id"))
    return p

# ======= API DOMAINS (v10) =======
def add_domain_to_project(project_id: str, domain: str):
    url = f"https://api.vercel.com/v9/projects/{project_id}/domains?teamId={TEAM_ID}"
    r = requests.get(url, headers=API_HEADERS, timeout=60)
    r.raise_for_status()
    for d in r.json().get("domains", []):
        if d.get("name") == domain:
            print(f"✅ Dominio ya asignado al proyecto: {domain}")
            return
    print(f"🌐 Agregando dominio al proyecto: {domain} …")
    r = requests.post(url, headers=API_HEADERS, data=json.dumps({"name": domain}), timeout=60)
    if r.status_code not in (200, 201):
        raise SystemExit(f"❌ Error al agregar dominio {domain}: {r.status_code} {r.text}")
    print(f"🌍 Dominio agregado: {domain}")

def check_domain_status(domain: str):
    url = f"https://api.vercel.com/v10/domains/{domain}?teamId={TEAM_ID}"
    r = requests.get(url, headers=API_HEADERS, timeout=60)
    if r.status_code != 200:
        print("❌ Domain status error:", r.text)
        return None
    data = r.json()
    print(f"🔎 {domain} configured={data.get('configured')}")
    return data

# ======= DEPLOY & ALIAS =======
DEPLOY_URL_RE = re.compile(r"https?://[a-zA-Z0-9\-\._]+\.vercel\.app")

def deploy_prod_and_get_url() -> str:
    print(f"📁 FRONTEND_DIR = {FRONTEND_DIR}")
    if not Path(FRONTEND_DIR).exists():
        raise SystemExit(f"❌ FRONTEND_DIR no existe: {FRONTEND_DIR}")
    print("🚀 Desplegando a producción con Vercel CLI…")
    proc = run(f"vercel --prod --scope {TEAM_ID} --yes --confirm", cwd=FRONTEND_DIR)
    urls = DEPLOY_URL_RE.findall(proc.stdout or "")
    if not urls:
        urls = DEPLOY_URL_RE.findall(proc.stderr or "")
    if not urls:
        raise RuntimeError("No se encontró la URL del deployment en la salida de la CLI.")
    deploy_url = urls[-1]
    print(f"✅ Deployment URL: {deploy_url}")
    return deploy_url

def set_alias(deploy_url: str, domain: str):
    print(f"🔗 Asignando alias {domain} …")
    run(f"vercel alias set {deploy_url} {domain} --scope {TEAM_ID}")

# ======= MAIN =======
def main():
    assert_prereqs()
    proj = create_project_if_needed()
    project_id = proj["id"]
    for dom in (APEX_DOMAIN, WWW_DOMAIN):
        add_domain_to_project(project_id, dom)
    check_domain_status(APEX_DOMAIN)
    check_domain_status(WWW_DOMAIN)
    deploy_url = deploy_prod_and_get_url()
    set_alias(deploy_url, APEX_DOMAIN)
    set_alias(deploy_url, WWW_DOMAIN)
    print("\n🎯 Listo. Verifica en incógnito: https://aitrustyou.com")

if __name__ == "__main__":
    main()





