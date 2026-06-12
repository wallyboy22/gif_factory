"""
Fire Col5 Export Pipeline — 5 estagios com upload GCS por combo.

Cada combo gera frames, GIF e collage localmente.
Ao completar, sobe para GCS e deleta o diretorio local.
Estado de upload persistente (.upload_state.json) evita re-processar
combos que ja foram enviados ao GCS.

Uso:
  python scripts/run_fire_col5_export.py --workers 6 --resume
  python scripts/run_fire_col5_export.py --stage 1            # so Brasil
  python scripts/run_fire_col5_export.py --stage 1-3          # Brasil + Biomas
  python scripts/run_fire_col5_export.py --skip-upload        # sem GCS
"""

import json
import sys
import os
import argparse
import shutil
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# AMBIENTE
# ============================================================

IN_COLAB = False
try:
    import google.colab
    IN_COLAB = True
except ImportError:
    pass

if IN_COLAB:
    get_ipython().system('pip install -q earthengine-api pillow pyyaml google-cloud-storage 2>/dev/null')
    import ee
    ee.Authenticate()
    ee.Initialize(project='mapbiomas-fire-485203')
else:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, 'src')):
        parent = os.path.dirname(cwd)
        while not os.path.exists(os.path.join(parent, 'src')) and parent != os.path.dirname(parent):
            parent = os.path.dirname(parent)
        if os.path.exists(os.path.join(parent, 'src')):
            os.chdir(parent)
    import ee
    try:
        ee.Initialize(project='mapbiomas-fire-485203')
    except Exception:
        pass

# ============================================================
# CONFIGURACAO
# ============================================================

DATASET_ID = "brasil_fire_col5"
UPLOAD_STATE_FILE = "outputs/v001/.upload_state.json"

PRODUCTS = [
    "annual_burned", "monthly_burned", "scar_size_range",
    "accumulated_burned", "fire_frequency", "year_last_fire", "time_after_fire", "unprecedented_fire",
    "annual_burned_coverage_nivel0", "annual_burned_coverage_nivel1",
    "annual_burned_coverage_nivel1_1", "annual_burned_coverage_nivel2",
    "annual_burned_coverage_nivel3", "annual_burned_coverage_nivel4",
    "accumulated_burned_coverage_nivel0", "accumulated_burned_coverage_nivel1",
    "accumulated_burned_coverage_nivel1_1", "accumulated_burned_coverage_nivel2",
    "accumulated_burned_coverage_nivel3", "accumulated_burned_coverage_nivel4",
    "severity", "fire_return_interval", "mean_fire_return_interval", "nbr_min",
]

STAGES = [
    {"name": "Brasil",               "territories": ["pais_brasil"]},
    {"name": "Biomas (agregado)",    "territories": ["biomas_todos"]},
    {"name": "Biomas (individual)",  "territories": [
        "bioma_amazonia", "bioma_caatinga", "bioma_cerrado", "bioma_mata_atlantica", "bioma_pampa", "bioma_pantanal",
    ]},
    {"name": "Regiões",              "territories": [
        "regiao_bap", "regiao_bap_planalto", "regiao_matopiba", "regiao_matopiba_cerrado",
        "regiao_centro_oeste", "regiao_nordeste", "regiao_norte", "regiao_sudeste", "regiao_sul",
    ]},
    {"name": "UFs",                  "territories": [
        "uf_df", "uf_acre", "uf_alagoas", "uf_amapa", "uf_amazonas", "uf_bahia", "uf_ceara",
        "uf_espirito_santo", "uf_goias", "uf_maranhao", "uf_mato_grosso", "uf_mato_grosso_do_sul",
        "uf_minas_gerais", "uf_para", "uf_paraiba", "uf_parana", "uf_pernambuco", "uf_piaui",
        "uf_rio_de_janeiro", "uf_rio_grande_do_norte", "uf_rio_grande_do_sul",
        "uf_rondonia", "uf_roraima", "uf_santa_catarina", "uf_sao_paulo", "uf_sergipe", "uf_tocantins",
    ]},
]

CREATE_COLLAGE = True
VERTICAL_DIMENSION = 1560
CELL_HEIGHT = 300

# GCS Config
BUCKET_NAME = "mapbiomas-fire"
PROJECT_ID = "mapbiomas-fire-485203"
GCS_ROOT = "data-container"

# ============================================================
# UPLOAD STATE (persiste entre execucoes)
# ============================================================

upload_state_lock = threading.Lock()


