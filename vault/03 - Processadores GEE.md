# Processadores GEE (`ee_transforms.py`)

## PROCESSOR_REGISTRY

44 funções server-side que decodificam a codificação de pixels MapBiomas.
Cada função recebe uma `ee.Image`, aplica transformações, e retorna uma
`ee.Image` pronta para visualização.

---

## Categorias de Processadores

### 1. Decodificadores de Produto Composto

Produtos MapBiomas frequentemente codificam múltiplas informações em um
único valor de pixel (ex: mês × 100 + classe LULC).

| Processor | Produto | Decodificação |
|---|---|---|
| `decode_monthly_burned` | Monthly burned | `pixel % 100 → month`, `floor(pixel / 100) → lulc_class` |
| `decode_fire_frequency` | Fire frequency | Extrai frequência de pixel codificado |
| `decode_fire_age` | Fire age | Extrai idade do fogo |
| `decode_edge_area` | Edge area | Classifica borda de fragmento |

### 2. Reclassificadores de Cobertura (5 níveis)

Hierarquia de agregação LULC usada em produtos de cobertura queimada:

| Nível | Nome | Agregação |
|---|---|---|
| Nível 0 | Original | Classes LULC completas (29 classes) |
| Nível 1 | Natural/Antrópico | 2 classes |
| Nível 2 | Floresta / Não-Floresta / Agro | 6-8 classes |
| Nível 3 | Subcategorias | 12-15 classes |
| Nível 4 | Detalhado | 20+ classes |

Processadores: `coverage_level_0` a `coverage_level_4`.

### 3. Processadores de Degradação

| Processor | Descrição |
|---|---|
| `degradation_fire_frequency` | Frequência de fogo em vegetação nativa |
| `degradation_fire_age` | Idade do último fogo |
| `degradation_edge_area` | Área de borda de fragmento |
| `degradation_edge_age` | Idade da borda |
| `degradation_patch_size` | Tamanho do fragmento |
| `degradation_patch_id` | ID único do fragmento |
| `degradation_isolation_100ha` | Isolamento (buffer 100ha) |
| `degradation_isolation_500ha` | Isolamento (buffer 500ha) |
| `degradation_isolation_1000ha` | Isolamento (buffer 1000ha) |
| `degradation_landscape_morphology` | Morfologia da paisagem |
| `degradation_logging` | Extração seletiva de madeira |
| `degradation_canopy_disturbance` | Perturbação de dossel |
| `degradation_native_vegetation_mask` | Máscara de vegetação nativa |
| `degradation_secondary_vegetation_age` | Idade da vegetação secundária |

### 4. Processadores de Fogo

| Processor | Descrição |
|---|---|
| `fire_severity` | Severidade potencial (ΔNBR) |
| `fire_return_interval` | Intervalo de retorno do fogo |
| `fire_scar_size` | Tamanho de cicatriz |
| `fire_frequency_decode` | Frequência de área queimada |
| `fire_last_year` | Ano do último fogo |
| `fire_time_after` | Tempo desde o último fogo |
| `fire_accumulated` | Área queimada acumulada |
| `fire_monthly_decode` | Mês da queimada |

### 5. Processadores Temporais

| Processor | Descrição |
|---|---|
| `cummax_iterator` | Itera sobre bandas aplicando máximo cumulativo |
| `nbr_mosaic_builder` | Constrói mosaico NBR para cálculo de severidade |

### 6. Processadores Específicos

| Processor | Descrição |
|---|---|
| `pasture_quality` | Qualidade de pastagem |
| `pasture_vigor` | Vigor de pastagem |
| `irrigation_systems` | Sistemas de irrigação |
| `mining_substances` | Substâncias minerais |
| `urban_risk` | Risco urbano |
| `water_bodies` | Corpos d'água |
| `soil_carbon` | Carbono orgânico no solo |
| `soil_texture` | Classes texturais |

---

## Por que isso importa para o SDK e Skills

1. **Documentação viva de pixel encoding**: Cada processor é a especificação exata de como interpretar valores de pixel MapBiomas. Isso é o que falta nas skills atuais.

2. **Código GEE real e testado**: Os processors são funções que rodam no GEE, não descrições textuais. Podem ser usados como exemplos nas skills ou como funções utilitárias no SDK.

3. **Convenções de nomenclatura**: Os nomes dos processors revelam padrões: `{theme}_{operation}`, `decode_{product}`, `{tema}_level_{n}`.

4. **Reuso entre produtos**: Processors de cobertura (5 níveis) são reusados por múltiplos produtos de fogo e degradação.

## Conexões

- [[01 - Arquitetura do Pipeline]] — Onde os processors são chamados
- [[04 - Licoes para o SDK]] — Como absorver os processors
- [[06 - Licoes para as Skills]] — Como usar processors nos exemplos de código
