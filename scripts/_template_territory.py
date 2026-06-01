"""
TEMPLATE: Adicionar um Novo Território
=======================================

Para adicionar um território novo à Fábrica de GIFs:
  1. Identifique o tipo: país, bioma, estado, ou região customizada
  2. Edite o arquivo YAML correspondente em config/
  3. Adicione ao batch: edite scripts/_template_batch.py
  4. Teste com: python run_fire_col5_test.py   (ajuste o território)


ARQUIVOS DE TERRITÓRIO:
========================

  config/territories.yaml            ← Hub (não editar, só lista includes)
  config/territories_countries.yaml  ← Países
  config/territories_biomes.yaml     ← Biomas
  config/territories_states.yaml     ← Estados (27 UFs)
  config/territories_custom.yaml     ← Regiões customizadas


ESTRUTURA DE UM TERRITÓRIO:
============================

  <territory_id>:                   # snake_case, em português
    name: "Nome legível"
    name_en: "English name"         # opcional
    source: "projects/..."          # Asset GEE FeatureCollection
    filter: "propriedade == 'valor'" # Filtro EE opcional
    bbox: [lon_min, lat_min, lon_max, lat_max]  # opcional
    overlay:                        # opcional: borda/máscara extra
      feature_collection: "projects/..."
      filter: "..."


EXEMPLOS:
==========

# Bioma individual (filtro sobre FC de biomas)
amazonia:
  name: "Amazônia"
  source: "projects/mapbiomas-workspace/AUXILIAR/biomas_IBGE_250mil"
  filter: "Bioma == 'Amazônia'"
  bbox: [-74.0, -18.0, -44.0, 5.0]

# Estado individual (filtro sobre FC de estados)
df:
  name: "Distrito Federal"
  source: "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
  filter: "NM_ESTADO == 'DISTRITO FEDERAL'"
  bbox: [-48.2, -16.1, -47.3, -15.5]

# Região customizada (FC própria)
matopiba:
  name: "MATOPIBA"
  source: "projects/mapbiomas-workspace/AUXILIAR/ESTATISTICAS/COLECAO8/VERSAO-1/matopiba"

# País (FC pública FAO)
paraguay:
  name: "Paraguay"
  name_en: "Paraguay"
  source: "FAO/GAUL/2015/level0"
  filter: "ADM0_NAME == 'Paraguay'"


PASSO A PASSO:
==============

1. ESCOLHA O ARQUIVO CERTO:
   - País → territories_countries.yaml
   - Bioma → territories_biomes.yaml
   - Estado → territories_states.yaml
   - Região → territories_custom.yaml

2. ADICIONE O BLOCO:

   <meu_id>:
     name: "Meu Território"
     source: "projects/..."   # asset da FeatureCollection
     filter: "..."            # filtro EE (opcional)

3. PARA TERRITÓRIOS COM BORDA PERSONALIZADA:

   <meu_id>:
     name: "Meu Território"
     source: "projects/minha_fc"
     overlay:
       feature_collection: "projects/minha_borda"

4. TESTE RÁPIDO:

   python run_fire_col5_test.py
   # (edite o script pra usar seu territory_id)


CONVENÇÕES:
============

  - ID do território: snake_case, em português
  - Nome legível: português com acentos
  - source: asset GEE FeatureCollection (não Image, não ImageCollection)
  - filter: string de expressão EE (ex: "Bioma == 'Amazônia'")
  - bbox: [lng_min, lat_min, lng_max, lat_max] (opcional, ajuda no zoom)


VERIFICAÇÕES FINAIS:
=====================

  [ ] O asset da FeatureCollection existe e está acessível?
  [ ] O filtro EE está sintaticamente correto?
  [ ] O ID usa snake_case e está em português?
  [ ] Testou com um produto simples (ex: annual_burned)?
  [ ] Adicionou ao batch?