def load_upload_state():
    """Carrega o estado de upload do disco (dict de combos ja enviados)."""
    if os.path.exists(UPLOAD_STATE_FILE):
        with open(UPLOAD_STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_upload_state(state):
    """Salva o estado de upload no disco."""
    os.makedirs(os.path.dirname(UPLOAD_STATE_FILE), exist_ok=True)
    with open(UPLOAD_STATE_FILE, "w") as f:
        json.dump(state, f)


def is_uploaded(dataset_id, product_id, territory_id):
    key = f"{dataset_id}/{product_id}/{territory_id}"
    return key in load_upload_state()


def mark_uploaded(dataset_id, product_id, territory_id):
    key = f"{dataset_id}/{product_id}/{territory_id}"
    with upload_state_lock:
        state = load_upload_state()
        state[key] = True
        save_upload_state(state)


# ============================================================
# UPLOAD + DELETE
# ============================================================

gcs_client = None
upload_count = 0
upload_count_lock = threading.Lock()


def get_gcs_client():
    global gcs_client
    if gcs_client is None:
        from google.cloud import storage
        import warnings
        warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")
        gcs_client = storage.Client(project=PROJECT_ID)
    return gcs_client


def upload_combo(dataset_id, product_id, territory_id):
    """Sobe todos os arquivos do diretorio do combo para GCS e deleta local."""
    global upload_count
    local_dir = Path(f"outputs/v001/{dataset_id}/{product_id}/{territory_id}")
    if not local_dir.exists():
        return 0

    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    count = 0

    for fpath in local_dir.iterdir():
        if fpath.is_file() and fpath.suffix.lower() in {'.gif', '.png', '.json'}:
            remote = f"{GCS_ROOT}/{dataset_id}/{product_id}/{territory_id}/{fpath.name}"
            try:
                blob = bucket.blob(remote)
                blob.upload_from_filename(str(fpath))
                count += 1
            except Exception as e:
                print(f"  [GCS ERRO] {fpath.name}: {e}")

    if count > 0:
        # Salva metadata no cache antes de deletar (para uso offline do CSV builder)
        for f in local_dir.glob("metadata_*.json"):
            cache_dir = Path(f"outputs/v001/.metadata_cache/{dataset_id}/{product_id}")
            cache_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(f), str(cache_dir / f"{territory_id}_{f.name}"))
        shutil.rmtree(str(local_dir), ignore_errors=True)
        mark_uploaded(dataset_id, product_id, territory_id)
        with upload_count_lock:
            upload_count += 1

    return count


def run_looker_csvs():
    """Atualiza CSVs do Looker Studio a partir dos metadata JSON locais."""
    print("\n--- Atualizando CSVs Looker Studio ---")
    import subprocess
    script = os.path.join(os.path.dirname(__file__), 'build_looker_csvs.py')
    env = os.environ.copy()
    env['GIF_FACTORY_DS_ID'] = DATASET_ID
    try:
        subprocess.run([sys.executable, script], env=env, check=True, timeout=300)
        print("  CSVs atualizados.")
    except subprocess.TimeoutExpired:
        print("  [AVISO] CSV timeout (5min) — execute build_looker_csvs.py manualmente.")
    except Exception as e:
        print(f"  [AVISO] CSV falhou: {e}")


# ============================================================
# PIPELINE
# ============================================================

print_lock = threading.Lock()
results_lock = threading.Lock()
results_list = []


def detect_workers():
    cores = os.cpu_count() or 4
    return max(1, min(cores - 1, 12))


def process_one(config, territory, prod, resume, skip_upload):
    if not skip_upload and is_uploaded(DATASET_ID, prod, territory):
        with print_lock:
            print(f"  [PULA] {prod} / {territory} (ja no GCS)")
        return {"status": "skipped", "product": prod, "territory": territory}

    from src.mapbiomas_data.core.pipeline import Pipeline

    pipeline = Pipeline(config)

    with print_lock:
        print(f"\n[INICIANDO] {prod} / {territory}")

    result = pipeline.run(
        dataset_id=DATASET_ID,
        product_id=prod,
        territory_id=territory,
        create_collage=CREATE_COLLAGE,
        add_labels=True,
        vertical_dimension=VERTICAL_DIMENSION,
        cell_height=CELL_HEIGHT,
        resume=resume,
    )

    with print_lock:
        if result["status"] == "success":
            print(f"  [OK] {prod} / {territory}")
            if not skip_upload:
                files = upload_combo(DATASET_ID, prod, territory)
                print(f"  [GCS] {files} arquivos enviados, diretorio local removido")
        else:
            err = result.get("error", "")
            print(f"  [FALHA] {prod} / {territory}: {err}")

    with results_lock:
        results_list.append(result)

    return result


