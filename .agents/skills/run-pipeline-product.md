# Skill: Processar Produto via CLI

## Objetivo
Gerar GIFs, collages e frames para um produto específico via linha de comando.

## Comando Base
```bash
python -m src.ipam_gif_factory.interfaces.cli \
    --generate \
    --dataset <dataset_id> \
    --product <product_id> \
    --territory <territory_id>
```

## Parâmetros

| Parâmetro | Obrigatório | Descrição | Exemplo |
|-----------|-------------|-----------|---------|
| `--dataset` | Sim | ID do dataset | `brasil_degradation_col10_1` |
| `--product` | Sim | ID do produto | `fire_frequency` |
| `--territory` | Sim (default: df) | ID do território | `matopiba_cerrado` |
| `--output` | Não | Diretório de saída | `./output/` |
| `--viz` | Não | Chave de visualização | `frequency_col101` |
| `--max-bands` | Não | Limitar número de bandas | `5` |
| `--cell-height` | Não | Altura das células do grid | `300` |

## Comandos Úteis

### Listar datasets disponíveis
```bash
python -m src.ipam_gif_factory.interfaces.cli --list-datasets
```

### Listar produtos de um dataset
```bash
python -m src.ipam_gif_factory.interfaces.cli --list-products brasil_degradation_col10_1
```

### Listar territórios
```bash
python -m src.ipam_gif_factory.interfaces.cli --list-territories
```

### Listar visualizações
```bash
python -m src.ipam_gif_factory.interfaces.cli --list-viz
```

### Validar configuração
```bash
python -m src.ipam_gif_factory.interfaces.cli --validate
```

### Autenticar Earth Engine
```bash
python -m src.ipam_gif_factory.interfaces.cli --auth
```

## Processar Todos os Produtos Pendentes (Dashboard)
Use o dashboard Streamlit na aba "Dev (Processar)":
1. Selecione os datasets e territórios desejados
2. Clique "Processar Todos" para adicionar todos à fila
3. A fila persiste em `queue.json` — não reseta com F5

## Produtos do Dataset `brasil_degradation_col10_1`

| Produto | Nome | Frames |
|---------|------|--------|
| `fire_frequency` | Frequência do Fogo | 40 |
| `fire_age` | Tempo desde o Último Fogo | 40 |
| `natural_coverage` | Cobertura e Uso da Terra | 40 |
| `burned_natural_coverage` | Cobertura Vegetal em Áreas Queimadas | 40 |
| `burned_at_least_once` | Queimado ao Menos uma Vez | 40 |
| `primary_natural_coverage` | Cobertura Natural Primária | 40 |
| `secondary_vegetation_age` | Idade da Vegetação Secundária | 40 |
| `secondary_vegetation_coverage` | Cobertura da Vegetação Secundária | 40 |
| `edge_area` | Área de Borda | 40 |
| `edge_age` | Idade da Borda | 40 |
| `patch_id` | Número de Fragmentos | 40 |
| `patch_size` | Tamanho do Fragmento | 40 |
| `landscape_morphology` | Morfologia dos Fragmentos | 40 |

## Exemplo Completo
```bash
# Gerar frequência do fogo para MATOPIBA no Cerrado
python -m src.ipam_gif_factory.interfaces.cli \
    --generate \
    --dataset brasil_degradation_col10_1 \
    --product fire_frequency \
    --territory matopiba_cerrado
```

## Saída Esperada
```
output/
└── <dataset_id>/
    └── <product_id>/
        └── <territory_id>/
            ├── <product_id>_<band>_<year>.png      # Frames individuais
            ├── <product_id>_<territory>_collage.png # Grid
            ├── <product_id>_<territory>_0_3s.gif    # GIF animado
            └── metadata_<product_id>.json            # Metadados
```

## Dicas
- Teste sempre com `df` (Distrito Federal) primeiro — é o território mais rápido
- Produtos com 40 frames levam de 3 a 8 minutos cada
- O processamento pode ser monitorado via `status.json`
