---
tags: [visualization, config]
aliases: [Visualização, Paletas, Legendas]
date: 2026-06-01
---

[[datasets]] | [[fire-col5]] | [[config-system]]

# Sistema de Visualização

## Estrutura de uma Visualização

```yaml
<viz_key>:
  name: "Nome legível"
  min: 0                     # Valor mínimo do range
  max: 40                    # Valor máximo
  cmap_type: "sequential"    # sequential | categorical | binary | diverging
  palette:                   # Lista de cores hex
    - "fdfdfd"
    - "#ff0000"
    - ...
  label: "Rótulo da legenda"
  unit: ""                   # Unidade (opcional)
  discrete_labels:           # Labels para cada valor (opcional, categorical)
    - "Classe A"
    - "Classe B"
  legend_type: "discrete"    # discrete | continuous (metadata)
  colorbar_ticks: [...]      # Ticks da barra de cores
  used_by: [...]             # Datasets que usam esta visualização
```

## Tipos de Color Map (cmap_type)

| Tipo | Comportamento | Legenda |
|------|--------------|---------|
| `sequential` | Gradiente linear entre min e max | Barra contínua com ticks |
| `categorical` | Cores discretas por classe | Caixas coloridas com labels |
| `binary` | 2 cores (0/1) | 2 caixas: "Não X" / "X" |
| `diverging` | Gradiente com ponto central | Barra contínua (similar sequential) |

## Tratamento Especial no FrameProcessor

O `FrameProcessor.add_legend()` e `add_bottom_bar()` tratam:
- `n <= 2` cores → **discreto** (caixas coloridas)
- `cmap_type == "categorical"` → **discreto**
- Caso contrário → **contínuo** (barra de gradiente)

Para discreto, se `n == 2` e `min=0, max=1`:
- Gera labels automáticas: "Não queimado" / "Queimado"

Para contínuo:
- Barra horizontal com gradiente
- Até 6 ticks com valores

## Visualizações Fire Col 5

| Viz Key | Tipo | Min | Max | Cores | Label |
|---------|------|-----|-----|-------|-------|
| `fire` | binary | 0 | 1 | 2 (#fdfdfd, #800000) | — |
| `fire_col5_coverage_total` | binary | 0 | 1 | 2 (#fff, #E84C3B) | "Pixel queimado" |
| `fire_col5_monthly` | sequential | 0 | 12 | 13 (branco + 12 meses) | "Mês de queimada" |
| `scar_size_range` | sequential | 0 | 10 | 11 tons marrom/dourado | — |
| `fire_col5_frequency` | sequential | 0 | 40 | 41 tons amarelo→preto | "Frequência de queimadas" |
| `fire_col5_year_last_fire` | sequential | 1985 | 2025 | 42 tons azul→vermelho | "Ano" |
| `fire_col5_time_after_fire` | sequential | 0 | 41 | 42 tons vermelho→azul | "Anos desde o último fogo" |

### Paleta `fire_col5_monthly`

```
 0 = #fdfdfd (sem fogo)
 1 = #a900ff (Janeiro)
 2 = #6f02ff (Fevereiro)
 3 = #020aff (Março)
 4 = #0675ff (Abril)
 5 = #06ffff (Maio)
 6 = #ffee00 (Junho)
 7 = #ff7700 (Julho)
 8 = #ff0800 (Agosto)
 9 = #c20202 (Setembro)
10 = #8b0000 (Outubro)
11 = #0aa602 (Novembro)
12 = #83f27e (Dezembro)
```

**Atenção:** No asset original o valor do pixel é o mês multiplicado por 100 + valor de Uso e Cobertura. O valor precisa ser decodificado (div 100) para obter o mês.

### Paleta `fire_col5_frequency`

41 cores do branco (#fdfdfd) passando por amarelos, laranjas, vermelhos até preto (#040101). Uma cor por valor de frequência (1-40).

### Paleta `fire_col5_year_last_fire`

42 cores: azul (#010079) = 1985 (mais antigo) → verde → amarelo → laranja → vermelho (#750000) = 2025 (mais recente).

### Paleta `fire_col5_time_after_fire`

42 cores: vermelho (#750000) = 0 anos (fogo recente) → laranja → amarelo → verde → azul (#010079) = 41 anos (sem fogo há muito tempo). Inverso da year_last_fire.

## Visualizações Degradação Col 10.1

Ver `visualization_col101.yaml` para overrides específicos. Principais:

| Viz Key | Tipo | Range | Cores |
|---------|------|-------|-------|
| `edge_area_col101` | categorical | 0-8 | 9 cores |
| `edge_age_col101` | sequential | 0-40 | verde→vermelho |
| `patch_size_continuous` | sequential | 0-10000 | gradiente |
| `patch_size_fragments` | categorical | 0-10 | 11 cores |
| `patch_size_massifs` | categorical | 0-10 | 11 cores |
| `morphology` | categorical | 0-6 | 7 cores |
| `secondary_vegetation_age` | sequential | 0-40 | verde limão |
| `secondary_vegetation_coverage` | categorical | 0-62 | 63 cores |
| `frequency_col101` | sequential | 0-40 | amarelo→escuro |
| `fire_age` | sequential | 0-40 | vermelho→azul |
| `canopy_disturbance` | categorical | 0-12 | 13 cores |
| `logging` | categorical | 0-1 | 2 cores |
| `natural_coverage` | categorical | 0-2 | 3 cores |
| `burned_at_least_once` | categorical | 0-4 | 5 cores |
| `random` | random | 0-1 | aleatório por patch_id |

## Legendas de Referência

As legendas oficiais do MapBiomas estão em `referencia_mbfire_col5/` (14 arquivos):
- `legenda_fogo_mensal.csv` — 12 meses + cores
- `legenda_fogo_frequencia.csv` — 41 valores de frequência
- `legenda_ultimo_fogo.csv` — 41 anos
- `legenda_time_after_fire.csv` — 42 valores
- `legenda_fogo_tamanho.csv` — 8 classes de tamanho de cicatriz
- `legenda_accumulated_total_burned.csv` / `_per_class.csv` / `_nat_athropic.csv`
- `legenda_annual_total_burned.csv` / `_per_class.csv` / `_nat_athropic.csv`

As paletas no `visualization.yaml` devem corresponder às legendas oficiais.
