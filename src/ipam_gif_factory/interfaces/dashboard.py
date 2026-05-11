import json
import os
import unicodedata
import sys
import time
import base64
import urllib.request
import warnings
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore", message="Your application has authenticated using end user credentials")

try:
    import streamlit as st
except ImportError:
    st = None

from ipam_gif_factory.config import ConfigLoader

ROOT_DIR = Path(__file__).resolve().parents[3]
LOGO_PATH = ROOT_DIR / "references" / "logo_ipam_30_anos_fundo_transparente_log_branca.png"
MAPBIOMAS_LOGO_PATH = ROOT_DIR / "references" / "logomapbiomas.png"
MAX_TERRITORIES = 50

GCS_BUCKET = "mapbiomas-fire"
GCS_HUB_ROOT = "gif-factory"
GCS_PROJECT = "mapbiomas-fire-485203"

try:
    from google.cloud import storage as gcs_storage
except ImportError:
    gcs_storage = None


def _gcs_base(config):
    gcs = config.paths.get("paths", {}).get("google_cloud_storage", {})
    bucket = gcs.get("bucket", GCS_BUCKET)
    root = gcs.get("hub_root", GCS_HUB_ROOT)
    return f"https://storage.googleapis.com/{bucket}/{root}"


def _clear_index_cache():
    for k in ["_index_entries", "_index_meta", "_index_mode"]:
        st.session_state.pop(k, None)


def _load_index(output_dir, config=None):
    state = st.session_state

    if "_index_entries" in state:
        return state["_index_entries"]

    entries = None
    meta = {}
    mode = state.get("_index_mode", "prod")
    gcs_base = _gcs_base(config) if config else None

    # 1) Try GCS client index
    if config and gcs_storage:
        gcs = config.paths.get("paths", {}).get("google_cloud_storage", {})
        bucket_name = gcs.get("bucket", GCS_BUCKET)
        hub_root = gcs.get("hub_root", GCS_HUB_ROOT)
        project_id = gcs.get("project_id", GCS_PROJECT)
        blob_path = f"{hub_root}/dev/index.json" if mode == "dev" else f"{hub_root}/index.json"
        try:
            client = gcs_storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            raw = blob.download_as_string()
            data = json.loads(raw)
            meta = data.get("_meta", {})
            entries = _index_to_entries(data["entries"], output_dir, gcs_base)
        except Exception:
            entries = None

    # 1.5) Fallback: HTTP URL to GCS index (no auth needed for public bucket)
    if entries is None and config:
        gcs = config.paths.get("paths", {}).get("google_cloud_storage", {})
        bucket_name = gcs.get("bucket", GCS_BUCKET)
        hub_root = gcs.get("hub_root", GCS_HUB_ROOT)
        blob_path = f"{hub_root}/dev/index.json" if mode == "dev" else f"{hub_root}/index.json"
        url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
                meta = data.get("_meta", {})
                entries = _index_to_entries(data["entries"], output_dir, gcs_base)
        except Exception:
            entries = None

    # 2) Fallback: local index.json
    if entries is None:
        index_path = Path(output_dir) / "index.json"
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text(encoding="utf-8"))
                meta = data.get("_meta", {})
                entries = _index_to_entries(data["entries"], output_dir)
            except Exception:
                entries = None

    # 3) Last fallback: legacy filesystem scan
    if entries is None:
        entries = _legacy_scan(output_dir)

    state["_index_entries"] = entries
    state["_index_meta"] = meta
    return entries


def _index_to_entries(index_entries, output_dir, gcs_base=None):
    result = []
    for e in index_entries:
        ds = e["dataset"]
        prod = e["product"]
        terr = e["territory"]
        meta = e.get("metadata", {})

        if gcs_base:
            gif = f"{gcs_base}/{e['gif_rel']}"
            collage = f"{gcs_base}/{e['collage_rel']}" if e.get("collage_rel") else None
            frame_names = meta.get("output", {}).get("frames", [])
            frames = [f"{gcs_base}/{ds}/{prod}/{terr}/{fname}" for fname in frame_names]
            combo_dir = f"{gcs_base}/{ds}/{prod}/{terr}"
        else:
            gif = str(Path(output_dir) / e["gif_rel"])
            collage = str(Path(output_dir) / e["collage_rel"]) if e.get("collage_rel") else None
            frame_names = meta.get("output", {}).get("frames", [])
            frames = [str(Path(output_dir) / ds / prod / terr / fname) for fname in frame_names]
            combo_dir = str(Path(gif).parent)

        result.append({
            "dataset": ds,
            "product": prod,
            "territory": terr,
            "gif": gif,
            "collage": collage,
            "frames": frames,
            "frames_count": e.get("frames_count", len(frames)),
            "product_name": e.get("product_name", prod),
            "territory_name": e.get("territory_name", terr),
            "duration_seconds": e.get("duration_seconds", 0),
            "duration_formatted": e.get("duration_formatted", ""),
            "eecu": e.get("eecu", 0),
            "gif_size_mb": e.get("gif_size_mb", 0),
            "metadata": meta,
            "dir": combo_dir,
        })
    return result


def _legacy_scan(output_dir):
    """Legacy filesystem scan when no index.json exists."""
    index = []
    base = Path(output_dir)
    if not base.exists():
        return index
    for gif_path in base.rglob("*.gif"):
        rel = gif_path.relative_to(base)
        parts = rel.parts
        if len(parts) >= 3:
            index.append({
                "dataset": parts[0],
                "product": parts[1],
                "territory": parts[2],
                "gif": str(gif_path),
                "collage": str(next(gif_path.parent.glob("*collage*.png"), None)),
                "frames": [str(f) for f in sorted(gif_path.parent.glob("*.png")) if "collage" not in f.name],
                "frames_count": 0,
                "metadata": (json.loads(Path(gif_path.parent / f"metadata_{parts[1]}.json").read_text(encoding="utf-8"))
                             if Path(gif_path.parent / f"metadata_{parts[1]}.json").exists() else {}),
                "dir": str(gif_path.parent),
            })
    return index


def _is_gcs_path(path):
    return isinstance(path, str) and path.startswith("http")


def _media_src(entry, field="gif"):
    """Return HTML src value: data URI (local) or direct URL (GCS)."""
    path = entry.get(field)
    if not path:
        return None
    if _is_gcs_path(path):
        return path
    mime = "image/gif" if field == "gif" else "image/png"
    try:
        b64 = base64.b64encode(_load_bytes(path)).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _download_media(entry, field="gif"):
    """Return raw bytes for download: local read or HTTP GET."""
    path = entry.get(field)
    if not path:
        return None
    if _is_gcs_path(path):
        try:
            with urllib.request.urlopen(path, timeout=30) as resp:
                return resp.read()
        except Exception:
            return None
    return _load_bytes(path)


def _product_label(entry):
    return entry.get("metadata", {}).get("product", {}).get("name", entry["product"])


def _territory_label(entry):
    if isinstance(entry, str):
        return entry
    return entry.get("metadata", {}).get("territory", {}).get("name", entry["territory"])


