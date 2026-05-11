# IPAM GIF Factory 🎬

**Pipeline automatizado para geração de GIFs animados do MapBiomas e dados de degradação via Earth Engine.**

---

## O que é?

A **Fábrica de GIFs do IPAM** (Instituto de Pesquisa Ambiental da Amazônia) é um sistema que transforma **imagens de satélite processadas no Earth Engine** em GIFs animados prontos para comunicação científica, divulgação e análise visual.

Ela nasceu da necessidade de produzir dezenas de GIFs de forma consistente — com mesma escala, legenda, proporção e qualidade — para diferentes **produtos** (frequência do fogo, idade da vegetação secundária, área de borda, etc.) em diferentes **territórios** (biomas, estados, países).

### O que ela resolve?

| Problema | Solução |
|----------|---------|
| Gerar 1 GIF manualmente no Earth Engine é rápido, mas repetir para N produtos × M territórios é inviável | Pipeline **config-driven**: produtos, territórios e visualizações são definidos em YAML |
| Cada GIF fica com escala, tamanho e qualidade diferentes | Pipeline **unificado**: mesma proporção, mesma escala, mesmas cores |
| Difícil saber quanto tempo/gasto cada GIF consumiu | **Métricas embutidas**: timing por fase, file sizes, EECU estimado |
| Sem rastreabilidade de processamento | **Metadata JSON** versionado (v1.1) com parâmetros completos da execução |

---

## Filosofia de Design

1. **Config-driven** — todo produto, território e visualização vive em YAML. Adicionar um novo produto = editar um arquivo.
2. **Pipeline sequencial, sem cópias** — os frames são modificados in-place (escala, margem, cabeçalho) para economizar disco e tempo.
3. **Métricas first-class** — cada execução gera metadata com timing, tamanho dos arquivos, estimativa de EECU (Earth Engine Compute Units) e dimensões dos frames. Isso permite monitorar e otimizar o processo.
4. **Grid horizontal inteligente** — o grid do GIF é calculado dinamicamente (máx 5 linhas, `ceil(n/5)` colunas, mínimo 2, máximo 10) para se adaptar a qualquer número de frames.
5. **Duas linhas de título** — título principal (produto · território) + subtítulo (coleção), tanto no grid quanto nos frames individuais.
6. **IA-First** — todo o código foi desenvolvido com assistência de IA, priorizando clareza e consistência.

---

## Arquitetura

```
src/ipam_gif_factory/
├── config/          # Carregamento de YAML (datasets, territórios, visualizações, paths)
├── core/            # Pipeline principal
│   ├── pipeline.py        # Orquestrador: download → resize → collage → GIF → metadata
│   ├── ee_downloader.py   # Download de thumbnails do Earth Engine
│   ├── ee_transforms.py   # Processadores de imagem EE (decode, build, cummax, etc.)
│   ├── frame_processor.py # Anotação: escala, norte, legenda, cabeçalho, margem
│   └── gif_generator.py   # Criação do grid (collage) e GIF animado
├── interfaces/      # Interfaces de usuário
│   ├── cli.py              # CLI (argparse)
│   ├── dashboard.py         # Dashboard interativo (Streamlit)
│   └── api.py               # API REST (Flask)
└── utils/           # Utilitários (arquivos, etc.)
```

### Fluxo de processamento

```
[1/4] Download dos thumbnails (EE)  →  PNGs individuais
[2/4] Redimensionamento uniforme    →  mesma altura
[3/4] Criação do grid               →  collage PNG
       ├── escala + norte nos frames
       ├── grid horizontal dinâmico
       └── título + legenda no grid
      Cabeçalho + legenda nos frames → frames finais
[4/4] GIF animado + Metadata JSON   →  entrega
```

---

## O que tem atualmente

### Datasets disponíveis

| Categoria | Dataset | Produtos |
|-----------|---------|----------|
| 🔥 Fogo | `brasil_fire_col3` | 12 (frequência, idade, área queimada, etc.) |
| 🔥 Fogo | `paraguay_fire_col1` | 6 |
| 🌳 Uso do Solo | `brasil_lulc_col9` | 7 (integração, pastagem, VS, etc.) |
| 🌳 Uso do Solo | `brasil_lulc_col10` | 5 |
| 🟤 Degradação | `brasil_degradation_col9` | 9 (borda, fragmento, isolamento) |
| 🟤 Degradação | `brasil_degradation_col10_1` | **13** (fogo, cobertura, VS, borda, morfologia) |
| 🌱 Solo | `brasil_soil` | 1 (carbono orgânico) |

