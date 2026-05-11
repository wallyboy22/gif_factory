# IPAM GIF Factory - Análise & Plano de Refatoração

## 📊 ANÁLISE DO CÓDIGO ATUAL

### Problemas Identificados

| Problema | Impacto | Exemplo |
|----------|---------|---------|
| **Dados espalhados** | Alto custo para adicionar novos datasets | 40+ variáveis globais de imagens |
| **Parâmetros visuais gigantes** | Difícil encontrar/editar cores e ranges | `visParams` com 15+ chaves complexas |
| **Loops aninhados** | Lógica confusa, difícil de debugar | Download + GIF geração misturados |
| **Sem versionamento de dados** | Perder track de qual asset usar | 3-4 versões do integration (COL9, COL10) |
| **Sem catálogo público** | Usuários não sabem o que existe | 30+ produtos comentados e ativos |
| **Sem cache** | Reprocessar tudo a cada run | 2-3 horas por execução |
| **Sem interface de vitrine** | Produtos invisíveis | Só vê em Google Drive |

### Arquitetura Atual (Problema)

```
Notebook Linear
├── Célula 1: Auth (OK)
├── Célula 2: Paths (OK)
├── Célula 3a: Dados (eeObjects) ❌ MISTURADO
│   ├── 40+ variáveis globais
│   ├── Sem organização
│   └── Duplicação
├── Célula 3b: Config visual ❌ ACOPLADO
│   └── Dicionário de 500+ linhas
├── Célula 3c: Lista de datasets ❌ HARDCODED
│   └── Comentar/descomentar para ativar
├── Célula 4: Territories ❌ DUPLICADO
│   └── Código comentado 10x
├── Célula 5: Functions (OK-ish)
├── Célula 6: Loop Frames ❌ MONOLÍTICO
└── Célula 7: Loop GIFs ❌ DEPENDÊNCIA OCULTA
```

---

## 🔧 GAPS CORRIGIDOS (v2 — pós-revisão)

> Estes itens foram identificados em revisão e estão integrados nas tasks correspondentes.

### Gap 1 — `get_territory_name()` ausente em `TerritoryManager`
`processing/pipeline.py` chama `self.territory_manager.get_territory_name(territory_type, territory_id)`, mas o método nunca foi definido. Incluído na **Task 2.3**.

### Gap 2 — `soc` é `ImageCollection`, não `Image`
O asset de Carbono Orgânico do Solo é uma `ImageCollection` que precisa de `.mosaic()`. O `EERegistry` precisa checar o campo `asset_type: image_collection` no YAML. Incluído nas **Tasks 1.2 e 2.1**.

### Gap 3 — Produtos de Degradação são composições dinâmicas
Produtos como `edge_area` e `fragment_size` são calculados via `.blend()` de múltiplos assets — não têm `asset_id` único. O plano usa `processor: "edge_area"` no YAML, mas a implementação estava ausente. Incluído na **Task 2.1b** (novo arquivo `data/ee_transforms.py`).

### Gap 4 — Monitor do Fogo usa lógica de iteração sobre `ImageCollection`
Variáveis como `monitor_monthly` e `monitor_monthly_accumulated` requerem iteração temporal customizada. Estão fora do escopo inicial: marcadas como `status: em_desenvolvimento` no YAML.

### Gap 5 — `only_coverage()` sem destino na arquitetura nova
Função de filtro por classe de cobertura movida para `data/ee_transforms.py` (Task 2.1b).

### Gaps Menores Corrigidos
- Ordenação dos frames por nome antes de criar GIF (Task 2.5)
- `__init__.py` em todos os pacotes (Task 1.1)
- `requirements.txt` preenchido (Task 1.6)
- Paleta `frequency_paraguay` completa no YAML (Task 1.3)
- Fluxo de autenticação EE + Drive no `main.py` (Task 4.1)

---

## 🎯 ARQUITETURA PROPOSTA

### Separação em Camadas

