"""
Regenera os 6 coverage_nivel* no visualization.yaml com base nos
dicionários oficiais EE do MapBiomas, corrigidos:
- Classe 0 e 27 = "Não observado" (#ffffff) em todos os níveis
- nivel1_1: id 5 e 6 = "Formação Florestal" (não Mangue/Floresta Alagavel)
"""
import re

PATH = "config/visualization.yaml"

# ============================================================
# Cores MapBiomas por grupo (padrão oficial)
# ============================================================
GROUP_COLORS = {
    "Natural": "1f8d49",
    "Antrópico": "FFD966",
    "Não observado": "ffffff",

    "Floresta": "1f8d49",
    "Vegetação Herbácea e Arbustiva": "d6bc74",
    "Agropecuária": "ffefc3",
    "Área não vegetada": "d4271e",
    "Corpos D´água": "2532e4",

    "Formação Florestal": "1f8d49",
    "Formação Savânica": "7dc975",
    "Formação Campestre": "d6bc74",
    "Campo Alagado e Área Pantanosa": "519799",
    "Pastagem": "edde8e",
    "Agricultura": "ffefc3",
    "Silvicultura": "7a5900",
    "Mosaico de Usos": "ffefc3",
    "Outros": "d5d5e5",

    "Mangue": "04381d",
    "Floresta Alagável": "026975",
    "Restinga Arbórea": "02d659",
    "Restinga herbácea": "ad5100",
    "Apicum": "091077",
    "Afloramento Rochoso": "ffaa5f",
    "Outras Formações não Florestais": "d6bc74",
    "Área não Vegetada": "d4271e",
    "Praia, Duna e Areal": "ffa07a",
    "Área Urbanizada": "db4d4f",
    "Mineração": "9c0027",
    "Usina Fotovoltaica": "E974ED",
    "Outras Áreas não Vegetadas": "d5d5e5",
    "Rio, Lago e Oceano": "2532e4",
    "Aquicultura": "fc8114",

    "Lavoura Temporária": "ffefc3",
    "Lavoura Perene": "ffefc3",
    "Formação Natural não Florestal": "d6bc74",

    "Soja": "f5b3c8",
    "Cana": "db7093",
    "Arroz": "c71585",
    "Algodão (beta)": "ff69b4",
    "Café": "d68fe2",
    "Citrus": "9932cc",
    "Dendê": "9065d0",
    "Outras Lavouras Temporárias": "f54ca9",
    "Outras Lavouras Perenes": "e6ccff",
    "Usina Fotovoltaica (beta)": "E974ED",
}

# ============================================================
# Dicionários EE corrigidos
# ============================================================
NIVEL0 = {
    0: "Não observado", 1: "Natural", 3: "Natural", 4: "Natural",
    5: "Natural", 6: "Natural", 49: "Natural", 10: "Natural",
    11: "Natural", 12: "Natural", 32: "Natural", 29: "Antrópico",
    50: "Natural", 13: "Natural", 14: "Antrópico", 15: "Antrópico",
    18: "Antrópico", 19: "Antrópico", 39: "Antrópico", 20: "Antrópico",
    40: "Antrópico", 62: "Antrópico", 41: "Antrópico", 36: "Antrópico",
    46: "Antrópico", 47: "Antrópico", 35: "Antrópico", 48: "Antrópico",
    9: "Antrópico", 21: "Antrópico", 22: "Antrópico", 23: "Antrópico",
    24: "Antrópico", 30: "Antrópico", 75: "Antrópico", 25: "Antrópico",
    26: "Antrópico", 33: "Natural", 31: "Antrópico", 27: "Não observado",
}

