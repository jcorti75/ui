import os
import requests
import zipfile
import tempfile

# ==== Configura tus datos ====
vercel_token = "jN0JcOHLPmP5DoCqhFFfMyTn"
vercel_project_name = "aitrustyou"
vercel_team_id = None  # Si no usas equipos, deja como None
frontend_dir = "ui"
deployment_name = "aitrustyou.com"  # Nombre que aparecerá en Vercel
alias_domain = "www.aitrustyou.com"  # Tu dominio público ya conectado a Vercel

# ==== Paso 1: Comprimir frontend (ui/) ====
def zip_frontend(source_dir):
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, start=source_dir)
                zipf.write(filepath, arcname)
    return temp_zip.name

# ==== Paso 2: Subir a Vercel ====
def deploy_to_vercel(zip_path):
    headers = {"Authorization": f"Bearer {vercel_token}"}
    files = {'file': open(zip_path, 'rb')}

    # Construir URL de despliegue
    url = "https://api.vercel.com/v13/deployments"
    params = {
        "name": vercel_project_name,
        "project": vercel_project_name,
    }
    if vercel_team_id:
        params["teamId"] = vercel_team_id

    print("🚀 Subiendo a Vercel...")
    res = requests.post(url, headers=headers, files=files, params=params)
    res.raise_for_status()
    data = res.json()
    print(f"✅ Deploy subido con ID: {data['id']}")

    # Asignar alias personalizado
    print("🔗 Asignando dominio...")
    alias_url = f"https://api.vercel.com/v2/now/deployments/{data['id']}/aliases"
    alias_payload = {"alias": alias_domain}
    alias_res = requests.post(alias_url, headers=headers, json=alias_payload)
    alias_res.raise_for_status()

    print(f"🌍 Dominio asignado correctamente: https://{alias_domain}")

# ==== Ejecutar todo ====
if __name__ == "__main__":
    zipped_path = zip_frontend(frontend_dir)
    deploy_to_vercel(zipped_path)

