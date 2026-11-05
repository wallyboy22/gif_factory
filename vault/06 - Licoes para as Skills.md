# Lições para as Skills

## O que a Fábrica de GIFs tem que as skills precisam

---

## Lição 1: Catálogo de produtos é a fonte de verdade

**O que a Fábrica tem:**

80+ produtos catalogados em YAML com TODOS os metadados que uma skill precisa:

| Campo no YAML | Seção da skill |
|---|---|
| `name` | Título da skill + descrição |
| `ee_asset` | Seção 1 — Regra de ouro de nomenclatura |
| `ee_type` | Seção 4 — Estrutura de script (Image vs ImageCollection) |
| `band_pattern` | Seção 2 — Tabela produto → asset → banda |
| `years` | Seção 4 — Período disponível |
| `viz_key` | Seção 3 — Paletas (referência ao módulo de visualização) |
| `processor` | Seção 4 — Código de transformação de pixel |

**Impacto na fórmula v03:**

O `generate_all_skills.py` pode ler o catálogo YAML da Fábrica como
**fonte primária** para a seção 2 (tabela de produtos). Zero trabalho manual.

```python
# v03 — auto_enrich.py com fonte YAML
product = catalog.get("fire", "annual_burned")
entry = ProductEntry(
    name=product.name,
    subtheme=product.id,
    years=product.years,
    band_pattern=product.band_pattern,
    gee_asset_path=product.ee_asset,
    gee_type=product.ee_type,
)
```

**Ação:**
- [ ] `auto_enrich.py` da v03 lê YAML da Fábrica como fonte complementar
- [ ] Mapear `dataset_id + product_id` → campos do `ProductEntry`

---

## Lição 2: Paletas são universais — não duplicar por tema

**O que a Fábrica tem:**

70+ paletas em um único arquivo YAML com rótulos discretos oficiais.
A mesma paleta `fire_monthly` serve para o produto Fogo, para o dashboard
Looker, e para a skill.

**O que a skill atual faz:**

Duplica as paletas no corpo do markdown (`references/legend-colors.md`).
Se a paleta mudar (ex: nova cor para severidade), precisa atualizar N skills.

**O que deveria fazer:**

Referenciar o catálogo central de visualizações. A skill diz "use a paleta
`fire_monthly`" e o leitor (IA ou humano) consulta o catálogo.

```markdown
## 3. Paletas

Consulte o catálogo de visualizações MapBiomas:

| Produto | viz_key |
|---|---|
| Área queimada mensal | `fire_monthly` |
| Severidade | `fire_severity` |
| Frequência | `fire_frequency` |
```

**Ação:**
- [ ] Substituir tabelas de cor inline por referências a `viz_key`
- [ ] O MCP tool `visualization_get` resolve a paleta em tempo real
- [ ] Skill v03: seção 3 vira "Consulte `visualization_get('fire_monthly')`"

---

## Lição 3: Territórios comuns com IDs e bounding boxes

**O que a Fábrica tem:**

45+ territórios com metadados completos: nome, tipo, bbox, fonte GEE, filtro.

**O que a skill atual faz:**

Menciona "biomas, estados, municípios" genericamente. Não lista quais existem.

**O que deveria fazer:**

Incluir uma tabela de territórios comuns com seus IDs e extensão geográfica.
Isso ajuda a IA a sugerir recortes espaciais nos exemplos de código.

```markdown
## Territórios comuns para Map.setCenter()

| Território | Tipo | Map.setCenter() |
|---|---|---|
| Amazônia | Bioma | (-55, -5, 4) |
| Cerrado | Bioma | (-48, -16, 5) |
| MATOPIBA | Região | (-46, -9, 5) |
| Brasil | País | (-53, -14, 4) |
```

**Ação:**
- [ ] Extrair bboxes do `territories/*.yaml` da Fábrica
- [ ] Adicionar seção opcional na skill: "Territórios de referência"

---

## Lição 4: Processadores GEE são exemplos de código reais

**O que a Fábrica tem:**

44 funções GEE que mostram exatamente como decodificar pixels MapBiomas.
São código real, testado, que roda no Earth Engine.

**O que a skill atual faz:**

Descreve a estrutura de script (seção 4) mas não mostra código de
transformação de pixel. Ex: "severidade é baseada em ΔNBR" mas não mostra
como calcular ΔNBR no GEE.

**O que deveria fazer:**

Incluir snippets dos processors como exemplos avançados na seção 4.
Ex: "Para calcular severidade a partir do NBR bruto:"

```javascript
// Cálculo de ΔNBR (usado internamente pelo produto de severidade)
var nbr_pre = preFire.normalizedDifference(['B5', 'B7']);
var nbr_post = postFire.normalizedDifference(['B5', 'B7']);
var dnbr = nbr_pre.subtract(nbr_post);
```

**Ação:**
- [ ] Selecionar os 5-10 processors mais relevantes por tema
- [ ] Incluir como "Exemplos avançados" na seção 4 da skill

---

## Lição 5: YAML é melhor que JSON para config de skill

**O que a Fábrica tem:**

Sistema de configuração YAML com `!include`, deep merge e auto-descoberta.

**O que a skill atual faz:**

Enrichment em JSON (`enrichment/brazil/fire.json`). Funciona, mas não tem
includes (cada tema duplica LULC classes, territórios, etc.).

**O que deveria fazer:**

Migrar de JSON para YAML com `!include`:

```yaml
# enrichment/brazil/fire.yaml
!include ../_partials/gee_assets_fire.yaml
!include ../_partials/palettes_ipam.yaml

products:
  - subtheme: fire_total_burned
    band_pattern: burned_area_{year}
    ...
```

**Ação:**
- [ ] Suporte a YAML no `auto_enrich.py`
- [ ] Criar `enrichment/_partials/` com definições compartilhadas

---

## Lição 6: Coverage levels resolvem o problema LULC nas skills

**O que a Fábrica tem:**

5 níveis de agregação LULC (Nível 0 = 29 classes, Nível 1 = Natural/Antrópico).
Cada produto de cobertura queimada suporta múltiplos níveis.

**O que a skill atual faz:**

Lista as 29 classes LULC completas. Não menciona que existem níveis de
agregação mais simples para análises rápidas.

**O que deveria fazer:**

Documentar os níveis de agregação disponíveis:

```markdown
## Níveis de agregação LULC

| Nível | Classes | Uso |
|---|---|---|
| Nível 0 | 29 classes | Análise detalhada |
| Nível 1 | Natural / Antrópico | Visão geral |
| Nível 2 | 6-8 classes | Agrupamento temático |
```

**Ação:**
- [ ] Documentar coverage levels nas skills de cobertura/fogo
- [ ] Mapear `legend_key` por nível de agregação

---

## Resumo para a v03

| P | Lição | Ação |
|---|---|---|
| **P0** | Catálogo YAML como fonte (L1) | `auto_enrich.py` lê YAML da Fábrica |
| **P0** | Paletas centralizadas (L2) | Substituir inline por `viz_key` |
| **P1** | Territórios com bbox (L3) | Nova seção opcional na skill |
| **P1** | Processors como exemplos (L4) | 5-10 snippets por tema |
| **P2** | YAML > JSON (L5) | Suporte a `!include` no enrichment |
| **P2** | Coverage levels (L6) | Documentar níveis LULC |