NIVEL1 = {
    0: "Não observado", 1: "Floresta", 3: "Floresta", 4: "Floresta",
    5: "Floresta", 6: "Floresta", 49: "Floresta",
    10: "Vegetação Herbácea e Arbustiva", 11: "Vegetação Herbácea e Arbustiva",
    12: "Vegetação Herbácea e Arbustiva", 32: "Vegetação Herbácea e Arbustiva",
    29: "Área não vegetada", 50: "Vegetação Herbácea e Arbustiva",
    13: "Vegetação Herbácea e Arbustiva",
    14: "Agropecuária", 15: "Agropecuária", 18: "Agropecuária",
    19: "Agropecuária", 39: "Agropecuária", 20: "Agropecuária",
    40: "Agropecuária", 62: "Agropecuária", 41: "Agropecuária",
    36: "Agropecuária", 46: "Agropecuária", 47: "Agropecuária",
    35: "Agropecuária", 48: "Agropecuária", 9: "Agropecuária",
    21: "Agropecuária",
    22: "Área não vegetada", 23: "Área não vegetada",
    24: "Área não vegetada", 30: "Área não vegetada",
    75: "Área não vegetada", 25: "Área não vegetada",
    26: "Corpos D´água", 33: "Corpos D´água", 31: "Corpos D´água",
    27: "Não observado",
}

NIVEL1_1 = {
    0: "Não observado", 1: "Formação Florestal", 3: "Formação Florestal",
    4: "Formação Savânica", 5: "Formação Florestal", 6: "Formação Florestal",
    49: "Formação Savânica",
    10: "Formação Campestre", 11: "Campo Alagado e Área Pantanosa",
    12: "Formação Campestre", 32: "Formação Campestre",
    29: "Outros", 50: "Formação Campestre", 13: "Formação Campestre",
    14: "Agropecuária", 15: "Pastagem", 18: "Agricultura",
    19: "Agricultura", 39: "Agricultura", 20: "Agricultura",
    40: "Agricultura", 62: "Agricultura", 41: "Agricultura",
    36: "Agricultura", 46: "Agricultura", 47: "Agricultura",
    35: "Agricultura", 48: "Agricultura",
    9: "Silvicultura", 21: "Mosaico de Usos",
    22: "Outros", 23: "Outros", 24: "Outros", 30: "Outros",
    75: "Outros", 25: "Outros",
    26: "Outros", 33: "Outros", 31: "Outros", 27: "Não observado",
}

NIVEL2 = {
    0: "Não observado", 1: "Floresta",
    3: "Formação Florestal", 4: "Formação Savânica",
    5: "Mangue", 6: "Floresta Alagável", 49: "Restinga Arbórea",
    10: "Vegetação Herbácea e Arbustiva", 11: "Campo Alagado e Área Pantanosa",
    12: "Formação Campestre", 32: "Apicum",
    29: "Afloramento Rochoso", 50: "Restinga herbácea",
    13: "Outras Formações não Florestais",
    14: "Agropecuária", 15: "Pastagem", 18: "Agricultura",
    19: "Agricultura", 39: "Agricultura", 20: "Agricultura",
    40: "Agricultura", 62: "Agricultura", 41: "Agricultura",
    36: "Agricultura", 46: "Agricultura", 47: "Agricultura",
    35: "Agricultura", 48: "Agricultura",
    9: "Silvicultura", 21: "Mosaico de Usos",
    22: "Área não Vegetada", 23: "Praia, Duna e Areal",
    24: "Área Urbanizada", 30: "Mineração",
    75: "Usina Fotovoltaica", 25: "Outras Áreas não Vegetadas",
    26: "Corpos D´água", 33: "Rio, Lago e Oceano", 31: "Aquicultura",
    27: "Não observado",
}

NIVEL3 = {
    0: "Não observado", 1: "Floresta",
    3: "Formação Florestal", 4: "Formação Savânica",
    5: "Mangue", 6: "Floresta Alagável", 49: "Restinga Arbórea",
    10: "Formação Natural não Florestal", 11: "Campo Alagado e Área Pantanosa",
    12: "Formação Campestre", 32: "Apicum",
    29: "Afloramento Rochoso", 50: "Restinga herbácea",
    13: "Outras Formações não Florestais",
    14: "Agropecuária", 15: "Pastagem", 18: "Agricultura",
    19: "Lavoura Temporária", 39: "Lavoura Temporária",
    20: "Lavoura Temporária", 40: "Lavoura Temporária",
    62: "Lavoura Temporária", 41: "Lavoura Temporária",
    36: "Lavoura Perene", 46: "Lavoura Perene", 47: "Lavoura Perene",
    35: "Lavoura Perene", 48: "Lavoura Perene",
    9: "Silvicultura", 21: "Mosaico de Usos",
    22: "Área não Vegetada", 23: "Praia, Duna e Areal",
    24: "Área Urbanizada", 30: "Mineração",
    75: "Usina Fotovoltaica", 25: "Outras Áreas não Vegetadas",
    26: "Corpos D´água", 33: "Rio, Lago e Oceano", 31: "Aquicultura",
    27: "Não observado",
}