def run_stage(stage_name, territories, config, workers, resume, skip_upload):
    print(f"\n{'=' * 60}")
    print(f"ESTAGIO: {stage_name}")
    print(f"  Territorios: {len(territories)} | Produtos: {len(PRODUCTS)}")
    total = len(territories) * len(PRODUCTS)
    print(f"  Total: {total} combos")
    print(f"{'=' * 60}\n")

    global results_list
    stage_results = []
    combos = [(t, p) for t in territories for p in PRODUCTS]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_one, config, t, p, resume, skip_upload): (t, p)
            for t, p in combos
        }
        for i, f in enumerate(as_completed(futures), 1):
            t, p = futures[f]
            r = f.result()
            stage_results.append(r)
            if i % 10 == 0 or i == len(combos):
                ok = sum(1 for r in stage_results if r["status"] == "success")
                fail = sum(1 for r in stage_results if r["status"] == "error")
                skipped = sum(1 for r in stage_results if r.get("status") == "skipped")
                print(f"  --- Progresso: {i}/{len(combos)} ({ok} OK, {fail} Falha, {skipped} Skip) ---")

    ok = sum(1 for r in stage_results if r["status"] == "success")
    fail = sum(1 for r in stage_results if r["status"] == "error")
    skipped = sum(1 for r in stage_results if r.get("status") == "skipped")
    print(f"\n  Estagio concluido: {ok} OK / {fail} Falha / {skipped} Skip / {len(combos)} Total")

    if ok > 0 and not skip_upload:
        run_looker_csvs()

    return stage_results


def main():
    from src.mapbiomas_data.config import ConfigLoader

    parser = argparse.ArgumentParser(description="Fire Col5 Export Pipeline — 5 estagios + GCS")
    parser.add_argument("--workers", type=int, default=None, help="Workers (padrao: auto-detect)")
    parser.add_argument("--resume", action="store_true", help="Retomar de onde parou")
    parser.add_argument("--stage", type=str, default="1-5", help="Estagios (ex: 1, 1-3, 5)")
    parser.add_argument("--skip-upload", action="store_true", help="Nao subir para GCS")
    parser.add_argument("--skip-csv", action="store_true", help="Nao gerar CSVs Looker")
    args = parser.parse_args()

    workers = args.workers or detect_workers()
    resume = args.resume
    skip_upload = args.skip_upload

    # Parse stage range
    stage_range = args.stage.split("-")
    start_stage = int(stage_range[0])
    end_stage = int(stage_range[-1]) if len(stage_range) > 1 else start_stage

    stages_to_run = STAGES[start_stage - 1:end_stage]
    total_combos = sum(len(s["territories"]) * len(PRODUCTS) for s in stages_to_run)

    config = ConfigLoader()

    # Mostra quantos combos ja estao no GCS
    state = load_upload_state()
    already = sum(1 for k in state if k.startswith(DATASET_ID))
    print(f"\n{'=' * 60}")
    print(f"FABRICA DE GIFS — FIRE COL5 EXPORT")
    print(f"{'=' * 60}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Produtos: {len(PRODUCTS)}")
    print(f"Ja no GCS: {already} combos")
    print(f"Estagios: {args.stage} ({len(stages_to_run)} estagios)")
    for s in stages_to_run:
        print(f"  - {s['name']}: {len(s['territories'])} terr. x {len(PRODUCTS)} prod. = {len(s['territories']) * len(PRODUCTS)} combos")
    print(f"Total: {total_combos} combos")
    print(f"Workers: {workers} | Resume: {resume}")
    print(f"Upload GCS: {'Sim' if not skip_upload else 'Nao'}")
    print(f"Colab: {'Sim' if IN_COLAB else 'Nao'}")
    print(f"{'=' * 60}\n")

    all_results = []
    for s in stages_to_run:
        results = run_stage(s["name"], s["territories"], config, workers, resume, skip_upload)
        all_results.extend(results)

    total_ok = sum(1 for r in all_results if r["status"] == "success")
    total_fail = sum(1 for r in all_results if r["status"] == "error")
    total_skip = sum(1 for r in all_results if r.get("status") == "skipped")

    print(f"\n{'=' * 60}")
    print(f"RESUMO FINAL")
    print(f"{'=' * 60}")
    print(f"Total: {total_combos} | OK: {total_ok} | Falha: {total_fail} | Skip: {total_skip}")
    print(f"Uploads: {upload_count} combos enviados ao GCS")
    print(f"Ja no GCS: {already}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
