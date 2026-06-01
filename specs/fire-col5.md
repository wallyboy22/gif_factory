---
tags: [fire-col5, visualization, pending]
aliases: [Fire Col 5, Coleção 5, Fogo Col 5]
date: 2026-06-01
---

[[datasets]] | [[visualization]] | [[batch-processing]] | [[degradation-col101]]

# Fire Coleção 5 — Especificação

**STATUS: Configurado no YAML, 0 GIFs gerados. Visualização precisa de ajuste.**

## Visão Geral

Dataset: `brasil_fire_col5`
Categoria: `fire`
Coleção: 5
Período: 1985-2025 (41 anos)
Asset base: `projects/mapbiomas-public/assets/brazil/fire/collection5/`

**Diferente da Degradação Col 10.1, todos os produtos acessam assets GEE diretamente (sem EE processors).**

## Produtos e Assets

### 1. `annual_burned` — Área Queimada Anual
- Asset: `mapbiomas_fire_collection5_annual_burned_v1`
- Bandas: `burned_area_1985` até `burned_area_2025` (41 bandas)
- Visualização: `fire` (binary, #fdfdfd / #800000)
- Valores: 0 = não queimado, 1 = queimado

### 2. `annual_burned_coverage` — Cobertura Queimada Anual
- Asset: `mapbiomas_fire_collection5_annual_burned_coverage_v1`
- Bandas: `burned_coverage_1985` até `burned_coverage_2025`
- Visualização: `fire_col5_coverage_total` (binary, #fff / #E84C3B)
- Valores: classes de cobertura do solo em áreas queimadas

### 3. `monthly_burned` — Área Queimada Mensal
- Asset: `mapbiomas_fire_collection5_monthly_burned_v1`
- Bandas: `burned_monthly_1985` até `burned_monthly_2025`
- Visualização: `fire_col5_monthly` (13 cores: branco + 12 meses)
- **ATENÇÃO:** Valor do pixel = mês × 100 + cobertura. Precisa decodificar (÷100).
- Valores: 1=Jan, 2=Fev, ..., 12=Dez

### 4. `scar_size_range` — Tamanho de Cicatriz
- Asset: `mapbiomas_fire_collection5_annual_burned_scar_size_range_v1`
- Bandas: `scar_area_ha_1985` até `scar_area_ha_2025`
- Visualização: `scar_size_range` (11 tons marrom/dourado, 0-10)
- Classes: 1=<10ha, 2=10-250ha, 3=250-500ha, 4=500-5kha, 5=5k-10kha, 6=10k-50kha, 7=50k-100kha, 8=>=100kha

### 5. `accumulated_burned` — Área Queimada Acumulada
- Asset: `mapbiomas_fire_collection5_accumulated_burned_v1`
- Bandas: `fire_accumulated_1985_2025` (bandas com range no nome)
- `bands_slice: [0, 41]`
- Visualização: `fire` (binary)

### 6. `accumulated_burned_coverage` — Cobertura Queimada Acumulada
- Asset: `mapbiomas_fire_collection5_accumulated_burned_coverage_v1`
- Bandas: `fire_accumulated_1985_2025`
- `bands_slice: [0, 41]`
- Visualização: `fire_col5_coverage_total` (binary)

### 7. `fire_frequency` — Frequência da Área Queimada
- Asset: `mapbiomas_fire_collection5_fire_frequency_v1`
- Bandas: `fire_frequency_1985_2025`
- `bands_slice: [0, 41]`
- Visualização: `fire_col5_frequency` (41 cores, 0-40)
- Valores: 0-41 (número de vezes queimado no período)

### 8. `year_last_fire` — Ano da Última Ocorrência de Fogo
- Asset: `mapbiomas_fire_collection5_year_last_fire_v1`
- Bandas: `classification_1986` até `classification_2026` (41 bandas)
- **Atenção:** Banda `classification_1986` contém dados do último fogo até 1986, etc.
- Visualização: `fire_col5_year_last_fire` (42 cores, 1985-2025)
- Valores: ano da última queimada (1985-2025)

### 9. `time_after_fire` — Tempo desde a Última Ocorrência de Fogo
- Asset: `mapbiomas_fire_collection5_time_after_fire_v1`
- Bandas: `classification_1986` até `classification_2026` (41 bandas)
- Visualização: `fire_col5_time_after_fire` (42 cores, 0-41)
- Valores: anos desde o último fogo (0 = queimou este ano, 41 = nunca queimou)

## Referências Oficiais

Pasta: `referencia_mbfire_col5/` (14 arquivos)

| Arquivo | Conteúdo |
|---------|----------|
| `codigo de legenda.txt` | Doc completo PT/EN: assets, bandas, valores |
| `MapBiomas-Fogo-Legenda-Col5.xlsx` | Planilha oficial completa |
| `legenda_fogo_mensal.csv` | 12 meses + cores hex |
| `legenda_fogo_frequencia.csv` | 41 valores (1-40 vezes) + cores |
| `legenda_ultimo_fogo.csv` | 41 anos (1985-2025) + cores |
| `legenda_time_after_fire.csv` | 42 valores (0-41 anos) + cores |
| `legenda_fogo_tamanho.csv` | 8 classes de tamanho + cores |
| `legenda_accumulated_total_burned.csv` | Acumulado total + #E84C3B |
| `legenda_annual_total_burned.csv` | Anual total + #E84C3B |
| `legenda_accumulated_per_class.csv` | Acumulado por classe LULC |
| `legenda_annual_per_class.csv` | Anual por classe LULC |
| `legenda_accumulated_nat_athropic.csv` | Natural/Antrópico |
| `legenda_annual_nat_athropic.csv` | Natural/Antrópico |
| `inteface_estatisiticas_col5.js.txt` | Script GEE para estatísticas |

## Verificações Necessárias (Fase 2 — Ajuste Visual)

### 1. Correspondência de paletas
- [ ] `fire_col5_monthly`: paleta do viz.yaml bate com `legenda_fogo_mensal.csv`?
- [ ] `fire_col5_frequency`: paleta bate com `legenda_fogo_frequencia.csv`?
- [ ] `fire_col5_year_last_fire`: paleta bate com `legenda_ultimo_fogo.csv`?
- [ ] `fire_col5_time_after_fire`: paleta bate com `legenda_time_after_fire.csv`?
- [ ] `scar_size_range`: paleta bate com `legenda_fogo_tamanho.csv`?

### 2. Decodificação de valores mensal
- O asset `monthly_burned` tem pixel = mês × 100 + cobertura
- O viz.yaml atual `fire_col5_monthly` tem `min: 0, max: 12`
- O GEE precisa receber os valores decodificados. Como?
  - Opção A: Fazer remap via expression no EEDownloader
  - Opção B: Ajustar o range para 0-1200 e usar paleta expandida
  - Opção C: Criar um processor EE para decodificar

### 3. Band naming para year_last_fire/time_after_fire
- Bandas `classification_1986` a `classification_2026` — 41 bandas
- Nomes não contêm o ano do dado, mas o ano da classificação
- O label automático do pipeline pode exibir "1986" em vez do período real
- Verificar se precisa de ajuste no label_map

### 4. Produtos com bandas multi-valor (accumulated, frequency)
- `accumulated_burned`, `accumulated_burned_coverage`, `fire_frequency`
- Têm `bands_slice: [0, 41]` — fatiar 41 bandas
- Bandas com nome range (`fire_accumulated_1985_2025`) — o label vai mostrar "1985_2025"
- Verificar se label automático faz sentido

### 5. discrete_labels
- `scar_size_range`: precisa de discrete_labels com as 8 classes de tamanho
- `fire_col5_monthly`: idealmente discrete com nomes dos meses
- Verificar se FrameProcessor renderiza corretamente com 13+ classes discretas

### 6. Preencher visualization_reference.yaml
- Adicionar entradas para `fire_col5_monthly`, `fire_col5_frequency`, `fire_col5_year_last_fire`, `fire_col5_time_after_fire`, `fire_col5_coverage_total`

### 7. Atualizar visibility.json
- Adicionar `brasil_fire_col5` com visibilidade true para todos os produtos

## Plano de Teste (DF primeiro)

1. Criar `run_fire_col5_test.py` similar a `run_pipeline_df.py`
2. Rodar com `fire_frequency` (mais simples: single-band, 0-40)
3. Rodar com `monthly_burned` (verificar decodificação mês)
4. Rodar com `year_last_fire` (verificar labels)
5. Inspecionar frames e GIFs
6. Ajustar parâmetros conforme necessário
7. Expandir para batch completo

## Batch Fire Col 5 (planejado)

Produtos: 9
Territórios iniciais: `df`, `amazonia`, `cerrado`, `caatinga`, `pantanal`, `mata_atlantica`, `pampa`, `biomas` (8)
Total: 72 combinações
Estimativa: ~1-2 horas com 6 workers