### Produtos de Degradação Col10.1 (13)

`fire_frequency` · `fire_age` · `natural_coverage` · `burned_natural_coverage` ·
`burned_at_least_once` · `primary_natural_coverage` · `secondary_vegetation_coverage` ·
`secondary_vegetation_age` · `edge_area` · `edge_age` · `patch_id` · `patch_size` ·
`landscape_morphology`

### Territórios (30+)

Estados (`df`, `ma`, `to`, `ba`, `pi`, `pa`, `mt`, `ms`, `go`, etc.),
Biomas (`amazonia`, `cerrado`, `mata_atlantica`, `pampa`, etc.),
Países (`brasil`, `paraguay`, `bolivia`),
Regiões (`matopiba_cerrado`)

---

## Interfaces

### 1. CLI — Linha de comando

```bash
# Listar tudo
python main.py --list-categories
python main.py --list-datasets
python main.py --list-products brasil_degradation_col10_1
python main.py --list-territories
python main.py --list-viz

# Validar configuração
python main.py --validate

# Gerar um GIF
python main.py --generate \
    --dataset brasil_degradation_col10_1 \
    --product fire_frequency \
    --territory matopiba_cerrado

# Com opções
python main.py --generate \
    --dataset brasil_degradation_col10_1 \
    --product burned_natural_coverage \
    --territory matopiba_cerrado \
    --max-bands 5 \
    --cell-height 400
```

Saída dos arquivos gerados:
```
output/<dataset_id>/<product_id>/<territory_id>/
├── <product_id>_<ano>.png           # frames individuais
├── <product_id>_<territory>_collage.png  # grid
├── <product_id>_<territory>_0_3s.gif     # GIF animado
└── metadata_<product_id>.json            # metadados
```

### 2. Dashboard (Streamlit)

```bash
streamlit run src/ipam_gif_factory/interfaces/dashboard.py
```

Abre em `http://localhost:8501`. Contém:

- **Navegador de produtos** — dataset → produto → visualização
- **Visualização de paletas** — cores em grid
- **Painel de Monitoramento** — histórico de execuções com:
  - Timing por fase (gráfico de barras)
  - EECU estimado por produto
  - Tamanho dos arquivos (GIF, collage, frames)
  - Comparativo entre execuções

### 3. API REST (Flask)

```bash
python src/ipam_gif_factory/interfaces/api.py
```

Abre em `http://localhost:5000`. Endpoints:

| Rota | Descrição |
|------|-----------|
| `GET /` | Info da API |
| `GET /categories` | Listar categorias |
| `GET /datasets?category=degradation` | Listar datasets |
| `GET /datasets/<id>/products` | Listar produtos |
| `GET /datasets/<id>/products/<pid>` | Detalhes do produto |
| `GET /territories?type=states` | Listar territórios |
| `GET /territories/<id>` | Detalhes do território |
| `GET /visualizations` | Listar visualizações |
| `POST /generate` | Agendar geração (JSON body) |

---

## Métricas e Monitoramento

Cada execução do pipeline gera um **metadata JSON** com:

```json
{
  "metadata_version": "1.1",
  "timing": {
    "phases": {
      "download": 214.0,
      "resize": 5.7,
      "collage_prep": 10.8,
      "collage_build": 1.9,
      "collage_labels": 0.9,
      "frame_labels": 17.3,
      "gif_creation": 10.7
    },
    "total_seconds": 266.0,
    "total_formatted": "4m 26s"
  },
  "files": {
    "gif_size_mb": 6.64,
    "collage_size_mb": 2.01,
    "frames_total_mb": 11.79,
    "frames_sizes_mb": { "...": 0.31 }
  },
  "ee_estimate": {
    "frame_dimensions": { "width": 1140, "height": 2350 },
    "pixels_per_frame": 2679000,
    "total_pixels_processed": 107160000,
    "tile_equivalent": 1635.1,
    "estimated_eecu": 2.4527,
    "estimated_eecu_hours": 0.000681
  }
}
```

