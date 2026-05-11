# Skill: Adicionar Novo Território

## Objective
Add a new territorial boundary to the system so it becomes available as a clipping region for GIF generation in CLI, Dashboard, and API.

## Steps

### 1. Identify Territory Info
- **Territory ID:** Programmatic key (e.g., `mato_grosso`)
- **Name:** Display name (e.g., "Mato Grosso")
- **Type:** `countries`, `biomes`, `states`, or `regions`
- **Source:** Earth Engine FeatureCollection asset ID
- **Filter:** Filter expression if the asset contains multiple features (e.g., `NM_ESTADO == 'MATO GROSSO'`)
- **Bbox:** Optional bounding box [west, south, east, north] for faster preview

### 2. Edit `config/territories.yaml`
Add entry under the appropriate type:

```yaml
territories:
  states:
    mato_grosso:
      name: "Mato Grosso"
      name_en: "Mato Grosso"
      source: "projects/mapbiomas-workspace/AUXILIAR/estados-2017"
      filter: "NM_ESTADO == 'MATO GROSSO'"
      bbox: [-61.0, -18.0, -50.0, -7.0]
```

### 3. Validate YAML
```bash
python -c "import yaml; yaml.safe_load(open('config/territories.yaml'))"
```

### 4. Test
```bash
python main.py --list-territories
python main.py --dataset brasil_fire_col3 --product annual_burned --territory mato_grosso --output ./output/test/
```

### 5. Verify
- Check that territory appears in list
- Check output GIF is properly clipped
- Check logs

## Notes
- For countries, use `FAO/GAUL/2015/level0` source
- For Brazilian states, use `projects/mapbiomas-workspace/AUXILIAR/estados-2017`
- For Brazilian biomes, use `projects/mapbiomas-workspace/AUXILIAR/biomas_IBGE_250mil`
- Filter syntax: `"FIELD_NAME == 'VALUE'"`
- Multiple filters: `"FIELD1 == 'V1' AND FIELD2 == 'V2'"`
- Always test with a fire dataset first (fastest rendering)