NIVEL4 = {
    0: "Não observado", 1: "Floresta",
    3: "Formação Florestal", 4: "Formação Savânica",
    5: "Mangue", 6: "Floresta Alagável", 49: "Restinga Arbórea",
    10: "Vegetação Herbácea e Arbustiva", 11: "Campo Alagado e Área Pantanosa",
    12: "Formação Campestre", 32: "Apicum",
    29: "Afloramento Rochoso", 50: "Restinga Herbácea",
    14: "Agropecuária", 15: "Pastagem", 18: "Agricultura",
    19: "Lavoura Temporária", 39: "Soja", 20: "Cana",
    40: "Arroz", 62: "Algodão (beta)", 41: "Outras Lavouras Temporárias",
    36: "Lavoura Perene", 46: "Café", 47: "Citrus", 35: "Dendê",
    48: "Outras Lavouras Perenes",
    9: "Silvicultura", 21: "Mosaico de Usos",
    22: "Área não Vegetada", 23: "Praia, Duna e Areal",
    24: "Área Urbanizada", 30: "Mineração",
    75: "Usina Fotovoltaica (beta)", 25: "Outras Áreas não Vegetadas",
    26: "Corpo D'água", 33: "Rio, Lago e Oceano", 31: "Aquicultura",
    27: "Não observado",
}

# ============================================================
# Configuração dos níveis
# ============================================================
LEVELS = [
    ("coverage_nivel0",   "Cobertura - Nível 0 (Natural/Antrópico)",  NIVEL0),
    ("coverage_nivel1",   "Cobertura - Nível 1",                      NIVEL1),
    ("coverage_nivel1_1", "Cobertura - Nível 1.1",                    NIVEL1_1),
    ("coverage_nivel2",   "Cobertura - Nível 2",                      NIVEL2),
    ("coverage_nivel3",   "Cobertura - Nível 3",                      NIVEL3),
    ("coverage_nivel4",   "Cobertura - Nível 4",                      NIVEL4),
]


def build_level(mapping):
    palette = ["ffffff"] * 76
    labels = [""] * 76
    seen_groups = set()

    for cid in sorted(mapping.keys()):
        if cid >= 76:
            continue
        name = mapping[cid]
        color = GROUP_COLORS.get(name, "d5d5e5")
        palette[cid] = color
        if name not in seen_groups:
            seen_groups.add(name)
            labels[cid] = name

    return palette, labels


def yaml_block(key, name_str, palette, labels):
    lines = [f"  {key}:"]
    lines.append(f'    name: "{name_str}"')
    lines.append("    min: 0")
    lines.append("    max: 75")
    lines.append("    palette:")
    for c in palette:
        lines.append(f'      - "{c}"')
    lines.append('    label: "Classe de cobertura"')
    lines.append("    cmap_type: categorical")
    lines.append("    discrete_labels:")
    for lbl in labels:
        lines.append(f'      - "{lbl}"')
    return "\n".join(lines)


def main():
    blocks = []
    for key, name, mapping in LEVELS:
        palette, labels = build_level(mapping)
        blocks.append(yaml_block(key, name, palette, labels))
        non_white = sum(1 for c in palette if c != "ffffff")
        unique_labels = sum(1 for lbl in labels if lbl)
        print(f"  {key}: {non_white}/76 cores, {unique_labels} grupos")

    new_section = "\n\n".join(blocks) + "\n"

    with open(PATH, "r", encoding="utf-8") as f:
        content = f.read()

    start_marker = "  coverage_nivel0:"
    end_marker = "\n  fire_age:"

    start_idx = content.index(start_marker)
    end_idx = content.index(end_marker, start_idx)

    updated = content[:start_idx] + new_section + content[end_idx:]

    with open(PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"\n  Substituído no {PATH}: {len(blocks)} níveis gerados.")


if __name__ == "__main__":
    main()
