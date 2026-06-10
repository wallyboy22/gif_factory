"""
TEMPLATE: Adicionar um Novo Dataset
====================================

Para adicionar um dataset novo à Fábrica de GIFs:
  1. Copie este arquivo como referência
  2. Edite config/datasets.yaml com a estrutura abaixo
  3. Se precisar de visualização nova, edite config/visualization.yaml
  4. Se precisar de processamento EE, adicione em ee_transforms.py
  5. Teste com: python run_fire_col5_test.py   (substitua pelo seu produto)
  6. Adicione ao batch: edite scripts/_template_batch.py

---

ESTRUTURA NO datasets.yaml:
============================

<dataset_id>:
  description: "Descrição legível do dataset"
  category: "fire"           # fire | land_cover | degradation | soil
  source: "MapBiomas"
  collection: 5
  visualization: "<viz_key_padrão>"   # visualização padrão (opcional)
  products:
    <product_id>:
      name: "Nome legível do produto"
      asset: "projects/..."                         # Asset GEE (Image)
      temporal_range: [1985, 2025]                  # Período
      visualization: "<viz_key>"                    # Viz específica (opcional)
      bands_slice: [0, 41]                          # Fatiar bandas (opcional)
      processor: "<processor_id>"                   # EE processor (opcional)


TIPOS DE PRODUTO:
=================

1. Produto com Asset GEE direto (Image):
   asset: "projects/mapbiomas-public/assets/brazil/fire/collection5/..."

2. Produto com EE Processor (computação on-the-fly):
   processor: "meu_processor_id"
   # Não precisa de 'asset' - o processor carrega o que precisa

3. Produto com RGB (3 bandas por frame, ex: mosaico Landsat):
   processor: "build_nbr_min_mosaic"
   rgb: true   # ← indica que cada frame usa 3 bandas (R, G, B)


EXEMPLO COMPLETO (Fire Col5):
==============================

brasil_fire_col5:
  description: "MapBiomas Fire Collection 5 - Brasil"
  category: "fire"
  source: "MapBiomas"
  collection: 5
  visualization: "fire"
  products:
    annual_burned:
      name: "Área Queimada Anual"
      asset: "projects/mapbiomas-public/assets/brazil/fire/collection5/mapbiomas_fire_collection5_annual_burned_v1"
      temporal_range: [1985, 2025]
      visualization: "fire"


ADICIONANDO VISUALIZAÇÃO NOVA:
===============================

Edite config/visualization.yaml:

  minha_viz:
    name: "Nome da visualização"
    min: 0
    max: 10
    palette:
      - "ffffff"
      - "ff0000"
      - "00ff00"
    label: "Rótulo da legenda"
    cmap_type: "sequential"          # sequential | categorical | binary
    discrete_labels:                 # (opcional, p/ categorical)
      - "Classe A"
      - "Classe B"


ADICIONANDO EE PROCESSOR:
==========================

Edite src/ipam_gif_factory/core/ee_transforms.py:

  def meu_processor():
      asset = "projects/..."
      img = ee.Image(asset)
      img = img.divide(100).int().unmask(0).int8()
      return img

  # Registrar em PROCESSOR_REGISTRY:
  PROCESSOR_REGISTRY = {
      ...
      "meu_processor": meu_processor,
  }


ADICIONANDO TERRITÓRIO:
========================

Edite o arquivo correspondente em config/:
  - territories_countries.yaml   → países
  - territories_biomes.yaml      → biomas
  - territories_states.yaml      → estados
  - territories_custom.yaml      → regiões customizadas

  df:
    name: "Distrito Federal"
    source: "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
    filter: "NM_ESTADO == 'DISTRITO FEDERAL'"


VERIFICAÇÕES FINAIS:
=====================

  [ ] O asset GEE existe e está acessível?
  [ ] A paleta de visualização tem cores hex válidas?
  [ ] min/max correspondem aos valores reais dos pixels?
  [ ] Testou com DF primeiro?  (rápido, ~30s)
  [ ] Adicionou ao batch?
  [ ] Rodou o batch completo com --resume?
