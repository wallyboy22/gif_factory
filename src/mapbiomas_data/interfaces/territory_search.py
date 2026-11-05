"""Busca sob demanda em assets de territórios escolhidos pela pessoa."""
import hashlib
import json


def search_features(ee, source, name_field, id_field, query, limit=30):
    if not all((source.strip(), name_field.strip(), id_field.strip(), query.strip())):
        raise ValueError("Informe asset, campos e termo de busca.")
    fc = ee.FeatureCollection(source).filter(ee.Filter.stringContains(name_field, query.strip()))
    data = fc.limit(limit).getInfo()
    found = []
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        identifier = feature.get("id") if id_field == "system:index" else props.get(id_field)
        name = props.get(name_field)
        if identifier is not None and name is not None:
            found.append({"name": str(name), "id": identifier, "source": source,
                          "name_field": name_field, "id_field": id_field})
    return found


def register_selection(config, records, combine=False, dissolve=False):
    """Registra recortes na configuração em memória, sem modificar YAML."""
    if not records:
        return []
    group = config.territories.setdefault("municipalities", {})
    ids = []
    for record in records:
        identity = json.dumps([record["source"], record["id_field"], record["id"]],
                              ensure_ascii=False, sort_keys=True)
        tid = "busca_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
        spec = {"name": record["name"], "source": record["source"],
                "filter_in": {"field": record["id_field"], "values": [record["id"]]}}
        if tid in group and group[tid] != spec:
            raise ValueError(f"Identificador já ocupado: {tid}")
        group[tid] = spec
        ids.append(tid)
    ids = sorted(set(ids))
    if not combine or len(ids) == 1:
        return ids
    identity = json.dumps([ids, bool(dissolve)])
    tid = "combinado_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    group[tid] = {"name": " + ".join(sorted({r["name"] for r in records})),
                  "union_of": ids, "dissolve": bool(dissolve)}
    return [tid]