```
FABRICA DE GIFS/               ← pasta local do projeto
├── 📁 config/
│   ├── datasets.yaml          # DADOS: Catálogo de produtos
│   ├── territories.yaml       # DADOS: Geometrias disponíveis
│   ├── visualization.yaml     # DADOS: Parâmetros visuais
│   └── paths.yaml             # CONFIG: Caminhos, saída local e EE
│
├── 📁 data/
│   ├── __init__.py
│   ├── ee_registry.py         # DATA LAYER: Abstrair acesso a EE
│   ├── ee_transforms.py       # DATA LAYER: Composições dinâmicas (degradação, monitor)
│   ├── catalog.py             # DATA LAYER: Gerenciar datasets
│   └── territory_manager.py   # DATA LAYER: Gerenciar geometrias
│
├── 📁 processing/
│   ├── __init__.py
│   ├── image_downloader.py    # LOGIC: Download de imagens
│   ├── gif_generator.py       # LOGIC: Criar GIFs (com ordenação)
│   ├── frame_processor.py     # LOGIC: Processar frames
│   └── pipeline.py            # LOGIC: Orquestração
│
├── 📁 interface/
│   ├── __init__.py
│   ├── dashboard.py           # UI: Streamlit (localhost:8501)
│   ├── gallery.html           # UI: Vitrine HTML estática
│   └── api.py                 # UI: REST API Flask (localhost:5000)
│
├── 📁 output/                 # GIFs e frames gerados localmente
├── 📁 cache/
│   └── metadata.json
├── 📁 notebooks/
│   ├── legacy_notebook.ipynb
│   └── refactored_notebook.ipynb
│
├── main.py                    # Entry point CLI
├── requirements.txt           # Dependências Python
└── run_local.sh / run_local.bat  # Script de inicialização local
```

---

## 🏗️ CAMADAS EXPLICADAS

### 1️⃣ DATA LAYER (Configuração)

**Objetivo:** Todos os dados em arquivos, nenhum hardcode

#### `config/datasets.yaml`
```yaml
datasets:
  
  # BRASIL - FOGO
  brasil_fire:
    category: "Fire - Brasil"
    description: "MapBiomas Fire Collection 3"
    products:
      - name: "Annual Burned"
        asset: "projects/mapbiomas-public/assets/brazil/fire/collection3/..."
        type: "annual"
        bands: 39
        viz_key: "fire"
      
      - name: "Fire Frequency"
        asset: "projects/mapbiomas-public/assets/brazil/fire/collection3/..."
        type: "frequency"
        bands: 39
        viz_key: "frequency"
  
  # PARAGUAI - FOGO
  paraguay_fire:
    category: "Fire - Paraguay"
    products:
      - name: "Annual Burned"
        asset: "projects/mapbiomas-paraguay/assets/FIRE/..."
        type: "annual"
        bands: 26
        viz_key: "fire"

  # BRASIL - USO DO SOLO
  brasil_lulc:
    category: "Land Use/Cover - Brasil"
    products:
      - name: "Col9 Integration"
        asset: "projects/mapbiomas-public/assets/brazil/lulc/collection9/..."
        version: 9
        viz_key: "lulc"

  # BRASIL - DEGRADAÇÃO
  brasil_degradation:
    category: "Degradation - Brasil"
    products:
      - name: "Edge Area (30-100m)"
        asset: "EXPRESSION_BASED"  # Para composições complexas
        processor: "edge_area"
        viz_key: "edge_area"
```

#### `config/visualization.yaml`
```yaml
visualizations:
  fire:
    min: 0
    max: 1
    palette: ["fdfdfd", "800000"]
    label: "Queimado / Não Queimado"
  
  frequency:
    min: 0
    max: 11
    palette: ["fdfdfd", "faf3cd", "fce68d", ..., "080202"]
    label: "Frequência de Fogo (1985-2024)"
  
  lulc:
    min: 0
    max: 62
    palette: ["#ffffff", "#32a65e", ...]
    label: "Uso e Cobertura do Solo"
  
  edge_area:
    min: 0
    max: 9
    palette: ["#55604B", ...]
    label: "Proximidade de Borda (m)"
```

#### `config/territories.yaml`
```yaml
territories:
  
  # NÍVEL PAÍS
  countries:
    brasil:
      name: "Brasil"
      source: "FAO/GAUL/2015/level0"
      filter: {ADM0_NAME: "Brazil"}
    
    paraguay:
      name: "Paraguai"
      source: "FAO/GAUL/2015/level0"
      filter: {ADM0_NAME: "Paraguay"}
  
  # NÍVEL BIOMA (BRASIL)
  biomes:
    amazonia:
      name: "Amazônia"
      source: "projects/mapbiomas-workspace/AUXILIAR/biomas_IBGE_250mil"
      filter: {Bioma: "Amazônia"}
    
    cerrado:
      name: "Cerrado"
      source: "projects/mapbiomas-workspace/AUXILIAR/biomas_IBGE_250mil"
      filter: {Bioma: "Cerrado"}
  
  # NÍVEL ESTADO (BRASIL)
  states:
    acre:
      name: "Acre"
      source: "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
      filter: {NM_ESTADO: "ACRE"}
    
    amazonas:
      name: "Amazonas"
      source: "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
      filter: {NM_ESTADO: "AMAZONAS"}
```

