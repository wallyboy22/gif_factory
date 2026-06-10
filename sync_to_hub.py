"""
sync_to_hub.py - Sincroniza GIFs locais com o GCS Hub (FIXED)
"""
import os
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage

# Silenciar avisos de quota do Google SDK
warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

# Configurações
BUCKET_NAME = "mapbiomas-fire"
PROJECT_ID = "mapbiomas-fire-485203" # Adicionado para resolver o erro de cota
GCS_HUB_ROOT = "gif-factory"
LOCAL_OUTPUT = Path(r"outputs\v001")

# Inicializa o cliente uma única vez com o projeto de cota
client = storage.Client(project=PROJECT_ID)

def upload_file(local_path, remote_path):
    try:
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"OK: {remote_path}"
    except Exception as e:
        return f"ERRO: {remote_path} -> {e}"

def main():
    if not LOCAL_OUTPUT.exists():
        print(f"Erro: Pasta local {LOCAL_OUTPUT} não encontrada.")
        return

    print(f"Iniciando sincronização (Project: {PROJECT_ID})")
    print(f"Local: {LOCAL_OUTPUT} -> gs://{BUCKET_NAME}/{GCS_HUB_ROOT}")
    
    files_to_upload = []
    valid_exts = {'.gif', '.png', '.json', '.jpg', '.pdf', '.tif', '.tiff'}
    
    for root, dirs, files in os.walk(LOCAL_OUTPUT):
        for f in files:
            local_path = Path(root) / f
            if local_path.suffix.lower() in valid_exts:
                rel_path = local_path.relative_to(LOCAL_OUTPUT)
                remote_path = f"{GCS_HUB_ROOT}/{rel_path.as_posix()}"
                files_to_upload.append((local_path, remote_path))

    total = len(files_to_upload)
    print(f"Encontrados {total} arquivos para upload.")

    # Executa em paralelo (15 threads para evitar rate limiting)
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(upload_file, lp, rp) for lp, rp in files_to_upload]
        for i, future in enumerate(futures, 1):
            res = future.result()
            if i % 20 == 0 or i == total:
                print(f"[{i}/{total}] {res}")

if __name__ == "__main__":
    main()
