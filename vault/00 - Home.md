# Fábrica de GIFs — Cofre de Conhecimento

> **Fonte**: `FABRICA DE GIFS/` — pipeline Python de visualização MapBiomas
> **Autor**: Wallace Vieira da Silva / IPAM Amazônia
> **Pacote**: `mapbiomas-data` v2.0.0
> **Analisado em**: 2026-08-01

---

## O que é

Pipeline automatizado que gera GIFs animados a partir de dados MapBiomas
no Google Earth Engine. Baixa séries temporais, aplica cartografia (legendas,
escala, norte), compõe colagens e produz GIFs prontos para comunicação
científica e dashboards públicos.

## Métricas

| Métrica | Valor |
|---|---|
| Datasets | 8 (fire, lulc, degradation, soil, paraguay) |
| Produtos catalogados | 80+ |
| GIFs gerados (jun/2026) | 386 (Degradação Col 10.1) |
| Paletas de cor | 70+ |
| Territórios | 45+ (países, biomas, estados, regiões) |
| Processadores GEE | 44 (decoders de pixel) |
| Linhas de código | ~8.000 (20+ arquivos Python) |
| Config YAML | 600+ linhas (produtos, territórios, visualizações) |

## Por que estudar

Este projeto é o **cliente mais completo de assets GEE do MapBiomas**.
Ele sabe:
- Onde cada produto vive no GEE (asset paths, bandas, coleções)
- Como decodificar pixels MapBiomas (44 funções de transformação)
- Quais as paletas oficiais (70+ com rótulos discretos)
- Quais territórios existem (45+ com FeatureCollections)

Para o SDK, MCP e fórmula de skills, este projeto é a **fonte de verdade
sobre visualização e catálogo de produtos**.

## Índice

| Doc | Descrição |
|---|---|
| [01 — Arquitetura](01%20-%20Arquitetura%20do%20Pipeline.md) | Fluxo de 5 fases, 9 etapas, checkpoint/resume |
| [02 — Configuração](02%20-%20Sistema%20de%20Configuracao.md) | YAMLs: datasets, territórios, visualizações, batches |
| [03 — Processadores GEE](03%20-%20Processadores%20GEE.md) | 44 funções de decodificação de pixel |
| [04 — Lições para o SDK](04%20-%20Licoes%20para%20o%20SDK.md) | 6 padrões absorvíveis pelo mapbiomas-sdk |
| [05 — Lições para o MCP](05%20-%20Licoes%20para%20o%20MCP.md) | 10 ferramentas MCP candidatas |
| [06 — Lições para as Skills](06%20-%20Licoes%20para%20as%20Skills.md) | Catálogo, paletas, territórios, YAML config |