### 2️⃣ PROCESSING LAYER (Lógica)

#### `processing/pipeline.py` - Orquestração
```python
class GIFPipeline:
    def __init__(self, catalog, territory_manager):
        self.catalog = catalog
        self.territory_manager = territory_manager
    
    def generate_gif(self, dataset_name, territory_name):
        """Pipeline limpo de 3 passos"""
        # Passo 1: Download frames
        images = self.downloader.download(dataset_name, territory_name)
        
        # Passo 2: Processar frames (redimensionar, adicionar texto)
        processed = self.processor.process_frames(images)
        
        # Passo 3: Criar GIF
        gif_path = self.generator.create_gif(processed, dataset_name)
        
        return gif_path
```

#### `processing/frame_processor.py` - Processamento
```python
class FrameProcessor:
    def add_year_label(self, image_path, year):
        """Adicionar ano no topo"""
        # Lógica limpa
        pass
    
    def resize_batch(self, images, target_height):
        """Redimensionar mantendo aspecto"""
        pass
```

### 3️⃣ INTERFACE LAYER (Vitrine)

#### `interface/dashboard.py` - Streamlit
```python
import streamlit as st
from data.catalog import DatasetCatalog
from processing.pipeline import GIFPipeline

# Inicializar
catalog = DatasetCatalog.from_yaml('config/datasets.yaml')
territories = TerritoryManager.from_yaml('config/territories.yaml')

# Sidebar: Seleção
st.sidebar.title("🎬 GIF Factory")

selected_category = st.sidebar.selectbox(
    "Categoria",
    catalog.get_categories()
)

selected_dataset = st.sidebar.selectbox(
    "Dataset",
    catalog.get_datasets_by_category(selected_category)
)

selected_territory = st.sidebar.selectbox(
    "Território",
    territories.list_territories()
)

# Main: Visualização
if st.button("Gerar GIF"):
    with st.spinner("Processando..."):
        gif_path = pipeline.generate_gif(selected_dataset, selected_territory)
        st.video(gif_path)
        st.success("✅ GIF gerado!")

# Gallery: Mostrar já existentes
st.markdown("## 📁 Galeria")
for gif in get_generated_gifs():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.video(gif['path'])
    with col2:
        st.info(f"Dataset: {gif['name']}")
```

#### `interface/gallery.html` - Vitrine Web Pura
```html
<!DOCTYPE html>
<html>
<head>
    <title>IPAM GIF Factory - Galeria</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <nav class="sidebar">
        <h2>Categorias</h2>
        <div id="categories"></div>
    </nav>
    
    <main class="gallery">
        <h1>📊 GIFs Disponíveis</h1>
        <div class="filter-bar">
            <input type="text" placeholder="Buscar...">
            <select id="territory-filter">
                <option>Todos os territórios</option>
            </select>
        </div>
        <div class="grid" id="gif-grid"></div>
    </main>
</body>
</html>
```

---

## 📋 COMPARAÇÃO ANTES vs DEPOIS

| Aspecto | ANTES | DEPOIS |
|---------|-------|--------|
| **Adicionar novo dataset** | Comentar/descomentar em 3 células | Adicionar 5 linhas em `datasets.yaml` |
| **Mudar cor de visualização** | Editar dicionário de 500 linhas | Editar 1 valor em `visualization.yaml` |
| **Adicionar novo território** | Duplicar 10 linhas de código | Adicionar entrada em `territories.yaml` |
| **Reutilizar funções** | Difícil (acopladas ao notebook) | Fácil (módulos independentes) |
| **Visualizar produtos** | Ir ao Google Drive | Dashboard web interativo |
| **Versionar mudanças** | Controlar notebook inteiro | Controlar só os configs + mudanças |
| **Debugar erro** | Procurar em 1000 linhas | Erro traceback aponta módulo exato |
| **Tempo de adicionar feature** | 2-3 horas | 15-30 minutos |

---

## 🔄 FLUXO DE USO APÓS REFATORAÇÃO

### Caso de Uso 1: Adicionar novo dataset
```bash
# 1. Adicionar em datasets.yaml (2 min)
datasets:
  novo_produto:
    products:
      - name: "Novo"
        asset: "projects/..."

# 2. Adicionar em visualization.yaml (2 min)
visualizations:
  novo_viz:
    palette: [...]

# 3. Usar no dashboard (automático!)
```

### Caso de Uso 2: Adicionar novo território
```bash
# 1. Adicionar em territories.yaml (2 min)
territories:
  countries:
    guyana:
      name: "Guiana"
      source: "FAO/GAUL/2015/level0"

# 2. Pronto! Aparece no dropdown do dashboard
```