### O que é EECU?

**Earth Engine Compute Unit (EECU)** é a métrica oficial do Google Earth Engine para medir consumo computacional. 1 EECU equivale aproximadamente a 1 hora de processamento em uma unidade de computação padrão do GEE.

O valor estimado considera:
- **Pixels processados** (dimensão do frame × número de frames)
- **Equivalente em tiles** (cada tile = 256×256 px)
- **Fator de complexidade** do produto (1.0 = simples, 1.5 = moderado, 2.0 = complexo)

---

## Predição de Tempo e Custo (Futuro)

Com o acúmulo de metadados das execuções, pretendemos:

1. **Prever tempo de processamento** baseado em:
   - Número de frames
   - Dimensão dos frames
   - Tipo de produto (simples vs. complexo)
   - Território (área, forma)

2. **Prever custo EECU** por execução

3. **Relatório ambiental** — estimar:
   - Energia consumida (CPU time × TDP)
   - CO₂ equivalente (fator da rede elétrica)
   - Água de resfriamento (cooling do datacenter)

---

## Setup — Como usar

### 1. Pré-requisitos

- **Python 3.10+** — [python.org](https://python.org)
- **Conta Earth Engine** (gratuita) — [signup.earthengine.google.com](https://signup.earthengine.google.com)
- **Git** (opcional, para clonar)

### 2. Ambiente virtual (venv)

**Windows (PowerShell):**
```powershell
# Criar o ambiente virtual
python -m venv .venv

# Ativar
.venv\Scripts\Activate.ps1
```
> Se der erro de permissão, execute antes: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

> Se quiser instalar manualmente: `pip install earthengine-api imageio[pyav] Pillow numpy requests PyYAML streamlit flask flask-cors click opencv-python-headless pytest`

### 4. Autenticar Earth Engine

```bash
python main.py --auth
```
Isso abre o navegador para autorizar o Earth Engine. Use o **mesmo e-mail** da sua conta GEE.

### 5. Rodar os pipelines

**CLI** — gerar um GIF:
```bash
python main.py --generate --dataset brasil_degradation_col10_1 --product fire_frequency --territory matopiba_cerrado
```

**Dashboard** — interface visual (Streamlit):
```bash
streamlit run src/ipam_gif_factory/interfaces/dashboard.py --server.runOnSave true
```
> O `--server.runOnSave true` recarrega automaticamente quando você edita o código.
Abre em: [http://localhost:8501](http://localhost:8501)

**API** — servidor REST (Flask):
```bash
python src/ipam_gif_factory/interfaces/api.py
```
Abre em: [http://localhost:5000](http://localhost:5000)

Testar a API:
```bash
curl http://localhost:5000/datasets
curl http://localhost:5000/categories
```

### 6. Outros comandos úteis

```bash
# Listar categorias de datasets
python main.py --list-categories

# Listar datasets de uma categoria
python main.py --list-datasets degradation

# Listar produtos de um dataset
python main.py --list-products brasil_degradation_col10_1

# Listar territórios disponíveis
python main.py --list-territories

# Listar visualizações (paletas)
python main.py --list-viz

# Validar configuração completa
python main.py --validate

# Filtrar por anos específicos
python main.py --generate --dataset brasil_degradation_col10_1 --product fire_frequency --territory matopiba_cerrado --band-names-filter 2020 2024

# Limitar número de frames (para teste rápido)
python main.py --generate --dataset brasil_degradation_col10_1 --product burned_at_least_once --territory matopiba_cerrado --max-bands 2
```

---

## Roadmap

- [x] Pipeline completo (download → GIF → metadata)
- [x] 13 produtos de degradação Col10.1
- [x] Grid horizontal dinâmico
- [x] Duas linhas de título (produto + coleção)
- [x] Métricas de timing, file sizes e EECU
- [x] CLI, Dashboard (Streamlit) e API (Flask)
- [ ] Painel de monitoramento completo no dashboard
- [ ] Predição de tempo/custo baseada em histórico
- [ ] Relatório ambiental (CO₂, água)
- [ ] Batches inteligentes (priorizar produtos mais rápidos)
- [ ] Suporte a novos datasets e territórios

---

## Licença

IPAM — Instituto de Pesquisa Ambiental da Amazônia
