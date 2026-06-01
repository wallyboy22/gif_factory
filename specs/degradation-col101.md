---
tags: [degradation, col101, done]
aliases: [Degradação Col 10.1, Degradação]
date: 2026-06-01
---

[[datasets]] | [[visualization]] | [[batch-processing]] | [[fire-col5]]

# Degradação Coleção 10.1 — Especificação

**STATUS: 386 GIFs gerados — pipeline completo e validado.**

## Visão Geral

Dataset: `brasil_degradation_col10_1`
Categoria: `degradation`
Coleção: 10.1
Período: 1985-2024 (40 anos)
Asset base: `projects/mapbiomas-public/assets/brazil/degradation/collection10_1/`

## Produtos (15 principais)

### Produtos baseados em Assets GEE (acesso direto)

| Produto | Asset | Bandas | Viz |
|---------|-------|--------|-----|
| `edge_age` | `...edge_age_collection10_1_v6` | 1985-2024 | `edge_age_col101` |
| `patch_size_fragments` | `...patch_size_fragments_collection10_1_v6` | classificação | `patch_size_fragments` |
| `patch_size_massifs` | `...patch_size_massifs_collection10_1_v6` | classificação | `patch_size_massifs` |
| `secondary_vegetation_coverage` | `...secondary_vegetation_coverage_collection10_1_v6` | 1985-2024 | `secondary_vegetation_coverage` |
| `primary_natural_coverage` | `...primary_natural_coverage_collection10_1_v6` | classificação | `natural_coverage` |

### Produtos baseados em EE Processors (computação on-the-fly)

| Produto | Processor | Descrição | Viz |
|---------|-----------|-----------|-----|
| `edge_area` | `edge_area` | Classes de distância da borda (0-8) | `edge_area_col101` |
| `patch_size` | `patch_size` | Tamanho do fragmento em ha (contínuo) | `patch_size_continuous` |
| `patch_id` | `patch_id` | ID único por fragmento | `random` |
| `landscape_morphology` | `landscape_morphology` | Core, Edge, Perforation, Patch, Loop, Bridge | `morphology` |
| `secondary_vegetation_age` | `secondary_vegetation_age` | Idade da vegetação secundária (0-40) | `secondary_vegetation_age` |
| `fire_frequency` | `fire_frequency` | Frequência de fogo (÷100, round) | `frequency_col101` |
| `fire_age` | `fire_age` | Tempo desde último fogo (0-40) | `fire_age` |
| `natural_coverage` | `natural_coverage` | Cobertura natural (0-2) | `natural_coverage` |
| `burned_natural_coverage` | `burned_natural_coverage` | Cobertura em áreas queimadas (mod 100) | `secondary_vegetation_coverage` |
| `canopy_disturbance_frequency` | `canopy_disturbance` | Eventos de distúrbio (1-12) | `canopy_disturbance` |
| `logging` | `logging` | Extração de madeira (binary 0-1) | `logging` |

**Extra:** `burned_at_least_once` (processor `burned_at_least_once`, viz `burned_at_least_once`)
— classificação ternária de histórico de fogo, definido fora dos products do dataset.

## Territórios Processados

- **27 estados** (todos) — pasta `outputs/v001/brasil_degradation_col10_1/<produto>/<uf>/`
- **9 biomas/regiões** — `amazonia`, `caatinga`, `cerrado`, `mata_atlantica`, `pampa`, `pantanal`, `biomas`, `bap`, `bap_planalto`
- **Regiões customizadas** — `matopiba`, `matopiba_cerrado`, regiões (N, NE, CO, SE, S)

## Batch v001

150 combinações no total: 10 territórios × 15 produtos.
Arquivo: `batch_v001.json`.
Executado via: `run_all_v001.ps1` → CLI com 6 workers, --resume.

Territórios no batch: `matopiba_cerrado`, `biomas`, `amazonia`, `caatinga`, `cerrado`, `mata_atlantica`, `pampa`, `pantanal`, `bap`, `bap_planalto`.

## Configuração do Pipeline

```python
vertical_dimension = 1560
cell_height = 300
frame_duration = 300ms  # → _0_3s.gif
create_collage = True
add_labels = True
```

## Lições Aprendidas

1. **EE Processors são pesados** — produtos como `patch_id`, `patch_size`, `landscape_morphology` demoram mais que assets diretos, pois computam no servidor GEE a cada thumbnail.

2. **Band naming inconsistente** — assets diretos têm bandas `YYYY`; processors geram bandas nomeadas pelo código. O `bands_slice` do dataset.yaml é essencial para produtos multi-banda (ex: `accumulated` com bandas `fire_accumulated_1985_2025`).

3. **Checkpoint é crítico** — para 150+ combos com 6 workers, falhas de rede GEE são comuns. O resume salva horas de re-trabalho.

4. **Ordem dos territórios importa** — territórios maiores (amazonia, cerrado) demoram mais. Começar pelos pequenos (pampa, pantanal) acelera o feedback inicial.

5. **Collage com patch_id** — o viz `random` gera cores aleatórias. A legenda não faz sentido (cada fragmento cor única). O FrameProcessor trata `n==0` como caso especial mostrando "Cada mancha possui uma cor única".

6. **Discrete labels nos viz YAML** — alguns viz têm `discrete_labels` explícitos (ex: `edge_area_col101` com classes "<=30m", "<=100m"...). Outros dependem do comportamento automático do FrameProcessor.

7. **Fontes Windows** — o FrameProcessor busca Arial → segoeui → Calibri → fallback. Funciona bem no Windows, requer DejaVu no Linux/Colab.

## Produtos Pendentes no Batch

Do batch_v001, 4 produtos não foram concluídos (não constam no index.json):
- `canopy_disturbance_frequency` (batch_canopy.json separado)
- `logging`
- `patch_size_fragments`
- `patch_size_massifs`

## Próximos Passos para Degradação

1. Completar os 4 produtos pendentes
2. Atualizar index.json
3. Regenerar CSVs do Looker
4. Upload GCS dos novos arquivos