def _load_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _strip_accents(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _render_frame_grid(frames, prefix):
    if not frames:
        return

    years = []
    for fpath in frames:
        year = Path(fpath).stem.split("_")[-1]
        years.append(year)

    all_years = sorted(set(years), key=lambda y: int(y))
    years_key = f"fg_years_{prefix}"
    default = st.session_state.get(years_key, all_years)
    ysel = st.multiselect(
        "Anos para exibir", all_years,
        default=default, key=years_key)

    filtered = [(f, y) for f, y in zip(frames, years) if y in ysel]
    if not filtered:
        return

    st.markdown("---")
    ncols = min(6, len(filtered))
    for i in range(0, len(filtered), ncols):
        cols = st.columns(ncols)
        for j in range(ncols):
            idx = i + j
            if idx < len(filtered):
                fpath, year = filtered[idx]
                with cols[j]:
                    st.image(fpath, use_container_width=True)
                    st.caption(year)
                    if _is_gcs_path(fpath):
                        try:
                            with urllib.request.urlopen(fpath, timeout=30) as resp:
                                data = resp.read()
                        except Exception:
                            data = None
                    else:
                        data = _load_bytes(fpath)
                    if data is None:
                        continue
                    st.download_button(
                        f"⬇ {year}", data=data,
                        file_name=Path(fpath).name,
                        mime="image/png",
                        key=f"fg_dl_{prefix}_{int(year)}_{j}",
                        width="stretch")


def _render_card(e, label, tname, ds, files_count, duration, eecu, territories_count, key, geral_mode=False, mode="leitor", output_dir=None, config=None):
    is_hidden = not _is_visible(e["dataset"], e["product"])
    st.markdown(f'<div class="ipam-card{" ipam-card-hidden" if is_hidden else ""}">', unsafe_allow_html=True)

    src = _media_src(e, "collage") or _media_src(e, "gif")
    if src:
        st.markdown(
            f'<div class="ipam-card-image">'
            f'<img src="{src}">'
            f'{"<div class=\"ipam-card-hidden-badge\">🔒 Oculto</div>" if is_hidden else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

    display_label = label[:35] + "..." if len(label) > 35 else label
    st.markdown(f'<div class="ipam-card-title">{display_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ipam-card-territory">{tname}</div>', unsafe_allow_html=True)

    ds_short = ds.replace("brasil_", "").replace("_", " ")
    tags = "".join([
        f'<span class="ipam-card-tag tag-dataset">{ds_short}</span>',
        f'<span class="ipam-card-tag tag-territory">{territories_count} territorio(s)</span>',
        f'<span class="ipam-card-tag tag-frames">{files_count} frames</span>',
        f'<span class="ipam-card-tag tag-duration">{duration}</span>',
        f'<span class="ipam-card-tag tag-eecu">{eecu:.2f} EECU</span>',
    ])
    st.markdown(f'<div class="ipam-card-tags">{tags}</div>', unsafe_allow_html=True)

    btn_cols = st.columns(2)
    with btn_cols[0]:
        if st.button("Ver", key=f"ver_{key}", use_container_width=True):
            if geral_mode:
                st.session_state["geral_view"] = {"active": True, "key": (e["dataset"], e["product"], e["territory"])}
            else:
                st.session_state["selected_product"] = (e["dataset"], e["product"])
            st.rerun()

    if _can(mode, "toggle_visibility"):
        with btn_cols[1]:
            vis = _is_visible(e["dataset"], e["product"])
            vlabel = "🔓 Público" if vis else "🔒 Oculto"
            if st.button(vlabel, key=f"v_{key}", use_container_width=True):
                _toggle_visible(e["dataset"], e["product"])
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_detail(index, product_key, config, geral_mode=False, mode="leitor", output_dir=None):
    ds, prod = product_key
    entries = [e for e in index if e["dataset"] == ds and e["product"] == prod]
    if not entries:
        st.info("Produto nao encontrado nos resultados.")
        if geral_mode:
            st.session_state["geral_view"] = {"active": False}
        else:
            st.session_state["selected_product"] = None
        st.rerun()
        return

    from ipam_gif_factory.core import TerritoryManager
    tm = TerritoryManager(config)

    label = _product_label(entries[0])
    ds_short = ds.replace("brasil_", "").replace("_", " ") 

    if st.button("\u2190 Voltar" if geral_mode else "\u2190 Voltar ao catalogo", use_container_width=False):
        if geral_mode:
            st.session_state["geral_view"] = {"active": False}
        else:
            st.session_state["selected_product"] = None
        st.rerun()

    st.markdown('<div class="report-container">', unsafe_allow_html=True)

    st.markdown(f'<h1 class="report-title">{label}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="report-subtitle">{ds_short}</div>', unsafe_allow_html=True)

    # Territory type + territory filters
    terr_info = {}
    for e in entries:
        tid = e["territory"]
        try:
            info = tm.get_territory(tid)
            terr_info[tid] = info
        except KeyError:
            terr_info[tid] = {"name": tid, "type": "unknown"}

    all_types = sorted(set(v["type"] for v in terr_info.values()))
    type_labels = {"countries": "Paises", "biomes": "Biomas",
                   "states": "Estados", "custom_regions": "Regioes",
                   "unknown": "Desconhecido"}

    sel_types = st.multiselect(
        "Tipo de territorio", all_types,
        default=["custom_regions"],
        format_func=lambda t: type_labels.get(t, t),
        key="sel_types")

    type_filtered = [e for e in entries
                     if terr_info.get(e["territory"], {}).get("type") in sel_types]

    if len(type_filtered) > MAX_TERRITORIES:
        st.warning(
            f"Mais de {MAX_TERRITORIES} territorios disponiveis. "
            "Selecione um tipo mais especifico para limitar.")

    terr_options = sorted(
        type_filtered, key=lambda e: _territory_label(e))
    default_terr = [e for e in terr_options if e["territory"] == "matopiba_cerrado"]
    sel_territories = st.multiselect(
        "Territorios", terr_options,
        default=default_terr,
        format_func=lambda e: f"{_territory_label(e)} ({type_labels.get(terr_info.get(e['territory'], {}).get('type', ''), '')})",
        key=f"det_terr_{ds}_{prod}")

    terr_search = st.text_input("Buscar territorio", "", key=f"det_search_{ds}_{prod}")
    if terr_search:
        sl = terr_search.lower()
        sel_territories = [e for e in sel_territories
                           if sl in _territory_label(e).lower() or sl in e["territory"].lower()]

    # Visibility toggles
    vcol1, vcol2, vcol3, vcol4 = st.columns(4)
    with vcol1:
        show_gif = st.checkbox("Mostrar GIF", value=True,
                               key=f"det_showgif_{ds}_{prod}")
    with vcol2:
        show_grid = st.checkbox("Mostrar Grid", value=True,
                                key=f"det_showgrid_{ds}_{prod}")
    with vcol3:
        show_frames = st.checkbox("Mostrar Frames", value=False,
                                  key=f"det_showframes_{ds}_{prod}")
    with vcol4:
        show_kpis = st.checkbox("Mostrar metricas", value=True,
                                key=f"det_showkpis_{ds}_{prod}")

    entries = sel_territories

    total_frames = sum(e.get("metadata", {}).get("files", {}).get("frames_count", 0) for e in entries)
    total_sec = sum(e.get("metadata", {}).get("timing", {}).get("total_seconds", 0) for e in entries)
    total_eecu = sum(e.get("metadata", {}).get("ee_estimate", {}).get("estimated_eecu", 0) for e in entries)
    dur_str = f"{total_sec/60:.1f}min" if total_sec > 60 else f"{total_sec:.0f}s"

    if show_kpis:
        sk1, sk2, sk3, sk4 = st.columns(4)
        with sk1: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{len(entries)}</div><div class="kpi-label">TERRITORIOS</div></div>', unsafe_allow_html=True)
        with sk2: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{total_frames}</div><div class="kpi-label">FRAMES TOTAIS</div></div>', unsafe_allow_html=True)
        with sk3: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{dur_str}</div><div class="kpi-label">TEMPO DE PROCESSAMENTO</div></div>', unsafe_allow_html=True)
        with sk4: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{total_eecu:.2f}</div><div class="kpi-label">EECU TOTAL</div></div>', unsafe_allow_html=True)

    for e in sorted(entries, key=lambda x: _territory_label(x)):
        meta = e.get("metadata", {})
        tname = _territory_label(e)
        tid = e["territory"]
        timing = meta.get("timing", {})
        files = meta.get("files", {})
        ee_est = meta.get("ee_estimate", {})

        st.markdown(f'<div class="report-section-title">{tname}</div>', unsafe_allow_html=True)
        st.markdown('<div class="report-section-line"></div>', unsafe_allow_html=True)

        if show_kpis:
            tk1, tk2, tk3, tk4 = st.columns(4)
            with tk1: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{files.get("frames_count", "?")}</div><div class="kpi-label">FRAMES</div></div>', unsafe_allow_html=True)
            with tk2: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{timing.get("total_formatted", "")}</div><div class="kpi-label">TEMPO DE PROCESSAMENTO</div></div>', unsafe_allow_html=True)
            with tk3: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{ee_est.get("estimated_eecu", 0):.2f}</div><div class="kpi-label">EECU</div></div>', unsafe_allow_html=True)
            with tk4:
                gm = files.get("gif_size_mb", 0)
                st.markdown(f'<div class="kpi-box"><div class="kpi-value">{gm:.1f}</div><div class="kpi-label">MB (GIF)</div></div>', unsafe_allow_html=True)

        if show_gif and show_grid:
            col_gif, col_grid = st.columns(2)
        elif show_gif:
            col_gif = st.columns(1)[0]
        elif show_grid:
            col_grid = st.columns(1)[0]

        if show_gif:
            with col_gif:
                gif_src = _media_src(e, "gif")
                if gif_src:
                    st.markdown(f'<div class="visual-container"><img src="{gif_src}"></div>', unsafe_allow_html=True)
                    data = _download_media(e, "gif")
                    if data:
                        st.download_button("\u2b07 Download GIF", data=data, file_name="output.gif", mime="image/gif", width="stretch", key=f"dlg_{ds}_{prod}_{tid}")

        if show_grid:
            with col_grid:
                coll_src = _media_src(e, "collage")
                if coll_src:
                    st.markdown(f'<div class="visual-container"><img src="{coll_src}"></div>', unsafe_allow_html=True)
                    data = _download_media(e, "collage")
                    if data:
                        st.download_button("\u2b07 Download Grid", data=data, file_name="collage.png", mime="image/png", width="stretch", key=f"dlc_{ds}_{prod}_{tid}")

        if show_frames:
            frames = e.get("frames", [])
            if frames:
                st.markdown("---")
                _render_frame_grid(frames, f"det_{ds}_{prod}_{tid}")

        with st.expander("Ver metadados", expanded=False):
            st.json(meta)

    st.markdown("</div>", unsafe_allow_html=True)

def _render_combo_detail(index, ds, prod, terr):
    entries = [e for e in index if e["dataset"] == ds and e["product"] == prod and e["territory"] == terr]
    if not entries:
        st.info("Combo nao encontrado.")
        return
    e = entries[0]
    meta = e.get("metadata", {})
    tname = _territory_label(e)
    pname = _product_label(e)

    st.button("\u2190 Voltar", on_click=lambda: st.session_state.__setitem__("geral_view", {"active": False}))
    st.markdown(f'<div class="report-container">', unsafe_allow_html=True)
    st.markdown(f'<h1 class="report-title">{pname}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="report-subtitle">{tname}</div>', unsafe_allow_html=True)

    show_kpis = st.checkbox("Mostrar metricas", value=True, key=f"combo_showkpis_{ds}_{prod}_{terr}")

    timing = meta.get("timing", {})
    files = meta.get("files", {})
    ee_est = meta.get("ee_estimate", {})
    if show_kpis:
        tk1, tk2, tk3, tk4 = st.columns(4)
        with tk1: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{files.get("frames_count", "?")}</div><div class="kpi-label">FRAMES</div></div>', unsafe_allow_html=True)
        with tk2: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{timing.get("total_formatted", "")}</div><div class="kpi-label">TEMPO DE PROCESSAMENTO</div></div>', unsafe_allow_html=True)
        with tk3: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{ee_est.get("estimated_eecu", 0):.2f}</div><div class="kpi-label">EECU</div></div>', unsafe_allow_html=True)
        with tk4: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{files.get("gif_size_mb", 0):.1f}</div><div class="kpi-label">MB (GIF)</div></div>', unsafe_allow_html=True)

    gif_src = _media_src(e, "gif")
    coll_src = _media_src(e, "collage")
    if gif_src:
        st.markdown(f'<div class="visual-container"><img src="{gif_src}"></div>', unsafe_allow_html=True)
        data = _download_media(e, "gif")
        if data:
            st.download_button("\u2b07 Download GIF", data=data, file_name="output.gif", mime="image/gif", width="stretch", key=f"dlg_combo_{ds}_{prod}_{terr}")
    if coll_src:
        st.markdown(f'<div class="visual-container"><img src="{coll_src}"></div>', unsafe_allow_html=True)
        data = _download_media(e, "collage")
        if data:
            st.download_button("\u2b07 Download Grid", data=data, file_name="collage.png", mime="image/png", width="stretch", key=f"dlc_combo_{ds}_{prod}_{terr}")
    frames = e.get("frames", [])
    if frames:
        st.markdown("---")
        _render_frame_grid(frames, f"combo_{ds}_{prod}_{terr}")
    with st.expander("Metadados", expanded=False):
        st.json(meta)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_geral(output_dir, config):
    mode = _user_mode(config)
    index = _load_index(output_dir, config)
    state = st.session_state

    geral_view = state.get("geral_view")
    if geral_view and geral_view.get("active"):
        _render_combo_detail(index, *geral_view["key"])
        return

    from ipam_gif_factory.core import TerritoryManager
    tm = TerritoryManager(config)

    terr_info = {}
    for e in index:
        tid = e["territory"]
        if tid not in terr_info:
            try:
                info = tm.get_territory(tid)
                terr_info[tid] = info
            except KeyError:
                terr_info[tid] = {"name": tid, "type": "unknown"}

    all_types = sorted(set(v["type"] for v in terr_info.values()))
    type_labels = {"countries": "Países", "biomes": "Biomas",
                   "states": "Estados", "custom_regions": "Regiões",
                   "unknown": "Desconhecido"}

    col_panels = st.columns(2)
    with col_panels[0]:
        datasets = sorted(set(e["dataset"] for e in index))
        default_ds = [d for d in datasets if "degradation" in d]
        sel_datasets = st.multiselect("Coleções", datasets, default=default_ds, key="geral_sel_datasets")

        sel_prod_pairs = set()
        for ds in sel_datasets:
            ds_products = sorted(set(
                (e["product"], _product_label(e)) for e in index if e["dataset"] == ds
            ))
            prod_keys = {pl: (ds, pid) for pid, pl in ds_products}
            selected = st.multiselect(
                ds.replace("brasil_", "").replace("_", " "),
                list(prod_keys.keys()),
                default=list(prod_keys.keys()),
                key=f"geral_prod_{ds}",
            )
            for k in selected:
                sel_prod_pairs.add(prod_keys[k])

    with col_panels[1]:
        sel_types = st.multiselect("Tipo", all_types, default=["custom_regions"],
                                   format_func=lambda t: type_labels.get(t, t), key="geral_sel_types")

        sel_territories = set()
        for t in sel_types:
            tids = sorted(tid for tid in terr_info if terr_info[tid]["type"] == t)
            selected = st.multiselect(
                type_labels.get(t, t),
                tids,
                default=tids if t != "custom_regions" else ["matopiba_cerrado"],
                format_func=lambda x, t=t: {
                    "biomas": "Todos os Biomas (seis biomas)",
                }.get(x, _territory_label(next((e for e in index if e["territory"] == x), x))),
                key=f"geral_terr_{t}",
            )
            sel_territories.update(selected)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search = st.text_input("Buscar", "", key="geral_search")
    with col_s2:
        vis_filter = st.selectbox("Visibilidade", ["Todos", "Público", "Oculto"], key="geral_vis_filter")

    def _match(e):
        if e["dataset"] not in sel_datasets:
            return False
        if (e["dataset"], e["product"]) not in sel_prod_pairs:
            return False
        if e["territory"] not in sel_territories:
            return False
        if search:
            sl = search.lower()
            if sl not in _product_label(e).lower() and sl not in e["dataset"].lower() and sl not in _territory_label(e).lower():
                return False
        if vis_filter == "Público":
            if not _is_visible(e["dataset"], e["product"]):
                return False
        elif vis_filter == "Oculto":
            if _is_visible(e["dataset"], e["product"]):
                return False
        return True

    filtered = [e for e in index if _match(e)]

    if not filtered:
        st.info("Nenhum item encontrado com esses filtros.")
        return

    by_dataset = {}
    for e in filtered:
        by_dataset.setdefault(e["dataset"], []).append(e)

    all_datasets = sorted(by_dataset.keys())
    total_items = len(filtered)
    ITEMS_PER_PAGE = 16
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = state.get("geral_page", 1)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    st.markdown(f"### Geral ({total_items})")

    if total_pages > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.button("◀ Anterior", key="geral_prev", disabled=(page <= 1),
                      on_click=lambda: state.__setitem__("geral_page", page - 1))
        with c2:
            st.markdown(f"<div style='text-align:center;padding-top:6px;'>Página {page} de {total_pages}</div>", unsafe_allow_html=True)
        with c3:
            st.button("Próximo ▶", key="geral_next", disabled=(page >= total_pages),
                      on_click=lambda: state.__setitem__("geral_page", page + 1))

    rendered = 0
    for ds in all_datasets:
        entries = by_dataset[ds]
        count = len(entries)
        if rendered + count <= start:
            rendered += count
            continue
        if rendered >= end:
            break

        ds_short = ds.replace("brasil_", "").replace("_", " ")
        st.markdown(f"#### {ds_short}")

        group_start = max(0, start - rendered)
        group_end = min(count, end - rendered)
        visible = entries[group_start:group_end]

        for i in range(0, len(visible), 4):
            cols = st.columns(4)
            for j in range(4):
                idx = i + j
                if idx < len(visible):
                    e = visible[idx]
                    meta = e.get("metadata", {})
                    timing = meta.get("timing", {})
                    files = meta.get("files", {})
                    ee_est = meta.get("ee_estimate", {})
                    _render_card(
                        e, _product_label(e), _territory_label(e), e["dataset"],
                        files.get("frames_count", "?"),
                        timing.get("total_formatted", ""),
                        ee_est.get("estimated_eecu", 0),
                        1,
                        key=f"geral_{e['dataset']}_{e['product']}_{e['territory']}",
                        geral_mode=True, mode=mode, output_dir=output_dir, config=config)

        rendered += count


def _render_catalog_product(output_dir, config):
    mode = _user_mode(config)
    index = _load_index(output_dir, config)
    if not index:
        st.info("Nenhum GIF encontrado.")
        return

    selected = st.session_state.get("selected_product")
    if selected:
        _render_detail(index, selected, config, mode=mode, output_dir=output_dir)
        return

    datasets = sorted(set(e["dataset"] for e in index))
    sel_datasets = st.multiselect("Coleções", datasets, default=datasets, key="prod_sel_datasets")
    sel_prod_pairs = set()
    for ds in sel_datasets:
        ds_products = sorted(set(
            (e["product"], _product_label(e)) for e in index if e["dataset"] == ds
        ))
        prod_keys = {pl: (ds, pid) for pid, pl in ds_products}
        selected = st.multiselect(
            ds.replace("brasil_", "").replace("_", " "),
            list(prod_keys.keys()),
            default=list(prod_keys.keys()),
            key=f"prod_prod_{ds}",
        )
        for k in selected:
            sel_prod_pairs.add(prod_keys[k])

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search = st.text_input("Buscar", "", key="prod_search")
    with col_s2:
        vis_filter = st.selectbox("Visibilidade", ["Todos", "Público", "Oculto"], key="prod_vis_filter")

    by_product = {}
    for e in index:
        by_product.setdefault((e["dataset"], e["product"]), []).append(e)

    cards = []
    for pk in sorted(by_product):
        ds, pid = pk
        if ds not in sel_datasets:
            continue
        if (ds, pid) not in sel_prod_pairs:
            continue
        entries = by_product[pk]
        label = _product_label(entries[0])
        if search:
            sl = search.lower()
            if sl not in label.lower() and sl not in pid.lower() and sl not in ds.lower():
                continue
        if vis_filter == "Público":
            if not _is_visible(ds, pid):
                continue
        elif vis_filter == "Oculto":
            if _is_visible(ds, pid):
                continue
        terrs = sorted(set(e["territory"] for e in entries), key=_territory_label)
        meta = entries[0].get("metadata", {})
        timing = meta.get("timing", {})
        files = meta.get("files", {})
        ee_est = meta.get("ee_estimate", {})
        cards.append((label, ds, pid, entries, terrs, timing, files, ee_est))

    if not cards:
        st.info("Nenhum produto encontrado com esses filtros.")
        return

    st.markdown(f"### Produtos ({len(cards)})")

    for i in range(0, len(cards), 4):
        cols = st.columns(4)
        for j in range(4):
            idx = i + j
            if idx < len(cards):
                label, ds, pid, entries, terrs, timing, files, ee_est = cards[idx]
                with cols[j]:
                    e = entries[0]
                    tname = f"{len(terrs)} territorios"
                    total_frames = sum(ent.get("metadata", {}).get("files", {}).get("frames_count", 0) for ent in entries)
                    total_sec = sum(ent.get("metadata", {}).get("timing", {}).get("total_seconds", 0) for ent in entries)
                    total_eecu = sum(ent.get("metadata", {}).get("ee_estimate", {}).get("estimated_eecu", 0) for ent in entries)
                    dur_str = f"{total_sec/60:.1f}min" if total_sec > 60 else f"{total_sec:.0f}s"
                    _render_card(
                        e, label, tname, ds,
                        total_frames,
                        dur_str,
                        total_eecu,
                        len(terrs),
                        key=f"prod_{ds}_{pid}")


def _territory_thumbnail_html(territory_id, config, output_dir):
    key = f"_terr_thumb_{territory_id}"
    cached = st.session_state.get(key)
    if cached:
        return cached

    thumb_dir = Path(output_dir) / "territories"
    thumb_path = thumb_dir / f"{territory_id}.png"

    if thumb_path.exists():
        b64 = base64.b64encode(_load_bytes(str(thumb_path))).decode()
        html = f'<img src="data:image/png;base64,{b64}" style="width:100%;border-radius:8px;">'
        st.session_state[key] = html
        return html

    try:
        import ee
        import math
        import urllib.request
        from io import BytesIO
        from PIL import Image, ImageDraw, ImageFont
        from ipam_gif_factory.core import TerritoryManager

        tm = TerritoryManager(config)
        terr_info = tm.get_territory(territory_id)
        fc = tm.get_feature_collection(territory_id)
        bbox = tm.get_bbox(territory_id)
        if fc is None:
            return None

        tname = terr_info.get("name", territory_id)
        terr_type = terr_info.get("type", "")
        type_labels = {"countries": "Pais", "biomes": "Bioma", "states": "Estado", "custom_regions": "Regiao"}
        type_label = type_labels.get(terr_type, terr_type)

        blank = ee.Image(0).byte()
        outline = blank.paint(fc, 1, 2)

        bnds = fc.geometry().bounds().getInfo()["coordinates"][0]
        xs = [c[0] for c in bnds]; ys = [c[1] for c in bnds]
        bx = [min(xs), min(ys), max(xs), max(ys)]
        pad_x = max((bx[2] - bx[0]) * 0.1, 0.5)
        pad_y = max((bx[3] - bx[1]) * 0.1, 0.5)
        region = [bx[0] - pad_x, bx[1] - pad_y, bx[2] + pad_x, bx[3] + pad_y]
        bbox = bx

        url = outline.getThumbURL({
            "min": 0, "max": 1,
            "palette": ["f9f9f7", "006b3f"],
            "dimensions": 440,
            "region": region,
        })

        with urllib.request.urlopen(url, timeout=30) as resp:
            ee_data = resp.read()

        ee_img = Image.open(BytesIO(ee_data))
        title_h = 44
        scale_h = 32
        total_h = ee_img.height + title_h + scale_h
        new_img = Image.new("RGB", (ee_img.width, total_h), "#f9f9f7")
        new_img.paste(ee_img, (0, title_h))
        draw = ImageDraw.Draw(new_img)

        font_title = font_sub = font_scale = ImageFont.load_default()
        has_title = False
        for fp in ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"]:
            try:
                if "arialbd" in fp:
                    font_title = ImageFont.truetype(fp, 16)
                    has_title = True
                else:
                    if not has_title:
                        font_title = ImageFont.truetype(fp, 14)
                    font_sub = ImageFont.truetype(fp, 10)
                    font_scale = ImageFont.truetype(fp, 11)
            except OSError:
                continue

        draw.text((12, 5), tname, fill="#006b3f", font=font_title)
        draw.text((12, 27), type_label, fill="#8a8780", font=font_sub)

        if bbox:
            mid_lat = (bbox[1] + bbox[3]) / 2
            kmpd = 111.0 * math.cos(math.radians(mid_lat))
            deg_w = bbox[2] - bbox[0]
            km_w = deg_w * kmpd
            raw = km_w / 3
            mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
            scale_km = round(raw / mag) * mag if raw > 0 else 100
            scale_px = min(int(scale_km / km_w * ee_img.width), ee_img.width - 20)
            y = total_h - 16
            draw.rectangle([(12, y), (12 + scale_px, y + 3)], fill="#353935")
            draw.rectangle([(12, y - 4), (12, y + 3)], fill="#353935")
            draw.rectangle([(12 + scale_px, y - 4), (12 + scale_px, y + 3)], fill="#353935")
            draw.text((12, y - 15), f"{scale_km} km", fill="#353935", font=font_scale)

        thumb_dir.mkdir(parents=True, exist_ok=True)
        new_img.save(str(thumb_path), format="PNG")

        b64 = base64.b64encode(_load_bytes(str(thumb_path))).decode()
        html = f'<img src="data:image/png;base64,{b64}" style="width:100%;border-radius:8px;">'
        st.session_state[key] = html
        return html
    except Exception:
        return None


def _render_catalog_territory(output_dir, config):
    index = _load_index(output_dir, config)
    if not index:
        st.info("Nenhum GIF encontrado.")
        return

    selected_territory = st.session_state.get("selected_territory")
    if selected_territory:
        _render_territory_detail(index, selected_territory)
        return

    from ipam_gif_factory.core import TerritoryManager
    tm = TerritoryManager(config)

    by_territory = {}
    terr_info = {}
    for e in index:
        by_territory.setdefault(e["territory"], []).append(e)
        if e["territory"] not in terr_info:
            try:
                info = tm.get_territory(e["territory"])
                terr_info[e["territory"]] = info
            except KeyError:
                terr_info[e["territory"]] = {"name": e["territory"], "type": "unknown"}

    all_types = sorted(set(v["type"] for v in terr_info.values()))
    type_labels = {"countries": "Países", "biomes": "Biomas",
                   "states": "Estados", "custom_regions": "Regiões",
                   "unknown": "Desconhecido"}

    sel_types = st.multiselect("Tipo", all_types, default=["custom_regions"],
                               format_func=lambda t: type_labels.get(t, t), key="terr_sel_types")
    sel_territories = set()
    for t in sel_types:
        tids = sorted(tid for tid in terr_info if terr_info[tid]["type"] == t)
        def_terr = ["matopiba_cerrado"] if t == "custom_regions" else tids[:1]
        selected = st.multiselect(
            type_labels.get(t, t),
            tids,
            default=def_terr,
            format_func=lambda x, t=t: {
                "biomas": "Todos os Biomas (seis biomas)",
            }.get(x, _territory_label(next((e for e in index if e["territory"] == x), x))),
            key=f"terr_terr_{t}",
        )
        sel_territories.update(selected)

    search = st.text_input("Buscar territorio", "", key="terr_search")
    sl = search.lower() if search else ""

    ter_ids = []
    for tid in sorted(by_territory.keys()):
        if tid not in sel_territories:
            continue
        tname = _territory_label(next(e for e in index if e["territory"] == tid))
        if search and sl not in tname.lower() and sl not in tid.lower():
            continue
        ter_ids.append(tid)

    if not ter_ids:
        st.info("Nenhum território encontrado com esses filtros.")
        return

    for i in range(0, len(ter_ids), 4):
        cols = st.columns(4)
        for j in range(4):
            idx = i + j
            if idx < len(ter_ids):
                tid = ter_ids[idx]
                entries = by_territory[tid]
                tname = _territory_label(next(e for e in index if e["territory"] == tid))
                datasets = sorted(set(e["dataset"] for e in entries))
                total = len(entries)
                with cols[j]:
                    thumb = _territory_thumbnail_html(tid, config, output_dir)
                    if thumb:
                        st.markdown(thumb, unsafe_allow_html=True)
                    st.markdown(f"**{tname}**")
                    ds_labels = [d.replace("brasil_", "").replace("_", " ") for d in datasets]
                    st.caption(f"{total} produtos  |  {', '.join(ds_labels)}")
                    if st.button("Abrir", key=f"ter_card_{tid}", width="stretch"):
                        st.session_state["selected_territory"] = tid
                        st.rerun()


def _render_territory_detail(index, territory_id, geral_mode=False):
    entries = [e for e in index if e["territory"] == territory_id]
    tname = _territory_label(entries[0])

    if st.button("<- Voltar" if geral_mode else "<- Voltar para territorios", use_container_width=False):
        if geral_mode:
            st.session_state["geral_view"] = {"active": False}
        else:
            st.session_state["selected_territory"] = None
        st.rerun()

    st.markdown(f"## {tname}")
    st.markdown(f"{len(entries)} produtos disponiveis")

    # Visibility toggles
    vcol1, vcol2, vcol3, vcol4 = st.columns(4)
    with vcol1:
        show_gif = st.checkbox("Mostrar GIF", value=True,
                               key=f"ter_showgif_{territory_id}")
    with vcol2:
        show_grid = st.checkbox("Mostrar Grid", value=True,
                                key=f"ter_showgrid_{territory_id}")
    with vcol3:
        show_frames = st.checkbox("Mostrar Frames", value=False,
                                  key=f"ter_showframes_{territory_id}")
    with vcol4:
        show_kpis = st.checkbox("Mostrar metricas", value=True,
                                key=f"ter_showkpis_{territory_id}")

    # Collections panel
    datasets = sorted(set(e["dataset"] for e in entries))
    sel_datasets = st.multiselect("Coleções", datasets, default=datasets, key=f"td_sel_datasets_{territory_id}")
    sel_prod_pairs = set()
    for ds in sel_datasets:
        ds_products = sorted(set(
            (e["product"], _product_label(e)) for e in entries if e["dataset"] == ds
        ))
        prod_keys = {pl: (ds, pid) for pid, pl in ds_products}
        selected = st.multiselect(
            ds.replace("brasil_", "").replace("_", " "),
            list(prod_keys.keys()),
            default=list(prod_keys.keys()),
            key=f"td_prod_{territory_id}_{ds}",
        )
        for k in selected:
            sel_prod_pairs.add(prod_keys[k])

    prod_search = st.text_input("Buscar produto", "", key=f"td_search_{territory_id}")

    selected_entries = []
    for e in entries:
        if e["dataset"] not in sel_datasets:
            continue
        if (e["dataset"], e["product"]) not in sel_prod_pairs:
            continue
        if prod_search:
            sl = _strip_accents(prod_search.lower())
            label = _strip_accents(_product_label(e).lower())
            if sl not in label and sl not in _strip_accents(e["product"].lower()) and sl not in _strip_accents(e["dataset"].lower()):
                continue
        selected_entries.append(e)

    if not selected_entries:
        st.info("Nenhum produto encontrado com esses filtros.")
        st.stop()

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        if st.button("Expandir todas", key=f"td_expand_all_{territory_id}"):
            for e in selected_entries:
                st.session_state[f"td_exp_{territory_id}_{e['dataset']}_{e['product']}"] = True
            st.rerun()
    with col_exp2:
        if st.button("Recolher todas", key=f"td_collapse_all_{territory_id}"):
            for e in selected_entries:
                st.session_state[f"td_exp_{territory_id}_{e['dataset']}_{e['product']}"] = False
            st.rerun()

    if show_kpis:
        total_frames = sum(e.get("metadata", {}).get("files", {}).get("frames_count", 0) for e in selected_entries)
        total_sec = sum(e.get("metadata", {}).get("timing", {}).get("total_seconds", 0) for e in selected_entries)
        total_eecu = sum(e.get("metadata", {}).get("ee_estimate", {}).get("estimated_eecu", 0) for e in selected_entries)
        dur_str = f"{total_sec/60:.1f}min" if total_sec > 60 else f"{total_sec:.0f}s"
        sk1, sk2, sk3, sk4 = st.columns(4)
        with sk1: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{len(selected_entries)}</div><div class="kpi-label">PRODUTOS</div></div>', unsafe_allow_html=True)
        with sk2: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{total_frames}</div><div class="kpi-label">FRAMES TOTAIS</div></div>', unsafe_allow_html=True)
        with sk3: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{dur_str}</div><div class="kpi-label">TEMPO DE PROCESSAMENTO</div></div>', unsafe_allow_html=True)
        with sk4: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{total_eecu:.2f}</div><div class="kpi-label">EECU TOTAL</div></div>', unsafe_allow_html=True)

    for e in sorted(selected_entries, key=lambda x: (x["dataset"], _product_label(x))):
        meta = e.get("metadata", {})
        timing = meta.get("timing", {})
        files = meta.get("files", {})
        ee_est = meta.get("ee_estimate", {})
        label = f"{e['dataset']} / {_product_label(e)}  |  {files.get('frames_count', '?')} frames  |  {timing.get('total_formatted', '')}  |  {ee_est.get('estimated_eecu', 0):.2f} EECU"

        exp_key = f"td_exp_{territory_id}_{e['dataset']}_{e['product']}"
        with st.expander(label, expanded=False, key=exp_key):
            if show_kpis:
                tk1, tk2, tk3, tk4 = st.columns(4)
                with tk1: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{files.get("frames_count", "?")}</div><div class="kpi-label">FRAMES</div></div>', unsafe_allow_html=True)
                with tk2: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{timing.get("total_formatted", "")}</div><div class="kpi-label">TEMPO DE PROCESSAMENTO</div></div>', unsafe_allow_html=True)
                with tk3: st.markdown(f'<div class="kpi-box"><div class="kpi-value">{ee_est.get("estimated_eecu", 0):.2f}</div><div class="kpi-label">EECU</div></div>', unsafe_allow_html=True)
                with tk4:
                    gm = files.get("gif_size_mb", 0)
                    st.markdown(f'<div class="kpi-box"><div class="kpi-value">{gm:.1f}</div><div class="kpi-label">MB (GIF)</div></div>', unsafe_allow_html=True)

            if show_gif and show_grid:
                col_gif, col_grid = st.columns(2)
            elif show_gif:
                col_gif = st.columns(1)[0]
            elif show_grid:
                col_grid = st.columns(1)[0]

            if show_gif:
                with col_gif:
                    gif_src = _media_src(e, "gif")
                    if gif_src:
                        st.markdown(f'<div class="visual-container" style="height:360px"><img src="{gif_src}"></div>', unsafe_allow_html=True)
                        data = _download_media(e, "gif")
                        if data:
                            st.download_button("\u2b07 Download GIF", data=data, file_name="output.gif", mime="image/gif", width="stretch", key=f"tdlg_{territory_id}_{e['dataset']}_{e['product']}")

            if show_grid:
                with col_grid:
                    coll_src = _media_src(e, "collage")
                    if coll_src:
                        st.markdown(f'<div class="visual-container" style="height:360px"><img src="{coll_src}"></div>', unsafe_allow_html=True)
                        data = _download_media(e, "collage")
                        if data:
                            st.download_button("\u2b07 Download Grid", data=data, file_name="collage.png", mime="image/png", width="stretch", key=f"tdlc_{territory_id}_{e['dataset']}_{e['product']}")

            if show_frames:
                frames = e.get("frames", [])
                if frames:
                    st.markdown("---")
                    prefix = f"t_{territory_id}_{e['dataset']}_{e['product']}"
                    _render_frame_grid(frames, prefix)


# ---- VISIBILITY ----

VISIBILITY_FILE = ROOT_DIR / "config" / "visibility.json"


def _visibility_load():
    if VISIBILITY_FILE.exists():
        try:
            return json.loads(VISIBILITY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _visibility_save(data):
    VISIBILITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    VISIBILITY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _is_visible(ds, prod):
    vis = _visibility_load()
    return vis.get(ds, {}).get(prod, {}).get("visible", True)


def _toggle_visible(ds, prod):
    vis = _visibility_load()
    current = vis.setdefault(ds, {}).setdefault(prod, {"visible": True})
    current["visible"] = not current.get("visible", True)
    _visibility_save(vis)


def _filter_visible(entries):
    vis = _visibility_load()
    return [e for e in entries if vis.get(e["dataset"], {}).get(e["product"], {}).get("visible", True)]


def _user_mode(config):
    mode = config.runtime_mode
    return {"local": "escritor"}.get(mode, mode)


def _can(mode, permission):
    hierarchy = {"leitor": 0, "escritor": 1, "proprietario": 2}
    levels = {
        "view": 0, "download": 0,
        "toggle_visibility": 1,
    }
    return hierarchy.get(mode, 0) >= levels.get(permission, 0)















_IPAM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

* { font-family: 'Roboto', sans-serif; }

/* Header - light background, dark text */
.ipam-header {
    background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
    padding: 1.2rem 2rem;
    border-radius: 0 0 14px 14px;
    margin: -1rem -2rem 1.8rem -2rem;
    display: flex;
    align-items: center;
    gap: 1.2rem;
}
.ipam-header-title {
    color: #1b5e20 !important; font-family: 'Roboto', sans-serif !important;
    font-size: 1.8rem; font-weight: 700; margin: 0; line-height: 1.2;
}
.ipam-header-sub {
    color: #2e7d32; font-family: 'Roboto', sans-serif !important;
    font-size: 0.85rem; font-weight: 500; margin: 0;
}

/* Pill tabs - light bg, dark text, selected = light green */
.stTabs [data-baseweb="tab-list"] {
    background: #f4ede5; border-radius: 30px; padding: 4px; gap: 0; border: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 30px; padding: 8px 24px; font-weight: 500 !important;
    font-size: 0.9rem !important; color: #353935 !important;
}
.stTabs [aria-selected="true"] {
    background: #c8e6c9 !important; color: #1b5e20 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }

/* Buttons - light background, dark text, subtle border */
.stButton > button {
    border-radius: 8px; font-weight: 500; font-family: 'Roboto', sans-serif !important;
    background-color: #ffffff !important; color: #353935 !important;
    border: 1px solid #d0ccc5 !important;
}
.stButton > button:hover {
    background-color: #f4ede5 !important; border-color: #006b3f !important;
}
div.stDownloadButton > button {
    padding: 0px 8px; font-size: 12px; line-height: 1.4;
    min-height: 26px; height: auto; border-radius: 6px;
    background-color: #ffffff !important;
    color: #353935 !important;
}

/* Checkboxes */
div.stCheckbox { padding-top: 0px; padding-bottom: 0px; min-height: 0px; }
div.stCheckbox label {
    padding-top: 0px; padding-bottom: 0px; margin: 0px;
    gap: 2px; font-size: 12px; min-height: 22px;
}
div[data-testid="column"] > div:has(> div.stCheckbox) { padding-right: 0px; }

/* Cards - white bg, dark borders/text */
.ipam-card {
    background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border-top: 4px solid #006b3f; padding: 1rem;
}
.ipam-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
.ipam-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important; }
.ipam-card-hidden {
    border-top-color: #d0ccc5; opacity: 0.75;
}
.ipam-card-hidden:hover {
    transform: none; box-shadow: 0 2px 8px rgba(0,0,0,0.07) !important;
}
.ipam-card-hidden-badge {
    position: absolute; top: 8px; right: 8px;
    background: rgba(53,57,53,0.8); color: #fff;
    font-size: 11px; padding: 2px 8px; border-radius: 4px;
    font-weight: 500; line-height: 1.5;
}

.ipam-card-title {
    color: #1b5e20 !important; font-weight: 600; font-size: 1rem;
    margin: 0.5rem 0 0.25rem 0; line-height: 1.3;
    font-family: 'Roboto', sans-serif !important;
}
.ipam-card-title:hover { color: #006b3f !important; text-decoration: underline; }

.ipam-card-image {
    height: 180px; display: flex; align-items: center; justify-content: center;
    background: #f4ede5; border-radius: 8px; overflow: hidden; margin-bottom: 0.5rem;
    position: relative;
}
.ipam-card-image img { width: 100%; height: 100%; object-fit: cover; }

.ipam-card-territory { color: #353935; font-size: 0.85rem; margin: 0.2rem 0; }

/* Tags - dark text on light backgrounds, higher contrast */
.ipam-card-tags { display: flex; flex-wrap: wrap; gap: 4px; margin: 0.4rem 0; }
.ipam-card-tag {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 10px; font-weight: 500; line-height: 1.6; white-space: nowrap;
}
.tag-dataset { background: #e8f5e9; color: #1b5e20; }
.tag-territory { background: #fff8e1; color: #5d4037; }
.tag-frames { background: #e3f2fd; color: #0d47a1; }
.tag-duration { background: #fff3e0; color: #bf360c; }
.tag-eecu { background: #f3e5f5; color: #4a148c; }

/* Expanders */
.streamlit-expanderHeader {
    border-left: 4px solid #1b5e20 !important;
    background: #f9f9f7 !important; border-radius: 8px !important;
    font-weight: 500 !important; border: none !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}
.streamlit-expanderHeader:hover { background: #f0f0ea !important; }

/* Metrics */
div[data-testid="metric-container"] {
    background: #f9f9f7; border-radius: 12px; padding: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #006b3f;
}
div[data-testid="metric-container"] label {
    font-family: 'Roboto', sans-serif !important; color: #353935;
}
div[data-testid="metric-container"] div[data-testid="metric-value"] {
    font-family: 'Roboto', sans-serif !important; font-weight: 700; color: #1b5e20;
}

/* Multiselect / Select - smaller fonts and padding */
.stMultiSelect div, .stMultiSelect span, .stMultiSelect p,
.stSelectbox div, .stSelectbox span, .stSelectbox p {
    font-size: 0.7rem !important;
}
.stMultiSelect > div, .stSelectbox > div { border-radius: 8px !important; }
.stMultiSelect div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border-radius: 8px !important;
    padding-left: 36px !important;
    padding-right: 36px !important;
}
.stMultiSelect [data-baseweb="select"] input,
.stSelectbox [data-baseweb="select"] input {
    text-align: center !important;
}
.stMultiSelect li, .stSelectbox li { padding-left: 8px !important; }
div[data-baseweb="input"] > div { border-radius: 8px !important; background-color: #ffffff !important; }

/* Subtle labels for all filter widgets */
div[data-testid="stMultiSelect"] label p, div[data-testid="stSelectbox"] label p {
    font-size: 0.65rem !important; color: #888 !important; font-weight: 400 !important; margin-bottom: 2px !important;
}

/* Dataframe */
div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

/* Footer */
.ipam-footer {
    text-align: center; color: #353935; font-size: 0.8rem;
    border-top: 2px solid #d0ccc5; padding-top: 1.2rem; margin-top: 2rem;
}

/* Force white background */
.stApp, .stMain, .main, .block-container, section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
}

/* MapBiomas logo - remove white background via multiply */
.logo-mapbiomas { mix-blend-mode: multiply; }

/* Report page container */
.report-container {
    background: #ffffff; border-radius: 16px; padding: 2rem;
    box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    border: 1px solid #e8e5df; margin-bottom: 2rem;
}

.report-title {
    font-family: 'Roboto', sans-serif !important;
    font-size: 2rem !important; font-weight: 700 !important;
    color: #1b5e20 !important; margin: 0 0 0.25rem 0 !important;
    line-height: 1.2 !important;
}
.report-subtitle {
    font-family: 'Roboto', sans-serif !important;
    font-size: 0.95rem; color: #353935;
}
.kpi-box {
    background: #f9f9f7; border-radius: 12px; padding: 1rem 1.2rem; text-align: center;
    border-left: 4px solid #006b3f;
}
.kpi-value {
    font-family: 'Roboto', sans-serif !important;
    font-size: 1.6rem; font-weight: 700; color: #1b5e20; line-height: 1.2;
}
.kpi-label {
    font-family: 'Roboto', sans-serif !important;
    font-size: 0.7rem; font-weight: 600; color: #353935;
    letter-spacing: 1px; margin-top: 2px;
}
.report-section-title {
    font-family: 'Roboto', sans-serif !important;
    font-size: 1.1rem; font-weight: 600; color: #353935;
    margin: 1.5rem 0 0.25rem 0;
}
.report-section-line {
    height: 2px; background: linear-gradient(90deg, #006b3f, #e8e5df);
    margin-bottom: 1rem;
}

/* Visual result containers - same height for GIF and grid */
.visual-container {
    height: 380px; display: flex; align-items: center; justify-content: center;
    background: #f9f9f7; border-radius: 8px; overflow: hidden;
    margin-bottom: 0.5rem;
}
.visual-container img { max-height: 100%; max-width: 100%; object-fit: contain; }

/* Selected state for multiselect tags - light bg, dark text */
div[data-baseweb="tag"] {
    background-color: #e8f5e9 !important;
    color: #1b5e20 !important;
}
div[data-baseweb="tag"] span[aria-label="close"] {
    color: #1b5e20 !important;
}
div[data-baseweb="tag"] span[aria-label="close"]:hover {
    color: #006b3f !important;
}

/* Multiselect dropdown options */
div[data-baseweb="popover"] li {
    color: #353935 !important;
    background: #ffffff !important;
}
div[data-baseweb="popover"] li[aria-selected="true"] {
    background: #e8f5e9 !important;
    color: #1b5e20 !important;
}
div[data-baseweb="popover"] li:hover {
    background: #f4ede5 !important;
}

/* Selectbox / dropdown */
div[data-baseweb="select"] div[role="listbox"] li {
    color: #353935 !important;
}
div[data-baseweb="select"] div[role="listbox"] li[aria-selected="true"] {
    background: #e8f5e9 !important;
    color: #1b5e20 !important;
}

/* Text inputs - dark text always, light background */
input, textarea, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
    color: #353935 !important;
    background-color: #ffffff !important;
}
input::placeholder, textarea::placeholder {
    color: #5a5855 !important;
}

/* Labels for all form elements */
label, .stTextInput label, .stSelectbox label, .stMultiselect label,
.stRadio label, .stCheckbox label, .stNumberInput label {
    color: #353935 !important;
    font-weight: 500 !important;
}

/* Alert / Info / Warning / Success / Error boxes */
.stAlert {
    color: #353935 !important;
}
.stAlert[data-baseweb="notification"] {
    color: #353935 !important;
}
div[role="alert"] {
    color: #353935 !important;
}

/* Override Streamlit's blue info box */
.stInfo, .st-bq, [data-testid="stInfo"] {
    color: #1b5e20 !important;
}
.stWarning, [data-testid="stWarning"] {
    color: #353935 !important;
}
.stSuccess, [data-testid="stSuccess"] {
    color: #1b5e20 !important;
}
.stError, [data-testid="stError"] {
    color: #353935 !important;
}

/* Radio buttons */
div[role="radiogroup"] label {
    color: #353935 !important;
}

/* Progress bar text */
.stProgress label {
    color: #353935 !important;
}

/* DataFrame / table cells */
div[data-testid="stDataFrame"] td,
div[data-testid="stDataFrame"] th,
div[data-testid="stDataFrame"] [data-testid="StyledDataFrameDataCell"] {
    color: #353935 !important;
}

/* Expander label */
.streamlit-expanderHeader svg {
    fill: #1b5e20 !important;
}

/* Help text */
.stHelp, div[data-testid="stMarkdownCaption"], div[data-testid="caption"] {
    color: #353935 !important;
}

/* Buttons hover/active - keep consistent dark text */
.stButton > button:active, .stButton > button:focus {
    color: #353935 !important;
}

/* Metric delta arrows */
div[data-testid="metric-container"] [data-testid="metric-delta"] {
    color: #353935 !important;
}

/* JSON viewer text */
div[data-testid="stJson"] {
    color: #353935 !important;
}

/* Tabs hover - unselected tabs */
.stTabs [data-baseweb="tab"]:not([aria-selected="true"]):hover {
    background: #e8f5e9 !important;
}

/* Enforce dark text on EVERYTHING - Streamlit defaults use light colors in many places */
.stApp, .stMain, .main, .block-container, div, section, article, aside, header, footer {
    color: #353935 !important;
}
.stApp a, .stApp a:link, .stApp a:visited {
    color: #1b5e20 !important;
}
.stApp a:hover {
    color: #006b3f !important;
}
"""


def _render_header():
    meta = st.session_state.get("_index_meta", {})
    last_updated = meta.get("last_updated", "")
    if last_updated:
        try:
            dt = datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%SZ")
            update_str = dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            update_str = last_updated
    else:
        update_str = "—"

    col1, col2 = st.columns([8, 2])
    with col1:
        if MAPBIOMAS_LOGO_PATH.exists():
            mb_b64 = base64.b64encode(open(MAPBIOMAS_LOGO_PATH, "rb").read()).decode()
            st.markdown(f"""
            <div class="ipam-header">
                <img src="data:image/png;base64,{mb_b64}" height="52" class="logo-mapbiomas" style="margin-right: 1rem;">
                <div>
                    <div class="ipam-header-title">MapBiomas GIF Factory</div>
                    <div class="ipam-header-sub">Módulo de Degradação · MapBiomas</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="ipam-header">
                <div>
                    <div class="ipam-header-title">MapBiomas GIF Factory</div>
                    <div class="ipam-header-sub">Módulo de Degradação · MapBiomas</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div style="text-align:right; padding-top:10px; font-size:0.75rem; color:#888;">📦 {update_str}</div>', unsafe_allow_html=True)


def run_dashboard():
    if st is None:
        print("Streamlit nao instalado. Execute: pip install streamlit")
        return

    st.set_page_config(page_title="MapBiomas GIF Factory",
                       page_icon=":movie_camera:",
                       layout="wide",
                       initial_sidebar_state="collapsed")

    st.markdown(f"<style>{_IPAM_CSS}</style>", unsafe_allow_html=True)

    config = ConfigLoader()
    config.load_all()
    output_dir = config.get_output_dir()

    try:
        import ee
        ee.Initialize()
    except Exception:
        pass

    _render_header()

    tabs = ["Geral", "Produto", "Territorio"]

    tab_objects = st.tabs(tabs)

    with tab_objects[0]:
        _clear_index_cache()
        st.session_state["_index_entries"] = _load_index(output_dir, config)
        _render_geral(output_dir, config)

    with tab_objects[1]:
        st.session_state["_index_entries"] = _filter_visible(_load_index(output_dir, config))
        _render_catalog_product(output_dir, config)

    with tab_objects[2]:
        st.session_state["_index_entries"] = _filter_visible(_load_index(output_dir, config))
        _render_catalog_territory(output_dir, config)

    ipam_b64 = base64.b64encode(open(LOGO_PATH, "rb").read()).decode() if LOGO_PATH.exists() else None
    footer_logo = f'<div style="margin-bottom:4px;"><img src="data:image/png;base64,{ipam_b64}" height="32"></div>' if ipam_b64 else ""
    st.markdown(f'<div class="ipam-footer">{footer_logo}Produzido por: IPAM<br>Produto experimental não oficial</div>',
                unsafe_allow_html=True)


if __name__ == "__main__":
    run_dashboard()