### Caso de Uso 3: Gerar GIF via CLI
```bash
python main.py \
  --dataset "paraguay_fire.Annual Burned" \
  --territory "paraguay" \
  --output "./output/"
```

---

## 🎨 Interface de Vitrine (Mockup)

```
┌─────────────────────────────────────────────────────┐
│  🌍 IPAM GIF Factory                        🔍 🌙  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  CATEGORIAS            PRODUTOS DISPONÍVEIS         │
│  ┌─────────────────┐   ┌──────────────────┐        │
│  │ 🔥 Fogo         │   │ 🎬 Paraguay      │        │
│  │ 📊 Uso Solo     │   │    Annual Burned │        │
│  │ 🌳 Degradação   │   │    📅 2024       │        │
│  │ 💧 Hidrologia   │   └──────────────────┘        │
│  └─────────────────┘                               │
│                     ┌──────────────────┐            │
│                     │ 🎬 Brasil        │            │
│                     │    Cerrado Fogo  │            │
│                     │    📅 2023       │            │
│                     └──────────────────┘            │
│
│  GIF SELECIONADO:                                   │
│  ┌─────────────────────────────────────┐           │
│  │                                     │           │
│  │     [GIF ANIMATION PLAYING]         │  ⏯️  ↻   │
│  │                                     │           │
│  └─────────────────────────────────────┘           │
│                                                     │
│  📥 Download  | 🔗 Compartilhar | 📋 Metadados    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## ✨ Benefícios da Refatoração

- ✅ **Escalabilidade**: Adicionar dados sem tocar código
- ✅ **Manutenção**: Cada camada tem responsabilidade clara
- ✅ **Reutilização**: Funções podem ser chamadas de CLI, API, UI
- ✅ **Versionamento**: Controlar configs e código separadamente
- ✅ **Visibilidade**: Catálogo público dos produtos
- ✅ **Performance**: Cache e processamento inteligente
- ✅ **Usabilidade**: Interface para não-programadores
- ✅ **Colaboração**: Fácil para outra IA implementar features

---

## 💻 DESENVOLVIMENTO LOCAL (Localhost)

### Objetivo
Rodar o projeto **100% localmente** na pasta `FABRICA DE GIFS`, sem depender de Google Colab ou Drive montado.

### Pré-requisitos
```bash
# Python 3.10+
python --version

# Instalar dependências
pip install -r requirements.txt

# Autenticar Earth Engine (uma vez)
eartheengine authenticate
```

### `config/paths.yaml` — Modo Local
```yaml
paths:
  # Saída local (desenvolvimento)
  local:
    output_dir: "./output/"      # GIFs salvos aqui
    cache_dir: "./cache/"
    logs_dir: "./logs/"
  
  # Google Drive (produção/Colab)
  google_drive:
    output_root: "/content/drive/MyDrive/IPAM FRAMES AND GIFS/"
    create_if_missing: true
  
  earth_engine:
    project_id: "workspace-ipam"
    timeout_seconds: 300
    retry_attempts: 3

runtime:
  mode: "local"   # Trocar para "colab" ao rodar no Colab
```

### Iniciar o Dashboard (Streamlit)
```bash
# Na pasta FABRICA DE GIFS
streamlit run interface/dashboard.py
# → abre http://localhost:8501
```

### Iniciar a API REST (Flask)
```bash
# Na pasta FABRICA DE GIFS
python interface/api.py
# → disponível em http://localhost:5000
```

### Script de inicialização rápida (`run_local.bat` — Windows)
```bat
@echo off
echo === IPAM GIF Factory - Modo Local ===
cd /d "%~dp0"

echo Iniciando API Flask em background...
start "GIF Factory API" python interface/api.py

echo Iniciando Dashboard Streamlit...
streamlit run interface/dashboard.py
```

### Gerar GIF via CLI (sem interface)
```bash
python main.py \
  --dataset brasil_fire_col3 \
  --product annual_burned \
  --territory-type biomes \
  --territory cerrado \
  --output ./output/
```

### Diferenças Local vs Colab

| Aspecto | Local (Windows) | Google Colab |
|---------|-----------------|-------------|
| Saída | `./output/` | Google Drive |
| Auth EE | `earthengine authenticate` (uma vez) | `ee.Authenticate()` por sessão |
| Drive | Não necessário | `drive.mount()` |
| Interface | `localhost:8501` | URL pública do Colab |
| `paths.yaml` | `mode: local` | `mode: colab` |