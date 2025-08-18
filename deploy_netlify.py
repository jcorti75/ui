# deploy_netlify.py
# ------------------------------------------------------------
# Despliegue + dominios para Netlify
# - Crea/usa sitio
# - Sube archivos vía ZIP
# - Agrega dominios custom
# ------------------------------------------------------------

import os
import json
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv, find_dotenv

# Cargar .env
load_dotenv(find_dotenv(), override=True)

# ======= CONFIG =======
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")
SITE_NAME = os.getenv("NETLIFY_SITE_NAME", "aitrustyou")
FRONTEND_DIR = os.getenv("FRONTEND_DIR", str(Path(__file__).parent.resolve()))

APEX_DOMAIN = os.getenv("APEX_DOMAIN", "aitrustyou.com")
WWW_DOMAIN = os.getenv("WWW_DOMAIN", "www.aitrustyou.com")

API_HEADERS = {"Authorization": f"Bearer {NETLIFY_TOKEN}"}

print("SITE_NAME:", SITE_NAME)
print("TOKEN:", (NETLIFY_TOKEN[:4] + "..." + NETLIFY_TOKEN[-4:]) if NETLIFY_TOKEN else None)
print("FRONTEND_DIR:", FRONTEND_DIR)

# ======= UTIL =======
def assert_prereqs():
    if not NETLIFY_TOKEN:
        raise SystemExit("❌ Falta NETLIFY_TOKEN en .env")

def create_zip_from_directory(directory: str) -> str:
    """Crea un ZIP temporal con todos los archivos del directorio."""
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    print(f"🔍 Explorando directorio: {directory}")
    
    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            # Excluir archivos innecesarios
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            print(f"📁 Procesando carpeta: {root}")
            print(f"📄 Archivos encontrados: {files}")
            
            for file in files:
                if file.startswith('.') or file.endswith('.py') or file == '.env':
                    print(f"❌ Excluyendo: {file}")
                    continue
                    
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, directory)
                print(f"✅ Incluyendo: {file} -> {arc_path}")
                zipf.write(file_path, arc_path)
                
    print(f"📦 ZIP creado: {temp_zip.name}")
    return temp_zip.name

# ======= API SITES =======
def get_site_by_name(name: str):
    """Busca un sitio por nombre."""
    url = "https://api.netlify.com/api/v1/sites"
    r = requests.get(url, headers=API_HEADERS, timeout=60)
    r.raise_for_status()
    
    for site in r.json():
        if site.get("name") == name:
            return site
    return None

def create_site_if_needed():
    """Crea o obtiene el sitio."""
    site = get_site_by_name(SITE_NAME)
    if site:
        print(f"✅ Sitio existe: {site['id']} ({SITE_NAME})")
        print(f"🌐 URL: {site['url']}")
        return site
        
    print("📦 Creando sitio…")
    url = "https://api.netlify.com/api/v1/sites"
    payload = {"name": SITE_NAME}
    
    r = requests.post(url, headers=API_HEADERS, json=payload, timeout=60)
    if r.status_code not in (200, 201):
        raise SystemExit(f"❌ Error al crear sitio: {r.status_code} {r.text}")
        
    site = r.json()
    print(f"✅ Sitio creado: {site['id']}")
    print(f"🌐 URL: {site['url']}")
    return site

# ======= DEPLOY =======
def deploy_site(site_id: str) -> str:
    """Despliega el sitio subiendo un ZIP."""
    print(f"📁 FRONTEND_DIR = {FRONTEND_DIR}")
    if not Path(FRONTEND_DIR).exists():
        raise SystemExit(f"❌ FRONTEND_DIR no existe: {FRONTEND_DIR}")
        
    # Crear ZIP
    zip_path = create_zip_from_directory(FRONTEND_DIR)
    
    try:
        print("🚀 Desplegando a Netlify…")
        url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        
        with open(zip_path, 'rb') as zip_file:
            files = {'file': ('site.zip', zip_file, 'application/zip')}
            headers = {"Authorization": f"Bearer {NETLIFY_TOKEN}"}
            
            r = requests.post(url, headers=headers, files=files, timeout=300)
            
        if r.status_code not in (200, 201):
            raise SystemExit(f"❌ Error al desplegar: {r.status_code} {r.text}")
            
        deploy = r.json()
        deploy_url = deploy.get('deploy_ssl_url') or deploy.get('ssl_url')
        
        print(f"✅ Deploy exitoso: {deploy['id']}")
        print(f"🌐 URL del deploy: {deploy_url}")
        
        return deploy_url
        
    finally:
        # Limpiar archivo temporal
        os.unlink(zip_path)

# ======= DOMAINS =======
def add_custom_domain(site_id: str, domain: str):
    """Agrega un dominio custom al sitio."""
    # Primero verificar si ya existe
    url = f"https://api.netlify.com/api/v1/sites/{site_id}"
    r = requests.get(url, headers=API_HEADERS, timeout=60)
    r.raise_for_status()
    
    site_data = r.json()
    current_domains = [d.get('name') for d in site_data.get('domain_aliases', [])]
    current_domains.append(site_data.get('custom_domain'))
    
    if domain in current_domains:
        print(f"✅ Dominio ya configurado: {domain}")
        return
        
    print(f"🌐 Agregando dominio custom: {domain}")
    url = f"https://api.netlify.com/api/v1/sites/{site_id}/domains"
    
    r = requests.post(url, headers=API_HEADERS, json={"name": domain}, timeout=60)
    if r.status_code not in (200, 201):
        print(f"⚠️  Advertencia al agregar {domain}: {r.status_code} {r.text}")
    else:
        print(f"✅ Dominio agregado: {domain}")

def show_dns_instructions():
    """Muestra las instrucciones DNS."""
    print("\n" + "="*50)
    print("📋 INSTRUCCIONES DNS:")
    print("="*50)
    print("En tu proveedor de dominio, configura:")
    print()
    print("Para aitrustyou.com:")
    print("  Tipo: A")
    print("  Nombre: @")
    print("  Valor: 75.2.60.5")
    print()
    print("Para www.aitrustyou.com:")
    print("  Tipo: CNAME") 
    print("  Nombre: www")
    print("  Valor: aitrustyou.netlify.app")
    print()
    print("⏰ La propagación puede tardar hasta 24 horas.")
    print("="*50)

# ======= MAIN =======
def main():
    assert_prereqs()
    
    # Crear/obtener sitio
    site = create_site_if_needed()
    site_id = site["id"]
    
    # Desplegar
    deploy_url = deploy_site(site_id)
    
    # Agregar dominios custom
    for domain in (APEX_DOMAIN, WWW_DOMAIN):
        add_custom_domain(site_id, domain)
    
    # Mostrar instrucciones DNS
    show_dns_instructions()
    
    print(f"\n🎯 ¡Listo! Sitio desplegado en: {deploy_url}")
    print(f"🔧 Configura el DNS y luego verifica: https://{APEX_DOMAIN}")

if __name__ == "__main__":
    main()






